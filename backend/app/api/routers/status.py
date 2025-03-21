"""
Status and initialization endpoints.

This module provides:
1. Root endpoint for web interface
2. Initialization status checks
3. Application health checks
4. Version information
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from ..dependencies import get_current_folder
from ..state import state
from ...core.logging import logger

router = APIRouter()

@router.get("/")
async def read_root():
    """
    Serve the main web interface.
    
    Returns:
        FileResponse: The main HTML interface
    """
    return FileResponse("static/index.html")

@router.get("/status")
async def get_status():
    """
    Get the current application status.
    
    Returns:
        dict: Status information including:
            - folder: Current folder if set
            - is_processing: Whether processing is active
            - queue_size: Number of items in queue
            - vector_store: Whether vector store is initialized
    """
    status = {
        "folder": state.current_folder,
        "is_processing": state.is_processing,
        "queue_size": len(state.processing_queue.queue) if state.processing_queue else 0,
        "vector_store_initialized": state.vector_store is not None
    }
    logger.debug(f"Status request: {status}")
    return status

@router.get("/health")
async def health_check():
    """
    Check the health of the application.
    
    This endpoint verifies:
    1. API is responsive
    2. Core services are available
    3. State is accessible
    
    Returns:
        dict: Health status information
    """
    try:
        health = {
            "status": "healthy",
            "services": {
                "api": "up",
                "vector_store": "up" if state.vector_store else "down",
                "queue": "up" if state.processing_queue else "down"
            }
        }
        logger.debug(f"Health check: {health}")
        return health
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        ) 
