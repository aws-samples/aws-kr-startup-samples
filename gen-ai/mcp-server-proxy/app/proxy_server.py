import json
import re
from pathlib import Path
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse
import os


def load_config():
    """Load configuration from mcp.json file"""
    config_path = Path(__file__).parent / "mcp.json"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    if "mcpServers" in config:
        filtered_servers = {}
        for server_name, server_config in config["mcpServers"].items():
            sanitized_name = re.sub(r'[^a-zA-Z0-9_-]', '_', server_name)
            
            filtered_config = {}
            for key in ["command", "args", "env"]:
                if key in server_config:
                    filtered_config[key] = server_config[key]
            
            # Ensure env dict exists
            if "env" not in filtered_config:
                filtered_config["env"] = {}
            
            # AWS Fargate Task Role 관련 환경변수들 주입
            aws_env_vars = [
                "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
                "AWS_CONTAINER_CREDENTIALS_FULL_URI", 
                "AWS_CONTAINER_AUTHORIZATION_TOKEN",
                "AWS_DEFAULT_REGION",
                "AWS_REGION"
            ]
            
            for env_var in aws_env_vars:
                # 기존에 설정된 환경변수가 없을 때만 주입
                if env_var in os.environ and env_var not in filtered_config["env"]:
                    filtered_config["env"][env_var] = os.environ[env_var]
            filtered_servers[sanitized_name] = filtered_config
        config["mcpServers"] = filtered_servers
    
    return config


config = load_config()
proxy = FastMCP.as_proxy(config)

@proxy.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")

# async def setup():
#     tools = await proxy.get_tools()
#     print("Available Tools: ", [tool for tool in tools.keys()])

if __name__ == "__main__":
    
    # asyncio.run(setup())
    proxy.run(transport="http", host="0.0.0.0", port=8000)

    