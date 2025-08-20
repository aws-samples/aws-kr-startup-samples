import os
from pathlib import Path
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_s3 as s3,
)
from constructs import Construct


class AgentLambdaStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        packaging_dir = Path(__file__).parent / "packaging"
        dependencies_zip = packaging_dir / "dependencies.zip"
        app_zip = packaging_dir / "app.zip"
        
        # S3 버킷 생성 (보안 스캔 결과 저장용)
        security_scan_bucket = s3.Bucket(
            self, "SecurityScanBucket",
            bucket_name=f"aws-security-scan-{self.account}-{self.region}",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,  # 데이터 보존
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="ArchiveOldScans",
                    enabled=True,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90)
                        )
                    ]
                )
            ]
        )
        
        # Lambda Layer for dependencies
        dependencies_layer = _lambda.LayerVersion(
            self, "SecurityAgentDependenciesLayer",
            code=_lambda.Code.from_asset(str(dependencies_zip)),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            description="Dependencies for AWS Security Agent Lambda"
        )
        
        # Lambda Function
        security_agent_function = _lambda.Function(
            self, "SecurityAgentLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            function_name="AWSSecurityAgentFunction",
            handler="agent_handler.handler",
            code=_lambda.Code.from_asset(str(app_zip)),
            timeout=Duration.minutes(15),  # 15분으로 유지
            memory_size=2048,  # 메모리를 2GB로 증가
            layers=[dependencies_layer],
            architecture=_lambda.Architecture.X86_64,
            environment={
                "PYTHONPATH": "/opt/python",
                "SECURITY_SCAN_BUCKET": security_scan_bucket.bucket_name,
                "BYPASS_TOOL_CONSENT": "true",
                "TMPDIR": "/tmp",  # python_repl이 임시 디렉터리를 사용하도록
                "TEMP": "/tmp",
                "TMP": "/tmp"
            }
        )
        
        # Bedrock permissions
        security_agent_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=["*"]
            )
        )
        
        # CloudTrail permissions
        security_agent_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "cloudtrail:LookupEvents",
                    "cloudtrail:DescribeTrails"
                ],
                resources=["*"]
            )
        )
        
        # S3 permissions (스캔 대상 + 결과 저장)
        security_agent_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:ListAllMyBuckets",
                    "s3:GetBucketPublicAccessBlock",
                    "s3:GetBucketAcl",
                    "s3:GetBucketPolicy"
                ],
                resources=["*"]
            )
        )
        
        # 보안 스캔 결과 저장 버킷 권한
        security_scan_bucket.grant_read_write(security_agent_function)
        
        # EC2 permissions
        security_agent_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "ec2:DescribeSecurityGroups",
                    "ec2:DescribeInstances"
                ],
                resources=["*"]
            )
        )
        
        # IAM permissions
        security_agent_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "iam:GetAccountSummary",
                    "iam:ListUsers",
                    "iam:ListRoles"
                ],
                resources=["*"]
            )
        )
        
        # STS permissions
        security_agent_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["sts:GetCallerIdentity"],
                resources=["*"]
            )
        )
        
        # CloudWatch Logs permissions
        security_agent_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                resources=["*"]
            )
        )