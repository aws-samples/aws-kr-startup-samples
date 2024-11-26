from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_cloudtrail as cloudtrail,
    aws_athena as athena,
    aws_sagemaker as sagemaker,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_glue as glue,
    RemovalPolicy,
    Duration,
    CfnOutput
)
from constructs import Construct
import uuid

class TextToAnalyzeCloudtrailLogStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create S3 bucket for CloudTrail logs
        # Use a fixed unique bucket name instead of random UUID
        bucket_name = "{UPDATE_WITH_YOUR_UNIQUE_NAME}"  # Update with your unique name
        trail_bucket = s3.Bucket(
            self, "CloudTrailBucket",
            bucket_name=bucket_name,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            enforce_ssl=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(180)
                        )
                    ]
                )
            ],
            removal_policy=RemovalPolicy.RETAIN
        )

        # Create CloudTrail
        trail = cloudtrail.Trail(
            self, "CloudTrail",
            bucket=trail_bucket,
            is_multi_region_trail=True,
            management_events=cloudtrail.ReadWriteType.ALL
        )

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

        # Create VPC Endpoints with security group
        vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3
        )

        vpc.add_interface_endpoint(
            "AthenaEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.ATHENA,
            private_dns_enabled=True,
            security_groups=[vpc_endpoint_sg]
        )

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

        # Add required policies
        notebook_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonAthenaFullAccess")
        )
        
        # Add S3 bucket access policy
        notebook_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket",
                    "s3:PutObject"
                ],
                resources=[
                    trail_bucket.bucket_arn,
                    f"{trail_bucket.bucket_arn}/*"
                ]
            )
        )
        
        notebook_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=["*"]
            )
        )

        # Create SageMaker Notebook
        notebook = sagemaker.CfnNotebookInstance(
            self, "SageMakerNotebook",
            notebook_instance_name="text-to-analyze-cloudtrail-logs",
            instance_type="ml.t3.2xlarge",
            platform_identifier="notebook-al2-v2",
            role_arn=notebook_role.role_arn,
            root_access="Disabled",
            subnet_id=vpc.private_subnets[0].subnet_id,
            security_group_ids=[sagemaker_sg.security_group_id],
            direct_internet_access="Disabled"  # Disable direct internet access to force VPC endpoint usage
        )

        # Create Glue Database
        glue_database = glue.CfnDatabase(
            self, "CloudTrailLogsDatabase",
            catalog_id=Stack.of(self).account,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name="cloudtrail_logs_db",
                description="Database for CloudTrail logs analysis"
            )
        )

        # Create Glue Table
        glue.CfnTable(
            self, "CloudTrailLogsTable",
            catalog_id=Stack.of(self).account,
            database_name="cloudtrail_logs_db",
            table_input=glue.CfnTable.TableInputProperty(
                name="cloudtrail_logs",
                description="CloudTrail logs table",
                parameters={
                    "classification": "cloudtrail"
                },
                storage_descriptor=glue.CfnTable.StorageDescriptorProperty(
                    location=f"s3://{trail_bucket.bucket_name}/AWSLogs/",
                    input_format="com.amazon.emr.cloudtrail.CloudTrailInputFormat",
                    output_format="org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
                    serde_info=glue.CfnTable.SerdeInfoProperty(
                        serialization_library="com.amazon.emr.hive.serde.CloudTrailSerde"
                    ),
                    columns=[
                        glue.CfnTable.ColumnProperty(name="eventversion", type="string"),
                        glue.CfnTable.ColumnProperty(name="useridentity", type="struct<type:string,principalid:string,arn:string,accountid:string,invokedby:string,accesskeyid:string,userName:string,sessioncontext:struct<attributes:struct<mfaauthenticated:string,creationdate:string>,sessionissuer:struct<type:string,principalId:string,arn:string,accountId:string,userName:string>>>"),
                        glue.CfnTable.ColumnProperty(name="eventtime", type="string"),
                        glue.CfnTable.ColumnProperty(name="eventsource", type="string"),
                        glue.CfnTable.ColumnProperty(name="eventname", type="string"),
                        glue.CfnTable.ColumnProperty(name="awsregion", type="string"),
                        glue.CfnTable.ColumnProperty(name="sourceipaddress", type="string"),
                        glue.CfnTable.ColumnProperty(name="useragent", type="string"),
                        glue.CfnTable.ColumnProperty(name="errorcode", type="string"),
                        glue.CfnTable.ColumnProperty(name="errormessage", type="string"),
                        glue.CfnTable.ColumnProperty(name="requestparameters", type="string"),
                        glue.CfnTable.ColumnProperty(name="responseelements", type="string"),
                        glue.CfnTable.ColumnProperty(name="additionaleventdata", type="string"),
                        glue.CfnTable.ColumnProperty(name="requestid", type="string"),
                        glue.CfnTable.ColumnProperty(name="eventid", type="string"),
                        glue.CfnTable.ColumnProperty(name="resources", type="array<struct<arn:string,accountid:string,type:string>>"),
                        glue.CfnTable.ColumnProperty(name="eventtype", type="string"),
                        glue.CfnTable.ColumnProperty(name="apiversion", type="string"),
                        glue.CfnTable.ColumnProperty(name="readonly", type="string"),
                        glue.CfnTable.ColumnProperty(name="recipientaccountid", type="string"),
                        glue.CfnTable.ColumnProperty(name="serviceeventdetails", type="string"),
                        glue.CfnTable.ColumnProperty(name="sharedeventid", type="string"),
                        glue.CfnTable.ColumnProperty(name="vpcendpointid", type="string")
                    ]
                )
            )
        )

        # Outputs
        CfnOutput(
            self, "BucketName",
            value=trail_bucket.bucket_name,
            description="CloudTrail Logs S3 Bucket Name"
        )
        
        CfnOutput(
            self, "NotebookName",
            value=notebook.notebook_instance_name,
            description="SageMaker Notebook Instance Name"
        )

        CfnOutput(
            self, "GlueDatabase",
            value=glue_database.database_input.name,
            description="Glue Database Name"
        )
