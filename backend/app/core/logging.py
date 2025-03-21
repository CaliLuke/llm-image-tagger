import logging
import sys
from .settings import settings

def setup_logging():
    """Configure logging for the application."""
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
