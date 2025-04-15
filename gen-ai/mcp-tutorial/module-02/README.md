# (Module 2) AWS 환경에서 MCP Server를 구축하기 - Claude Desktop에 연동하기

## CDK 배포하기

## Claude Desktop 설정하기

```
npm install -g mcp-remote
```

```
{
  "mcpServers": {
    "weather": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://localhost:8000/sse"
      ]
    }
  }
}
```