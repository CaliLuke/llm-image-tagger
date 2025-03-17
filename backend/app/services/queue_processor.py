from pathlib import Path
from typing import Optional, Dict, Any, Callable
from fastapi import BackgroundTasks

from ..core.logging import logger
from .processing_queue import ProcessingQueue, ImageTask
from .image_processor import ImageProcessor, update_image_metadata

class QueueProcessor:
    """Processor for the image processing queue."""
    
    def __init__(self, queue: ProcessingQueue, image_processor: Optional[ImageProcessor] = None):
        """
        Initialize a new queue processor.
        
        Args:
            queue: The processing queue to process
            image_processor: Optional image processor to use
        """
        self.queue = queue
        self.image_processor = image_processor or ImageProcessor(stop_check=self._should_stop)
    
    def _should_stop(self) -> bool:
        """
        Check if processing should stop.
        
        Returns:
            True if processing should stop, False otherwise
        """
        return self.queue.should_stop
    
    async def process_queue(self, background_tasks: BackgroundTasks) -> Dict[str, Any]:
        """
        Start processing the queue in the background.
        
        Args:
            background_tasks: FastAPI background tasks
            
        Returns:
            Dictionary with success status
        """
        if self.queue.is_processing:
            logger.info("Queue is already being processed")
            return {
                "success": False,
                "message": "Queue is already being processed"
            }
        
        self.queue.start_processing()
        background_tasks.add_task(self._process_queue_task)
        
        return {
            "success": True,
            "message": "Queue processing started"
        }
    
    async def _process_queue_task(self) -> None:
        """Background task to process the queue."""
        logger.info("Starting queue processing task")
        
        try:
            while not self.queue.should_stop and (task := self.queue.get_next_task()):
                await self._process_task(task)
                
                if self.queue.should_stop:
                    logger.info("Stopping queue processing due to stop request")
                    break
            
            logger.info("Queue processing completed")
        except Exception as e:
            logger.error(f"Error processing queue: {str(e)}")
        finally:
            self.queue.is_processing = False
            # Save final state
            if self.queue.persistence:
                self.queue.save()
    
    async def _process_task(self, task: ImageTask) -> None:
        """
        Process a single task.
        
        Args:
            task: The task to process
        """
        logger.info(f"Processing task: {task.image_path}")
        
        try:
            # Mark task as started
            task.start()
            
            # Check if processing should stop
            if self.queue.should_stop:
                logger.info(f"Interrupting task {task.image_path} due to stop request")
                self.queue.interrupt_current_task()
                return
            
            # Create progress callback
            def progress_callback(progress: float) -> None:
                task.update_progress(progress)
                # Auto-save on progress updates
                if self.queue.persistence:
                    self.queue.save()
            
            # Process the image with progress tracking
            image_path = Path(task.image_path)
            metadata = await self.image_processor.process_image(
                image_path, 
                progress_callback=progress_callback
            )
            
            # Check if processing should stop
            if self.queue.should_stop:
                logger.info(f"Interrupting task {task.image_path} after processing due to stop request")
                self.queue.interrupt_current_task()
                return
            
            # Mark task as completed
            self.queue.finish_current_task(True, metadata)
            logger.info(f"Task completed: {task.image_path}")
        except Exception as e:
            logger.error(f"Error processing task {task.image_path}: {str(e)}")
            self.queue.finish_current_task(False, error=str(e))
    
    async def stop_processing(self) -> Dict[str, Any]:
        """
        Stop processing the queue.
        
        Returns:
            Dictionary with success status
        """
        if not self.queue.is_processing:
            logger.info("Queue is not being processed")
            return {
                "success": False,
                "message": "Queue is not being processed"
            }
        
        self.queue.stop_processing()
        
        return {
            "success": True,
            "message": "Queue processing stopped"
        } 
