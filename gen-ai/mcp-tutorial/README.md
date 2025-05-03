Read this in other languages: English, [Korean(한국어)](./README.ko.md)

## Getting started with MCP(Model Context Protocol)

This workshop is designed to build comprehensive infrastructure capabilities from local/cloud deployment of **Model Context Protocol(MCP)** servers to integration with AWS-based applications.

Through practical exercises, you can understand the mechanism of connecting AI models and external systems, and implement MCP-based solution architectures applicable to real business scenarios.

## Key Learning Objectives
- Design AI-infrastructure integration systems using the **MCP protocol**
- Deploy cloud-native MCP servers using **AWS CDK**
- Implement LLM extension capabilities through real-time integration with **MCP Client applications**

## Module Details

**Module-01: Building a Local MCP Server**[:link:](./module-01/)
- **Part 1: Basic MCP Server Setup**[:link:](./module-01/part-01/)

  Build a Python-based MCP server on a local machine and implement tool calling functionality by integrating with Claude Desktop.

- **Part 2: Using Public MCP Servers**[:link:](./module-01/part-02/)

  Learn how to integrate with open-source MCP servers provided by Smithery.

- **Part 3: Integrating the Local MCP Server with Amazon Q Developer CLI**[:link:](./module-01/part-03/)

  Learn how to integrate your local MCP server with the Amazon Q Developer CLI.

**Module-02: AWS Cloud Deployment**[:link:](./module-02/)
- **AWS CDK Infrastructure Automation**

  Deploy MCP servers to Amazon ECS clusters through IaC (Infrastructure as Code) using CDK.

- **Claude Desktop Integration**

  Configure a centralized resource management system by connecting the deployed MCP server endpoints to the Claude Desktop application.

**Module-03: Developing a Streamlit MCP Host**[:link:](./module-03/)
- **Building an Interactive Web Interface**

  Develop a Streamlit-based MCP Client application using the Model Context Protocol (MCP).

- **MCP Server Integration**

  Configure an MCP Client-Server system on AWS by integrating a Streamlit-based MCP Client application with an MCP server.

## Workshop Outcomes
- MCP server instances deployed in local/cloud environments
- Infrastructure stacks created with AWS CDK (CloudFormation templates)
- Demo of Streamlit-based LLM application integrated with MCP server

Upon completing this workshop, participants will learn **how to use MCP** when designing and operating End-to-End systems that connect AI models and cloud infrastructure.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
