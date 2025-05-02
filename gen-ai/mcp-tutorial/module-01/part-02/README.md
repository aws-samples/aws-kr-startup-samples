Read this in other languages: English, [Korean(한국어)](./README.kr.md)

# Using Smithery's MCP Server

## Using Smithery Server from a Local Client

Let's first set up and use the Smithery AI server.

### Prerequisites

1. **Sign up for Smithery AI:** Create an account at the [Smithery AI website](https://www.smithery.ai/) and obtain an API key.
2. **Install Claude Desktop:** Install the Claude Desktop client for your operating system from the [Claude AI website](https://claude.ai/download).

### MCP Configuration

1. Open a terminal and run the following command to install the `@mcp-examples/weather` tool and connect it to the Claude Desktop client.

    ```bash
    npx -y @smithery/cli@latest install @mcp-examples/weather --client claude --key YOUR_API_KEY
    ```

    **Note:** You must replace the `YOUR_API_KEY` part with the actual API key you received.

    Now you are ready to use the `@mcp-examples/weather` tool through the Claude Desktop client.

2. Ask a question as shown below to call the weather MCP. Select "Allow for this conversation" in the popup that asks for tool permission.
    ![prompt](./assets/prompt.png)

3. Claude Desktop generates a response using the MCP server's reply.
    ![weather](./assets/weather.png)

