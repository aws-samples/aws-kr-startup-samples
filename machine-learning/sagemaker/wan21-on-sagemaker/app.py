#!/usr/bin/env python3

import os
from aws_cdk import App
from cdk_stacks.sm_execution_role import SageMakerExecutionRoleStack
from cdk_stacks.sm_model import SageMakerWanModelStack
from cdk_stacks.sm_endpoint_config import SageMakerEndpointConfigStack
from cdk_stacks.sm_endpoint import SageMakerEndpointStack

app = App()

s3_bucket = os.environ.get("S3_BUCKET_NAME", "wan-model-bucket-default")
model_data_url = f"s3://{s3_bucket}/models/wan2.1-t2v-1.3b/model.tar.gz"

sm_execution_role_stack = SageMakerExecutionRoleStack(
    app, "WanVideoExecutionRoleStack",
    env={"region": "us-east-1"}
)

sm_model_stack = SageMakerWanModelStack(
    app, "WanVideoModelStack",
    execution_role=sm_execution_role_stack.sm_execution_role,
    model_data_url=model_data_url, 
    env={"region": "us-east-1"}
)
sm_model_stack.add_dependency(sm_execution_role_stack)

sm_endpoint_config_stack = SageMakerEndpointConfigStack(
    app, "WanVideoEndpointConfigStack",
    model=sm_model_stack.model,
    env={"region": "us-east-1"}
)
sm_endpoint_config_stack.add_dependency(sm_model_stack)

sm_endpoint_stack = SageMakerEndpointStack(
    app, "WanVideoEndpointStack",
    endpoint_config=sm_endpoint_config_stack.endpoint_config,
    env={"region": "us-east-1"}
)
sm_endpoint_stack.add_dependency(sm_endpoint_config_stack)

app.synth()