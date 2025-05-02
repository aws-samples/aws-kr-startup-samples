Read this in other languages: English, [Korean(한국어)](./README.kr.md)

# Exercise 3: Building an MCP Client and Connecting to an MCP Server

In this module, you will learn how to build a Streamlit MCP Host chatbot based on the MCP (Model Context Protocol) client and how to integrate it with the MCP server deployed in the previous module. Through this, you will practice the client-side implementation of MCP, which is a standard protocol for interaction between LLMs and external tools.

# Prerequisites

## Bedrock Model Access Setup

1. Access the AWS console and navigate to the Amazon Bedrock service.

2. Select 'Model access' from 'Bedrock configurations' in the left navigation.

3. Click the 'Modify model access' button to go to the 'Edit model access' screen, then enable access to the Amazon Nova Lite model.

## Setting Up a Virtual Environment and Installing Dependencies:

Run the following commands in the IDE terminal to create a Python virtual environment:

```bash
uv venv --python 3.11
source .venv/bin/activate
```

Run the following command to install the necessary dependency packages:

```bash
uv pip install -r requirements.txt
```

You can test the MCP Client by running the following command in the terminal.
Add the `/sse` endpoint to the MCP Server URL deployed in module-02 and pass it as a command-line argument.

```bash
python app/streamplit-app/client.py <MCP Server URL from module-02>/sse
```

Enter a query like `What's the weather in Newyork?` to check the response. If a normal response is returned, the client setup is complete.

# Checking the Application

## Running Locally

Run the following command in the IDE terminal to launch the Streamlit application:

```bash
streamlit run app/streamplit-app/app.py
```

## Deploying to AWS Environment

Open the `cdk.context.json` file in the cdk folder and add the cdk outputs values deployed in module-02:

```bash
McpServerAmazonECSStack.McpServerAmazonECSStackClusterNameOutput = McpServerAmazonECSStack-***
McpServerAmazonECSStack.McpServerAmazonECSStackListenerArnOutput = arn:aws:elasticloadbalancing:***
McpServerAmazonECSStack.McpServerAmazonECSStackVpcIdOutput = vpc-***
```

```json
{
  "vpc-id": "McpServer***",
  "cluster-name": "McpServerAmazonECSStack-***",
  "listener-arn": "arn:aws:elasticloadbalancing:***"
}
```

Then run the following command in the IDE terminal to deploy the CDK Stack:

```bash
cdk deploy --require-approval never
```

Access `http://<MCP Server URL from module-02>/app` to see the deployed Streamlit application.

# References

- [Model Context Protocol Official Documentation](https://modelcontextprotocol.io/)
- [langchain-aws Library Documentation](https://python.langchain.com/docs/integrations/providers/aws/)
- [LangChain MCP Adapters Repository](https://github.com/langchain-ai/langchain-mcp-adapters)
- [LangGraph Framework Official Documentation](https://langchain-ai.github.io/langgraph/)
