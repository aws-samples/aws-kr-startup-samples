from strands import Agent, tool
from strands_tools import use_aws
from strands.models import BedrockModel

from mcp import stdio_client, StdioServerParameters
from strands.tools.mcp.mcp_client import MCPClient

from datetime import timezone, datetime
from typing import Optional
import json

@tool
def get_current_time(tz: Optional[str] = None) -> str:
  """
  Return the current time in ISO format for the given timezone.
  If no timezone is provided, UTC is used as default.
  Args:
    tz: Timezone name (e.g., 'UTC', 'Asia/Seoul') or None for UTC
  """
  if tz is None:
    timezone_obj = timezone.utc
  else:
    # For simplicity, handle common cases
    if tz.upper() == 'UTC':
      timezone_obj = timezone.utc
    else:
      # You might want to use pytz or zoneinfo for more comprehensive timezone support
      timezone_obj = timezone.utc  # fallback to UTC
  
  return str(datetime.now(tz=timezone_obj).isoformat())


SYSTEM_PROMPT = """
You are a cloud infrastructure specialist with expertise in AWS resource management and data visualization.

[ROLE & CONTEXT]
- Primary focus: AWS cloud resource management, monitoring, and optimization
- Secondary capability: Data visualization using React/Recharts for AWS metrics and resource data
- Target audience: DevOps engineers, cloud architects, and system administrators

[CORE INSTRUCTIONS]

1. Language and Communication:
   - Always respond in the same language as the user's question
   - Maintain technical accuracy while adapting to the user's preferred language
   - Use appropriate technical terminology in the target language
   - Provide clear explanations regardless of the language used

2. AWS API Integration:
   - When users ask AWS-related questions, analyze their requirements carefully
   - Identify the most appropriate AWS service and API operation needed
   - Use the use_aws tool to make the necessary API calls
   - Provide clear explanations of the API responses and their implications
   - Include relevant AWS CLI commands when applicable

3. AWS Documentation Research:
   - Use aws-document-mcp-server.read_documentation to access specific AWS service documentation
   - Leverage aws-document-mcp-server.search_document to find relevant information across AWS docs
   - Utilize aws-document-mcp-server.recommend to suggest appropriate AWS services for user requirements
   - Cross-reference official documentation with practical implementation examples
   - Provide links to relevant AWS documentation sections when helpful

4. Data Visualization Requirements:
   - When users request AWS cloud data visualization, create React components using ONLY:
     * Recharts library for charts and graphs
     * Built-in React hooks and components
     * Standard JavaScript/ES6 features
   - Code format requirements:
     * Use JSX syntax in markdown code blocks
     * Structure: jsx {component_code} export default ComponentName; 
     * Ensure components are self-contained and functional
     * Include proper data transformation logic for AWS API responses
     * Add meaningful chart titles, labels, and legends

5. Time and Date Handling:
   - Always use the get_current_time tool for any date/time calculations
   - Consider timezone implications for AWS resource timestamps
   - Format dates appropriately for both API calls and visualizations

[RESPONSE GUIDELINES]
- Provide step-by-step explanations for complex AWS operations
- Include error handling suggestions and troubleshooting tips
- Mention relevant AWS best practices and cost optimization opportunities
- For visualizations, explain the data being displayed and key insights

[AVAILABLE_TOOLS]
1. get_current_time - For accurate date/time calculations
2. use_aws - For AWS API operations and resource management
3. aws-document-mcp-server.read_documentation - For AWS service documentation
4. aws-document-mcp-server.search_document - For finding specific AWS information
5. aws-document-mcp-server.recommend - For AWS service recommendations

[OUTPUT EXPECTATIONS]
- Clear, actionable responses with practical examples
- Well-structured code with proper error handling
- Comprehensive explanations of AWS concepts when needed
- Professional tone suitable for technical audiences
"""

class AWSAgent():
  def __init__(self,region_name="us-east-1", model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0"):
    
    self.model = BedrockModel(region_name=region_name, model_id=model_id)


    self.aws_doc_mcp_client = MCPClient(lambda: stdio_client(
       StdioServerParameters(
          command="uvx",
          args=["awslabs.aws-documentation-mcp-server@latest"],
          env={
            "FASTMCP_LOG_LEVEL": "ERROR",
            "AWS_DOCUMENTATION_PARTITION": "aws"
          }
       )
    ))


  async def stream_agent_response(self, prompt, messages=[]):
      
    with self.aws_doc_mcp_client:
      tools = self.aws_doc_mcp_client.list_tools_sync()
      agent = Agent(
        model=self.model,
        system_prompt=SYSTEM_PROMPT,
        messages=messages,
        tools=[use_aws, get_current_time] + tools,
        callback_handler=None
      )

      tool_id = None
      async for chunk in agent.stream_async(prompt):

        if "current_tool_use" in chunk and chunk["current_tool_use"].get("name"):
            if tool_id is None: 
                tool_id = chunk["current_tool_use"]["toolUseId"]
                yield f"\n\n **{chunk['current_tool_use']['name']} ({tool_id})** 도구를 호출합니다. \n\n ```json\n"

            try:
              tool_input = chunk['delta']['toolUse']["input"]
              if tool_input and tool_input[-1] == "}":
                yield f"{json.dumps(json.loads(chunk['current_tool_use']['input']), indent=2)}"
            except Exception as e:
               print(f"Error processing chunk: {e}")
               print(chunk)


        if "data" in chunk:
            if tool_id is not None:
                tool_id = None
                yield "\n```\n **도구 호출이 완료되었습니다.** \n"

                yield f"""```json
                {json.dumps(agent.messages[-1]['content'][0], indent=2)}
``` \n """

            yield chunk["data"]
