Read this in other languages: English, [Korean(한국어)](./README.ko.md)

# MCP Server Deployment and Claude Desktop Connection Setup

## Overview
In this module, you will learn how to deploy an MCP (Model Context Protocol) server to AWS using AWS CDK and connect it to the Claude Desktop application. You will build centralized MCP servers that can be shared by multiple users or applications, with both legacy SSE transport and modern Streamable HTTP transport implementations.

## Module Structure

This module contains two different MCP server implementations:

### 1. `mcp-server-cdk/` (Legacy Implementation)
- **Transport**: HTTP+SSE (Server-Sent Events) from 2024-11-05 version
- **Purpose**: Backward compatibility and educational reference
- **Status**: Legacy, maintained for compatibility

### 2. `mcp-server/` (Modern Implementation) ⭐ **Recommended**
- **Transport**: Streamable HTTP from 2025-03-26 specification
- **Purpose**: Production-ready implementation with modern MCP features
- **Status**: Active development, recommended for new projects

## Key Concepts

### MCP Transport Methods
MCP (Model Context Protocol) supports various transport methods for communication between LLMs and external tools. According to the MCP specification (2025-03-26), the following transport methods are available:

#### 1. stdio Transport
- **Execution Method**: Communication through standard input/output (stdin/stdout)
- **Usage Environment**: Primarily used in local environments
- **Characteristics**: The client directly starts and manages the server process
- **Advantages**: Simple setup and no additional network configuration required
- **Use Cases**: Local development environments, single-user scenarios

#### 2. Streamable HTTP Transport (2025-03-26) ⭐ **Current Standard**
- **Execution Method**: Bidirectional communication via HTTP with single endpoint
- **Characteristics**:
  - Single endpoint (`/mcp`) handles all MCP communication
  - Supports both JSON responses and SSE streaming
  - Advanced session management with stateless operation
  - Built-in error recovery and message retransmission
- **Advantages**:
  - Scalable server-client communication
  - Optimized for cloud deployment
  - Better performance and reliability
  - Future-proof design
- **Use Cases**: Production environments, cloud deployments, multi-user scenarios

#### 3. HTTP+SSE Transport (2024-11-05) ⚠️ **Legacy**
- **Execution Method**: Unidirectional event stream via HTTP
- **Endpoints**: Separate `/sse` and `/messages` endpoints
- **Characteristics**: Provides a continuous data stream from server to client
- **Advantages**: Simple implementation, firewall-friendly
- **Use Cases**: Educational purposes, backward compatibility
- **Status**: Deprecated, but maintained for compatibility

### Why We Provide Both Implementations

1. **Educational Value**: Understanding the evolution from SSE to Streamable HTTP
2. **Migration Path**: Existing users can gradually migrate from SSE to Streamable HTTP
3. **Compatibility**: Support for different client implementations
4. **Best Practices**: Demonstrate modern MCP server development patterns

### Recommended Implementation: `mcp-server/`

The modern `mcp-server/` implementation offers:

- **Streamable HTTP Transport**: Latest MCP specification compliance
- **Stateless Operation**: Optimized for cloud scaling
- **Better Performance**: Reduced overhead and improved error handling
- **Production Ready**: Comprehensive logging, monitoring, and health checks
- **Future Proof**: Aligned with ongoing MCP development

## Prerequisites

- AWS account with appropriate permissions
- AWS CDK installed
- Node.js and npm installed
- Python 3.11 or higher

## Quick Start Guide

### Option 1: Modern Implementation (Recommended)

1. **Navigate to the modern implementation**:
   ```bash
   cd mcp-server
   ```

2. **Set up and deploy**:
   ```bash
   # Set up CDK environment
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # .venv\Scripts\activate.bat  # Windows
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Deploy to AWS
   cdk bootstrap  # First time only
   cdk deploy
   ```

3. **Local development**:
   ```bash
   cd app
   pip install -e .
   cd src
   python server.py
   ```

### Option 2: Legacy Implementation (For Compatibility)

1. **Navigate to the legacy implementation**:
   ```bash
   cd mcp-server-cdk
   ```

2. **Follow the traditional deployment process**:
   ```bash
   source .venv/bin/activate
   pip install -r requirements.txt
   cdk deploy
   ```

## Claude Desktop Setup

### For Modern Implementation (Streamable HTTP)

1. **Install MCP client tools**:
   ```bash
   npm install -g @anthropic/mcp-client
   ```

2. **Configure claude_desktop_config.json**:
   ```json
   {
     "mcpServers": {
       "weather": {
         "command": "mcp-client",
         "args": [
           "http://<YOUR-ALB-ENDPOINT>/mcp",
           "--transport", "streamable-http"
         ]
       }
     }
   }
   ```

### For Legacy Implementation (SSE)

1. **Install MCP-Remote**:
   ```bash
   npm install -g mcp-remote
   ```

2. **Configure claude_desktop_config.json**:
   ```json
   {
     "mcpServers": {
       "weather": {
         "command": "npx",
         "args": [
           "mcp-remote",
           "<YOUR-ALB-ENDPOINT>/sse",
           "--allow-http"
         ]
       }
     }
   }
   ```

## Testing the Connection

1. Start a new conversation in Claude Desktop
2. Ask: `What are the active weather alerts in Texas?`
3. Verify that the MCP server responds correctly

## Architecture Comparison

### Modern Implementation (`mcp-server/`)
```
Client → HTTP POST /mcp → StreamableHTTPSessionManager → MCP Server → Weather API
```

### Legacy Implementation (`mcp-server-cdk/`)
```
Client → SSE /sse + POST /messages → SSE Transport → MCP Server → Weather API
```

## Migration from Legacy to Modern

If you're currently using the legacy SSE implementation, here's how to migrate:

1. **Deploy the new implementation** alongside the existing one
2. **Update client configuration** to use Streamable HTTP transport
3. **Test thoroughly** with your existing workflows
4. **Gradually switch traffic** from old to new implementation
5. **Decommission legacy implementation** once migration is complete

## Troubleshooting

### Common Issues

1. **Port conflicts**: Change `PORT` environment variable
2. **Transport mismatch**: Ensure client and server use same transport protocol
3. **Network connectivity**: Verify ALB endpoint accessibility
4. **Dependencies**: Use `uv sync` for consistent Python dependencies

### Debugging Tips

- Check CloudWatch logs for server-side issues
- Use browser developer tools to inspect HTTP requests
- Verify MCP client configuration syntax
- Test with curl for basic connectivity

## Performance Considerations

### Modern Implementation Benefits
- **Lower Latency**: Single HTTP round-trip for most operations
- **Better Scaling**: Stateless design supports horizontal scaling
- **Efficient Resource Usage**: Reduced connection overhead
- **Error Recovery**: Built-in retry and recovery mechanisms

### Legacy Implementation Limitations
- **Multiple Connections**: Requires separate SSE and HTTP connections
- **State Management**: More complex session handling
- **Resource Overhead**: Higher memory and connection usage

## Summary

This module demonstrates the evolution of MCP server deployment patterns, from legacy SSE transport to modern Streamable HTTP transport. The modern implementation in `mcp-server/` represents current best practices for production MCP server deployment, while the legacy implementation in `mcp-server-cdk/` provides backward compatibility and educational value.

Choose the modern implementation for new projects and consider migrating existing deployments to take advantage of improved performance, scalability, and future compatibility.

## References

- [Model Context Protocol Official Documentation](https://modelcontextprotocol.io/)
- [MCP Streamable HTTP Transport Specification](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#streamable-http)
- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/latest/guide/home.html)
- [MCP Client Tools](https://github.com/anthropics/mcp-client)