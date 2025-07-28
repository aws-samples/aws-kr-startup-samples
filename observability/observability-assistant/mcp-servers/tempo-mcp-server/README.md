# Tempo MCP Server

A Go-based server implementation for the Model Context Protocol (MCP) with Grafana Tempo integration.

## Overview

This MCP server allows AI assistants to query and analyze distributed tracing data from Grafana Tempo. It follows the Model Context Protocol to provide tool definitions that can be used by compatible AI clients such as Claude Desktop.

## Getting Started

### Prerequisites

* Go 1.21 or higher
* Docker and Docker Compose (for local testing)

### Building and Running

Build and run the server:

```bash
# Build the server
go build -o tempo-mcp-server ./cmd/server

# Run the server
./tempo-mcp-server
```

Or run directly with Go:

```bash
go run ./cmd/server
```

The server uses streamable-http transport method and runs on port 8000 by default.

## Server Endpoints

The server exposes the following endpoint:

- MCP Endpoint: `http://localhost:8000/mcp` - For MCP protocol messaging using streamable-http transport

## Docker Support

You can build and run the MCP server using Docker:

```bash
# Build the Docker image
docker build -t tempo-mcp-server .

# Run the server
docker run -p 8000:8000 --rm -i tempo-mcp-server
```

Alternatively, you can use Docker Compose for a complete test environment:

```bash
# Build and run with Docker Compose
docker-compose up --build
```

## Project Structure

```
.
├── cmd/
│   └── server/       # MCP server implementation
├── internal/
│   └── handlers/     # Tool handlers
└── go.mod            # Go module definition
```

## MCP Server

The Tempo MCP Server implements the Model Context Protocol (MCP) and provides the following tools:

### Search Traces Tool

The `search_traces` tool allows you to search for traces in Grafana Tempo:

* Required parameters:
  * `query`: Tempo trace search query string (e.g., `{service.name="frontend"}`, `{duration>1s}`)
* Optional parameters:
  * `url`: The Tempo server URL (default: from TEMPO_URL environment variable or http://localhost:3200)
  * `start`: Start time for the query (default: 1h ago)
  * `end`: End time for the query (default: now)
  * `limit`: Maximum number of traces to return (default: 20)

### Get Trace by ID Tool

The `get_trace_by_id` tool allows you to retrieve a specific trace by its trace ID:

* Required parameters:
  * `traceID`: The trace ID to retrieve
* Optional parameters:
  * `url`: The Tempo server URL (default: from TEMPO_URL environment variable or http://localhost:3200)
  * `start`: Start time for the search (unix epoch seconds)
  * `end`: End time for the search (unix epoch seconds)

### Search Tags Tool

The `search_tags` tool allows you to search for available tag names in Grafana Tempo:

* Optional parameters:
  * `url`: The Tempo server URL (default: from TEMPO_URL environment variable or http://localhost:3200)
  * `scope`: Scope of the tags (resource|span|intrinsic). Default: all scopes
  * `start`: Start time for the search (unix epoch seconds)
  * `end`: End time for the search (unix epoch seconds)
  * `limit`: Maximum number of tag values to return
  * `maxStaleValues`: Limits the search for tag names

### Search Tag Values Tool

The `search_tag_values` tool allows you to search for values of a specific tag in Grafana Tempo:

* Required parameters:
  * `tagName`: The tag name to search values for (e.g., 'service.name', 'http.method')
* Optional parameters:
  * `url`: The Tempo server URL (default: from TEMPO_URL environment variable or http://localhost:3200)
  * `start`: Start time for the search (unix epoch seconds)
  * `end`: End time for the search (unix epoch seconds)
  * `limit`: Maximum number of tag values to return
  * `maxStaleValues`: Limits the search for tag values

#### Environment Variables

The Tempo MCP server supports the following environment variables:

* `TEMPO_URL`: Default Tempo server URL to use if not specified in the request
* `TEMPO_USERNAME`: Username for basic authentication (optional)
* `TEMPO_PASSWORD`: Password for basic authentication (optional)  
* `TEMPO_TOKEN`: Bearer token for authentication (optional, alternative to username/password)

## Using with Claude Desktop

You can use this MCP server with Claude Desktop to add Tempo query tools. Follow these steps:

1. Build the server or Docker image
2. Configure Claude Desktop to use the server by adding it to your Claude Desktop configuration file

Example Claude Desktop configuration:

```json
{
  "mcpServers": {
    "temposerver": {
      "command": "path/to/tempo-mcp-server",
      "args": [],
      "env": {
        "TEMPO_URL": "http://localhost:3200",
        "TEMPO_USERNAME": "your-username",
        "TEMPO_PASSWORD": "your-password"
      },
      "disabled": false,
      "autoApprove": ["search_traces", "get_trace_by_id", "search_tags", "search_tag_values"]
    }
  }
}
```

Or using bearer token authentication:

```json
{
  "mcpServers": {
    "temposerver": {
      "command": "path/to/tempo-mcp-server",
      "args": [],
      "env": {
        "TEMPO_URL": "http://localhost:3200",
        "TEMPO_TOKEN": "your-bearer-token"
      },
      "disabled": false,
      "autoApprove": ["search_traces", "get_trace_by_id", "search_tags", "search_tag_values"]
    }
  }
}
```

For Docker:

```json
{
  "mcpServers": {
    "temposerver": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "-p", "8000:8000", "-e", "TEMPO_URL=http://host.docker.internal:3200", "-e", "TEMPO_USERNAME=your-username", "-e", "TEMPO_PASSWORD=your-password", "tempo-mcp-server"],
      "disabled": false,
      "autoApprove": ["search_traces", "get_trace_by_id", "search_tags", "search_tag_values"]
    }
  }
}
```

Or using bearer token authentication:

```json
{
  "mcpServers": {
    "temposerver": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "-p", "8000:8000", "-e", "TEMPO_URL=http://host.docker.internal:3200", "-e", "TEMPO_TOKEN=your-bearer-token", "tempo-mcp-server"],
      "disabled": false,
      "autoApprove": ["search_traces", "get_trace_by_id", "search_tags", "search_tag_values"]
    }
  }
}
```

The Claude Desktop configuration file is located at:
* On macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
* On Windows: `%APPDATA%\Claude\claude_desktop_config.json`
* On Linux: `~/.config/Claude/claude_desktop_config.json`

## Using with Cursor

You can also integrate the Tempo MCP server with the Cursor editor. To do this, add the following configuration to your Cursor settings:

```json
{
  "mcpServers": {
    "tempo-mcp-server": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "-p", "8000:8000", "-e", "TEMPO_URL=http://host.docker.internal:3200", "-e", "TEMPO_USERNAME=your-username", "-e", "TEMPO_PASSWORD=your-password", "tempo-mcp-server:latest"]
    }
  }
}
```

Or using bearer token authentication:

```json
{
  "mcpServers": {
    "tempo-mcp-server": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "-p", "8000:8000", "-e", "TEMPO_URL=http://host.docker.internal:3200", "-e", "TEMPO_TOKEN=your-bearer-token", "tempo-mcp-server:latest"]
    }
  }
}
```

## Example Usage

Once configured, you can use the tools in Claude with queries like:

**Search Traces:**
* "Search Tempo for traces with the query `{duration>1s}`"
* "Find traces from the frontend service in Tempo using query `{service.name=\"frontend\"}`"
* "Show me the most recent 50 traces from Tempo with `{http.status_code=500}`"

**Get Trace by ID:**
* "Get the trace with ID `abc123def456` from Tempo"
* "Show me the details of trace `7f8e9d0a-1b2c-3d4e-5f6g-7h8i9j0k1l2m`"

**Search Tags:**
* "What tag names are available in Tempo?"
* "Show me all available span tags in Tempo"
* "List all resource tags available for the last hour"

**Search Tag Values:**
* "What are all the values for the service.name tag in Tempo?"
* "Show me all HTTP methods available in the http.method tag"
* "List all error types in the error.type tag"

<img width="991" alt="Screenshot 2025-04-11 at 5 24 03 PM" src="https://github.com/user-attachments/assets/bcb1fb78-5532-48ab-ada2-4857f6f22514" />


## License

This project is licensed under the MIT License. 
