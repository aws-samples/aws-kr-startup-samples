from os import path
import os
import json
from aws_cdk import (
    Stack,
    CfnOutput,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
    aws_iam as iam,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
    aws_logs as logs,
    Duration,
)
from constructs import Construct


class PythonStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Configuration from cdk.json
        region = self.node.try_get_context("region")
        github_token = self.node.try_get_context("github_token")
        github_repo = self.node.try_get_context("github_repo")
        bedrock_model_id = self.node.try_get_context("bedrock_model_id")

        # Create IAM Role for Lambda
        lambda_role = self.create_lambda_role()

        # Create Lambda functions
        initiate_pr = self.create_lambda_function('initiatePR', lambda_role, {
            "REGION": region,
            "GITHUB_TOKEN": github_token,
            "GITHUB_REPO": github_repo,
            "BEDROCK_MODEL_ID": bedrock_model_id
        }, handler='initiate_pr.lambda_handler')

        summary_pr = self.create_lambda_function('summaryPR', lambda_role, {
            "GITHUB_TOKEN": github_token,
        }, handler='summary_pr.lambda_handler')

        # Create Step Functions state machine
        state_machine = self.create_state_machine(initiate_pr, summary_pr)

        # Create API Gateway
        api_gateway = self.create_api_gateway(state_machine)

        # Outputs
        self.create_outputs(api_gateway)

    def create_lambda_role(self):
        bedrock_runtime_policy = iam.PolicyStatement(
            actions=[
                "bedrock:InvokeModel",
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            resources=["*"]
        )
        return iam.Role(
            self, 'BedrockLambdaRole',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            inline_policies={'bedrock_runtime_policy': iam.PolicyDocument(statements=[bedrock_runtime_policy])}
        )

    def create_lambda_function(self, id, role, env, handler):
        return lambda_.Function(
            self, id,
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset(
                path.join(os.getcwd(), 'python/lambda'),
                bundling={
                    "image": lambda_.Runtime.PYTHON_3_9.bundling_image,
                    "command": [
                        "bash", "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"
                    ],
                },
            ),
            handler=handler,
            environment=env,
            tracing=lambda_.Tracing.ACTIVE,
            role=role,
            timeout=Duration.minutes(1)
        )

    def create_state_machine(self, initiate_pr, summary_pr):
        initiate_task = sfn_tasks.LambdaInvoke(
            self, 'InitiatePR',
            lambda_function=initiate_pr,
            output_path='$.Payload'
        )

        complete_task = sfn_tasks.LambdaInvoke(
            self, 'SummaryPR',
            lambda_function=summary_pr,
            output_path='$.Payload'
        )

        definition = initiate_task.next(complete_task)

        log_group = logs.LogGroup(
            self, "StateMachineLogGroup",
            log_group_name="/aws/vendedlogs/states/PRSummaryStateMachine",
            retention=logs.RetentionDays.ONE_WEEK
        )

        logging_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "logs:CreateLogDelivery",
                "logs:GetLogDelivery",
                "logs:UpdateLogDelivery",
                "logs:DeleteLogDelivery",
                "logs:ListLogDeliveries",
                "logs:PutLogEvents",
                "logs:PutResourcePolicy",
                "logs:DescribeResourcePolicies",
                "logs:DescribeLogGroups"
            ],
            resources=["*"]
        )

        state_machine = sfn.StateMachine(
            self, 'PRSummaryStateMachine',
            definition=definition,
            timeout=Duration.minutes(10),
            state_machine_type=sfn.StateMachineType.EXPRESS,
            logs=sfn.LogOptions(
                destination=log_group,
                level=sfn.LogLevel.ALL
            )
        )
        state_machine.add_to_role_policy(logging_policy)

        return state_machine

    def create_api_gateway(self, state_machine):
        api_gateway = apigateway.RestApi(
            self, 'ApiGateway',
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_credentials=True,
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=["POST", "OPTIONS"],
                allow_headers=["Content-Type", "Authorization", "Content-Length", "X-Requested-With"]
            )
        )

        api = api_gateway.root.add_resource('api')
        prs = api.add_resource('prs')

        step_functions_integration = apigateway.StepFunctionsIntegration.start_execution(
            state_machine,
            integration_responses=[{
                'statusCode': '202',
                'responseTemplates': {
                    'application/json': json.dumps({
                        'executionArn': '$context.executionArn',
                        'startDate': '$context.requestTime'
                    })
                }
            }]
        )

        prs.add_method(
            'POST',
            step_functions_integration,
            method_responses=[apigateway.MethodResponse(status_code="202")]
        )

        return api_gateway

    def create_outputs(self, api_gateway):
        CfnOutput(self, 'ApiEndpoint', value=api_gateway.url)
        CfnOutput(self, 'ApiDomain', value=api_gateway.url.split('/')[2])
        CfnOutput(self, 'ApiStage', value=api_gateway.deployment_stage.stage_name)
