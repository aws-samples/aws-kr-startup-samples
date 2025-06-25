Read this in other languages: English, [Korean(한국어)](./README.ko.md)

# MCP Weather Server

A Model Context Protocol (MCP) server that provides weather data from the National Weather Service (NWS) API. This project demonstrates how to deploy an MCP server to AWS using containerization and streamable HTTP transport.

## Overview

This MCP server implements weather-related tools and is designed to be deployed on AWS infrastructure. It provides real-time weather alerts and forecasts for locations within the United States through a streamable HTTP interface.

## Project Structure

```
mcp-server/
├── main.py          # MCP server implementation
├── pyproject.toml   # Project configuration and dependencies
├── Dockerfile       # Container configuration for AWS deployment
├── uv.lock         # Dependency lock file
└── README.md       # This documentation
```

## Features

- **Weather Alerts**: Get active weather alerts for any US state
- **Weather Forecasts**: Get detailed weather forecasts for specific coordinates
- **Streamable HTTP**: HTTP-based transport for reliable MCP communication
- **AWS Ready**: Containerized for easy deployment on AWS services
- **FastMCP Framework**: Built using the modern FastMCP framework

## MCP Tools

### 1. get_alerts
Retrieves active weather alerts for a specified US state.

**Parameters:**
- `state` (string): Two-letter US state code (e.g., "CA", "NY", "TX")

**Returns:** Formatted weather alerts including event type, area, severity, and instructions.

### 2. get_forecast
Retrieves detailed weather forecast for specific coordinates.

**Parameters:**
- `latitude` (float): Latitude of the location
- `longitude` (float): Longitude of the location

**Returns:** 5-day weather forecast with temperature, wind, and detailed descriptions.

## Local Development

### Prerequisites

- Python 3.12 or higher
- uv package manager

### Setup

1. Install dependencies:
```bash
uv sync
```

2. Run the server:
```bash
uv run main.py
```

The server will start on `http://0.0.0.0:8000` using streamable HTTP transport.

## AWS Deployment

This project is designed for AWS deployment using containerization. The included Dockerfile creates a lightweight container suitable for AWS services like ECS, EKS, or App Runner.

### Container Build

```bash
docker build -t mcp-weather-server .
```

### Container Run

```bash
docker run -p 8000:8000 mcp-weather-server
```

## Configuration

The MCP server is configured with:
- **Server Name**: MyWeatherServer
- **Transport**: Streamable HTTP
- **Port**: 8000
- **Host**: 0.0.0.0 (all interfaces)
- **API Source**: National Weather Service (weather.gov)

## Dependencies

- `fastmcp>=2.8.1`: Modern MCP framework
- `httpx>=0.28.1`: Async HTTP client for NWS API calls

## API Integration

The server integrates with the National Weather Service API:
- **Base URL**: `https://api.weather.gov`
- **Format**: GeoJSON
- **Coverage**: United States only
- **Authentication**: Not required
- **Rate Limits**: Respectful usage with proper User-Agent headers

## Error Handling

- Network timeout protection (30-second timeout)
- HTTP status code validation
- Graceful API failure handling
- User-friendly error messages
- Robust async exception handling

## Usage with MCP Clients

This server can be connected to MCP clients (like Claude Desktop) using the streamable HTTP transport:

```json
{
  "mcpServers": {
    "weather": {
      "command": "http",
      "args": ["http://your-aws-endpoint:8000"]
    }
  }
}
```

## Environment Variables

No environment variables are required for basic functionality. The server uses public NWS API endpoints.

## Monitoring

The server includes built-in error handling and logging for monitoring in production environments.