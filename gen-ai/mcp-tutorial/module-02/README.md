# (Module 2) AWS 환경에서 MCP Server를 구축하기 - Claude Desktop에 연동하기

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