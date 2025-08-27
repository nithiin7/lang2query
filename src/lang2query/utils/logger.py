"""Logging configuration for the Lang2Query system."""

import logging
import sys


# Configure logging
def setup_logger(name: str = "lang2query", level: str = "INFO") -> logging.Logger:
    """Set up and configure the logger."""
    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    # Set log level
    logger.setLevel(getattr(logging, level.upper()))

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s]: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(console_handler)

    return logger


# Create default logger instance
logger = setup_logger()
