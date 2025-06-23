#!/bin/bash

# Milvus on EKS Automated Deployment Script
# This script automates the deployment of Milvus vector database on Amazon EKS

set -e

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
    aws eks update-kubeconfig --region us-east-1 --name milvus-eks-cluster
    
    # Set environment variables
    export milvus_cluster_name='milvus-eks-cluster'
    export eks_vpc_id=$(aws eks describe-cluster --name milvus-eks-cluster --query 'cluster.resourcesVpcConfig.vpcId' --output text)
    export eks_subnet_ids=$(aws eks describe-cluster --name milvus-eks-cluster --query 'cluster.resourcesVpcConfig.subnetIds' --output text)
    
    log_info "EKS VPC ID: $eks_vpc_id"
    log_info "EKS Subnet IDs: $eks_subnet_ids"
    
    # Configure storage
    kubectl apply -f infrastructure/eks/gp3_storage_class.yaml
    kubectl patch storageclass gp2 -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"false"}}}'
    
    log_success "EKS cluster configuration completed!"
}

# Configure S3 and IAM
configure_s3_iam() {
    log_info "Configuring S3 bucket and IAM policies..."
    
    # Create S3 bucket
    export MILVUS_BUCKET_NAME="milvus-bucket-$(openssl rand -hex 12)"
    aws s3 mb s3://${MILVUS_BUCKET_NAME}
    log_success "S3 bucket created: $MILVUS_BUCKET_NAME"
    
    # Get AWS account information
    export user_name=$(aws sts get-caller-identity --query 'Arn' --output text | cut -d'/' -f2)
    export account_id=$(aws sts get-caller-identity --query 'Account' --output text)
    
    # Generate IAM policies
    envsubst < infrastructure/s3/milvus-s3-policy-template.json > infrastructure/iam/milvus-s3-policy.json
    envsubst < infrastructure/iam/milvus-iam-policy-template.json > infrastructure/iam/milvus-iam-policy.json
    
    # Create and attach policies
    if aws iam get-policy --policy-arn "arn:aws:iam::${account_id}:policy/MilvusS3ReadWrite" &> /dev/null; then
        log_warning "IAM policy 'MilvusS3ReadWrite' already exists. Skipping creation."
    else
        aws iam create-policy --policy-name MilvusS3ReadWrite --policy-document file://infrastructure/iam/milvus-s3-policy.json
        aws iam attach-user-policy --user-name ${user_name} --policy-arn "arn:aws:iam::${account_id}:policy/MilvusS3ReadWrite"
        log_success "IAM policies configured successfully!"
    fi
}

# Install AWS Load Balancer Controller
install_alb_controller() {
    log_info "Installing AWS Load Balancer Controller..."
    
    helm repo add eks https://aws.github.io/eks-charts
    helm repo update
    
    if helm list -n kube-system | grep -q aws-load-balancer-controller; then
        log_warning "AWS Load Balancer Controller already installed. Skipping."
    else
        helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
            -n kube-system \
            --set clusterName=${milvus_cluster_name} \
            --set serviceAccount.create=false \
            --set serviceAccount.name=aws-load-balancer-controller
        
        log_success "AWS Load Balancer Controller installed successfully!"
    fi
    
    # Verify installation
    kubectl wait --for=condition=available --timeout=300s deployment/aws-load-balancer-controller -n kube-system
}

# Deploy MSK cluster
deploy_msk() {
    log_info "Creating Amazon MSK cluster..."
    
    # Check if MSK cluster already exists
    if aws kafka list-clusters --cluster-name-filter "milvus-msk-cluster" --query 'ClusterInfoList[0].ClusterArn' --output text | grep -q arn; then
        log_warning "MSK cluster 'milvus-msk-cluster' already exists. Skipping creation."
        export CLUSTER_ARN=$(aws kafka list-clusters --cluster-name-filter "milvus-msk-cluster" --query 'ClusterInfoList[0].ClusterArn' --output text --region us-east-1)
    else
        # Create security group
        export MSK_SECURITY_GROUP_ID=$(aws ec2 create-security-group \
            --group-name milvus-msk-sg \
            --description "Security group for Milvus MSK cluster" \
            --vpc-id $eks_vpc_id \
            --query 'GroupId' \
            --output text \
            --region us-east-1)
        
        # Add ingress rules to allow Kafka traffic from EKS nodes
        # Allow Kafka plaintext traffic (port 9092)
        aws ec2 authorize-security-group-ingress \
            --group-id $MSK_SECURITY_GROUP_ID \
            --protocol tcp \
            --port 9092 \
            --cidr 192.168.0.0/16 \
            --region us-east-1
        
        # Allow Kafka TLS traffic (port 9094) 
        aws ec2 authorize-security-group-ingress \
            --group-id $MSK_SECURITY_GROUP_ID \
            --protocol tcp \
            --port 9094 \
            --cidr 192.168.0.0/16 \
            --region us-east-1
        
        # Allow Zookeeper traffic (port 2181) - needed for older Kafka versions
        aws ec2 authorize-security-group-ingress \
            --group-id $MSK_SECURITY_GROUP_ID \
            --protocol tcp \
            --port 2181 \
            --cidr 192.168.0.0/16 \
            --region us-east-1
        
        # Get private subnets
        export PRIVATE_SUBNETS=($(aws eks describe-cluster --name milvus-eks-cluster --query 'cluster.resourcesVpcConfig.subnetIds' --output text))
        export PRIVATE_SUBNET_1=$(aws ec2 describe-subnets --subnet-ids ${PRIVATE_SUBNETS[@]} --query 'Subnets[?Tags[?Key==`kubernetes.io/role/internal-elb`]].SubnetId' --output text | awk '{print $1}')
        export PRIVATE_SUBNET_2=$(aws ec2 describe-subnets --subnet-ids ${PRIVATE_SUBNETS[@]} --query 'Subnets[?Tags[?Key==`kubernetes.io/role/internal-elb`]].SubnetId' --output text | awk '{print $2}')
        
        # Generate MSK configuration
        envsubst < infrastructure/msk/msk-cluster-config-template.json > infrastructure/msk/msk-cluster-config.json
        
        # Create MSK cluster
        aws kafka create-cluster --cli-input-json file://infrastructure/msk/msk-cluster-config.json --region us-east-1
        export CLUSTER_ARN=$(aws kafka list-clusters --cluster-name-filter "milvus-msk-cluster" --query 'ClusterInfoList[0].ClusterArn' --output text --region us-east-1)
        
        log_success "MSK cluster creation initiated!"
    fi
    
    # Wait for cluster to be active
    log_info "Waiting for MSK cluster to become active..."
    while true; do
        STATUS=$(aws kafka describe-cluster --cluster-arn "$CLUSTER_ARN" --query 'ClusterInfo.State' --output text --region us-east-1)
        log_info "Current status: $STATUS"
        
        if [ "$STATUS" = "ACTIVE" ]; then
            log_success "MSK cluster is now ACTIVE!"
            break
        elif [ "$STATUS" = "FAILED" ]; then
            log_error "MSK cluster creation failed!"
            exit 1
        fi
        
        sleep 30
    done
    
    export BROKER_LIST=$(aws kafka get-bootstrap-brokers --cluster-arn "$CLUSTER_ARN" --query 'BootstrapBrokerString' --output text --region us-east-1)
    log_info "BROKER_LIST: $BROKER_LIST"
}

# Configure Kafka topics
configure_kafka_topics() {
    log_info "Configuring Kafka topics..."
    
    # Create namespace if it doesn't exist
    kubectl create namespace milvus --dry-run=client -o yaml | kubectl apply -f -
    
    # Create temporary Kafka client
    kubectl apply -f infrastructure/msk/kafka-client.yaml
    kubectl wait --for=condition=Ready pod/kafka-client -n milvus --timeout=60s
    
    # Create topics
    local topics=("by-dev-rootcoord-dml_0" "by-dev-rootcoord-dml_1" "by-dev-rootcoord-delta")
    
    for topic in "${topics[@]}"; do
        if kubectl exec -n milvus kafka-client -- kafka-topics --bootstrap-server $BROKER_LIST --list | grep -q "$topic"; then
            log_warning "Topic '$topic' already exists. Skipping."
        else
            kubectl exec -n milvus kafka-client -- kafka-topics \
                --bootstrap-server $BROKER_LIST \
                --create --topic $topic \
                --partitions 1 --replication-factor 2
            log_success "Topic '$topic' created successfully!"
        fi
    done
    
    # Clean up
    kubectl delete pod kafka-client -n milvus
}

# Deploy Milvus
deploy_milvus() {
    log_info "Deploying Milvus..."
    
    # Get AWS credentials
    export ACCESS_KEY=$(aws configure get aws_access_key_id)
    export SECRET_KEY=$(aws configure get aws_secret_access_key)
    
    # Generate Milvus configuration
    envsubst < infrastructure/milvus/milvus-template.yaml > infrastructure/milvus/milvus.yaml
    
    # Add Milvus Helm repository
    helm repo add milvus https://zilliztech.github.io/milvus-helm/
    helm repo update
    
    # Install Milvus
    if helm list -n milvus | grep -q milvus; then
        log_warning "Milvus already installed. Upgrading..."
        helm upgrade --namespace milvus -f infrastructure/milvus/milvus.yaml milvus milvus/milvus
    else
        helm install --namespace milvus -f infrastructure/milvus/milvus.yaml milvus milvus/milvus
    fi
    
    log_success "Milvus deployment completed!"
    
    # Wait for pods to be ready
    log_info "Waiting for Milvus pods to be ready..."
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=milvus -n milvus --timeout=600s
    
    log_success "All Milvus pods are ready!"
}

# Main deployment function
main() {
    # Configure AWS CLI
    aws configure set region us-east-1

    log_info "Starting Milvus on EKS deployment..."
    
    check_prerequisites
    deploy_eks
    configure_s3_iam
    install_alb_controller
    deploy_msk
    configure_kafka_topics
    deploy_milvus
    
    log_success "Milvus on EKS deployment completed successfully!"
    log_info "You can now use the examples in the ./examples directory to test your deployment."
    log_info "To clean up resources, run: ./scripts/cleanup.sh"
}

# Run main function
main "$@"
