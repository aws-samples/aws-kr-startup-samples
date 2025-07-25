"""Agents module for the observability assistant."""

from .coordinator import CoordinatorAgent
from .trace_to_logs import trace_to_logs

__all__ = [
    'CoordinatorAgent',
    'trace_to_logs'
] 