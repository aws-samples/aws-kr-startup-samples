#!/usr/bin/env python3
import os
import aws_cdk as cdk
from stacks.video_maker_with_nova_reel_stack import VideoMakerWithNovaReelStack

app = cdk.App()

lambda_stack = VideoMakerWithNovaReelStack(app, "VideoMakerWithNovaReelStack")

app.synth()
