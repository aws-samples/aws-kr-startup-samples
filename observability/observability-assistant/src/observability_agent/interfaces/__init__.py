"""Interface modules for the observability agent."""

from .cli import main as cli_main
from . import web

__all__ = [
    'cli_main',
    'web'
] 