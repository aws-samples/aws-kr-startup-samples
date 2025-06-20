#!/bin/bash

# Milvus on EKS Cleanup Script
# This script removes all resources created by the deployment

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

# Confirmation prompt
confirm_cleanup() {
    log_warning "This will delete ALL resources created by the Milvus on EKS deployment."
    log_warning "This action cannot be undone!"
    echo
    read -p "Are you sure you want to proceed? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log_info "Cleanup cancelled."
        exit 0
    fi
}

# Get environment variables
get_environment_vars() {
    log_info "Getting environment variables..."
    
    export user_name=$(aws sts get-caller-identity --query 'Arn' --output text | cut -d'/' -f2 2>/dev/null || echo "")
    export account_id=$(aws sts get-caller-identity --query 'Account' --output text 2>/dev/null || echo "")
    
    # Try to get MSK cluster ARN
    export CLUSTER_ARN=$(aws kafka list-clusters --cluster-name-filter "milvus-msk-cluster" --query 'ClusterInfoList[0].ClusterArn' --output text --region us-east-1 2>/dev/null || echo "")
    
    # Try to get S3 bucket name from existing buckets
    export MILVUS_BUCKET_NAME=$(aws s3 ls | grep "milvus-bucket-" | awk '{print $3}' | head -1 || echo "")
}

# Delete Milvus
cleanup_milvus() {
    log_info "Cleaning up Milvus..."
    
    if helm list -n milvus | grep -q milvus 2>/dev/null; then
        helm uninstall milvus -n milvus
        log_success "Milvus uninstalled successfully!"
    else
        log_warning "Milvus installation not found. Skipping."
    fi
    
    # Delete namespace
    if kubectl get namespace milvus &>/dev/null; then
        kubectl delete namespace milvus --timeout=300s
        log_success "Milvus namespace deleted!"
    fi
}

# Delete MSK cluster
cleanup_msk() {
    log_info "Cleaning up MSK cluster..."
    
    if [ -n "$CLUSTER_ARN" ] && [ "$CLUSTER_ARN" != "None" ]; then
        log_info "Deleting MSK cluster: $CLUSTER_ARN"
        aws kafka delete-cluster --cluster-arn "$CLUSTER_ARN" --region us-east-1
        
        # Wait for deletion to complete
        log_info "Waiting for MSK cluster deletion to complete..."
        while true; do
            STATUS=$(aws kafka describe-cluster --cluster-arn "$CLUSTER_ARN" --query 'ClusterInfo.State' --output text --region us-east-1 2>/dev/null || echo "DELETED")
            
            if [ "$STATUS" = "DELETED" ] || [ "$STATUS" = "None" ]; then
                log_success "MSK cluster deleted successfully!"
                break
            fi
            
            log_info "Current status: $STATUS"
            sleep 30
        done
    else
        log_warning "MSK cluster not found. Skipping."
    fi
    
    # Delete security group
    local sg_id=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=milvus-msk-sg" --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || echo "")
    if [ -n "$sg_id" ] && [ "$sg_id" != "None" ]; then
        aws ec2 delete-security-group --group-id "$sg_id" --region us-east-1
        log_success "MSK security group deleted!"
    fi
}

# Delete EKS cluster
cleanup_eks() {
    log_info "Cleaning up EKS cluster..."
    
    if eksctl get cluster --name milvus-eks-cluster &>/dev/null; then
        log_info "Deleting EKS cluster: milvus-eks-cluster"
        eksctl delete cluster --name milvus-eks-cluster --wait
        log_success "EKS cluster deleted successfully!"
    else
        log_warning "EKS cluster 'milvus-eks-cluster' not found. Skipping."
    fi
}

# Delete S3 bucket
cleanup_s3() {
    log_info "Cleaning up S3 bucket..."
    
    if [ -n "$MILVUS_BUCKET_NAME" ]; then
        log_info "Emptying and deleting S3 bucket: $MILVUS_BUCKET_NAME"
        
        # Empty bucket first
        aws s3 rm s3://"$MILVUS_BUCKET_NAME" --recursive 2>/dev/null || true
        
        # Delete bucket
        aws s3 rb s3://"$MILVUS_BUCKET_NAME" --force
        log_success "S3 bucket deleted successfully!"
    else
        log_warning "Milvus S3 bucket not found. Skipping."
    fi
}

# Delete IAM policies
cleanup_iam() {
    log_info "Cleaning up IAM policies..."
    
    if [ -n "$user_name" ] && [ -n "$account_id" ]; then
        local policy_arn="arn:aws:iam::${account_id}:policy/MilvusS3ReadWrite"
        
        # Detach policy from user
        if aws iam get-user-policy --user-name "$user_name" --policy-name MilvusS3ReadWrite &>/dev/null; then
            aws iam detach-user-policy --user-name "$user_name" --policy-arn "$policy_arn" 2>/dev/null || true
        fi
        
        # Delete policy
        if aws iam get-policy --policy-arn "$policy_arn" &>/dev/null; then
            aws iam delete-policy --policy-arn "$policy_arn"
            log_success "IAM policies deleted successfully!"
        else
            log_warning "IAM policy not found. Skipping."
        fi
    else
        log_warning "Unable to determine user information. Skipping IAM cleanup."
    fi
}

# Main cleanup function
main() {
    log_info "Starting Milvus on EKS cleanup..."
    
    confirm_cleanup
    get_environment_vars
    
    cleanup_milvus
    cleanup_msk
    cleanup_eks
    cleanup_s3
    cleanup_iam
    
    log_success "Cleanup completed successfully!"
    log_info "All Milvus on EKS resources have been removed."
}

# Run main function
main "$@"
