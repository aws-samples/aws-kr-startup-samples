from strands import Agent, tool
from strands_tools import file_read, file_write
from .settings import get_default_settings

AGENT_SYSTEM_PROMPT = """You are a prompt enhancement agent. Your task is to generate new versions of prompt based on given feedback.
The prompt is structured in your current working directory in the following way:

prompts/
├── v1.0.0/
│ ├── extraction.txt
│ ├── analysis.txt
│ └── report.txt
├── v1.1.0/
│ ├── extraction.txt
│ ├── analysis.txt
│ └── report.txt
└── metadata.json

Your task is to modify the latest version of the prompt based on the provided feedback, and create a new version of it.
To do so, you will:
    1. Read the latest version of prompts
    2. Analyze how the prompts are structured
    3. Apply feedback by creating new prompts
    4. Use semantic versioning to determine the new version, and save the prompts according to the above structure


Returns:
    A confirmation message describing the changes made, the new version number 
    created, and a summary of modifications applied to each prompt file.

Use semantic versioning for versioning the prompts.
DO NOT MODIFY EXISTING PROMPTS."""

@tool
def feedback_learning_agent(query: str) -> str:
    """
    Enhance and version prompts based on user feedback using semantic versioning.

    Use this tool when you need to improve or modify existing prompts based on user 
    feedback, performance issues, or quality concerns. This agent analyzes the current 
    prompt structure, applies the requested changes, and creates a new semantically 
    versioned copy while preserving all previous versions.

    The agent works with a structured prompt directory containing versioned folders 
    (e.g., v1.0.0, v1.1.0) where each version contains prompt files like extraction.txt, 
    analysis.txt, and report.txt. It automatically determines the appropriate version 
    number increment based on the nature of changes.

    This tool is ideal for:
    - Iterative prompt refinement based on output quality feedback
    - Fixing issues in prompt instructions or formatting
    - Adding new capabilities or constraints to existing prompts
    - Maintaining a version history of prompt evolution

    Example usage scenarios:
    - "The extraction prompt is missing instructions for handling edge cases"
    - "Make the analysis prompt more concise and focused"
    - "Add error handling guidelines to the report generation prompt"

    Args:
        query: Detailed feedback describing the desired prompt changes.
            Should specify which prompt file(s) to modify and what changes to make.
            Example: "Update extraction.txt in the latest version to include 
            instructions for handling null values and create version 1.2.0"

    Returns:
        A confirmation message describing the changes made, the new version number 
        created, and a summary of modifications applied to each prompt file.
    """

    try:
        settings = get_default_settings()
        
        # Get all MCP tools from the initialized clients
        # tools = get_all_aws_mcp_tools()
        tools = []
        tools.append(file_read)
        tools.append(file_write)
        
        # Create AWS assistant agent with appropriate tools
        agent = Agent(
            model=settings.bedrock.model_id,
            system_prompt=AGENT_SYSTEM_PROMPT,
            tools=tools,
        )
        
        # Process the query through the agent
        agent_response = agent(query)
        text_response = str(agent_response)
        
        if len(text_response) > 0:
            return text_response

        return "I apologize, but I couldn't process your query."
        
    except Exception as e:
        # Return specific error message for AWS processing
        return f"Error processing your query: {str(e)}. Please ensure your query is related to prompt feedback."