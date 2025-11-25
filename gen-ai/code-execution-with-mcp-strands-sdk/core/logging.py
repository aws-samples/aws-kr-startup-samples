"""Shared logging configuration for all agents."""

from __future__ import annotations

import logging
import os


def setup_logging() -> logging.Logger:
    """Configure logging with consistent format across all agents.
    
    Returns:
        Logger instance for the caller module.
    """
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    return logging.getLogger(__name__)


logger = setup_logging()

