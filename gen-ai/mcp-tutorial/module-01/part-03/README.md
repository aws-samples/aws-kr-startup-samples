# Overview

Amazon Q Developer enables autocomplete functionality for hundreds of popular CLIs such as git, npm, docker, and aws. Amazon Q for command line integrates contextual information to enhance understanding of your use cases and provide relevant, context-aware responses. As you start typing, Amazon Q automatically fills in contextually appropriate subcommands, options, and arguments.

In this module, we will learn how to integrate the MCP Server we created in [**Part 1: Building a Local MCP Server and Integrating with Claude Desktop**](../part-01/README.md) with the Amazon Q Developer CLI.

# Prerequisites

The instructions below are based on a MacOS environment. For Amazon Q Developer CLI installation, please refer to [Installing Amazon Q for command line](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line-installing.html).

## 1. Installing Amazon Q Developer CLI

```bash
brew install amazon-q
q --version
```

## 2. Logging in to Amazon Q Developer CLI

Amazon Q Developer CLI provides an interactive chat environment directly in your terminal. You can ask questions, get help with AWS services, troubleshoot issues, and generate code snippets without leaving your command line environment. To start a chat session with Amazon Q, use the chat subcommand.

```bash
q chat
```

This opens an interactive chat session where you can enter questions or commands as shown below:

# Step 1: Configuring MCP Server in Amazon Q Developer CLI

Create a configuration file in your home directory (e.g., ~/.aws/amazonq/mcp.json). This configuration applies to all projects on your computer. We'll use the same values that we set up in [**Part 1: Building a Local MCP Server and Integrating with Claude Desktop**](../part-01/README.md).

```json
{
    "mcpServers": {
        "weather": {
            "command": "uv",
            "args": [
                "--directory",
                "/ABSOLUTE/PATH/TO/aws-kr-startup-samples/gen-ai/mcp-tutorial/module-01/part-01/src/example-1",
                "run",
                "weather.py"
            ]
        }
    }
}
```

Verify that the MCP server is properly registered by using the `/tools` command in the CLI.

```bash
/tools
```

# Step 2: Testing the MCP Server in Amazon Q Developer CLI

Enter a question like `What's the weather in Newyork?` to check the response.

# Summary

In this module, we learned how to integrate a local MCP server with the Amazon Q Developer CLI. By connecting the MCP server we built in the previous module with Amazon Q Developer CLI, we can obtain various information and perform tasks through interactive chat directly in the terminal.

# References

- [AWS Blog: Amazon Q Developer CLI now supports Model Context Protocol (MCP)](https://aws.amazon.com/ko/blogs/korea/extend-the-amazon-q-developer-cli-with-mcp/)
- [Using Amazon Q Developer on the command line](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line.html)
