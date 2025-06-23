#!/bin/bash

# Milvus on EKS Cleanup Script
# This script removes all resources created by the deployment

# Remove set -e to handle errors gracefully
# set -e

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

# Function to safely run commands and continue on error
safe_run() {
    local cmd="$1"
    local description="$2"
    
    log_info "$description"
    if eval "$cmd" 2>/dev/null; then
        log_success "$description completed successfully!"
        return 0
    else
        log_warning "$description failed or resource not found. Continuing..."
        return 1
    fi
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
    
    export user_name=$(aws sts get-caller-identity --query 'Arn' --output text 2>/dev/null | cut -d'/' -f2 || echo "")
    export account_id=$(aws sts get-caller-identity --query 'Account' --output text 2>/dev/null || echo "")
    
    # Try to get MSK cluster ARN
    export CLUSTER_ARN=$(aws kafka list-clusters --cluster-name-filter "milvus-msk-cluster" --query 'ClusterInfoList[0].ClusterArn' --output text --region us-east-1 2>/dev/null || echo "")
    
    # Try to get S3 bucket name from existing buckets
    export MILVUS_BUCKET_NAME=$(aws s3 ls 2>/dev/null | grep "milvus-bucket-" | awk '{print $3}' | head -1 || echo "")
    
    # Try to get EKS VPC ID for later cleanup
    export EKS_VPC_ID=$(aws eks describe-cluster --name milvus-eks-cluster --query 'cluster.resourcesVpcConfig.vpcId' --output text --region us-east-1 2>/dev/null || echo "")
}

# Clean up EKS-created security groups that may prevent VPC deletion
cleanup_eks_security_groups() {
    log_info "Cleaning up EKS-created security groups..."
    
    if [ -n "$EKS_VPC_ID" ] && [ "$EKS_VPC_ID" != "None" ]; then
        # Find EKS-created security groups in the VPC
        local sg_ids=$(aws ec2 describe-security-groups \
            --filters "Name=vpc-id,Values=$EKS_VPC_ID" "Name=tag:aws:eks:cluster-name,Values=milvus-eks-cluster" \
            --query 'SecurityGroups[].GroupId' --output text --region us-east-1 2>/dev/null || echo "")
        
        if [ -n "$sg_ids" ]; then
            for sg_id in $sg_ids; do
                log_info "Attempting to delete security group: $sg_id"
                # First, try to remove any ingress rules that reference other security groups
                aws ec2 describe-security-groups --group-ids "$sg_id" --region us-east-1 2>/dev/null | \
                jq -r '.SecurityGroups[0].IpPermissions[]? | select(.UserIdGroupPairs[]?) | @base64' 2>/dev/null | \
                while read -r rule; do
                    if [ -n "$rule" ]; then
                        echo "$rule" | base64 -d | jq -c '.' 2>/dev/null | \
                        while read -r ip_perm; do
                            aws ec2 revoke-security-group-ingress --group-id "$sg_id" --ip-permissions "$ip_perm" --region us-east-1 2>/dev/null || true
                        done
                    fi
                done
                
                # Try to delete the security group
                aws ec2 delete-security-group --group-id "$sg_id" --region us-east-1 2>/dev/null || log_warning "Could not delete security group $sg_id"
            done
        fi
        
        # Also clean up the default security group rules that might reference EKS security groups
        local default_sg=$(aws ec2 describe-security-groups \
            --filters "Name=vpc-id,Values=$EKS_VPC_ID" "Name=group-name,Values=default" \
            --query 'SecurityGroups[0].GroupId' --output text --region us-east-1 2>/dev/null || echo "")
        
        if [ -n "$default_sg" ] && [ "$default_sg" != "None" ]; then
            log_info "Cleaning up default security group rules..."
            # Remove any rules that reference EKS security groups
            aws ec2 describe-security-groups --group-ids "$default_sg" --region us-east-1 2>/dev/null | \
            jq -r '.SecurityGroups[0].IpPermissions[]? | select(.UserIdGroupPairs[]?) | @base64' 2>/dev/null | \
            while read -r rule; do
                if [ -n "$rule" ]; then
                    echo "$rule" | base64 -d | jq -c '.' 2>/dev/null | \
                    while read -r ip_perm; do
                        aws ec2 revoke-security-group-ingress --group-id "$default_sg" --ip-permissions "$ip_perm" --region us-east-1 2>/dev/null || true
                    done
                fi
            done
        fi
    fi
}

# Clean up failed CloudFormation stacks
cleanup_failed_cloudformation_stacks() {
    log_info "Checking for failed CloudFormation stacks..."
    
    local failed_stacks=$(aws cloudformation list-stacks \
        --stack-status-filter DELETE_FAILED \
        --query 'StackSummaries[?contains(StackName, `eksctl-milvus-eks-cluster`)].StackName' \
        --output text --region us-east-1 2>/dev/null || echo "")
    
    if [ -n "$failed_stacks" ]; then
        for stack in $failed_stacks; do
            log_info "Attempting to delete failed CloudFormation stack: $stack"
            aws cloudformation delete-stack --stack-name "$stack" --region us-east-1 2>/dev/null || log_warning "Could not delete stack $stack"
        done
    fi
}

# Delete Milvus
cleanup_milvus() {
    log_info "Cleaning up Milvus..."
    
    # Check if helm and kubectl are available
    if ! command -v helm &> /dev/null; then
        log_warning "Helm not found. Skipping Milvus uninstall."
        return
    fi
    
    if ! command -v kubectl &> /dev/null; then
        log_warning "kubectl not found. Skipping Milvus cleanup."
        return
    fi
    
    # Try to uninstall Milvus
    if helm list -n milvus 2>/dev/null | grep -q milvus; then
        safe_run "helm uninstall milvus -n milvus --timeout=300s" "Uninstalling Milvus"
    else
        log_warning "Milvus installation not found. Skipping."
    fi
    
    # Delete namespace with timeout
    if kubectl get namespace milvus &>/dev/null; then
        safe_run "kubectl delete namespace milvus --timeout=300s --ignore-not-found=true" "Deleting Milvus namespace"
    fi
}

# Delete MSK cluster
cleanup_msk() {
    log_info "Cleaning up MSK cluster..."
    
    if [ -n "$CLUSTER_ARN" ] && [ "$CLUSTER_ARN" != "None" ] && [ "$CLUSTER_ARN" != "" ]; then
        log_info "Deleting MSK cluster: $CLUSTER_ARN"
        if aws kafka delete-cluster --cluster-arn "$CLUSTER_ARN" --region us-east-1 2>/dev/null; then
            # Wait for deletion to complete with timeout
            log_info "Waiting for MSK cluster deletion to complete..."
            local timeout=1800  # 30 minutes
            local elapsed=0
            
            while [ $elapsed -lt $timeout ]; do
                local status=$(aws kafka describe-cluster --cluster-arn "$CLUSTER_ARN" --query 'ClusterInfo.State' --output text --region us-east-1 2>/dev/null || echo "DELETED")
                
                if [ "$status" = "DELETED" ] || [ "$status" = "None" ] || [ -z "$status" ]; then
                    log_success "MSK cluster deleted successfully!"
                    break
                fi
                
                log_info "Current status: $status"
                sleep 30
                elapsed=$((elapsed + 30))
            done
            
            if [ $elapsed -ge $timeout ]; then
                log_warning "MSK cluster deletion timed out. It may still be in progress."
            fi
        else
            log_warning "Failed to initiate MSK cluster deletion."
        fi
    else
        log_warning "MSK cluster not found. Skipping."
    fi
    
    # Delete MSK security group
    local sg_id=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=milvus-msk-sg" --query 'SecurityGroups[0].GroupId' --output text --region us-east-1 2>/dev/null || echo "")
    if [ -n "$sg_id" ] && [ "$sg_id" != "None" ]; then
        safe_run "aws ec2 delete-security-group --group-id '$sg_id' --region us-east-1" "Deleting MSK security group"
    fi
}

# Delete EKS cluster
cleanup_eks() {
    log_info "Cleaning up EKS cluster..."
    
    # Check if eksctl is available
    if ! command -v eksctl &> /dev/null; then
        log_warning "eksctl not found. Skipping EKS cluster deletion."
        return
    fi
    
    if eksctl get cluster --name milvus-eks-cluster --region us-east-1 &>/dev/null; then
        log_info "Deleting EKS cluster: milvus-eks-cluster"
        
        # Clean up security groups first to prevent VPC deletion issues
        cleanup_eks_security_groups
        
        # Delete the cluster with timeout
        if timeout 3600 eksctl delete cluster --name milvus-eks-cluster --region us-east-1 --wait; then
            log_success "EKS cluster deleted successfully!"
        else
            log_warning "EKS cluster deletion failed or timed out. Attempting manual cleanup..."
            
            # Try to clean up failed CloudFormation stacks
            cleanup_failed_cloudformation_stacks
            
            # Wait a bit and try security group cleanup again
            sleep 30
            cleanup_eks_security_groups
        fi
    else
        log_warning "EKS cluster 'milvus-eks-cluster' not found. Skipping."
    fi
}

# Delete S3 bucket
cleanup_s3() {
    log_info "Cleaning up S3 buckets..."
    
    # Clean up all Milvus-related buckets
    local milvus_buckets=$(aws s3 ls 2>/dev/null | grep "milvus-bucket-" | awk '{print $3}' || echo "")
    
    if [ -n "$milvus_buckets" ]; then
        for bucket in $milvus_buckets; do
            log_info "Emptying and deleting S3 bucket: $bucket"
            
            # Empty bucket first (handle both versioned and non-versioned objects)
            safe_run "aws s3 rm s3://'$bucket' --recursive" "Emptying bucket $bucket"
            
            # Delete any object versions if versioning is enabled
            aws s3api list-object-versions --bucket "$bucket" --query 'Versions[].{Key:Key,VersionId:VersionId}' --output text 2>/dev/null | \
            while read -r key version_id; do
                if [ -n "$key" ] && [ -n "$version_id" ]; then
                    aws s3api delete-object --bucket "$bucket" --key "$key" --version-id "$version_id" 2>/dev/null || true
                fi
            done
            
            # Delete any delete markers
            aws s3api list-object-versions --bucket "$bucket" --query 'DeleteMarkers[].{Key:Key,VersionId:VersionId}' --output text 2>/dev/null | \
            while read -r key version_id; do
                if [ -n "$key" ] && [ -n "$version_id" ]; then
                    aws s3api delete-object --bucket "$bucket" --key "$key" --version-id "$version_id" 2>/dev/null || true
                fi
            done
            
            # Delete bucket
            safe_run "aws s3 rb s3://'$bucket' --force" "Deleting bucket $bucket"
        done
    else
        log_warning "No Milvus S3 buckets found. Skipping."
    fi
}

# Delete IAM policies
cleanup_iam() {
    log_info "Cleaning up IAM policies..."
    
    if [ -n "$user_name" ] && [ -n "$account_id" ]; then
        local policy_arn="arn:aws:iam::${account_id}:policy/MilvusS3ReadWrite"
        
        # Check if policy exists
        if aws iam get-policy --policy-arn "$policy_arn" &>/dev/null; then
            # Detach policy from user
            safe_run "aws iam detach-user-policy --user-name '$user_name' --policy-arn '$policy_arn'" "Detaching IAM policy from user"
            
            # Detach from any roles that might have it
            local attached_roles=$(aws iam list-entities-for-policy --policy-arn "$policy_arn" --query 'PolicyRoles[].RoleName' --output text 2>/dev/null || echo "")
            if [ -n "$attached_roles" ]; then
                for role in $attached_roles; do
                    safe_run "aws iam detach-role-policy --role-name '$role' --policy-arn '$policy_arn'" "Detaching IAM policy from role $role"
                done
            fi
            
            # Detach from any groups that might have it
            local attached_groups=$(aws iam list-entities-for-policy --policy-arn "$policy_arn" --query 'PolicyGroups[].GroupName' --output text 2>/dev/null || echo "")
            if [ -n "$attached_groups" ]; then
                for group in $attached_groups; do
                    safe_run "aws iam detach-group-policy --group-name '$group' --policy-arn '$policy_arn'" "Detaching IAM policy from group $group"
                done
            fi
            
            # Delete policy
            safe_run "aws iam delete-policy --policy-arn '$policy_arn'" "Deleting IAM policy"
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
    
    # Check for required tools
    local missing_tools=()
    command -v aws >/dev/null 2>&1 || missing_tools+=("aws")
    command -v jq >/dev/null 2>&1 || missing_tools+=("jq")
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_error "Please install the missing tools and try again."
        exit 1
    fi
    
    confirm_cleanup
    get_environment_vars
    
    # Run cleanup functions in order, continuing even if some fail
    cleanup_milvus
    cleanup_msk
    cleanup_eks
    cleanup_s3
    cleanup_iam
    
    # Final cleanup attempt for any remaining resources
    log_info "Performing final cleanup checks..."
    cleanup_failed_cloudformation_stacks
    
    log_success "Cleanup completed!"
    log_info "All Milvus on EKS resources have been removed or cleanup attempted."
    log_warning "If any resources remain, you may need to delete them manually through the AWS Console."
}

# Run main function
main "$@"
