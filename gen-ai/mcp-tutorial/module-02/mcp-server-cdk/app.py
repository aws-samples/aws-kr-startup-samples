#!/usr/bin/env python3
import os

import aws_cdk as cdk

from stacks.mcp_server_amazon_ecs_stack import McpServerAmazonECSStack


app = cdk.App()

mcp_server_amazon_ecs_stack = McpServerAmazonECSStack(app, "McpServerAmazonECSStack")

app.synth()
