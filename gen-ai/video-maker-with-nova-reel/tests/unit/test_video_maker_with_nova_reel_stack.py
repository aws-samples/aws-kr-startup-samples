import aws_cdk as core
import aws_cdk.assertions as assertions

from video_maker_with_nova_reel.video_maker_with_nova_reel_stack import VideoMakerWithNovaReelStack

# example tests. To run these tests, uncomment this file along with the example
# resource in video_maker_with_nova_reel/video_maker_with_nova_reel_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = VideoMakerWithNovaReelStack(app, "video-maker-with-nova-reel")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
