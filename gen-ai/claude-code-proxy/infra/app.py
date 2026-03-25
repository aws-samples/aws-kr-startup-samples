#!/usr/bin/env python3
import aws_cdk as cdk
from stacks.network_stack import NetworkStack
from stacks.secrets_stack import SecretsStack
from stacks.database_stack import DatabaseStack
from stacks.compute_stack import ComputeStack
from stacks.api_gateway_stack import ApiGatewayStack

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
    ecs_sg=network.ecs_sg,
    vpclink_sg=network.vpclink_sg,
    db_secret=database.db_secret,
    kms_key=secrets.kms_key,
    secrets=secrets,
    env=env,
)

ApiGatewayStack(
    app,
    "ApiGatewayStack",
    vpc=compute.vpc,
    vpclink_sg=compute.vpclink_sg,
    ecs_service=compute.service,
    env=env,
)

app.synth()
