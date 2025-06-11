from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi import APIRouter
from main import app

router = APIRouter(tags=["General"])

@router.get("/status")
async def status():
    """Status endpoint that returns the current server status"""
    status_info = {
        "status": "running",
        "server": "FastAPI MCP SSE",
        "version": "0.1.0",
    }
    return JSONResponse(status_info)


@router.get("/health")
async def health_check():
    """Health check endpoint for ALB"""
    return JSONResponse({"status": "healthy"}, status_code=200)


app.include_router(router)