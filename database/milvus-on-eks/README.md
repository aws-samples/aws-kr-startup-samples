# Installation

https://zilliz.com/blog/set-up-milvus-vector-database-on-amazon-eks

1. Create eks cluster

```bash
eksctl create cluster -f eks/eks_cluster.yaml
aws eks update-kubeconfig --region 'us-east-1' --name 'milvus-eks-cluster'
export milvus_cluster_name='milvus-eks-cluster'
```

```bash
export eks_vpc_id=$(aws eks describe-cluster --name milvus-eks-cluster --query 'cluster.resourcesVpcConfig.vpcId' --output text)
export eks_subnet_ids=$(aws eks describe-cluster --name milvus-eks-cluster --query 'cluster.resourcesVpcConfig.subnetIds' --output text)
echo "EKS VPC ID: $eks_vpc_id"
echo "EKS Subnet IDs: $eks_subnet_ids"

EKS VPC ID: vpc-06370490385bbd9ae
EKS Subnet IDs: subnet-09a33614e6c29b76b        subnet-023b3b4740fbb3609        subnet-0d182b10068707fa2  subnet-0e067b0c267e7c869
```

```bash
kubectl apply -f eks/gp3_storage_class.yaml
kubectl patch storageclass gp2 -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"false"}}}'
```

2. Create S3 bucket

```bash
export MILVUS_BUCKET_NAME="milvus-bucket-$(openssl rand -hex 12)"
aws s3 mb s3://${MILVUS_BUCKET_NAME}
```

configure policies

```bash
export user_name=$(aws sts get-caller-identity --query 'Arn' --output text | cut -d'/' -f2)
export account_id=$(aws sts get-caller-identity --query 'Account' --output text)

envsubst < iam/milvus-s3-policy-template.json > iam/milvus-s3-policy.json
envsubst < iam/milvus-iam-policy-template.json > iam/milvus-iam-policy.json

aws iam create-policy --policy-name MilvusS3ReadWrite --policy-document file://policies/milvus-s3-policy.json
aws iam attach-user-policy --user-name ${user_name} --policy-arn "arn:aws:iam::${account_id}:policy/MilvusS3ReadWrite"
```

3. Install AWS Load Balancer Controller

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
 -n kube-system \
 --set clusterName=${milvus_cluster_name} \
 --set serviceAccount.create=false \
 --set serviceAccount.name=aws-load-balancer-controller
```

check

```bash
kubectl get deployment -n kube-system aws-load-balancer-controller

NAME                           READY   UP-TO-DATE   AVAILABLE   AGE
aws-load-balancer-controller   2/2     2            2           49s
```

4. Create MSK cluster

```bash
export MSK_SECURITY_GROUP_ID=$(aws ec2 create-security-group \
  --group-name milvus-msk-sg \
  --description "Security group for Milvus MSK cluster" \
  --vpc-id $eks_vpc_id \
  --query 'GroupId' \
  --output text \
  --region us-east-1)

# Get private subnets from EKS cluster
export PRIVATE_SUBNETS=($(aws eks describe-cluster --name milvus-eks-cluster --query 'cluster.resourcesVpcConfig.subnetIds' --output text))

# Filter for private subnets (those with internal-elb role)
export PRIVATE_SUBNET_1=$(aws ec2 describe-subnets --subnet-ids ${PRIVATE_SUBNETS[@]} --query 'Subnets[?Tags[?Key==`kubernetes.io/role/internal-elb`]].SubnetId' --output text | awk '{print $1}')
export PRIVATE_SUBNET_2=$(aws ec2 describe-subnets --subnet-ids ${PRIVATE_SUBNETS[@]} --query 'Subnets[?Tags[?Key==`kubernetes.io/role/internal-elb`]].SubnetId' --output text | awk '{print $2}')

# Generate the actual config file
envsubst < msk/msk-cluster-config-template.json > msk/msk-cluster-config.json

# Create the cluster
aws kafka create-cluster --cli-input-json file://msk/msk-cluster-config.json --region us-east-1
```

```bash
export CLUSTER_ARN=$(aws kafka list-clusters --cluster-name-filter "milvus-msk-cluster" --query 'ClusterInfoList[0].ClusterArn' --output text --region us-east-1)

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

5. Create Required Kafka Topics 

```bash
# Create a temporary Kafka client pod to manage MSK topics
kubectl apply -f msk/kafka-client.yaml

# Wait for the client pod to be ready
kubectl wait --for=condition=Ready pod/kafka-client -n milvus --timeout=60s

# Get MSK broker endpoints
export CLUSTER_ARN=$(aws kafka list-clusters --cluster-name-filter "milvus-msk-cluster" --query 'ClusterInfoList[0].ClusterArn' --output text --region us-east-1)
export BROKER_LIST=$(aws kafka get-bootstrap-brokers --cluster-arn "$CLUSTER_ARN" --query 'BootstrapBrokerString' --output text --region us-east-1)

echo "MSK Broker List: $BROKER_LIST"

# Create required topics for Milvus internal messaging
kubectl exec -n milvus kafka-client -- kafka-topics \
  --bootstrap-server $BROKER_LIST \
  --create --topic by-dev-rootcoord-dml_0 \
  --partitions 1 --replication-factor 2

kubectl exec -n milvus kafka-client -- kafka-topics \
  --bootstrap-server $BROKER_LIST \
  --create --topic by-dev-rootcoord-dml_1 \
  --partitions 1 --replication-factor 2

kubectl exec -n milvus kafka-client -- kafka-topics \
  --bootstrap-server $BROKER_LIST \
  --create --topic by-dev-rootcoord-delta \
  --partitions 1 --replication-factor 2

# Verify topics were created successfully
echo "Created topics:"
kubectl exec -n milvus kafka-client -- kafka-topics \
  --bootstrap-server $BROKER_LIST --list

# Clean up the temporary client pod
kubectl delete pod kafka-client -n milvus
```

6. Install Milvus

Next, create the "milvus" namespace

```bash
kubectl create namespace milvus
```

```bash
# Get AWS credentials from default profile
export ACCESS_KEY=$(aws configure get aws_access_key_id)
export SECRET_KEY=$(aws configure get aws_secret_access_key)

envsubst < milvus/milvus-template.yaml > milvus/milvus.yaml

helm repo add milvus https://zilliztech.github.io/milvus-helm/
helm repo update

helm upgrade --install \
  --namespace milvus \
  -f milvus/milvus.yaml \
  milvus milvus/milvus
```

# Usage

see instructions in [exmaples](./examples/README.md)