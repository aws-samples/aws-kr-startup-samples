#!/bin/bash

# Milvus on EKS Automated Deployment Script
# This script automates the deployment of Milvus vector database on Amazon EKS

set -e

# Default messaging option
MESSAGING_OPTION="msk"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --messaging)
            MESSAGING_OPTION="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--messaging msk|pulsar]"
            echo ""
            echo "Options:"
            echo "  --messaging msk|pulsar    Choose messaging system (default: msk)"
            echo "  -h, --help               Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validate messaging option
if [[ "$MESSAGING_OPTION" != "msk" && "$MESSAGING_OPTION" != "pulsar" ]]; then
    log_error "Invalid messaging option: $MESSAGING_OPTION. Must be 'msk' or 'pulsar'"
    exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing_tools=()
    
    if ! command -v aws &> /dev/null; then
        missing_tools+=("aws-cli")
    fi
    
    if ! command -v kubectl &> /dev/null; then
        missing_tools+=("kubectl")
    fi
    
    if ! command -v eksctl &> /dev/null; then
        missing_tools+=("eksctl")
    fi
    
    if ! command -v helm &> /dev/null; then
        missing_tools+=("helm")
    fi
    
    if ! command -v openssl &> /dev/null; then
        missing_tools+=("openssl")
    fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_error "Please install the missing tools and try again."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    log_success "All prerequisites met!"
}

# Deploy EKS cluster
deploy_eks() {
    log_info "Creating EKS cluster..."
    
    if eksctl get cluster --name milvus-eks-cluster &> /dev/null; then
        log_warning "EKS cluster 'milvus-eks-cluster' already exists. Skipping creation."
    else
        eksctl create cluster -f infrastructure/eks/eks_cluster.yaml
        log_success "EKS cluster created successfully!"
    fi
    
    # Update kubeconfig
    aws eks update-kubeconfig --region us-east-1 --name milvus-eks-cluster >/dev/null 2>&1
    
    # Set environment variables
    export milvus_cluster_name='milvus-eks-cluster'
    export eks_vpc_id=$(aws eks describe-cluster --name milvus-eks-cluster --query 'cluster.resourcesVpcConfig.vpcId' --output text)
    export eks_subnet_ids=$(aws eks describe-cluster --name milvus-eks-cluster --query 'cluster.resourcesVpcConfig.subnetIds' --output text)
    
    log_info "EKS VPC ID: $eks_vpc_id"
    log_info "EKS Subnet IDs: $eks_subnet_ids"
    
    # Configure storage
    kubectl apply -f infrastructure/eks/gp3_storage_class.yaml >/dev/null 2>&1
    kubectl patch storageclass gp2 -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"false"}}}' >/dev/null 2>&1
    
    log_success "EKS cluster configuration completed!"
}

# Configure S3 and IAM
configure_s3_iam() {
    log_info "Configuring S3 bucket and IAM policies..."
    
    # Create S3 bucket
    export MILVUS_BUCKET_NAME="milvus-bucket-$(openssl rand -hex 12)"
    if aws s3 mb s3://${MILVUS_BUCKET_NAME} >/dev/null 2>&1; then
        log_success "S3 bucket created: $MILVUS_BUCKET_NAME"
    else
        log_error "Failed to create S3 bucket: $MILVUS_BUCKET_NAME"
        exit 1
    fi
    
    # Get AWS account information
    export account_id=$(aws sts get-caller-identity --query 'Account' --output text)
    export caller_arn=$(aws sts get-caller-identity --query 'Arn' --output text)
    
    # Generate IAM policies
    envsubst < infrastructure/s3/milvus-s3-policy-template.json > infrastructure/s3/milvus-s3-policy.json
    envsubst < infrastructure/iam/milvus-iam-policy-template.json > infrastructure/iam/milvus-iam-policy.json
    
    # Create IAM policy for S3 access
    if aws iam get-policy --policy-arn "arn:aws:iam::${account_id}:policy/MilvusS3ReadWrite" >/dev/null 2>&1; then
        log_warning "IAM policy 'MilvusS3ReadWrite' already exists. Skipping creation."
    else
        if aws iam create-policy --policy-name MilvusS3ReadWrite --policy-document file://infrastructure/s3/milvus-s3-policy.json >/dev/null 2>&1; then
            log_success "IAM policy 'MilvusS3ReadWrite' created successfully!"
        else
            log_error "Failed to create IAM policy 'MilvusS3ReadWrite'"
            exit 1
        fi
    fi
    
    # Attach S3 policy to EKS node group role
    log_info "Attaching S3 policy to EKS node group role..."
    export node_role_name=$(aws eks describe-nodegroup --cluster-name milvus-eks-cluster --nodegroup-name milvus-node-group --query 'nodegroup.nodeRole' --output text | cut -d'/' -f2)
    
    if aws iam attach-role-policy --role-name ${node_role_name} --policy-arn "arn:aws:iam::${account_id}:policy/MilvusS3ReadWrite" >/dev/null 2>&1; then
        log_success "S3 policy attached to EKS node group role: $node_role_name"
    else
        log_warning "Failed to attach S3 policy or policy already attached"
    fi
    
    log_info "Using IAM role authentication for S3 access."
}

# Install AWS Load Balancer Controller
install_alb_controller() {
    log_info "Installing AWS Load Balancer Controller..."
    
    helm repo add eks https://aws.github.io/eks-charts >/dev/null 2>&1
    helm repo update >/dev/null 2>&1
    
    if helm list -n kube-system | grep -q aws-load-balancer-controller; then
        log_warning "AWS Load Balancer Controller already installed. Skipping."
    else
        if helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
            -n kube-system \
            --set clusterName=${milvus_cluster_name} \
            --set serviceAccount.create=false \
            --set serviceAccount.name=aws-load-balancer-controller >/dev/null 2>&1; then
            log_success "AWS Load Balancer Controller installed successfully!"
        else
            log_error "Failed to install AWS Load Balancer Controller"
            exit 1
        fi
    fi
    
    # Verify installation
    kubectl wait --for=condition=available --timeout=300s deployment/aws-load-balancer-controller -n kube-system >/dev/null 2>&1
}

# Deploy MSK cluster (only if messaging option is MSK)
deploy_msk() {
    if [[ "$MESSAGING_OPTION" != "msk" ]]; then
        log_info "Skipping MSK deployment (using $MESSAGING_OPTION instead)"
        return 0
    fi
    
    log_info "Creating Amazon MSK cluster..."
    
    # Check if MSK cluster already exists
    if aws kafka list-clusters --cluster-name-filter "milvus-msk-cluster" --query 'ClusterInfoList[0].ClusterArn' --output text | grep -q arn; then
        log_warning "MSK cluster 'milvus-msk-cluster' already exists. Skipping creation."
        export CLUSTER_ARN=$(aws kafka list-clusters --cluster-name-filter "milvus-msk-cluster" --query 'ClusterInfoList[0].ClusterArn' --output text --region us-east-1)
    else
        # Create MSK configuration first
        log_info "Creating MSK configuration with auto.create.topics.enable=true..."
        if aws kafka list-configurations --query 'Configurations[?Name==`milvus-msk-config`].Arn' --output text | grep -q arn; then
            log_warning "MSK configuration 'milvus-msk-config' already exists. Skipping creation."
        else
            # Create base64 encoded server properties
            local server_properties_b64=$(base64 -w 0 infrastructure/msk/msk-custom-config.properties)
            if aws kafka create-configuration \
                --name milvus-msk-config \
                --description "Custom configuration for Milvus MSK cluster with auto topic creation" \
                --kafka-versions "3.9.x" \
                --server-properties "$server_properties_b64" \
                --region us-east-1 >/dev/null 2>&1; then
                log_success "MSK configuration created successfully!"
            else
                log_error "Failed to create MSK configuration"
                exit 1
            fi
        fi
        
        # Get the configuration ARN
        export MSK_CONFIG_ARN=$(aws kafka list-configurations \
            --query 'Configurations[?Name==`milvus-msk-config`].Arn' \
            --output text \
            --region us-east-1)
        log_info "MSK Configuration ARN: $MSK_CONFIG_ARN"
        
        # Create security group
        if aws ec2 describe-security-groups --group-names milvus-msk-sg --region us-east-1 >/dev/null 2>&1; then
            log_warning "Security group 'milvus-msk-sg' already exists. Using existing one."
            export MSK_SECURITY_GROUP_ID=$(aws ec2 describe-security-groups --group-names milvus-msk-sg --query 'SecurityGroups[0].GroupId' --output text --region us-east-1)
        else
            export MSK_SECURITY_GROUP_ID=$(aws ec2 create-security-group \
                --group-name milvus-msk-sg \
                --description "Security group for Milvus MSK cluster" \
                --vpc-id $eks_vpc_id \
                --query 'GroupId' \
                --output text \
                --region us-east-1)
            log_success "Security group created: $MSK_SECURITY_GROUP_ID"
        fi
        
        # Add ingress rules to allow Kafka traffic from EKS nodes
        log_info "Configuring security group rules..."
        
        # Allow Kafka plaintext traffic (port 9092)
        if aws ec2 authorize-security-group-ingress \
            --group-id $MSK_SECURITY_GROUP_ID \
            --protocol tcp \
            --port 9092 \
            --cidr 192.168.0.0/16 \
            --region us-east-1 >/dev/null 2>&1; then
            log_success "Port 9092 rule added successfully"
        else
            log_warning "Port 9092 rule may already exist"
        fi
        
        # Allow Kafka TLS traffic (port 9094) 
        if aws ec2 authorize-security-group-ingress \
            --group-id $MSK_SECURITY_GROUP_ID \
            --protocol tcp \
            --port 9094 \
            --cidr 192.168.0.0/16 \
            --region us-east-1 >/dev/null 2>&1; then
            log_success "Port 9094 rule added successfully"
        else
            log_warning "Port 9094 rule may already exist"
        fi
        
        # Allow Zookeeper traffic (port 2181) - needed for older Kafka versions
        if aws ec2 authorize-security-group-ingress \
            --group-id $MSK_SECURITY_GROUP_ID \
            --protocol tcp \
            --port 2181 \
            --cidr 192.168.0.0/16 \
            --region us-east-1 >/dev/null 2>&1; then
            log_success "Port 2181 rule added successfully"
        else
            log_warning "Port 2181 rule may already exist"
        fi
        
        # Get private subnets
        export PRIVATE_SUBNETS=($(aws eks describe-cluster --name milvus-eks-cluster --query 'cluster.resourcesVpcConfig.subnetIds' --output text))
        export PRIVATE_SUBNET_1=$(aws ec2 describe-subnets --subnet-ids ${PRIVATE_SUBNETS[@]} --query 'Subnets[?Tags[?Key==`kubernetes.io/role/internal-elb`]].SubnetId' --output text | awk '{print $1}')
        export PRIVATE_SUBNET_2=$(aws ec2 describe-subnets --subnet-ids ${PRIVATE_SUBNETS[@]} --query 'Subnets[?Tags[?Key==`kubernetes.io/role/internal-elb`]].SubnetId' --output text | awk '{print $2}')
        
        # Generate MSK configuration
        envsubst < infrastructure/msk/msk-cluster-config-template.json > infrastructure/msk/msk-cluster-config.json
        
        # Create MSK cluster
        if aws kafka create-cluster --cli-input-json file://infrastructure/msk/msk-cluster-config.json --region us-east-1 >/dev/null 2>&1; then
            export CLUSTER_ARN=$(aws kafka list-clusters --cluster-name-filter "milvus-msk-cluster" --query 'ClusterInfoList[0].ClusterArn' --output text --region us-east-1)
            log_success "MSK cluster creation initiated!"
        else
            log_error "Failed to create MSK cluster"
            exit 1
        fi
    fi
    
    # Wait for cluster to be active
    log_info "Waiting for MSK cluster to become active..."
    local retry_count=0
    local max_retries=60  # 30 minutes with 30-second intervals
    
    while [ $retry_count -lt $max_retries ]; do
        STATUS=$(aws kafka describe-cluster --cluster-arn "$CLUSTER_ARN" --query 'ClusterInfo.State' --output text --region us-east-1 2>/dev/null)
        log_info "Current status: $STATUS (attempt $((retry_count + 1))/$max_retries)"
        
        if [ "$STATUS" = "ACTIVE" ]; then
            log_success "MSK cluster is now ACTIVE!"
            break
        elif [ "$STATUS" = "FAILED" ]; then
            log_error "MSK cluster creation failed!"
            exit 1
        fi
        
        retry_count=$((retry_count + 1))
        sleep 30
    done
    
    if [ $retry_count -eq $max_retries ]; then
        log_error "MSK cluster did not become active within the timeout period"
        exit 1
    fi
    
    export BROKER_LIST=$(aws kafka get-bootstrap-brokers --cluster-arn "$CLUSTER_ARN" --query 'BootstrapBrokerString' --output text --region us-east-1)
    log_info "BROKER_LIST: $BROKER_LIST"
}

# Deploy Milvus
deploy_milvus() {
    log_info "Deploying Milvus with $MESSAGING_OPTION messaging..."
    
    # Create Milvus namespace if it doesn't exist
    if ! kubectl get namespace milvus >/dev/null 2>&1; then
        log_info "Creating Milvus namespace..."
        kubectl create namespace milvus >/dev/null 2>&1
        log_success "Milvus namespace created!"
    else
        log_warning "Milvus namespace already exists. Skipping creation."
    fi
    
    log_info "Using IAM role authentication for S3 access."
    
    # Choose appropriate template and generate configuration based on messaging option
    if [[ "$MESSAGING_OPTION" == "msk" ]]; then
        # Get broker list for MSK
        export BROKER_LIST=$(aws kafka get-bootstrap-brokers --cluster-arn "$CLUSTER_ARN" --query 'BootstrapBrokerString' --output text --region us-east-1)
        log_info "Using MSK Broker List: $BROKER_LIST"
        
        # Generate Milvus configuration from MSK template
        envsubst < infrastructure/milvus/milvus-msk-template.yaml > infrastructure/milvus/milvus.yaml
    else
        # Generate Milvus configuration from Pulsar template
        envsubst < infrastructure/milvus/milvus-pulsar-template.yaml > infrastructure/milvus/milvus.yaml
        log_info "Using embedded Pulsar for messaging"
    fi
    
    # Add Milvus Helm repository
    helm repo add milvus https://zilliztech.github.io/milvus-helm/ >/dev/null 2>&1
    helm repo update >/dev/null 2>&1
    
    # Install Milvus
    if helm list -n milvus | grep -q milvus; then
        log_warning "Milvus already installed. Upgrading..."
        if helm upgrade --namespace milvus -f infrastructure/milvus/milvus.yaml milvus milvus/milvus >/dev/null 2>&1; then
            log_success "Milvus upgraded successfully!"
        else
            log_error "Failed to upgrade Milvus"
            exit 1
        fi
    else
        if helm install --namespace milvus -f infrastructure/milvus/milvus.yaml milvus milvus/milvus >/dev/null 2>&1; then
            log_success "Milvus installed successfully!"
        else
            log_error "Failed to install Milvus"
            exit 1
        fi
    fi
    
    log_success "Milvus deployment completed!"
    
    # Wait for pods to be ready
    log_info "Waiting for Milvus pods to be ready..."
    if kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=milvus -n milvus --timeout=600s >/dev/null 2>&1; then
        log_success "All Milvus pods are ready!"
    else
        log_warning "Some Milvus pods may not be ready yet. Please check with 'kubectl get pods -n milvus'"
    fi
}

# Cleanup function for error handling
cleanup_on_error() {
    log_error "Script encountered an error. Cleaning up..."
    # Add cleanup logic here if needed
    exit 1
}

# Set error trap
trap cleanup_on_error ERR

# Main deployment function
main() {
    # Configure AWS CLI
    aws configure set region us-east-1 >/dev/null 2>&1

    log_info "Starting Milvus on EKS deployment with $MESSAGING_OPTION messaging..."
    
    check_prerequisites
    deploy_eks
    configure_s3_iam
    install_alb_controller
    deploy_msk
    deploy_milvus
    
    log_success "Milvus on EKS deployment completed successfully!"
    log_info "Messaging system: $MESSAGING_OPTION"
    log_info "You can now use the examples in the ./examples directory to test your deployment."
    log_info "To clean up resources, run: ./scripts/cleanup.sh"
}

# Run main function
main "$@"