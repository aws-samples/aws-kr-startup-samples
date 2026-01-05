#!/usr/bin/env python3
import aws_cdk as cdk
from stacks.network_stack import NetworkStack
from stacks.secrets_stack import SecretsStack
from stacks.database_stack import DatabaseStack
from stacks.compute_stack import ComputeStack
from stacks.cloudfront_stack import CloudFrontStack

app = cdk.App()

env = cdk.Environment(
    account=app.node.try_get_context("account"),
    region=app.node.try_get_context("region") or "ap-northeast-2",
)

network = NetworkStack(app, "NetworkStack", env=env)
secrets = SecretsStack(app, "SecretsStack", env=env)
database = DatabaseStack(app, "DatabaseStack", vpc=network.vpc, db_sg=network.db_sg, env=env)
compute = ComputeStack(
    app,
    "ComputeStack",
    vpc=network.vpc,
    alb_sg=network.alb_sg,
    ecs_sg=network.ecs_sg,
    db_secret=database.db_secret,
    kms_key=secrets.kms_key,
    secrets=secrets,
    env=env,
)

# CloudFront Stack for securing admin access
# ALB is protected by CloudFront prefix list SG + custom header validation
CloudFrontStack(
    app,
    "CloudFrontStack",
    alb=compute.load_balancer,
    origin_verify_secret=compute.origin_verify_secret,
    env=env,
)

app.synth()
