"""
Image processing endpoints.

This module provides:
1. Image processing control
2. Progress monitoring
3. Task management
4. Error handling
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List
import asyncio
import traceback

from ..dependencies import (
    get_current_folder,
    get_processing_queue,
    get_image_processor,
    ensure_not_processing
)
from ..state import state
from ...core.logging import logger
from ...models.schemas import (
    ProcessingRequest,
    ProcessingStatus,
    TaskInfo
)
from ...services.image_processor import ImageProcessor
from ...services.processing_queue import ProcessingQueue

router = APIRouter()

@router.post("/start")
async def start_processing(
    request: ProcessingRequest,
    background_tasks: BackgroundTasks,
    current_folder: str = Depends(get_current_folder),
    queue: ProcessingQueue = Depends(get_processing_queue),
    processor: ImageProcessor = Depends(get_image_processor),
    _: None = Depends(ensure_not_processing)
):
    """
    Start image processing.
    
    This endpoint:
    1. Validates processing request
    2. Initializes processing state
    3. Starts background processing
    4. Returns initial status
    
    Args:
        request (ProcessingRequest): Processing configuration
        background_tasks (BackgroundTasks): FastAPI background tasks
        current_folder (str): Current working folder from dependency
        queue (ProcessingQueue): Queue instance from dependency
        processor (ImageProcessor): Processor instance from dependency
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If processing cannot start
    """
    try:
        logger.info("Starting image processing")
        state.is_processing = True
        state.should_stop_processing = False
        
        async def process_images():
            """Background task for image processing."""
            try:
                while not queue.is_empty() and not state.should_stop_processing:
                    # Get next task
                    task = queue.get_next_task()
                    if not task:
                        continue
                        
                    logger.info(f"Processing task: {task.image_path}")
                    try:
                        # Process image
                        results = await processor.process_image(
                            task.image_path,
                            lambda: state.should_stop_processing
                        )
                        
                        # Update task with results
                        task.complete(results)
                        logger.info(f"Task completed: {task.image_path}")
                        
                    except Exception as e:
                        logger.error(f"Task failed: {task.image_path}")
                        logger.error(traceback.format_exc())
                        task.fail(str(e))
                        
                    # Save queue state
                    if state.queue_persistence:
                        state.queue_persistence.save_queue(queue)
                        
            finally:
                state.is_processing = False
                logger.info("Processing finished")
                
        # Start background processing
        background_tasks.add_task(process_images)
        return {"message": "Processing started"}
        
    except Exception as e:
        state.is_processing = False
        logger.error(f"Error starting processing: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error starting processing: {str(e)}"
        )

@router.post("/stop")
async def stop_processing():
    """
    Stop image processing.
    
    This endpoint:
    1. Sets stop flag
    2. Waits for current task
    3. Updates queue state
    
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If stop request fails
    """
    try:
        logger.info("Stopping image processing")
        state.should_stop_processing = True
        
        # Wait for processing to stop
        while state.is_processing:
            await asyncio.sleep(0.1)
            
        return {"message": "Processing stopped"}
        
    except Exception as e:
        logger.error(f"Error stopping processing: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error stopping processing: {str(e)}"
        )

@router.get("/status", response_model=ProcessingStatus)
async def get_processing_status(
    queue: ProcessingQueue = Depends(get_processing_queue)
):
    """
    Get current processing status.
    
    Returns information about:
    1. Processing state
    2. Current task
    3. Queue progress
    4. Error state
    
    Args:
        queue (ProcessingQueue): Queue instance from dependency
        
    Returns:
        ProcessingStatus: Current processing status
        
    Raises:
        HTTPException: If status cannot be retrieved
    """
    try:
        logger.debug("Getting processing status")
        return {
            "is_processing": state.is_processing,
            "should_stop": state.should_stop_processing,
            "current_task": queue.current_task.to_dict() if queue.current_task else None,
            "queue_size": len(queue.queue),
            "completed_tasks": len(queue.completed_tasks),
            "failed_tasks": len(queue.failed_tasks)
        }
    except Exception as e:
        logger.error(f"Error getting processing status: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error getting status: {str(e)}"
        ) 
