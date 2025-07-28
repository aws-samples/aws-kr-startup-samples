from strands import Agent, tool
from observability_agent.mcp import get_tool_by_name
from observability_agent.datasources.cache import get_datasource_by_type
from observability_agent.config.settings import get_default_settings
from typing import Dict, Any, Optional

SYSTEM_PROMPT = """
You are a specialized observability agent which can convert a trace ID to logs.
You have access to cached datasource configurations and should use them efficiently.

Do the following steps:
1. Use the provided tracesToLogsV2 configuration from the cached Tempo datasource
2. Extract the Loki datasource UID and query template from the configuration
3. Substitute variables in the query template as needed:
   - ${__trace.traceId} with the provided trace_id
   - ${__span.spanId} with the provided span_id (if available)
   - For any label selectors, use available Loki labels (a suggested placeholder is provided)
4. Execute the LogQL query using query_loki_logs tool with the correct Loki datasource UID
5. Process and return the results

Note: Not all query templates will contain the same variables. Adapt the variable substitution based on what's actually present in the template.

Use the cached configuration to avoid redundant API calls.
"""


def extract_traces_to_logs_config() -> Optional[Dict[str, Any]]:
    """Extract tracesToLogsV2 configuration from cached Tempo datasource.
    
    Args:
        tempo_datasource_uid: The UID of the Grafana Tempo datasource
        
    Returns:
        Optional[Dict[str, Any]]: The tracesToLogsV2 configuration or None if not found
    """
    try:
        tempo_config = get_datasource_by_type('tempo')
        if not tempo_config:
            return None
        
        tempo_details = tempo_config.get('details', {})
        json_data = tempo_details.get('jsonData', {})
        traces_to_logs_config = json_data.get('tracesToLogsV2', {})
        
        return traces_to_logs_config if traces_to_logs_config else None
    
    except Exception as e:
        print(f"Error extracting tracesToLogsV2 config: {e}")
        return None


@tool
def trace_to_logs(trace_id: str, span_id: Optional[str] = None, service_name: Optional[str] = None) -> str:
    """
    Convert a trace ID to logs using cached datasource configuration and tracesToLogsV2 settings.
    
    Args:
        trace_id: The trace ID to search for in logs
        span_id: Optional span ID to filter logs
        service_name: Optional service name to filter logs
        
    Returns:
        Logs related to the trace ID
    """
    # Extract tracesToLogsV2 configuration from cached data
    traces_to_logs_config = extract_traces_to_logs_config()
    
    # Get cached Loki configuration
    loki_config = get_datasource_by_type('loki')
    loki_labels = loki_config.get('labels', []) if loki_config else []
    
    # Create a suggested label placeholder that can be used in query templates as needed
    placeholder_label = loki_labels[0] if loki_labels else 'service_name'
    label_placeholder = f'{placeholder_label}=~".+"'
    
    # Prepare tools for the agent
    tools = []
    if get_tool_by_name("query_loki_logs"):
        tools.append(get_tool_by_name("query_loki_logs"))
    
    # Create an internal agent to help with the process
    settings = get_default_settings()
    agent = Agent(
        model=settings.bedrock_model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT
    )
    
    # Build comprehensive context with cached configuration
    context_parts = [
        f"Trace ID: {trace_id}",
        f"Span ID: {span_id}",
        f"Service Name: {service_name}",
        ""
    ]
    
    # Add tracesToLogsV2 configuration if available
    if traces_to_logs_config:
        context_parts.extend([
            "TracesToLogsV2 Configuration:",
            f"- Loki Datasource UID: {traces_to_logs_config.get('datasourceUid', 'N/A')}",
            f"- Query Template: {traces_to_logs_config.get('query', 'N/A')}",
            f"- Suggested label placeholder: {label_placeholder}",
            ""
        ])
    else:
        context_parts.extend([
            "Warning: No tracesToLogsV2 configuration found in cached Tempo datasource.",
            f"- Suggested label placeholder: {label_placeholder}",
            ""
        ])
    
    # Add Loki configuration if available
    if loki_config:
        loki_basic = loki_config.get('basic_info', {})
        context_parts.extend([
            "Cached Loki Configuration:",
            f"- Loki Name: {loki_basic.get('name', 'Unknown')}",
            f"- Loki UID: {loki_basic.get('uid', 'N/A')}",
            f"- Available Labels: {', '.join(loki_labels[:10])}{'...' if len(loki_labels) > 10 else ''}" if loki_labels else "- No labels cached",
            f"- Using label for placeholder: {placeholder_label}",
            ""
        ])
    
    prompt = "\n".join(context_parts)
    
    return agent(prompt)
            