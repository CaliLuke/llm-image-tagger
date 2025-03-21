"""
Frontend logging endpoints.

This module provides:
1. Frontend log collection
2. Log level filtering
3. Log persistence
4. Error reporting
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import traceback

from ...core.logging import logger

router = APIRouter()

@router.post("/error")
async def log_frontend_error(error: Dict[str, Any]):
    """
    Log frontend errors.
    
    This endpoint:
    1. Collects frontend error details
    2. Formats error information
    3. Logs to backend system
    
    Args:
        error (Dict[str, Any]): Error details including:
            - message: Error message
            - stack: Error stack trace
            - context: Additional context
            
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If logging fails
    """
    try:
        logger.error(
            "Frontend error: %s\nStack: %s\nContext: %s",
            error.get("message", "Unknown error"),
            error.get("stack", "No stack trace"),
            error.get("context", {})
        )
        return {"message": "Error logged successfully"}
        
    except Exception as e:
        logger.error(f"Error logging frontend error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error logging: {str(e)}"
        )

@router.post("/info")
async def log_frontend_info(info: Dict[str, Any]):
    """
    Log frontend information.
    
    This endpoint:
    1. Collects frontend info
    2. Formats message
    3. Logs to backend system
    
    Args:
        info (Dict[str, Any]): Information including:
            - message: Info message
            - context: Additional context
            
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If logging fails
    """
    try:
        logger.info(
            "Frontend info: %s\nContext: %s",
            info.get("message", "No message"),
            info.get("context", {})
        )
        return {"message": "Info logged successfully"}
        
    except Exception as e:
        logger.error(f"Error logging frontend info: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error logging: {str(e)}"
        )

@router.post("/debug")
async def log_frontend_debug(debug: Dict[str, Any]):
    """
    Log frontend debug information.
    
    This endpoint:
    1. Collects debug info
    2. Formats message
    3. Logs to backend system
    
    Args:
        debug (Dict[str, Any]): Debug information including:
            - message: Debug message
            - context: Additional context
            
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If logging fails
    """
    try:
        logger.debug(
            "Frontend debug: %s\nContext: %s",
            debug.get("message", "No message"),
            debug.get("context", {})
        )
        return {"message": "Debug info logged successfully"}
        
    except Exception as e:
        logger.error(f"Error logging frontend debug: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error logging: {str(e)}"
        ) 
