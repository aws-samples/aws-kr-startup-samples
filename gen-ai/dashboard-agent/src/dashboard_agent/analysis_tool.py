"""Analysis tool for processing Google Sheets data through extraction, analysis, and reporting pipeline."""

import json
import os
from pathlib import Path
from typing import Dict, Any

from strands import Agent, tool
from strands_tools import file_read

from .settings import get_default_settings


def get_latest_prompt_version(prompts_dir: str = "prompts") -> str:
    """Get the latest semantic version from the prompts directory.
    
    Args:
        prompts_dir: Path to the prompts directory
        
    Returns:
        Latest version string (e.g., "v1.2.0")
    """
    prompts_path = Path(prompts_dir)
    if not prompts_path.exists():
        raise FileNotFoundError(f"Prompts directory not found: {prompts_dir}")
    
    versions = [d.name for d in prompts_path.iterdir() if d.is_dir() and d.name.startswith("v")]
    if not versions:
        raise ValueError("No versioned prompts found in prompts directory")
    
    # Sort versions semantically (v1.0.0, v1.1.0, v1.2.0, etc.)
    def version_key(v: str):
        parts = v[1:].split(".")  # Remove 'v' prefix and split
        return tuple(int(p) for p in parts)
    
    versions.sort(key=version_key, reverse=True)
    return versions[0]


def load_prompts(version: str, prompts_dir: str = "prompts") -> Dict[str, str]:
    """Load extraction, analysis, and report prompts for a specific version.
    
    Args:
        version: Version string (e.g., "v1.2.0")
        prompts_dir: Path to the prompts directory
        
    Returns:
        Dictionary with 'extraction', 'analysis', and 'report' prompts
    """
    version_path = Path(prompts_dir) / version
    
    prompts = {}
    for prompt_type in ["extraction", "analysis", "report"]:
        prompt_file = version_path / f"{prompt_type}.txt"
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
        
        with open(prompt_file, "r") as f:
            prompts[prompt_type] = f.read()
    
    return prompts


@tool
def analysis_tool(sheet_data_json: str) -> str:
    """
    Process Google Sheets data through a three-stage pipeline: extraction, analysis, and reporting.
    
    This tool orchestrates a complete data processing workflow using the latest versioned prompts.
    It takes raw spreadsheet data from Google Drive and produces a comprehensive report through
    three specialized agents, each using domain-specific prompts.
    
    Use this tool when you need to:
    - Generate insights and reports from Google Sheets data
    - Process spreadsheet data through a structured analysis pipeline
    - Create comprehensive reports with extraction, analysis, and synthesis
    
    The tool automatically:
    - Fetches the latest version of prompts (extraction.txt, analysis.txt, report.txt)
    - Chains three specialized agents in sequence
    - Passes output from each stage to the next
    - Returns a final formatted report
    
    Pipeline stages:
    1. Extraction Agent: Extracts relevant information from raw spreadsheet data
    2. Analysis Agent: Analyzes extracted data for patterns and insights
    3. Report Agent: Synthesizes analysis into a comprehensive report
    
    Args:
        sheet_data_json: JSON string containing Google Sheets data with structure:
            {
                "sheetName": "Sheet1",
                "data": [[{"value": "A1"}, {"value": "B1"}], ...],
                "totalRows": 100,
                "totalColumns": 10,
                "columnHeaders": [{"value": "Header1"}, {"value": "Header2"}]
            }
    
    Returns:
        A comprehensive report string containing the final analysis and insights
        from the three-stage processing pipeline.
    
    Example:
        sheet_data = json.dumps({
            "sheetName": "Sales Data",
            "data": [[{"value": "Product"}, {"value": "Revenue"}], ...],
            "columnHeaders": [{"value": "Product"}, {"value": "Revenue"}]
        })
        report = analysis_tool(sheet_data)
    """
    try:
        settings = get_default_settings()
        
        # Parse input data
        try:
            sheet_data = json.loads(sheet_data_json)
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON input - {str(e)}"
        
        # Get latest prompt version and load prompts
        try:
            latest_version = get_latest_prompt_version()
            prompts = load_prompts(latest_version)
        except (FileNotFoundError, ValueError) as e:
            return f"Error loading prompts: {str(e)}"
        
        # Stage 1: Extraction Agent
        extraction_agent = Agent(
            model=settings.bedrock.model_id,
            system_prompt=prompts["extraction"],
            tools=[],
        )
        
        extraction_input = f"Process the following spreadsheet data:\n\n{json.dumps(sheet_data, indent=2)}"
        extraction_result = extraction_agent(extraction_input)
        extraction_output = str(extraction_result)
        
        if not extraction_output:
            return "Error: Extraction stage produced no output"
        
        # Stage 2: Analysis Agent
        analysis_agent = Agent(
            model=settings.bedrock.model_id,
            system_prompt=prompts["analysis"],
            tools=[],
        )
        
        analysis_input = f"Analyze the following extracted data:\n\n{extraction_output}"
        analysis_result = analysis_agent(analysis_input)
        analysis_output = str(analysis_result)
        
        if not analysis_output:
            return "Error: Analysis stage produced no output"
        
        # Stage 3: Report Agent
        report_agent = Agent(
            model=settings.bedrock.model_id,
            system_prompt=prompts["report"],
            tools=[],
        )
        
        report_input = f"Generate a report based on the following analysis:\n\n{analysis_output}"
        report_result = report_agent(report_input)
        report_output = str(report_result)
        
        if not report_output:
            return "Error: Report stage produced no output"
        
        # Return final report with metadata
        return f"""=== ANALYSIS REPORT ===
Prompt Version: {latest_version}
Sheet: {sheet_data.get('sheetName', 'Unknown')}

{report_output}
"""
        
    except Exception as e:
        return f"Error processing analysis pipeline: {str(e)}"
