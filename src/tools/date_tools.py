"""
Date and time related tools for agents.

This module provides tools for working with dates and times.
"""

from datetime import datetime, timezone
from typing import Optional
from langchain_core.tools import tool
import logging

logger = logging.getLogger(__name__)


@tool
def get_current_date(format: Optional[str] = None, tz: Optional[str] = "UTC") -> str:
    """
    Get the current date and time.

    Args:
        format: Date format string (e.g., '%Y-%m-%d'). If not provided, uses ISO format.
        tz: Timezone name (e.g., 'UTC', 'US/Eastern'). Defaults to UTC.

    Returns:
        Current date and time as a formatted string.
    """
    try:
        if tz.upper() == "UTC":
            now = datetime.now(timezone.utc)
        else:
            logger.warning(f"Timezone {tz} not implemented, using UTC")
            now = datetime.now(timezone.utc)

        if format:
            return now.strftime(format)
        else:
            return now.isoformat()

    except Exception as e:
        logger.error(f"Error getting current date: {e}")
        return f"Error: {str(e)}"