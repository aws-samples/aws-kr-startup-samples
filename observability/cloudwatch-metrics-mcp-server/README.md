# CloudWatch Metrics MCP Server

A Model Context Protocol (MCP) server for CloudWatch Metrics

## Instructions

Use this MCP server to run read-only commands and analyze CloudWatch Metrics. Supports discovering metrics namespaces, listing metrics, retrieving metric statistics, and performing advanced metric queries with mathematical expressions. This server enables comprehensive monitoring and analysis of your AWS infrastructure and applications through CloudWatch Metrics.

## Features

- **Namespace Discovery**: Explore available CloudWatch namespaces across your AWS account
- **Metric Discovery**: List and filter metrics within namespaces with dimension support
- **Metric Statistics**: Retrieve statistical data (Average, Sum, Min, Max, SampleCount) for metrics
- **Advanced Metric Queries**: Execute complex queries with mathematical expressions across multiple metrics
- **Dimension Analysis**: Discover available dimensions and their values for better metric filtering

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. An AWS account with [CloudWatch Metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/working_with_metrics.html)
4. This MCP server can only be run locally on the same host as your LLM client.
5. Set up AWS credentials with access to AWS services
   - You need an AWS account with appropriate permissions
   - Configure AWS credentials with `aws configure` or environment variables

## Available Tools

* `list_namespaces` - List available CloudWatch namespaces in your AWS account
* `list_metrics` - List metrics within a namespace with optional filtering by name and dimensions
* `get_metric_statistics` - Retrieve statistical data for a specific metric over a time period
* `list_dimensions` - Discover available dimensions and their values within a namespace
* `get_metric_data` - Execute advanced metric queries with support for multiple metrics and mathematical expressions

### Required IAM Permissions

* `cloudwatch:ListMetrics`
* `cloudwatch:GetMetricStatistics`
* `cloudwatch:GetMetricData`
* `cloudwatch:DescribeAlarms` (optional, for future alarm features)

## Installation

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/install-mcp?name=cloudwatch-metrics-mcp-server&config=eyJhdXRvQXBwcm92ZSI6W10sImRpc2FibGVkIjpmYWxzZSwidGltZW91dCI6NjAsImNvbW1hbmQiOiJ1diIsImFyZ3MiOlsicnVuIiwiY2xvdWR3YXRjaC1tZXRyaWNzLW1jcC1zZXJ2ZXIiXSwiZW52Ijp7iQVdTX1BST0ZJTEUiOiJbVGhlIEFXUyBQcm9maWxlIE5hbWUgdG8gdXNlIGZvciBBV1MgYWNjZXNzXSIsIkFXU19SRUdJT04iOiJbVGhlIEFXUyByZWdpb24gdG8gcnVuIGluXSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwidHJhbnNwb3J0VHlwZSI6InN0ZGlvIn0%3D)

### Installation Options

#### Option 1: Install with uv (Recommended)
```bash
# Install the package in your current environment
uv pip install cloudwatch-metrics-mcp-server
```

#### Option 2: Install with pip
```bash
pip install cloudwatch-metrics-mcp-server
```

#### Option 3: Install from source (for development)
```bash
# Clone the repository
git clone <repository-url>
cd cloudwatch-metrics-mcp-server

# Install in development mode
uv pip install -e .
```

Example for Amazon Q Developer CLI (~/.aws/amazonq/mcp.json):

```json
{
  "mcpServers": {
    "cloudwatch-metrics-mcp-server": {
      "autoApprove": [],
      "disabled": false,
      "timeout": 60,
      "command": "cloudwatch-metrics-mcp-server",
      "env": {
        "AWS_PROFILE": "[The AWS Profile Name to use for AWS access]",
        "AWS_REGION": "[The AWS region to run in]",
        "MCP_TRANSPORT": "stdio",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "transportType": "stdio"
    }
  }
}
```

Alternative using uv run:

```json
{
  "mcpServers": {
    "cloudwatch-metrics-mcp-server": {
      "autoApprove": [],
      "disabled": false,
      "timeout": 60,
      "command": "uv",
      "args": [
        "run",
        "cloudwatch-metrics-mcp-server"
      ],
      "env": {
        "AWS_PROFILE": "[The AWS Profile Name to use for AWS access]",
        "AWS_REGION": "[The AWS region to run in]",
        "MCP_TRANSPORT": "stdio",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "transportType": "stdio"
    }
  }
}
```

### Build and install docker image locally

1. Clone or download this repository
2. Go to the project directory
3. Run 'docker build -t cloudwatch-metrics-mcp-server:latest .'

### Add or update your LLM client's config with following:
```json
{
  "mcpServers": {
    "cloudwatch-metrics-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e", "AWS_PROFILE=[your data]",
        "-e", "AWS_REGION=[your data]",
        "-e", "MCP_TRANSPORT=stdio",
        "cloudwatch-metrics-mcp-server:latest"
      ]
    }
  }
}
```

## Usage Examples

**Important**: This is an MCP server, not a CLI tool. The tools listed below are accessed through MCP clients (like Claude, Cursor, Amazon Q Developer, etc.) after the server is properly configured and running. You cannot run these as direct shell commands.

The following examples show how to use the MCP tools through your MCP client:

### Basic Metric Discovery
```
# List all available namespaces
Use the list_namespaces tool

# List metrics in the AWS/EC2 namespace
Use the list_metrics tool with namespace="AWS/EC2"

# List metrics filtered by name
Use the list_metrics tool with namespace="AWS/EC2" and metric_name="CPUUtilization"
```

### Metric Statistics
```
# Get CPU utilization statistics for an EC2 instance
Use the get_metric_statistics tool with:
- namespace="AWS/EC2"
- metric_name="CPUUtilization"
- start_time="2023-01-01T00:00:00Z"
- end_time="2023-01-01T01:00:00Z"
- period=300
- dimensions=[{"Name":"InstanceId","Value":"i-1234567890abcdef0"}]
```

### Advanced Metric Queries
```
# Execute advanced query with mathematical expression
Use the get_metric_data tool with:
- metric_data_queries=[{"id":"cpu_avg","metricStat":{"metric":{"Namespace":"AWS/EC2","MetricName":"CPUUtilization"},"period":300,"stat":"Average"},"label":"CPU Average"}]
- start_time="2023-01-01T00:00:00Z"
- end_time="2023-01-01T01:00:00Z"
```

### Running the Server Locally

After installation, you can run the server locally:

```bash
# If you installed the package (recommended)
cloudwatch-metrics-mcp-server

# Or using uv run (works with or without installation)
uv run cloudwatch-metrics-mcp-server

# Or if you're developing from source
cd /path/to/cloudwatch-metrics-mcp-server
uv run python -m cloudwatch_metrics_mcp_server.server
```

## Configuration

### Environment Variables

- `AWS_PROFILE`: The AWS profile to use for authentication
- `AWS_REGION`: The AWS region to run in (default: `us-east-1`)
- `MCP_TRANSPORT`: The transport method for the MCP server (default: `streamable-http`)
  - Available options: `stdio`, `streamable-http`
- `FASTMCP_LOG_LEVEL`: Log level for the server (default: `ERROR`)

### Transport Methods

The server supports two transport methods:

- **`stdio`**: Uses standard input/output for communication (recommended for most MCP clients)
- **`streamable-http`**: Uses HTTP streaming for communication

You can configure the transport method using the `MCP_TRANSPORT` environment variable:

```bash
export MCP_TRANSPORT=stdio
cloudwatch-metrics-mcp-server
```

## Contributing

Contributions are welcome! Please open issues and pull requests to help improve the project.
