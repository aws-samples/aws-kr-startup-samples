#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_ec2,
  aws_iam,
  aws_sagemaker
)
from constructs import Construct


class SageMakerStudioStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, vpc, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    sagemaker_execution_policy_doc = aws_iam.PolicyDocument()
    sagemaker_execution_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "resources": ["arn:aws:s3:::*"],
      "actions": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ]
    }))

    sagemaker_custom_access_policy_doc = aws_iam.PolicyDocument()
    sagemaker_custom_access_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "resources": [f"arn:aws:es:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:domain/*"],
      "actions": ["es:ESHttp*"],
      "sid": "ReadFromOpenSearch"
    }))

    sagemaker_custom_access_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "resources": [f"arn:aws:secretsmanager:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:secret:*"],
      "actions": ["secretsmanager:GetSecretValue"],
      "sid": "ReadSecretFromSecretsManager"
    }))

    sagemaker_docker_build_policy_doc = aws_iam.PolicyDocument()
    sagemaker_docker_build_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "resources": ["arn:aws:codebuild:*:*:project/sagemaker-studio*"],
      "actions": [
        "codebuild:DeleteProject",
        "codebuild:CreateProject",
        "codebuild:BatchGetBuilds",
        "codebuild:StartBuild"
      ]
    }))

    sagemaker_docker_build_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "resources": ["arn:aws:logs:*:*:log-group:/aws/codebuild/sagemaker-studio*"],
      "actions": ["logs:CreateLogStream"],
    }))

    sagemaker_docker_build_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "resources": ["arn:aws:logs:*:*:log-group:/aws/codebuild/sagemaker-studio*:log-stream:*"],
      "actions": [
        "logs:GetLogEvents",
        "logs:PutLogEvents"
      ]
    }))

    sagemaker_docker_build_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "resources": ["*"],
      "actions": ["logs:CreateLogGroup"]
    }))

    sagemaker_docker_build_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "resources": ["*"],
      "actions": [
        "ecr:BatchGetImage",
        "ecr:BatchCheckLayerAvailability",
        "ecr:CompleteLayerUpload",
        "ecr:DescribeImages",
        "ecr:DescribeRepositories",
        "ecr:GetDownloadUrlForLayer",
        "ecr:InitiateLayerUpload",
        "ecr:ListImages",
        "ecr:PutImage",
        "ecr:UploadLayerPart",
        "ecr:CreateRepository",
        "ecr:GetAuthorizationToken",
        "ec2:DescribeAvailabilityZones"
      ],
      "sid": "ReadWriteFromECR"
    }))

    sagemaker_docker_build_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "resources": ["*"],
      "actions": ["ecr:GetAuthorizationToken"]
    }))

    sagemaker_docker_build_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "resources": ["arn:aws:s3:::sagemaker-*/*"],
      "actions": [
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:PutObject"
      ]
    }))

    sagemaker_docker_build_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "resources": ["arn:aws:s3:::sagemaker*"],
      "actions": ["s3:CreateBucket"],
    }))

    sagemaker_docker_build_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "resources": ["*"],
      "actions": [
        "iam:GetRole",
        "iam:ListRoles"
      ]
    }))

    sagemaker_docker_build_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "resources": ["arn:aws:iam::*:role/*"],
      "conditions": {
        "StringLikeIfExists": {
          "iam:PassedToService": [
            "codebuild.amazonaws.com"
          ]
        }
      },
      "actions": ["iam:PassRole"]
    }))

    #XXX: For more information, see
    # https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless-data-access.html
    opensearch_serverless_data_access_policy_doc = aws_iam.PolicyDocument()
    opensearch_serverless_data_access_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "sid": "UsingOpenSearchServerlessIntheConsole",
      "effect": aws_iam.Effect.ALLOW,
      "resources": ["*"],
      "actions": [
        "aoss:BatchGetCollection",
        "aoss:GetAccessPolicy",
        "aoss:GetAccountSettings",
        "aoss:GetSecurityConfig",
        "aoss:GetSecurityPolicy",
        "aoss:ListAccessPolicies",
        "aoss:ListCollections",
        "aoss:ListSecurityConfigs",
        "aoss:ListSecurityPolicies",
        "aoss:ListTagsForResource",
        "aoss:ListVpcEndpoints",
        "aoss:UpdateAccessPolicy"
      ]
    }))

    opensearch_serverless_data_access_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "sid": "OpenSearchServerlessCollectionAccess",
      "effect": aws_iam.Effect.ALLOW,
      # arn:{partition}:{service}:{region}:{account}:{resource}{sep}{resource-name}
      "resources": [self.format_arn(service="aoss",
                      region=cdk.Aws.REGION, account=cdk.Aws.ACCOUNT_ID,
                      resource="collection", arn_format=cdk.ArnFormat.SLASH_RESOURCE_NAME,
                      resource_name="*")],
      "actions": [
        "aoss:APIAccessAll"
      ]
    }))

    opensearch_serverless_data_access_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "sid": "OpenSearchServerlessDashboardAccess",
      "effect": aws_iam.Effect.ALLOW,
      # arn:{partition}:{service}:{region}:{account}:{resource}{sep}{resource-name}
      "resources": [self.format_arn(service="aoss",
                      region=cdk.Aws.REGION, account=cdk.Aws.ACCOUNT_ID,
                      resource="dashboards", arn_format=cdk.ArnFormat.SLASH_RESOURCE_NAME,
                      resource_name="default")],
      "actions": [
        "aoss:DashboardsAccessAll"
      ]
    }))

    bedrock_access_policy_doc = aws_iam.PolicyDocument()
    bedrock_access_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "sid": "BedrockList",
      "effect": aws_iam.Effect.ALLOW,
      "resources": ["*"],
      "actions": [
        "bedrock:ListDataSources",
        "bedrock:ListFoundationModelAgreementOffers",
        "bedrock:ListFoundationModels",
        "bedrock:ListIngestionJobs",
        "bedrock:ListKnowledgeBases",
        "bedrock:ListModelInvocationJobs",
      ]
    }))

    bedrock_access_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "sid": "BedrockRead",
      "effect": aws_iam.Effect.ALLOW,
      "resources": ["*"],
      "actions": [
        "bedrock:GetDataSource",
        "bedrock:GetFoundationModel",
        "bedrock:GetFoundationModelAvailability",
        "bedrock:GetIngestionJob",
        "bedrock:GetKnowledgeBase",
        "bedrock:GetModelInvocationJob",
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:ListTagsForResource",
        "bedrock:Retrieve",
      ]
    }))

    bedrock_access_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "sid": "BedrockWrite",
      "effect": aws_iam.Effect.ALLOW,
      "resources": ["*"],
      "actions": [
        "bedrock:CreateFoundationModelAgreement",
        "bedrock:CreateModelInvocationJob",
        "bedrock:CreateProvisionedModelThroughput",
        "bedrock:DeleteFoundationModelAgreement",
        "bedrock:DeleteModelInvocationLoggingConfiguration",
        "bedrock:DeleteProvisionedModelThroughput",
        "bedrock:PutModelInvocationLoggingConfiguration",
        "bedrock:RetrieveAndGenerate",
        "bedrock:StartIngestionJob",
        "bedrock:UpdateDataSource",
        "bedrock:UpdateKnowledgeBase",
      ]
    }))

    bedrock_access_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "sid": "BedrockTagging",
      "effect": aws_iam.Effect.ALLOW,
      "resources": ["*"],
      "actions": [
        "bedrock:TagResource",
        "bedrock:UntagResource",
      ]
    }))

    sagemaker_execution_role = aws_iam.Role(self, 'SageMakerExecutionRole',
      role_name=f'AmazonSageMakerStudioExecutionRole-{self.stack_name}',
      assumed_by=aws_iam.ServicePrincipal('sagemaker.amazonaws.com'),
      path='/',
      inline_policies={
        'sagemaker-execution-policy': sagemaker_execution_policy_doc,
        'sagemaker-custom-access-policy': sagemaker_custom_access_policy_doc,
        'sagemaker-docker-build-policy': sagemaker_docker_build_policy_doc,
        'aoss-access-policy': opensearch_serverless_data_access_policy_doc,
        'bedrock-access-policy': bedrock_access_policy_doc,
      },
      managed_policies=[
        aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSageMakerFullAccess'),
        aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSageMakerCanvasFullAccess'),
        aws_iam.ManagedPolicy.from_aws_managed_policy_name('AWSCloudFormationReadOnlyAccess'),
      ]
    )

    #XXX: To use the sm-docker CLI, the Amazon SageMaker execution role used by the Studio notebook
    # environment should have a trust policy with CodeBuild
    sagemaker_execution_role.assume_role_policy.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "principals": [aws_iam.ServicePrincipal('codebuild.amazonaws.com')],
      "actions": ["sts:AssumeRole"]
    }))

    sm_studio_user_settings = aws_sagemaker.CfnDomain.UserSettingsProperty(
      execution_role=sagemaker_execution_role.role_arn
    )

    sagemaker_studio_domain_name = self.node.try_get_context('sagemaker_studio_domain_name') or 'llm-app-rag-with-kb'
    sagemaker_studio_domain = aws_sagemaker.CfnDomain(self, 'SageMakerStudioDomain',
      auth_mode='IAM', # [SSO | IAM]
      default_user_settings=sm_studio_user_settings,
      domain_name=sagemaker_studio_domain_name,
      subnet_ids=vpc.select_subnets(subnet_type=aws_ec2.SubnetType.PUBLIC).subnet_ids,
      vpc_id=vpc.vpc_id,
      app_network_access_type='PublicInternetOnly' # [PublicInternetOnly | VpcOnly]
    )

    #XXX: https://docs.aws.amazon.com/sagemaker/latest/dg/studio-jl.html#studio-jl-set
    sagmaker_jupyerlab_arn = self.node.try_get_context('sagmaker_jupyterlab_arn')

    default_user_settings = aws_sagemaker.CfnUserProfile.UserSettingsProperty(
      jupyter_server_app_settings=aws_sagemaker.CfnUserProfile.JupyterServerAppSettingsProperty(
        default_resource_spec=aws_sagemaker.CfnUserProfile.ResourceSpecProperty(
          #XXX: JupyterServer apps only support the system value.
          instance_type="system",
          sage_maker_image_arn=sagmaker_jupyerlab_arn
        )
      )
    )

    sagemaker_user_profile = aws_sagemaker.CfnUserProfile(self, 'SageMakerStudioUserProfile',
      domain_id=sagemaker_studio_domain.attr_domain_id,
      user_profile_name='default-user',
      user_settings=default_user_settings
    )

    self.sagemaker_execution_role_arn = sagemaker_execution_role.role_arn
    self.sagemaker_execution_role_name = sagemaker_execution_role.role_name

    cdk.CfnOutput(self, 'DomainUrl',
      value=sagemaker_studio_domain.attr_url,
      export_name=f'{self.stack_name}-DomainUrl')
    cdk.CfnOutput(self, 'DomainId',
      value=sagemaker_user_profile.domain_id,
      export_name=f'{self.stack_name}-DomainId')
    cdk.CfnOutput(self, 'UserProfileName',
      value=sagemaker_user_profile.user_profile_name,
      export_name=f'{self.stack_name}-UserProfileName')
