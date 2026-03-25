from aws_cdk import (
    Stack,
    CfnOutput,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as integrations,
    aws_apigatewayv2_authorizers as authorizers,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_servicediscovery as sd,
)
from constructs import Construct


class ApiGatewayStack(Stack):
    """HTTP API Gateway with VPC Link to ECS (no NLB required).

    Routes:
    - POST /auth/sso (IAM Auth) — SSO user provisioning
    - POST /ak/{access_key}/v1/messages — proxy traffic (access_key in path)
    - POST /v1/messages — proxy traffic (access_key in header)
    - GET /health
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        vpc: ec2.Vpc,
        vpclink_sg: ec2.SecurityGroup,
        ecs_service: ecs.FargateService,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # HTTP API VPC Link (no NLB needed)
        vpc_link = apigwv2.VpcLink(
            self,
            "ProxyVpcLink",
            vpc=vpc,
            security_groups=[vpclink_sg],
            subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
        )

        # Get Cloud Map service from ECS service
        cloud_map_service = ecs_service.cloud_map_service

        # HTTP API
        api = apigwv2.HttpApi(
            self,
            "ProxyApi",
            api_name="claude-code-proxy",
            description="Claude Code Proxy — bedrock_only + SSO",
        )

        # Integration via Cloud Map service discovery
        ecs_integration = integrations.HttpServiceDiscoveryIntegration(
            "EcsIntegration",
            service=cloud_map_service,
            vpc_link=vpc_link,
        )

        # --- POST /auth/sso (IAM Auth) ---
        iam_authorizer = authorizers.HttpIamAuthorizer()
        api.add_routes(
            path="/auth/sso",
            methods=[apigwv2.HttpMethod.POST],
            integration=ecs_integration,
            authorizer=iam_authorizer,
        )

        # --- POST /ak/{access_key}/v1/messages ---
        api.add_routes(
            path="/ak/{access_key}/v1/messages",
            methods=[apigwv2.HttpMethod.POST],
            integration=ecs_integration,
        )

        # --- POST /v1/messages (header auth) ---
        api.add_routes(
            path="/v1/messages",
            methods=[apigwv2.HttpMethod.POST],
            integration=ecs_integration,
        )

        # --- GET /health ---
        api.add_routes(
            path="/health",
            methods=[apigwv2.HttpMethod.GET],
            integration=ecs_integration,
        )

        # IAM policy for SSO users to invoke /auth/sso
        self.sso_invoke_policy = iam.ManagedPolicy(
            self,
            "SsoInvokePolicy",
            statements=[
                iam.PolicyStatement(
                    actions=["execute-api:Invoke"],
                    resources=[
                        f"arn:aws:execute-api:{self.region}:{self.account}:{api.http_api_id}/*/POST/auth/sso",
                    ],
                )
            ],
        )

        CfnOutput(self, "ApiUrl", value=api.url or "")
        CfnOutput(
            self,
            "SsoEndpoint",
            value=f"{api.url}auth/sso",
            description="SSO authentication endpoint (IAM Auth)",
        )
        CfnOutput(
            self,
            "SsoInvokePolicyArn",
            value=self.sso_invoke_policy.managed_policy_arn,
            description="Attach to SSO roles for /auth/sso access",
        )
