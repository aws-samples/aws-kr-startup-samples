#!/usr/bin/env python3
from aws_cdk import App
from ec2_stack import EC2InstanceStack

app = App()

# bootstrap 단계에서는 스택을 생성하지 않음
is_bootstrap = app.node.try_get_context("bootstrap") == "true"

if not is_bootstrap:
    EC2InstanceStack(app, "MCPAuthStack")

app.synth()