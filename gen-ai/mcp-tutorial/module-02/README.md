Read this in other languages: English, [Korean(한국어)](./README.kr.md)

# MCP Server Deployment and Claude Desktop Connection Setup

## Overview
In this module, you will learn how to deploy an MCP (Model Context Protocol) server to AWS using AWS CDK and connect it to the Claude Desktop application. You will build a centralized MCP server that can be shared by multiple users or applications.

## Key Concepts

### MCP Transport Methods
MCP (Model Context Protocol) supports various transport methods for communication between LLMs and external tools. According to the MCP specification (2025-03-26), the following transport methods are available:

#### 1. stdio Transport
- **Execution Method**: Communication through standard input/output (stdin/stdout)
- **Usage Environment**: Primarily used in local environments
- **Characteristics**: The client directly starts and manages the server process
- **Advantages**: Simple setup and no additional network configuration required
- **Use Cases**: Local development environments, single-user scenarios

#### 2. Streamable HTTP Transport
- **Execution Method**: Bidirectional communication via HTTP POST and GET
- **Characteristics**:
  - Supports both POST and GET at a single endpoint
  - Streaming support through Server-Sent Events (SSE)
  - Session management functionality
- **Advantages**:
  - Scalable server-client communication
  - Session-based state management
  - Support for connection resumption and message retransmission
- **Use Cases**: Cloud environments, multi-user scenarios

#### 3. HTTP+SSE Transport (2024-11-05 version)
- **Execution Method**: Unidirectional event stream via HTTP
- **Endpoint**: `/sse`
- **Characteristics**: Provides a continuous data stream from server to client
- **Advantages**: Easy firewall traversal using standard HTTP
- **Use Cases**: Centralized servers, environments shared by multiple users
- **Compatibility**: Maintains backward compatibility with the 2025-03-26 version

### Why HTTP+SSE Transport was Chosen for this Module

This module uses the HTTP+SSE Transport method from the 2024-11-05 version for the following reasons:

1. **Simple Implementation**: It is simpler to implement compared to Streamable HTTP Transport.
2. **Backward Compatibility**: It ensures backward compatibility with the 2025-03-26 version.
3. **Tutorial Purpose**: As the purpose of this module is to understand the basic concepts of MCP and cloud deployment, we chose a simpler transport method.

For future production environments, you might consider using the Streamable HTTP Transport from the 2025-03-26 version, as it provides advanced features such as session management, connection resumption, and message retransmission.

### MCP-Server-CDK Stack

The MCP-Server-CDK stack creates the following AWS resources:

- **VPC**: Provides a network environment for the MCP server.
- **ECS Cluster**: Provides a container execution environment based on EC2 instances.
- **EC2 Instance**: Uses an ARM-based c6g.xlarge instance to host the MCP server.
- **Application Load Balancer (ALB)**: Distributes traffic to the MCP server and provides an HTTP endpoint.
- **ECS Service and Task Definition**: Provides settings to run the MCP server container.
- **CloudWatch Logs**: Stores and monitors server logs.

## Prerequisites

- AWS account with appropriate permissions
- AWS CDK installed
- Node.js and npm installed

## Practical Guide

### Exercise 1: Deploying the MCP-Server-CDK Stack

1. Navigate to the project directory:
   ```bash
   cd mcp-server-cdk
   ```

2. Activate the virtual environment:
   ```bash
   source .venv/bin/activate  # Linux/Mac
   source.bat                 # Windows
   ```

3. Install the necessary dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Deploy the CDK:
   ```bash
   cdk deploy
   ```

5. Once deployment is complete, note the ALB URL from the output:
   ```
   Outputs:
   McpServerAmazonECSStack.McpServerAmazonECSStackALBHostnameOutput = McpServerAmazonECSStack-xxxxxxxxxxxx.your-region.elb.amazonaws.com
   ```
   > 💡 **Tip**: This URL will be needed for Claude Desktop setup in the next step.

### Exercise 2: Installing MCP-Remote

1. Install MCP-Remote:
   ```bash
   npm install -g mcp-remote
   ```

2. Verify that it's installed:
   ```bash
   which mcp-remote
   ```
   > 💡 **Note**: MCP-Remote is a tool that manages communication between Claude Desktop and the MCP server.

### Exercise 3: Claude Desktop Setup

1. Launch the Claude Desktop application.

2. Navigate to the Settings menu.

3. Find the "Developer" section.

4. Locate claude_desktop_config.json through "Edit Config".

5. Add the following settings to the claude_desktop_config.json file:
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

6. Save the settings and restart Claude Desktop.

### Exercise 4: Testing the Connection

1. Start a new conversation in Claude Desktop.

2. Enter a question like `What's the weather in Sacramento?` to verify that the response is processed through the MCP server.

3. If the response comes back normally, your setup is complete.

## Summary
In this module, you learned how to deploy an MCP server to AWS using AWS CDK and connect it to Claude Desktop. You built a centralized MCP server using the HTTP+SSE Transport method, which provides a scalable environment that can be shared by multiple users. This approach offers the advantage of easy deployment to cloud environments and enables you to build an MCP server infrastructure with scalability and reliability.

## References
- [Model Context Protocol Official Documentation](https://modelcontextprotocol.io/)
- [MCP Transport Specification](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)
- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/latest/guide/home.html)
- [MCP-Remote GitHub Repository](https://github.com/anthropic-labs/mcp-remote)
