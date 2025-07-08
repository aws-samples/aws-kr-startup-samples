# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""CloudWatch Metrics MCP Server implementation."""

import asyncio
import boto3
import datetime
import os
from cloudwatch_metrics_mcp_server import MCP_SERVER_VERSION
from cloudwatch_metrics_mcp_server.common import (
    remove_null_values,
    normalize_dimensions,
    extract_namespaces_from_metrics,
    build_metric_data_query_dict,
)
from cloudwatch_metrics_mcp_server.models import (
    Dimension,
    DimensionList,
    DimensionMetadata,
    Datapoint,
    MetricData,
    MetricDataQuery,
    MetricDataResult,
    MetricList,
    MetricMetadata,
    MetricStatistics,
    NamespaceList,
)
from botocore.config import Config
from loguru import logger
from fastmcp import Context, FastMCP
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse
from typing import Any, Dict, List, Literal, Optional


mcp = FastMCP(
    'cloudwatch-metrics-mcp-server',
    instructions='Use this MCP server to run read-only commands and analyze CloudWatch Metrics. Supports discovering metrics namespaces, listing metrics, and retrieving metric data.',
    dependencies=[
        'pydantic',
        'loguru',
    ],
)

# Initialize client
aws_region: str = os.environ.get('AWS_REGION', 'us-east-1')
config = Config(user_agent_extra=f'cloudwatch-metrics-mcp-server/{MCP_SERVER_VERSION}')

try:
    if aws_profile := os.environ.get('AWS_PROFILE'):
        cloudwatch_client = boto3.Session(profile_name=aws_profile, region_name=aws_region).client(
            'cloudwatch', config=config
        )
    else:
        cloudwatch_client = boto3.Session(region_name=aws_region).client('cloudwatch', config=config)
except Exception as e:
    logger.error(f'Error creating CloudWatch client: {str(e)}')
    raise


@mcp.tool(name='list_namespaces')
async def list_namespaces_tool(
    ctx: Context,
    next_token: Optional[str] = Field(
        None,
        description='Token for pagination to get the next set of namespaces',
    ),
    max_results: Optional[int] = Field(
        None,
        description='Maximum number of namespaces to return',
    ),
) -> NamespaceList:
    """Lists available CloudWatch namespaces.

    This tool retrieves a list of all available CloudWatch namespaces in the current AWS account.
    Namespaces are used to organize metrics and are typically associated with AWS services.

    Usage: Use this tool to discover what AWS services and custom applications are publishing
    metrics to CloudWatch, which helps in understanding the monitoring landscape.

    Returns:
    --------
    List of CloudWatch namespaces
        Each namespace represents a category of metrics (e.g., AWS/EC2, AWS/Lambda, AWS/RDS)
    """

    try:
        # Get all metrics to extract namespaces
        paginator = cloudwatch_client.get_paginator('list_metrics')
        kwargs = {}
        if next_token:
            kwargs['NextToken'] = next_token

        all_metrics = []
        for page in paginator.paginate(**kwargs):
            all_metrics.extend(page.get('Metrics', []))

        # Extract unique namespaces
        namespaces = sorted(extract_namespaces_from_metrics(all_metrics))

        # Handle pagination
        response_next_token = None
        if max_results and len(namespaces) > max_results:
            namespaces = namespaces[:max_results]
            response_next_token = str(len(namespaces))

        return NamespaceList(namespaces=namespaces, next_token=response_next_token)

    except Exception as e:
        logger.error(f'Error in list_namespaces_tool: {str(e)}')
        await ctx.error(f'Error listing namespaces: {str(e)}')
        raise


@mcp.tool(name='list_metrics')
async def list_metrics_tool(
    ctx: Context,
    namespace: str = Field(
        ...,
        description='CloudWatch namespace to search for metrics (e.g., AWS/EC2, AWS/Lambda)',
    ),
    metric_name: Optional[str] = Field(
        None,
        description='Filter metrics by name (exact match)',
    ),
    dimensions: Optional[List[Dict[str, str]]] = Field(
        None,
        description='Filter metrics by dimensions (list of {Name: str, Value: str} objects)',
    ),
    max_results: Optional[int] = Field(
        None,
        description='Maximum number of metrics to return',
    ),
    next_token: Optional[str] = Field(
        None,
        description='Token for pagination to get the next set of metrics',
    ),
) -> MetricList:
    """List available metrics within a CloudWatch namespace.

    This tool retrieves metrics from a specified CloudWatch namespace, with optional filtering
    by metric name and dimensions. It's essential for discovering what metrics are available.

    Usage: After discovering namespaces, use this tool to explore available metrics within
    each namespace. This helps identify specific metrics for monitoring and analysis.

    Returns:
    --------
    List of metric metadata
        Each metric contains details such as:
            - metricName: The name of the metric
            - namespace: The CloudWatch namespace
            - dimensions: List of metric dimensions
    """

    try:
        # Normalize dimensions
        normalized_dimensions = normalize_dimensions(dimensions) if dimensions else []

        # Build request parameters
        kwargs = {'Namespace': namespace}

        if metric_name:
            kwargs['MetricName'] = metric_name

        if normalized_dimensions:
            kwargs['Dimensions'] = normalized_dimensions

        if next_token:
            kwargs['NextToken'] = next_token

        # Execute request
        paginator = cloudwatch_client.get_paginator('list_metrics')
        all_metrics = []
        response_next_token = None

        for page in paginator.paginate(**remove_null_values(kwargs)):
            metrics = page.get('Metrics', [])
            all_metrics.extend(metrics)

            # Handle pagination
            if max_results and len(all_metrics) >= max_results:
                all_metrics = all_metrics[:max_results]
                response_next_token = page.get('NextToken')
                break

        # Convert to MetricMetadata objects
        metric_objects = []
        for metric in all_metrics:
            metric_obj = MetricMetadata(
                metricName=metric['MetricName'],
                namespace=metric['Namespace'],
                dimensions=[
                    Dimension(name=dim['Name'], value=dim['Value'])
                    for dim in metric.get('Dimensions', [])
                ]
            )
            metric_objects.append(metric_obj)

        return MetricList(metrics=metric_objects, next_token=response_next_token)

    except Exception as e:
        logger.error(f'Error in list_metrics_tool: {str(e)}')
        await ctx.error(f'Error listing metrics: {str(e)}')
        raise


@mcp.tool(name='get_metric_statistics')
async def get_metric_statistics_tool(
    ctx: Context,
    namespace: str = Field(
        ...,
        description='CloudWatch namespace (e.g., AWS/EC2, AWS/Lambda)',
    ),
    metric_name: str = Field(
        ...,
        description='Name of the metric to retrieve statistics for',
    ),
    start_time: str = Field(
        ...,
        description='Start time for data retrieval in ISO 8601 format',
    ),
    end_time: str = Field(
        ...,
        description='End time for data retrieval in ISO 8601 format',
    ),
    period: int = Field(
        ...,
        description='Period in seconds for data aggregation',
    ),
    dimensions: Optional[List[Dict[str, str]]] = Field(
        None,
        description='Metric dimensions as list of {Name: str, Value: str} objects',
    ),
    statistics: Optional[List[str]] = Field(
        None,
        description='List of statistics to retrieve (Average, Sum, Minimum, Maximum, SampleCount)',
    ),
    unit: Optional[str] = Field(
        None,
        description='Unit of measurement to filter by',
    ),
) -> MetricStatistics:
    """Retrieves statistical data for a CloudWatch metric.

    This tool gets metric statistics for a specified metric within a time range.
    Statistics can include Average, Sum, Minimum, Maximum, and SampleCount.

    Usage: Use this tool to retrieve detailed statistical data for specific metrics
    to analyze performance, usage patterns, or system behavior over time.

    Returns:
    --------
    MetricStatistics object containing:
        - label: Descriptive label for the metric
        - datapoints: List of data points with timestamps and values
    """

    try:
        # Convert ISO times to datetime objects
        start_dt = datetime.datetime.fromisoformat(start_time)
        end_dt = datetime.datetime.fromisoformat(end_time)

        # Normalize dimensions
        normalized_dimensions = normalize_dimensions(dimensions) if dimensions else []

        # Default statistics
        if not statistics:
            statistics = ['Average']

        # Build request parameters
        kwargs = {
            'Namespace': namespace,
            'MetricName': metric_name,
            'StartTime': start_dt,
            'EndTime': end_dt,
            'Period': period,
            'Statistics': statistics,
        }

        if normalized_dimensions:
            kwargs['Dimensions'] = normalized_dimensions

        if unit:
            kwargs['Unit'] = unit

        # Execute request
        response = cloudwatch_client.get_metric_statistics(**remove_null_values(kwargs))

        # Process datapoints
        datapoints = []
        for dp in response.get('Datapoints', []):
            datapoint = Datapoint(
                timestamp=dp['Timestamp'],
                sampleCount=dp.get('SampleCount'),
                average=dp.get('Average'),
                sum=dp.get('Sum'),
                minimum=dp.get('Minimum'),
                maximum=dp.get('Maximum'),
                unit=dp.get('Unit'),
            )
            datapoints.append(datapoint)

        # Sort by timestamp
        datapoints.sort(key=lambda x: x.timestamp)

        return MetricStatistics(
            label=response.get('Label', f'{namespace}/{metric_name}'),
            datapoints=datapoints
        )

    except Exception as e:
        logger.error(f'Error in get_metric_statistics_tool: {str(e)}')
        await ctx.error(f'Error retrieving metric statistics: {str(e)}')
        raise


@mcp.tool(name='list_dimensions')
async def list_dimensions_tool(
    ctx: Context,
    namespace: str = Field(
        ...,
        description='CloudWatch namespace to discover dimensions for (e.g., AWS/EC2, AWS/Lambda)',
    ),
    dimension_name: Optional[str] = Field(
        None,
        description='Filter dimensions by name (optional)',
    ),
    max_results: Optional[int] = Field(
        None,
        description='Maximum number of dimension entries to return',
    ),
    next_token: Optional[str] = Field(
        None,
        description='Token for pagination to get the next set of dimensions',
    ),
) -> DimensionList:
    """Discover available dimensions for a CloudWatch namespace.

    This tool helps understand the dimensional structure of metrics within a namespace.
    Dimensions are name-value pairs that identify the resources being monitored.

    Usage: Use this tool after discovering metrics to understand what dimension values
    are available for filtering and querying specific resources.

    Returns:
    --------
    List of dimension metadata with available values for the namespace
        Each dimension contains:
            - dimension_name: The name of the dimension
            - dimension_values: Available values for this dimension
            - namespace: The CloudWatch namespace
    """

    try:
        # Get all metrics for the namespace to extract dimensions
        kwargs = {'Namespace': namespace}
        
        if next_token:
            kwargs['NextToken'] = next_token
        
        # Use paginator to get all metrics
        paginator = cloudwatch_client.get_paginator('list_metrics')
        
        # Collect all metrics and their dimensions
        all_metrics = []
        response_next_token = None
        
        for page in paginator.paginate(**remove_null_values(kwargs)):
            metrics = page.get('Metrics', [])
            all_metrics.extend(metrics)
            
            # Handle pagination
            if max_results and len(all_metrics) >= max_results:
                response_next_token = page.get('NextToken')
                break
        
        # Extract and organize dimensions
        dimension_map = {}
        
        for metric in all_metrics:
            for dimension in metric.get('Dimensions', []):
                dim_name = dimension['Name']
                dim_value = dimension['Value']
                
                # Filter by dimension name if specified
                if dimension_name and dim_name != dimension_name:
                    continue
                
                if dim_name not in dimension_map:
                    dimension_map[dim_name] = set()
                
                dimension_map[dim_name].add(dim_value)
        
        # Convert to DimensionMetadata objects
        dimensions = []
        for dim_name, dim_values in dimension_map.items():
            dimension_obj = DimensionMetadata(
                dimension_name=dim_name,
                dimension_values=sorted(list(dim_values)),
                namespace=namespace
            )
            dimensions.append(dimension_obj)
        
        # Sort by dimension name for consistent output
        dimensions.sort(key=lambda x: x.dimension_name)
        
        return DimensionList(dimensions=dimensions, next_token=response_next_token)

    except Exception as e:
        logger.error(f'Error in list_dimensions_tool: {str(e)}')
        await ctx.error(f'Error listing dimensions: {str(e)}')
        raise


@mcp.tool(name='get_metric_data')
async def get_metric_data_tool(
    ctx: Context,
    metric_data_queries: List[Dict[str, Any]] = Field(
        ...,
        description='List of metric data query configurations',
        max_length=500
    ),
    start_time: str = Field(
        ...,
        description='Start time for data retrieval in ISO 8601 format',
    ),
    end_time: str = Field(
        ...,
        description='End time for data retrieval in ISO 8601 format',
    ),
    max_datapoints: Optional[int] = Field(
        None,
        description='Maximum number of datapoints to return',
    ),
    scan_by: Optional[Literal['TimestampDescending', 'TimestampAscending']] = Field(
        'TimestampDescending',
        description='Order in which to return datapoints',
    ),
    next_token: Optional[str] = Field(
        None,
        description='Token for pagination',
    ),
) -> MetricData:
    """Retrieve metric data using advanced multi-metric queries.

    This tool enables complex metric analysis including multiple metrics, metric math expressions,
    and cross-resource comparisons. It's more powerful than get_metric_statistics for
    advanced analytics scenarios.

    Each query can specify either:
    - A metric with dimensions and statistics
    - A math expression combining multiple metrics

    Usage: Use this tool for advanced analysis like calculating ratios, comparing metrics
    across multiple resources, or performing mathematical operations on metric data.

    Returns:
    --------
    Metric data results with timestamps and values for each query
        Each result contains:
            - id: The unique identifier for the query
            - label: A human-readable label
            - timestamps: List of ISO 8601 timestamps
            - values: List of values corresponding to timestamps
    """

    try:
        # Convert ISO times to datetime objects
        start_dt = datetime.datetime.fromisoformat(start_time)
        end_dt = datetime.datetime.fromisoformat(end_time)

        # Convert query dictionaries to MetricDataQuery objects and validate
        validated_queries = []
        for i, query_dict in enumerate(metric_data_queries):
            try:
                query_obj = MetricDataQuery(**query_dict)
                validated_queries.append(query_obj)
            except Exception as e:
                raise ValueError(f"Invalid query at index {i}: {str(e)}")

        # Convert to AWS API format
        aws_queries = []
        for query_obj in validated_queries:
            aws_query = build_metric_data_query_dict(query_obj)
            aws_queries.append(aws_query)

        # Build request parameters
        kwargs = {
            'MetricDataQueries': aws_queries,
            'StartTime': start_dt,
            'EndTime': end_dt,
            'ScanBy': scan_by,
        }

        if max_datapoints:
            kwargs['MaxDatapoints'] = max_datapoints

        if next_token:
            kwargs['NextToken'] = next_token

        # Execute request
        response = cloudwatch_client.get_metric_data(**remove_null_values(kwargs))

        # Convert response to our models
        metric_data_results = []
        for result in response.get('MetricDataResults', []):
            result_obj = MetricDataResult(
                id=result['Id'],
                label=result.get('Label'),
                timestamps=result.get('Timestamps', []),
                values=result.get('Values', []),
                statusCode=result.get('StatusCode'),
                messages=result.get('Messages')
            )
            metric_data_results.append(result_obj)

        return MetricData(
            metric_data_results=metric_data_results,
            next_token=response.get('NextToken'),
            messages=response.get('Messages')
        )

    except Exception as e:
        logger.error(f'Error in get_metric_data_tool: {str(e)}')
        await ctx.error(f'Error getting metric data: {str(e)}')
        raise


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for monitoring server status.
    
    This endpoint provides a simple health check that returns server status,
    version information, and basic operational metrics.
    """
    try:
        # Basic health check - verify AWS client is accessible
        # This is a lightweight check that doesn't make actual AWS calls
        health_data = {
            "status": "healthy",
            "timestamp": datetime.datetime.now().isoformat(),
            "server_name": "cloudwatch-metrics-mcp-server",
            "version": MCP_SERVER_VERSION,
            "aws_region": aws_region,
            "transport": "http",
            "services": {
                "cloudwatch": "available",
                "mcp": "running"
            }
        }
        
        return JSONResponse(health_data, status_code=200)
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        error_data = {
            "status": "unhealthy",
            "timestamp": datetime.datetime.now().isoformat(),
            "server_name": "cloudwatch-metrics-mcp-server",
            "version": MCP_SERVER_VERSION,
            "error": str(e)
        }
        return JSONResponse(error_data, status_code=503)


def main():
    """Run the MCP server."""
    # Get transport method from environment variable, default to 'streamable-http'
    transport = os.environ.get('MCP_TRANSPORT', 'streamable-http')
    
    # Configure host for Docker containers (bind to all interfaces)
    host = os.environ.get('MCP_HOST', '0.0.0.0')
    port = int(os.environ.get('MCP_PORT', '8000'))
    
    mcp.run(transport=transport, host=host, port=port)


if __name__ == '__main__':
    main()