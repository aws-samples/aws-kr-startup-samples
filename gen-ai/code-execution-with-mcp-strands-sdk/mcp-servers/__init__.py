"""Filesystem-based MCP server adapters.

Each subpackage exposes Python functions that wrap a single MCP tool. Agents
can inspect this directory (e.g. via the `search_tools` Strands tool) to
discover available integrations and import only the helpers they need.
"""

from . import amazon_ecs, amazon_eks, aws_cdk, aws_documentation  # noqa: F401

__all__ = [
    "amazon_ecs",
    "amazon_eks",
    "aws_cdk",
    "aws_documentation",
]

