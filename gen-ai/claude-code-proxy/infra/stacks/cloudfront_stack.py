from aws_cdk import (
    Duration,
    Stack,
    CfnOutput,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_elasticloadbalancingv2 as elbv2,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct


class CloudFrontStack(Stack):
    """CloudFront distribution for securing admin access to ALB."""

    def __init__(
        self,
        scope: Construct,
        id: str,
        alb: elbv2.IApplicationLoadBalancer,
        origin_verify_secret: secretsmanager.ISecret,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        self.origin_verify_secret = origin_verify_secret

        # Attach a shared header so ALB can verify CloudFront-originated traffic.
        self.distribution = cloudfront.Distribution(
            self,
            "AdminDistribution",
            comment="CloudFront distribution for Claude Code Proxy Admin",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.HttpOrigin(
                    alb.load_balancer_dns_name,
                    protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
                    read_timeout=Duration.seconds(300),
                    custom_headers={
                        "X-Origin-Verify": self.origin_verify_secret.secret_value.unsafe_unwrap(),
                    },
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
            ),
            price_class=cloudfront.PriceClass.PRICE_CLASS_200,
            enabled=True,
        )

        CfnOutput(
            self,
            "DistributionDomainName",
            value=self.distribution.distribution_domain_name,
            description="CloudFront Distribution Domain Name",
        )

        CfnOutput(
            self,
            "DistributionId",
            value=self.distribution.distribution_id,
            description="CloudFront Distribution ID",
        )
