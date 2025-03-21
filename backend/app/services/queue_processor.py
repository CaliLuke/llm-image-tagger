"""
Queue processor module for handling background image processing tasks.
This module manages the processing of images in a queue, with support for:
- Background task processing
- Progress tracking
- State persistence
- Graceful interruption
"""

from pathlib import Path
from typing import Optional, Dict, Any, Callable
from fastapi import BackgroundTasks
import traceback
import json

from ..core.logging import logger
from .processing_queue import ProcessingQueue, ImageTask
from .image_processor import ImageProcessor, update_image_metadata

class QueueProcessor:
    """
    Processor for the image processing queue.
    
    This class manages the background processing of images in a queue, providing:
    1. Background task execution
    2. Progress tracking and reporting
    3. State persistence
    4. Graceful interruption handling
    
    Attributes:
        queue (ProcessingQueue): The queue to process
        image_processor (ImageProcessor): Processor for individual images
    """
    
    def __init__(self, queue: ProcessingQueue, image_processor: Optional[ImageProcessor] = None):
        """
        Initialize a new queue processor.
        
        Args:
            queue (ProcessingQueue): The processing queue to process
            image_processor (Optional[ImageProcessor]): Optional image processor to use.
                If not provided, a new one will be created with stop checking enabled.
        """
        logger.info("Initializing QueueProcessor")
        self.queue = queue
        self.image_processor = image_processor or ImageProcessor(stop_check=self._should_stop)
        logger.debug(f"QueueProcessor initialized with {'provided' if image_processor else 'default'} ImageProcessor")
    
    def _should_stop(self) -> bool:
        """
        Check if processing should stop.
        
        This method is used as a callback by the ImageProcessor to check if it should
        stop processing the current image.
        
        Returns:
            bool: True if processing should stop, False otherwise
        """
        should_stop = self.queue.should_stop
        if should_stop:
            logger.debug("Stop check returned True")
        return should_stop
    
    async def process_queue(self, background_tasks: BackgroundTasks) -> Dict[str, Any]:
        """
        Start processing the queue in the background.
        
        This method:
        1. Checks if the queue is already being processed
        2. Starts the queue processing state
        3. Adds the processing task to FastAPI's background tasks
        
        Args:
            background_tasks (BackgroundTasks): FastAPI background tasks manager
            
        Returns:
            Dict[str, Any]: Dictionary containing:
                - success: Boolean indicating if the operation was successful
                - message: Status message
        """
        if self.queue.is_processing:
            logger.warning("Queue is already being processed")
            return {
                "success": False,
                "message": "Queue is already being processed"
            }
        
        logger.info("Starting queue processing")
        self.queue.start_processing()
        background_tasks.add_task(self._process_queue_task)
        logger.debug("Added queue processing task to background tasks")

        return {
            "success": True,
            "message": "Queue processing started"
        }
    
    async def _process_queue_task(self) -> None:
        """
        Background task to process the queue.
        
        This method:
        1. Processes tasks from the queue until stopped or empty
        2. Handles errors and ensures proper cleanup
        3. Saves the final queue state
        
        The task will stop if:
        - The queue is empty
        - A stop request is received
        - An unhandled error occurs
        """
        logger.info("Starting queue processing task")
        processed_count = 0
        
        try:
            while not self.queue.should_stop and (task := self.queue.get_next_task()):
                logger.debug(f"Processing task {processed_count + 1}")
                await self._process_task(task)
                processed_count += 1
                
                if self.queue.should_stop:
                    logger.info("Stopping queue processing due to stop request")
                    break
            
            logger.info(f"Queue processing completed. Processed {processed_count} tasks")
        except Exception as e:
            logger.error(f"Error processing queue: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
        finally:
            self.queue.is_processing = False
            # Save final state
            if self.queue.persistence:
                try:
                    logger.debug("Saving final queue state")
                    self.queue.save()
                    logger.debug("Final queue state saved successfully")
                except Exception as e:
                    logger.error(f"Failed to save final queue state: {str(e)}")
                    logger.error(f"Error type: {type(e)}")
                    logger.error(f"Full traceback: {traceback.format_exc()}")
    
    async def _process_task(self, task: ImageTask) -> None:
        """
        Process a single task from the queue.
        
        This method:
        1. Marks the task as started
        2. Sets up progress tracking
        3. Processes the image
        4. Handles task completion or failure
        5. Saves state on progress updates
        
        Args:
            task (ImageTask): The task to process
            
        The task will be interrupted if:
        - A stop request is received before processing
        - A stop request is received during processing
        - An error occurs during processing
        """
        logger.info(f"Processing task: {task.image_path}")
        
        try:
            # Mark task as started
            task.start()
            logger.debug(f"Task started at: {task.started_at}")
            
            # Check if processing should stop
            if self.queue.should_stop:
                logger.info(f"Interrupting task {task.image_path} due to stop request")
                self.queue.interrupt_current_task()
                return
            
            # Create progress callback
            def progress_callback(progress: float) -> None:
                """
                Callback function to update task progress.
                
                Args:
                    progress (float): Progress value between 0 and 1
                """
                task.update_progress(progress)
                logger.debug(f"Task progress updated: {progress:.2%}")
                # Auto-save on progress updates
                if self.queue.persistence:
                    try:
                        self.queue.save()
                    except Exception as e:
                        logger.error(f"Failed to save queue state during progress update: {str(e)}")
                        logger.error(f"Error type: {type(e)}")
                        logger.error(f"Full traceback: {traceback.format_exc()}")
            
            # Process the image with progress tracking
            image_path = Path(task.image_path)
            logger.debug(f"Processing image at path: {image_path}")
            metadata = await self.image_processor.process_image(
                image_path, 
                progress_callback=progress_callback
            )
            logger.debug(f"Received metadata: {json.dumps(metadata, indent=2)}")
            
            # Check if processing should stop
            if self.queue.should_stop:
                logger.info(f"Interrupting task {task.image_path} after processing due to stop request")
                self.queue.interrupt_current_task()
                return
            
            # Mark task as completed
            self.queue.finish_current_task(True, metadata)
            logger.info(f"Task completed: {task.image_path}")
            logger.debug(f"Task completed at: {task.completed_at}")
        except Exception as e:
            logger.error(f"Error processing task {task.image_path}: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            self.queue.finish_current_task(False, error=str(e))
    
    async def stop_processing(self) -> Dict[str, Any]:
        """
        Stop processing the queue.
        
        This method:
        1. Checks if the queue is currently being processed
        2. Sets the stop flag to interrupt processing
        3. Returns the operation status
        
        Returns:
            Dict[str, Any]: Dictionary containing:
                - success: Boolean indicating if the operation was successful
                - message: Status message
        """
        if not self.queue.is_processing:
            logger.warning("Queue is not being processed")
            return {
                "success": False,
                "message": "Queue is not being processed"
            }
        
        logger.info("Stopping queue processing")
        self.queue.stop_processing()
        logger.debug("Queue processing stopped")
        
        return {
            "success": True,
            "message": "Queue processing stopped"
        } 
