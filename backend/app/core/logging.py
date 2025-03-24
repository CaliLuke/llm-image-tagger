"""
Application logging configuration.

This module provides:
1. Centralized logging setup
2. Configurable log levels via settings
3. Consistent log formatting
4. Stdout logging for container compatibility
5. Third-party logger management

IMPORTANT: ALL APPLICATION LOGGING MUST USE THIS MODULE
- Do NOT create additional log files
- Do NOT bypass this centralized logging configuration
- ALL logs should go to app.log only
"""

import logging
import sys
import os
import datetime
from .settings import settings

def cleanup_old_logs(log_file_path):
    """
    Remove log entries from previous days, keeping only the current day's logs.
    
    Args:
        log_file_path: Path to the log file
    """
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    
    if not os.path.exists(log_file_path):
        return  # No log file exists yet
        
    try:
        with open(log_file_path, 'r') as f:
            log_content = f.readlines()
        
        # Filter logs to keep only current day's entries
        current_day_logs = []
        for line in log_content:
            # Only check lines that might contain a timestamp
            if len(line) > 10 and '-' in line[:10]:
                try:
                    # Extract the date part (YYYY-MM-DD)
                    log_date = line[:10]
                    if log_date == today:
                        current_day_logs.append(line)
                except (ValueError, IndexError):
                    # If the line doesn't have a proper date format, keep it for safety
                    current_day_logs.append(line)
            else:
                # Keep lines without timestamps (could be stack traces, etc.)
                current_day_logs.append(line)
        
        # Write back only today's logs
        with open(log_file_path, 'w') as f:
            f.writelines(current_day_logs)
            
        print(f"Log cleanup complete. Removed entries older than {today}")
    except Exception as e:
        print(f"Error during log cleanup: {str(e)}")

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
    
    IMPORTANT: This is the ONLY place where log files should be configured.
    Do NOT create additional log files elsewhere in the application.
    
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
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Configure root logger with consistent format
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n%(pathname)s:%(lineno)d',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # More concise format for terminal output
    terminal_format = logging.Formatter(
        '%(message)s',  # Just the message
        datefmt='%H:%M:%S'
    )
    
    # Add stdout handler with color formatting
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(terminal_format)
    stdout_handler.setLevel(logging.WARNING)  # Only show warnings and errors in terminal
    
    # Clean up old logs
    log_file_path = os.path.join(logs_dir, 'app.log')
    cleanup_old_logs(log_file_path)
    
    # Add file handler for persistent logging
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(file_format)
    file_handler.setLevel(logging.DEBUG)  # Always log everything to file
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add our handlers
    root_logger.addHandler(stdout_handler)
    root_logger.addHandler(file_handler)
    
    # Configure third-party loggers
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('chromadb').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('PIL.Image').setLevel(logging.WARNING)
    logging.getLogger('PIL.PngImagePlugin').setLevel(logging.WARNING)
    logging.getLogger('PIL.JpegImagePlugin').setLevel(logging.WARNING)
    
    # Configure module-specific log levels
    logging.getLogger('app.api.routes').setLevel(logging.WARNING)
    logging.getLogger('app.api.routers.images').setLevel(logging.WARNING)
    logging.getLogger('app.utils.helpers').setLevel(logging.WARNING)  # Reduce file operation noise
    logging.getLogger('app.services.image_processor').setLevel(logging.INFO)  # Keep important processing logs
    
    # Create our app logger with separate terminal handler for important info
    app_logger = logging.getLogger("app")
    app_logger.setLevel(log_level)
    app_logger.propagate = False  # Prevent duplicate logs
    
    # Add a separate handler for app-specific info in terminal
    app_terminal_handler = logging.StreamHandler(sys.stdout)
    app_terminal_handler.setFormatter(terminal_format)
    app_terminal_handler.setLevel(logging.INFO)
    
    # Add filters to exclude noisy messages
    class NoiseFilter(logging.Filter):
        def filter(self, record):
            # Skip file operation messages
            if any(x in record.msg for x in ['File stats:', 'File size:', 'Image format:', 'Image mode:', 'Image size:', 'Serving image file:', 'Response headers:', 'File is readable:', 'File is executable:']):
                return False
            return True
    
    app_terminal_handler.addFilter(NoiseFilter())
    app_terminal_handler.addFilter(lambda record: record.name == "app")  # Only show app logs
    app_logger.addHandler(app_terminal_handler)
    
    return app_logger

# Create the global logger instance
logger = setup_logging()

# Export the logger
__all__ = ['logger', 'cleanup_old_logs'] 
