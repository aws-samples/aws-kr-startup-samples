import os
from aws_cdk import CfnOutput, Stack, RemovalPolicy
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3deploy
from constructs import Construct

class ByocFaceChainCodeBuildStack(Stack):
    def __init__(self, scope: Construct, id: str, repository: ecr.IRepository, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        # Store repository as instance variable
        self.repository = repository

        # Get the absolute path of the project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        facechain_dir = os.path.join(project_root, "byoc", "facechain")

        # Verify if the directory exists
        if not os.path.exists(facechain_dir):
            raise ValueError(f"Directory not found: {facechain_dir}")

        # Create an S3 bucket to store the Dockerfile and source files
        bucket = s3.Bucket(self, "ByocFaceChainSourceBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True)

        # Upload the Dockerfile and src directory to the S3 bucket
        s3_deployment = s3deploy.BucketDeployment(self, "DeployDockerfileAndSrc",
            sources=[s3deploy.Source.asset(facechain_dir)],
            destination_bucket=bucket,
            destination_key_prefix="source")

        # Create a CodeBuild project
        self.project = codebuild.Project(self, "ByocFaceChainBuildProject",
            project_name="ByocFaceChainBuildProject",
            description="Build Docker image for BYOC FaceChain",
            environment=codebuild.BuildEnvironment(
                privileged=True,
                build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_4,
                compute_type=codebuild.ComputeType.LARGE
            ),
            source=codebuild.Source.s3(
                bucket=bucket,
                path="source/"
            ),
            environment_variables={
                "ECR_REPO": codebuild.BuildEnvironmentVariable(value=repository.repository_uri),
                "ECR_REPOSITORY": codebuild.BuildEnvironmentVariable(value="huggingface-pytorch-inference"),
                "IMAGE_TAG": codebuild.BuildEnvironmentVariable(value="1.13.1-transformers4.26.0-gpu-py39-cu117-ubuntu20.04")
            },
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "pre_build": {
                        "commands": [
                            "export ECR_REGISTRY=763104351884.dkr.ecr.${AWS_REGION}.amazonaws.com",
                            "echo Logging in to Amazon ECR...",
                            "aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY",
                            "TIMESTAMP=$(date +%Y%m%d%H%M%S)",
                            "BUILD_IMAGE_TAG=${TIMESTAMP}_build",
                            "echo ECR_REPO: $ECR_REPO",
                            "echo ECR_REGISTRY: $ECR_REGISTRY",
                        ]
                    },
                    "build": {
                        "commands": [
                            "echo Build started on `date`",
                            "echo Building the Docker image...",
                            "docker build --build-arg ECR_REGISTRY=$ECR_REGISTRY --build-arg ECR_REPOSITORY=$ECR_REPOSITORY --build-arg IMAGE_TAG=$IMAGE_TAG -t $ECR_REPO:$BUILD_IMAGE_TAG .",
                            "docker tag $ECR_REPO:$BUILD_IMAGE_TAG $ECR_REPO:latest"
                        ]
                    },
                    "post_build": {
                        "commands": [
                            "echo Build completed on `date`",
                            "echo Logging in to Amazon ECR...",
                            "aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO",
                            "echo Pushing the Docker image...",
                            "docker push $ECR_REPO:$BUILD_IMAGE_TAG",
                            "docker push $ECR_REPO:latest",
                            "echo Writing image definitions file...",
                            "printf '{\"ImageURI\":\"%s\"}' $ECR_REPO:$BUILD_IMAGE_TAG > imageDetail.json"
                        ]
                    }
                },
                "artifacts": {
                    "files": ["imageDetail.json"]
                }
            })
        )

        # Add dependency to ensure S3 deployment completes before CodeBuild project is created
        self.project.node.add_dependency(s3_deployment)

        # Grant CodeBuild permissions to push to ECR
        repository.grant_pull_push(self.project)

        # Grant CodeBuild permissions to read from S3
        bucket.grant_read(self.project)

        # Grant CodeBuild permissions to create and manage ECR images
        self.project.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "ecr:BatchCheckLayerAvailability",
                "ecr:CompleteLayerUpload",
                "ecr:GetAuthorizationToken",
                "ecr:InitiateLayerUpload",
                "ecr:PutImage",
                "ecr:UploadLayerPart"
            ],
            resources=["*"]
        ))

        # Grant CodeBuild permissions to pull from the base image ECR
        self.project.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage"
            ],
            resources=[f"arn:aws:ecr:*:763104351884:repository/*"]
        ))

        # Output the CodeBuild project name
        CfnOutput(self, "FaceChainCodeBuildProjectName", value=self.project.project_name)
