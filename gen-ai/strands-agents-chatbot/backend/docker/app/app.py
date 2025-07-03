from http.client import HTTPException
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from agent import AWSAgent
from pydantic import BaseModel
from typing import List, Literal
import os

app = FastAPI(title="AWS Chatbot API",
             description="API for managing AWS resources and getting AWS information")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

class TextContent(BaseModel):
    text: str

class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: List[TextContent]

class PromptRequest(BaseModel):
    prompt: str
    messages: List[Message]

@app.get("/")
def read_root():
    return {"status": "OK"}

@app.post("/chat")
async def chat(request: PromptRequest):
    """Chat with the AI agent for AWS-related queries"""
    
    prompt = request.prompt
    messages = [msg.model_dump() for msg in request.messages]

    region_name = os.environ.get("BEDROCK_REGION", 'us-east-1')
    model_id = os.environ.get("BEDROCK_MODEL_ID", 'us.anthropic.claude-3-7-sonnet-20250219-v1:0')

    if not prompt:
        raise HTTPException(status_code=400, detail="No prompt provided")
    
    if not messages:
        raise HTTPException(status_code=400, detail="No messages provided")
    
    return StreamingResponse(
        AWSAgent(region_name=region_name, model_id=model_id).stream_agent_response(prompt, messages),
        media_type="text/event-stream"
    )

@app.get("/health")
def health_check():
    """API health check endpoint"""
    return {"status": "healthy"}