import os
from pathlib import Path
from aws_cdk import (
    Stack,
    aws_ecr as ecr,
    aws_ecr_assets as ecr_assets,
    aws_eks as eks,
    aws_iam as iam,
    aws_lambda as lambda_,
    RemovalPolicy,
    CfnOutput,
    Fn,
)
from constructs import Construct
import cdk_ecr_deployment as ecr_deploy


class ObservabilityAssistantStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, cluster_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.cluster_name = cluster_name
        
        # Build and push Docker images using CDK Docker assets
        self.build_docker_assets()
        
        # Get EKS cluster reference
        self.get_eks_cluster()
        
        # Create Pod Identity resources
        self.create_pod_identity_resources()
        
        # Output values for Helm deployment
        self.output_helm_values()
    

    
    def build_docker_assets(self):
        """Build Docker images as CDK assets with dedicated ECR repositories"""
        # Create ECR repositories
        self.observability_repo = ecr.Repository(
            self, "ObservabilityAssistantRepo",
            repository_name="observability-assistant/agent",
            removal_policy=RemovalPolicy.DESTROY
        )
        
        self.tempo_repo = ecr.Repository(
            self, "TempoMcpServerRepo",
            repository_name="observability-assistant/tempo-mcp-server",
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Build observability assistant image
        self.observability_asset = ecr_assets.DockerImageAsset(
            self, "ObservabilityAssistantAsset",
            directory=str(Path(__file__).parent.parent),
            file="Dockerfile",
            platform=ecr_assets.Platform.LINUX_AMD64,
            exclude=[
                ".venv",
                ".git", 
                "cdk/cdk.out",
                "cdk/.venv",
                "node_modules",
                "*.pyc",
                "__pycache__",
                ".pytest_cache",
                ".coverage",
                "*.egg-info"
            ]
        )
        
        # Build tempo MCP server image  
        self.tempo_asset = ecr_assets.DockerImageAsset(
            self, "TempoMcpServerAsset", 
            directory=str(Path(__file__).parent.parent / "mcp-servers" / "tempo-mcp-server"),
            file="Dockerfile",
            platform=ecr_assets.Platform.LINUX_AMD64,
            exclude=[
                ".git",
                "*.pyc", 
                "__pycache__",
                ".pytest_cache",
                "node_modules"
            ]
        )
        
        # Deploy images to specific repositories using cdk-ecr-deployment
        self.observability_deployment = ecr_deploy.ECRDeployment(
            self, "ObservabilityAssistantDeployment",
            src=ecr_deploy.DockerImageName(self.observability_asset.image_uri),
            dest=ecr_deploy.DockerImageName(f"{self.observability_repo.repository_uri}:latest")
        )
        
        self.tempo_deployment = ecr_deploy.ECRDeployment(
            self, "TempoMcpServerDeployment",
            src=ecr_deploy.DockerImageName(self.tempo_asset.image_uri),
            dest=ecr_deploy.DockerImageName(f"{self.tempo_repo.repository_uri}:latest")
        )
    
    
    def get_eks_cluster(self):
        """Get reference to existing EKS cluster"""
        # Get the cluster's kubectl role ARN from context or create one
        kubectl_role_arn = self.node.try_get_context("kubectl_role_arn")
        
        if not kubectl_role_arn:
            # Create a role for kubectl operations with proper permissions
            kubectl_role = iam.Role(
                self, "KubectlRole",
                assumed_by=iam.CompositePrincipal(
                    iam.ServicePrincipal("lambda.amazonaws.com"),
                    iam.AccountRootPrincipal()
                ),
                managed_policies=[
                    iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
                ]
            )
            
            # Add EKS permissions to the kubectl role
            kubectl_role.add_to_policy(
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "eks:DescribeCluster",
                        "eks:ListClusters"
                    ],
                    resources=["*"]
                )
            )
            
            kubectl_role_arn = kubectl_role.role_arn
        
        self.cluster = eks.Cluster.from_cluster_attributes(
            self, "EksCluster",
            cluster_name=self.cluster_name,
            kubectl_role_arn=kubectl_role_arn
        )
    
    def create_pod_identity_resources(self):
        """Create IAM role and Pod Identity association for Bedrock access"""
        # Create IAM role for the observability assistant pod
        # For EKS Pod Identity, create a custom principal with the correct trust policy
        pod_identity_principal = iam.ServicePrincipal(
            "pods.eks.amazonaws.com",
            conditions={
                "StringEquals": {
                    "aws:SourceAccount": self.account
                }
            }
        )
        
        self.pod_role = iam.Role(
            self, "ObservabilityAssistantPodRole",
            role_name=f"ObservabilityAssistant-{self.cluster_name}-PodRole",
            assumed_by=pod_identity_principal,
            description="IAM role for observability assistant pod to access Bedrock"
        )
        
        # Add the TagSession permission to the role's trust policy
        self.pod_role.assume_role_policy.add_statements(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[pod_identity_principal],
                actions=["sts:TagSession"]
            )
        )
        
        # Add Bedrock permissions
        bedrock_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:ListFoundationModels",
                "bedrock:GetFoundationModel"
            ],
            resources=["*"]  # You can restrict this to specific model ARNs if needed
        )
        
        self.pod_role.add_to_policy(bedrock_policy)
        
        # Add CloudWatch Logs permissions for observability
        logs_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "logs:CreateLogGroup",
                "logs:CreateLogStream", 
                "logs:PutLogEvents",
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams"
            ],
            resources=[f"arn:aws:logs:{self.region}:{self.account}:*"]
        )
        
        self.pod_role.add_to_policy(logs_policy)
        
        # Create Pod Identity Association
        self.pod_identity_association = eks.CfnPodIdentityAssociation(
            self, "ObservabilityAssistantPodIdentity",
            cluster_name=self.cluster_name,
            namespace="default",  # Adjust if using different namespace
            service_account="observability-assistant-sa",
            role_arn=self.pod_role.role_arn
        )
    

    def output_helm_values(self):
        """Output values needed for Helm deployment"""
        # Output the image URIs and other important information for Helm deployment
        
        # Output the image URIs and other important information
        CfnOutput(
            self, "ObservabilityAssistantImageUri",
            value=self.observability_asset.image_uri,
            description="URI of the observability assistant Docker image"
        )
        
        CfnOutput(
            self, "TempoMcpServerImageUri", 
            value=self.tempo_asset.image_uri,
            description="URI of the tempo MCP server Docker image"
        )
        
        CfnOutput(
            self, "PodRoleArn",
            value=self.pod_role.role_arn,
            description="ARN of the IAM role for Pod Identity"
        )
        
        CfnOutput(
            self, "ServiceAccountName",
            value="observability-assistant-sa",
            description="Name of the Kubernetes service account"
        )
        
        CfnOutput(
            self, "HelmChartName",
            value="observability-assistant",
            description="Name of the deployed Helm chart"
        )
        
        CfnOutput(
            self, "ObservabilityAssistantRepoUri",
            value=self.observability_repo.repository_uri,
            description="URI of the observability assistant ECR repository"
        )
        
        CfnOutput(
            self, "TempoMcpServerRepoUri",
            value=self.tempo_repo.repository_uri,
            description="URI of the tempo MCP server ECR repository"
        )