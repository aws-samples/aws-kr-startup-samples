# Milvus Vector Database on Amazon EKS

This project demonstrates how to deploy Milvus, an open-source vector database, on Amazon EKS with enterprise-grade scalability and reliability. The solution integrates Amazon MSK for message queuing and Amazon S3 for object storage, providing a production-ready vector database infrastructure for AI/ML workloads.

## Architecture

The solution deploys Milvus on Amazon EKS with the following components:

- **Amazon EKS**: Kubernetes cluster hosting Milvus components
- **Amazon MSK**: Managed Kafka service for Milvus message queuing
- **Amazon S3**: Object storage for Milvus data persistence
- **AWS Load Balancer Controller**: For external access and load distribution

For detailed architecture overview, see [Architecture Diagram](./assets/architecture.md).

## Prerequisites

Before you begin, ensure you have the following tools installed and configured:

- **AWS CLI** (v2.0+) configured with appropriate permissions
- **kubectl** (v1.21+) for Kubernetes cluster management
- **eksctl** (v0.100+) for EKS cluster creation
- **Helm** (v3.0+) for package management
- **OpenSSL** for generating random values

### Required AWS Permissions

Your AWS credentials need permissions for:
- EKS cluster creation and management
- MSK cluster creation and management
- S3 bucket creation and management
- IAM policy creation and attachment
- EC2 VPC and security group management

## Key Learning Objectives

- Deploy a scalable vector database on Kubernetes
- Integrate Milvus with AWS managed services (MSK, S3)
- Configure enterprise-grade storage and messaging for vector operations
- Set up load balancing and external access for vector database clients
- Understand vector database architecture patterns on AWS

## Quick Start

For a rapid deployment, run the automated setup script:

```bash
# Clone the repository (if not already done)
git clone https://github.com/aws-samples/aws-kr-startup-samples.git
cd aws-kr-startup-samples
git sparse-checkout init --cone
git sparse-checkout set database/milvus-on-aws

# Navigate to the project directory
cd database/milvus-on-aws

# Run the automated deployment
./scripts/deploy.sh
```

## Detailed Setup

### Step 1: Create EKS Cluster

Create the EKS cluster with optimized configuration for Milvus workloads:

```bash
# Configure AWS CLI
aws configure set region us-east-1

# Create EKS cluster
eksctl create cluster -f infrastructure/eks/eks_cluster.yaml

# Update kubeconfig
aws eks update-kubeconfig --region us-east-1 --name milvus-eks-cluster

# Set environment variables
export milvus_cluster_name='milvus-eks-cluster'
export eks_vpc_id=$(aws eks describe-cluster --name milvus-eks-cluster --query 'cluster.resourcesVpcConfig.vpcId' --output text)
export eks_subnet_ids=$(aws eks describe-cluster --name milvus-eks-cluster --query 'cluster.resourcesVpcConfig.subnetIds' --output text)

echo "EKS VPC ID: $eks_vpc_id"
echo "EKS Subnet IDs: $eks_subnet_ids"
```

Configure storage classes for optimal performance:

```bash
# Apply GP3 storage class for better performance
kubectl apply -f infrastructure/eks/gp3_storage_class.yaml

# Set GP3 as default storage class
kubectl patch storageclass gp2 -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"false"}}}'
```

### Step 2: Configure S3 Object Storage

Create S3 bucket and configure IAM policies for Milvus data persistence:

```bash
# Create unique S3 bucket name
export MILVUS_BUCKET_NAME="milvus-bucket-$(openssl rand -hex 12)"
aws s3 mb s3://${MILVUS_BUCKET_NAME}

# Get AWS account information
export user_name=$(aws sts get-caller-identity --query 'Arn' --output text | cut -d'/' -f2)
export account_id=$(aws sts get-caller-identity --query 'Account' --output text)

# Generate IAM policies from templates
envsubst < infrastructure/s3/milvus-s3-policy-template.json > infrastructure/s3/milvus-s3-policy.json
envsubst < infrastructure/iam/milvus-iam-policy-template.json > infrastructure/iam/milvus-iam-policy.json

# Create and attach IAM policies
aws iam create-policy --policy-name MilvusS3ReadWrite --policy-document file://infrastructure/s3/milvus-s3-policy.json
aws iam attach-user-policy --user-name ${user_name} --policy-arn "arn:aws:iam::${account_id}:policy/MilvusS3ReadWrite"
```

### Step 3: Install AWS Load Balancer Controller

Set up the AWS Load Balancer Controller for external access:

```bash
# Add EKS Helm repository
helm repo add eks https://aws.github.io/eks-charts
helm repo update

# Install AWS Load Balancer Controller
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=${milvus_cluster_name} \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller

# Verify installation
kubectl get deployment -n kube-system aws-load-balancer-controller
```

### Step 4: Create Amazon MSK Cluster

Deploy Amazon MSK for Milvus message queuing with custom configuration:

**Note**: We use Kafka version 3.9.x as it's the latest supported version in MSK with the longest support lifecycle.

```bash
# Create MSK configuration with auto.create.topics.enable=true
aws kafka create-configuration \
  --name milvus-msk-config \
  --description "Custom configuration for Milvus MSK cluster with auto topic creation" \
  --kafka-versions "3.9.x" \
  --server-properties file://infrastructure/msk/msk-custom-config.properties \
  --region us-east-1

# Get the configuration ARN
export MSK_CONFIG_ARN=$(aws kafka list-configurations \
  --query 'Configurations[?Name==`milvus-msk-config`].Arn' \
  --output text \
  --region us-east-1)

echo "MSK Configuration ARN: $MSK_CONFIG_ARN"

# Create security group for MSK
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

# Get private subnets from EKS cluster
export PRIVATE_SUBNETS=($(aws eks describe-cluster --name milvus-eks-cluster --query 'cluster.resourcesVpcConfig.subnetIds' --output text))

# Filter for private subnets
export PRIVATE_SUBNET_1=$(aws ec2 describe-subnets --subnet-ids ${PRIVATE_SUBNETS[@]} --query 'Subnets[?Tags[?Key==`kubernetes.io/role/internal-elb`]].SubnetId' --output text | awk '{print $1}')
export PRIVATE_SUBNET_2=$(aws ec2 describe-subnets --subnet-ids ${PRIVATE_SUBNETS[@]} --query 'Subnets[?Tags[?Key==`kubernetes.io/role/internal-elb`]].SubnetId' --output text | awk '{print $2}')

# Generate MSK configuration
envsubst < infrastructure/msk/msk-cluster-config-template.json > infrastructure/msk/msk-cluster-config.json

# Create MSK cluster
aws kafka create-cluster --cli-input-json file://infrastructure/msk/msk-cluster-config.json --region us-east-1
```

Wait for MSK cluster to become active:

```bash
export CLUSTER_ARN=$(aws kafka list-clusters --cluster-name-filter "milvus-msk-cluster" --query 'ClusterInfoList[0].ClusterArn' --output text --region us-east-1)

# Monitor cluster status
while true; do
    STATUS=$(aws kafka describe-cluster --cluster-arn "$CLUSTER_ARN" --query 'ClusterInfo.State' --output text --region us-east-1)
    echo "Current status: $STATUS ($(date))"
    
    if [ "$STATUS" = "ACTIVE" ]; then
        echo "MSK cluster is now ACTIVE!"
        break
    elif [ "$STATUS" = "FAILED" ]; then
        echo "MSK cluster creation failed!"
        exit 1
    fi
    
    echo "Waiting 30 seconds before checking again..."
    sleep 30
done

export BROKER_LIST=$(aws kafka get-bootstrap-brokers --cluster-arn "$CLUSTER_ARN" --query 'BootstrapBrokerString' --output text --region us-east-1)
echo "BROKER_LIST: $BROKER_LIST"
```

### Step 5: Deploy Milvus

Install Milvus using Helm with custom configuration:

```bash
# Create Milvus namespace
kubectl create namespace milvus

# Get AWS credentials for Milvus configuration
export ACCESS_KEY=$(aws configure get aws_access_key_id)
export SECRET_KEY=$(aws configure get aws_secret_access_key)

# Generate Milvus configuration from template
envsubst < infrastructure/milvus/milvus-template.yaml > infrastructure/milvus/milvus.yaml

# Add Milvus Helm repository
helm repo add milvus https://zilliztech.github.io/milvus-helm/
helm repo update

# Install Milvus
helm upgrade --install \
  --namespace milvus \
  -f infrastructure/milvus/milvus.yaml \
  milvus milvus/milvus

# Verify installation
kubectl get pods -n milvus
```

## Usage Examples

Explore practical examples of using Milvus for vector operations:

- [Basic Vector Operations](./examples/basic-operations/)
- [Similarity Search](./examples/similarity-search/)
- [Integration with AI/ML Pipelines](./examples/ml-integration/)

For detailed usage instructions, see [Examples README](./examples/README.md).

## Monitoring and Observability

Monitor your Milvus deployment with:

```bash
# Check Milvus pod status
kubectl get pods -n milvus

# View Milvus logs
kubectl logs -n milvus -l app.kubernetes.io/name=milvus

# Check MSK cluster metrics
aws kafka describe-cluster --cluster-arn $CLUSTER_ARN --query 'ClusterInfo.CurrentBrokerSoftwareInfo'
```

## Cost Optimization

This deployment includes several AWS resources that incur costs:

- **EKS Cluster**: ~$73/month for control plane
- **EC2 Instances**: Variable based on node group configuration
- **MSK Cluster**: ~$150/month for kafka.t3.small instances
- **S3 Storage**: Pay-per-use based on data volume
- **Data Transfer**: Charges for cross-AZ traffic

Use the [AWS Pricing Calculator](https://calculator.aws) for detailed cost estimates.

## Troubleshooting

### Common Issues

**EKS Cluster Creation Fails**
```bash
# Check AWS CLI configuration
aws sts get-caller-identity

# Verify IAM permissions
aws iam get-user
```

**MSK Cluster Not Accessible**
```bash
# Check security group rules
aws ec2 describe-security-groups --group-ids $MSK_SECURITY_GROUP_ID

# Verify subnet configuration
aws ec2 describe-subnets --subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2
```

**Milvus Pods Not Starting**
```bash
# Check pod events
kubectl describe pod -n milvus <pod-name>

# Verify storage class
kubectl get storageclass
```

### Getting Help

- Check the [Milvus Documentation](https://milvus.io/docs)
- Review [EKS Troubleshooting Guide](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html)
- Open an issue in this repository

## Cleanup

To avoid ongoing charges, clean up all resources:

```bash
# Delete Milvus installation
helm uninstall milvus -n milvus

# Delete MSK cluster
aws kafka delete-cluster --cluster-arn $CLUSTER_ARN

# Delete EKS cluster
eksctl delete cluster --name milvus-eks-cluster

# Delete S3 bucket (after emptying it)
aws s3 rb s3://${MILVUS_BUCKET_NAME} --force

# Delete IAM policies
aws iam detach-user-policy --user-name ${user_name} --policy-arn "arn:aws:iam::${account_id}:policy/MilvusS3ReadWrite"
aws iam delete-policy --policy-arn "arn:aws:iam::${account_id}:policy/MilvusS3ReadWrite"
```

**Cleanup Script**

For easier cleanup, use the provided script:

```bash
./scripts/cleanup.sh
```

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file.