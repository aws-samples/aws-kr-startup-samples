#!/usr/bin/env python3
import aws_cdk as cdk
from persona_chatbot_usermade.persona_chatbot_usermade_stack import PersonaChatbotUsermadeStack

app = cdk.App()
PersonaChatbotUsermadeStack(app, "PersonaChatbotUsermadeStack")

app.synth()