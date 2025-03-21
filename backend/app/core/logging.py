"""
Application logging configuration.

This module provides:
1. Centralized logging setup
2. Configurable log levels via settings
3. Consistent log formatting
4. Stdout logging for container compatibility
5. Third-party logger management

Features:
- Timestamp with millisecond precision
- Module name for easy tracing
- Log level indicators
- Structured message format
- Quiet mode for chatty dependencies
"""

import logging
import sys
from .settings import settings

def setup_logging():
    """
    Configure logging for the application.
    
    This function:
    1. Sets up the root logger with consistent format
    2. Creates an app-specific logger
    3. Configures third-party loggers
    4. Ensures container-friendly output
    
    Configuration details:
    - Log Level: Configurable via settings.LOG_LEVEL
    - Format: timestamp - module - level - message
    - Timestamp Format: YYYY-MM-DD HH:MM:SS
    - Output: Directed to stdout for container logging
    
    Third-party logger management:
    - uvicorn: Set to WARNING to reduce API noise
    - uvicorn.access: Set to WARNING to reduce API access logs
    - chromadb: Set to WARNING to reduce vector DB noise
    
    Returns:
        logging.Logger: Configured application logger
    
    Usage:
        from core.logging import logger
        
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
    """
    # Get log level from settings, default to INFO
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Configure root logger with consistent format
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stdout)  # Ensure output goes to stdout
        ]
    )
    
    # Create our app logger
    app_logger = logging.getLogger("app")
    app_logger.setLevel(log_level)
    
    # Quiet down some chatty loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    
    return app_logger

# Create a global logger instance
logger = setup_logging()

# Export the logger
__all__ = ['logger'] 
