"""
FastAPI dependency injection.

This module provides:
1. State-based dependencies
2. Service dependencies
3. Validation dependencies
4. Error handling

Dependencies are used to:
- Ensure state is initialized
- Provide access to services
- Validate requests
- Handle common errors
"""

from fastapi import HTTPException, Depends
from typing import Optional
from pathlib import Path

from .state import state
from ..services.vector_store import VectorStore
from ..services.image_processor import ImageProcessor
from ..services.processing_queue import ProcessingQueue
from ..core.logging import logger

async def get_vector_store() -> VectorStore:
    """
    Get the initialized vector store instance.
    
    This dependency:
    1. Checks if vector store is initialized
    2. Returns the instance if available
    3. Raises error if not initialized
    
    Returns:
        VectorStore: Initialized vector store instance
        
    Raises:
        HTTPException: If vector store is not initialized
    """
    if not state.vector_store:
        logger.error("Vector store not initialized")
        raise HTTPException(
            status_code=500,
            detail="Vector store not initialized. Please select a folder first."
        )
    return state.vector_store

async def get_image_processor() -> ImageProcessor:
    """
    Get or create an ImageProcessor instance.
    
    This dependency:
    1. Creates ImageProcessor if needed
    2. Returns existing instance if available
    3. Configures with current settings
    
    Returns:
        ImageProcessor: Configured processor instance
    """
    if not hasattr(state, "image_processor"):
        logger.info("Creating new ImageProcessor instance")
        state.image_processor = ImageProcessor()
    return state.image_processor

async def get_current_folder() -> str:
    """
    Get the current working folder path.
    
    This dependency:
    1. Validates current folder is set
    2. Checks folder exists
    3. Returns absolute path
    
    Returns:
        str: Absolute path to current folder
        
    Raises:
        HTTPException: If no folder is selected or folder is invalid
    """
    if not state.validate_folder():
        raise HTTPException(
            status_code=400,
            detail="No folder selected or invalid folder"
        )
    return state.current_folder

async def get_processing_queue() -> ProcessingQueue:
    """
    Get the initialized processing queue.
    
    This dependency:
    1. Checks if queue is initialized
    2. Returns queue instance if available
    3. Raises error if not initialized
    
    Returns:
        ProcessingQueue: Initialized queue instance
        
    Raises:
        HTTPException: If queue is not initialized
    """
    if not state.processing_queue:
        logger.error("Processing queue not initialized")
        raise HTTPException(
            status_code=500,
            detail="Processing queue not initialized. Please select a folder first."
        )
    return state.processing_queue

async def validate_folder_exists(folder_path: str) -> Path:
    """
    Validate that a folder exists and is accessible.
    
    This dependency:
    1. Converts path to absolute
    2. Resolves symlinks
    3. Validates existence
    4. Checks permissions
    
    Args:
        folder_path (str): Path to validate
        
    Returns:
        Path: Validated Path object
        
    Raises:
        HTTPException: If folder is invalid or inaccessible
    """
    try:
        path = Path(folder_path).resolve()
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"Folder not found: {folder_path}")
        if not path.is_dir():
            raise HTTPException(status_code=400, detail=f"Not a directory: {folder_path}")
        return path
    except Exception as e:
        logger.error(f"Error validating folder {folder_path}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error accessing folder: {str(e)}")

async def ensure_not_processing() -> None:
    """
    Ensure no processing is currently active.
    
    This dependency:
    1. Checks processing state
    2. Raises error if processing
    
    Raises:
        HTTPException: If processing is active
    """
    if state.is_processing:
        raise HTTPException(
            status_code=400,
            detail="Processing already in progress"
        ) 
