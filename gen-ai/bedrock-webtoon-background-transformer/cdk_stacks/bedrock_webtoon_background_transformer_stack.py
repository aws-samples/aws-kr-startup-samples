from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_sagemaker as sagemaker,
    CfnOutput
)
from constructs import Construct

class BedrockWebtoonBackgroundTransformerStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create VPC for SageMaker
        vpc = ec2.Vpc(
            self, "SageMakerVPC",
            max_azs=2,
            nat_gateways=1
        )

        # Create Security Group for VPC Endpoints
        vpc_endpoint_sg = ec2.SecurityGroup(
            self, "VPCEndpointSecurityGroup",
            vpc=vpc,
            description="Security group for VPC Endpoints",
            allow_all_outbound=True
        )

        # Create Security Group for SageMaker
        sagemaker_sg = ec2.SecurityGroup(
            self, "SageMakerSecurityGroup", 
            vpc=vpc,
            description="Security group for SageMaker Notebook",
            allow_all_outbound=True
        )

        # Allow inbound traffic from SageMaker to VPC Endpoints
        vpc_endpoint_sg.add_ingress_rule(
            peer=sagemaker_sg,
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS from SageMaker"
        )

        # Create VPC Endpoints
        vpc.add_interface_endpoint(
            "BedrockEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.BEDROCK_RUNTIME,
            private_dns_enabled=True,
            security_groups=[vpc_endpoint_sg]
        )

        vpc.add_interface_endpoint(
            "SageMakerAPIEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SAGEMAKER_API,
            private_dns_enabled=True,
            security_groups=[vpc_endpoint_sg]
        )

        vpc.add_interface_endpoint(
            "SageMakerRuntimeEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SAGEMAKER_RUNTIME,
            private_dns_enabled=True,
            security_groups=[vpc_endpoint_sg]
        )

        # Create IAM role for SageMaker
        notebook_role = iam.Role(
            self, "SageMakerNotebookRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com")
        )
        
        # Add Bedrock access policy
        notebook_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:*"
                ],
                resources=["*"]
            )
        )

        # Create SageMaker Notebook
        notebook = sagemaker.CfnNotebookInstance(
            self, "SageMakerNotebook",
            notebook_instance_name="bedrock-sagemaker-notebook",
            instance_type="ml.t3.medium",
            platform_identifier="notebook-al2-v2",
            role_arn=notebook_role.role_arn,
            root_access="Disabled",
            subnet_id=vpc.private_subnets[0].subnet_id,
            security_group_ids=[sagemaker_sg.security_group_id],
            direct_internet_access="Disabled"  # Disable direct internet access to force VPC endpoint usage
        )

        # Output
        CfnOutput(
            self, "NotebookName",
            value=notebook.notebook_instance_name,
            description="SageMaker Notebook Instance Name"
        )
