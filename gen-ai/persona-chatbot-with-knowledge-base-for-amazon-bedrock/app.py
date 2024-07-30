#!/usr/bin/env python3
import aws_cdk as cdk
from stacks.knowledge_base_stack import KnowledgeBaseStack
from stacks.chatbot_stack import ChatbotStack

app = cdk.App()

kb_stack = KnowledgeBaseStack(app, "KnowledgeBaseStack")
chatbot_stack = ChatbotStack(app, "ChatbotStack", knowledge_base_id=kb_stack.knowledge_base_id)
chatbot_stack.add_dependency(kb_stack)

app.synth()