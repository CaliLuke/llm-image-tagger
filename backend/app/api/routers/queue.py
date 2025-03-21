"""
Queue management endpoints.

This module provides:
1. Queue status and monitoring
2. Task management
3. Queue persistence
4. Task history
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
import traceback

from ..dependencies import get_processing_queue
from ..state import state
from ...core.logging import logger
from ...models.schemas import QueueStatus, TaskInfo
from ...services.processing_queue import ProcessingQueue

router = APIRouter()

@router.get("/status", response_model=QueueStatus)
async def get_queue_status(
    queue: ProcessingQueue = Depends(get_processing_queue)
):
    """
    Get current queue status.
    
    Returns information about:
    1. Queue size
    2. Active tasks
    3. Completed tasks
    4. Failed tasks
    
    Args:
        queue (ProcessingQueue): Queue instance from dependency
        
    Returns:
        QueueStatus: Current queue status
        
    Raises:
        HTTPException: If queue not initialized
    """
    try:
        logger.info("Getting queue status")
        return {
            "queue_size": len(queue.queue),
            "active_tasks": len(queue.active_tasks),
            "completed_tasks": len(queue.completed_tasks),
            "failed_tasks": len(queue.failed_tasks)
        }
    except Exception as e:
        logger.error(f"Error getting queue status: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error getting queue status: {str(e)}"
        )

@router.get("/tasks", response_model=List[TaskInfo])
async def get_tasks(
    queue: ProcessingQueue = Depends(get_processing_queue)
):
    """
    Get all tasks in queue.
    
    Returns:
    1. Pending tasks
    2. Active tasks
    3. Completed tasks
    4. Failed tasks
    
    Args:
        queue (ProcessingQueue): Queue instance from dependency
        
    Returns:
        List[TaskInfo]: List of all tasks
        
    Raises:
        HTTPException: If queue not initialized
    """
    try:
        logger.info("Getting all tasks")
        tasks = []
        
        # Add tasks from each category
        tasks.extend(queue.queue)
        tasks.extend(queue.active_tasks)
        tasks.extend(queue.completed_tasks)
        tasks.extend(queue.failed_tasks)
        
        logger.info(f"Found {len(tasks)} total tasks")
        return tasks
        
    except Exception as e:
        logger.error(f"Error getting tasks: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error getting tasks: {str(e)}"
        )

@router.post("/clear")
async def clear_queue(
    queue: ProcessingQueue = Depends(get_processing_queue)
):
    """
    Clear all tasks from queue.
    
    This endpoint:
    1. Removes all pending tasks
    2. Clears task history
    3. Updates persistence
    
    Args:
        queue (ProcessingQueue): Queue instance from dependency
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If queue not initialized or clear fails
    """
    try:
        logger.info("Clearing queue")
        queue.clear()
        
        # Save cleared state
        if state.queue_persistence:
            state.queue_persistence.save_queue(queue)
            logger.info("Saved cleared queue state")
            
        return {"message": "Queue cleared successfully"}
        
    except Exception as e:
        logger.error(f"Error clearing queue: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing queue: {str(e)}"
        ) 
