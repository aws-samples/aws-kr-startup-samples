import time
from aws_cdk import (
    Duration,
    Stack,
    RemovalPolicy,
    CfnOutput,
    aws_apigateway as apigateway,
    aws_wafv2 as wafv2,
    aws_s3 as s3,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
)
from constructs import Construct

class WafLogGeneratorStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 bucket for WAF logs with security enhancements
        timestamp = str(int(time.time()))
        logs_bucket = s3.Bucket(self, "WafLogsBucket",
            bucket_name=f"aws-waf-logs-{self.account}-{self.region}-{timestamp}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.DESTROY
        )

        # API Gateway with Mock responses
        api = apigateway.RestApi(self, "TestApi",
            rest_api_name="waf-test-api"
        )

        # Mock endpoints
        users = api.root.add_resource("users")
        users.add_method("GET", 
            apigateway.MockIntegration(
                integration_responses=[
                    apigateway.IntegrationResponse(status_code="200")
                ],
                request_templates={"application/json": '{"statusCode": 200}'}
            ),
            method_responses=[
                apigateway.MethodResponse(status_code="200")
            ]
        )

        admin = api.root.add_resource("admin")
        admin.add_method("GET",
            apigateway.MockIntegration(
                integration_responses=[
                    apigateway.IntegrationResponse(status_code="403")
                ],
                request_templates={"application/json": '{"statusCode": 403}'}
            ),
            method_responses=[
                apigateway.MethodResponse(status_code="403")
            ]
        )

        # WAF Web ACL
        web_acl = wafv2.CfnWebACL(self, "TestWebACL",
            scope="REGIONAL",
            default_action={"allow": {}},
            rules=[{
                "name": "RateLimitRule",
                "priority": 1,
                "statement": {
                    "rateBasedStatement": {
                        "limit": 20,
                        "aggregateKeyType": "IP"
                    }
                },
                "action": {"block": {}},
                "visibilityConfig": {
                    "sampledRequestsEnabled": True,
                    "cloudWatchMetricsEnabled": True,
                    "metricName": "RateLimit"
                }
            }],
            visibility_config={
                "sampledRequestsEnabled": True,
                "cloudWatchMetricsEnabled": True,
                "metricName": "TestWebACL"
            }
        )

        # Associate WAF with API Gateway
        wafv2.CfnWebACLAssociation(self, "WafAssociation",
            resource_arn=f"arn:aws:apigateway:{self.region}::/restapis/{api.rest_api_id}/stages/{api.deployment_stage.stage_name}",
            web_acl_arn=web_acl.attr_arn
        )

        # WAF Logging to S3 (direct logging with proper bucket name)
        wafv2.CfnLoggingConfiguration(self, "WafLogging",
            resource_arn=web_acl.attr_arn,
            log_destination_configs=[logs_bucket.bucket_arn]
        )

        # EventBridge rules for traffic generation
        # Normal traffic every minute
        events.Rule(self, "NormalTraffic",
            schedule=events.Schedule.rate(Duration.minutes(1)),
            targets=[targets.ApiGateway(api,
                path="/users",
                method="GET"
            )]
        )

        # Burst traffic every 5 minutes (triggers rate limit)
        events.Rule(self, "BurstTraffic",
            schedule=events.Schedule.rate(Duration.minutes(5)),
            targets=[targets.ApiGateway(api,
                path="/admin", 
                method="GET"
            )]
        )

        # Outputs for easy access
        CfnOutput(self, "ApiGatewayUrl",
            value=api.url,
            description="API Gateway URL for testing"
        )
        
        CfnOutput(self, "S3BucketName",
            value=logs_bucket.bucket_name,
            description="S3 bucket name for WAF logs"
        )
        
        CfnOutput(self, "WafLogPath",
            value=f"s3://{logs_bucket.bucket_name}/AWSLogs/{self.account}/WAFLogs/{self.region}/",
            description="S3 path where WAF logs are stored (copy this path for analysis)"
        )
        
        CfnOutput(self, "WafLogConsoleUrl",
            value=f"https://s3.console.aws.amazon.com/s3/buckets/{logs_bucket.bucket_name}?region={self.region}&prefix=AWSLogs/{self.account}/WAFLogs/{self.region}/",
            description="Click to open S3 console and browse WAF logs"
        )
        
        CfnOutput(self, "S3ConsoleUrl",
            value=f"https://s3.console.aws.amazon.com/s3/buckets/{logs_bucket.bucket_name}/AWSLogs/{self.account}/WAFLogs/{self.region}/",
            description="Click to open S3 console and browse WAF logs"
        )
