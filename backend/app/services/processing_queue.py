from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
import time
from ..core.logging import logger

class TaskStatus(Enum):
    """Status of a task in the processing queue."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"

class ImageTask:
    """Represents a single image processing task in the queue."""
    
    def __init__(self, image_path: str):
        """
        Initialize a new image task.
        
        Args:
            image_path: Path to the image to process
        """
        self.image_path: str = image_path
        self.status: TaskStatus = TaskStatus.PENDING
        self.progress: float = 0.0
        self.error: Optional[str] = None
        self.result: Optional[Dict] = None
        self.created_at: float = time.time()
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None
    
    def start(self) -> None:
        """Mark the task as started."""
        self.status = TaskStatus.PROCESSING
        self.started_at = time.time()
    
    def complete(self, result: Dict) -> None:
        """
        Mark the task as completed.
        
        Args:
            result: Result of the task
        """
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.progress = 1.0
        self.completed_at = time.time()
    
    def fail(self, error: str) -> None:
        """
        Mark the task as failed.
        
        Args:
            error: Error message
        """
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = time.time()
    
    def interrupt(self) -> None:
        """Mark the task as interrupted."""
        self.status = TaskStatus.INTERRUPTED
        self.completed_at = time.time()
    
    def update_progress(self, progress: float) -> None:
        """
        Update the progress of the task.
        
        Args:
            progress: Progress value between 0 and 1
        """
        self.progress = max(0.0, min(1.0, progress))
    
    def to_dict(self) -> Dict:
        """
        Convert the task to a dictionary.
        
        Returns:
            Dictionary representation of the task
        """
        return {
            "image_path": self.image_path,
            "status": self.status.value,
            "progress": self.progress,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        }

class ProcessingQueue:
    """Queue for processing images."""
    
    def __init__(self):
        """Initialize a new processing queue."""
        self.queue: List[ImageTask] = []
        self.current_task: Optional[ImageTask] = None
        self.is_processing: bool = False
        self.should_stop: bool = False
        self.progress: Dict[str, float] = {}
        self.history: List[ImageTask] = []
    
    def add_task(self, image_path: str) -> ImageTask:
        """
        Add a new task to the queue.
        
        Args:
            image_path: Path to the image to process
            
        Returns:
            The created task
        """
        task = ImageTask(image_path)
        self.queue.append(task)
        logger.info(f"Added task to queue: {image_path}")
        return task
    
    def get_next_task(self) -> Optional[ImageTask]:
        """
        Get the next task from the queue.
        
        Returns:
            The next task, or None if the queue is empty
        """
        if not self.queue:
            self.current_task = None
            return None
        
        task = self.queue.pop(0)
        self.current_task = task
        return task
    
    def start_processing(self) -> None:
        """Start processing the queue."""
        self.is_processing = True
        self.should_stop = False
        logger.info("Started processing queue")
    
    def stop_processing(self) -> None:
        """Stop processing the queue."""
        self.should_stop = True
        logger.info("Stopping queue processing")
    
    def finish_current_task(self, success: bool, result: Optional[Dict] = None, error: Optional[str] = None) -> None:
        """
        Finish the current task.
        
        Args:
            success: Whether the task was successful
            result: Result of the task
            error: Error message if the task failed
        """
        if not self.current_task:
            return
        
        if success:
            self.current_task.complete(result or {})
        else:
            self.current_task.fail(error or "Unknown error")
        
        self.history.append(self.current_task)
        self.current_task = None
    
    def interrupt_current_task(self) -> None:
        """Interrupt the current task."""
        if not self.current_task:
            return
        
        self.current_task.interrupt()
        self.history.append(self.current_task)
        self.current_task = None
    
    def clear_queue(self) -> None:
        """Clear the queue."""
        self.queue = []
        logger.info("Cleared queue")
    
    def get_status(self) -> Dict:
        """
        Get the status of the queue.
        
        Returns:
            Dictionary with queue status
        """
        return {
            "is_processing": self.is_processing,
            "should_stop": self.should_stop,
            "queue_length": len(self.queue),
            "current_task": self.current_task.to_dict() if self.current_task else None,
            "history_length": len(self.history)
        }
    
    def get_detailed_status(self) -> Dict:
        """
        Get detailed status of the queue.
        
        Returns:
            Dictionary with detailed queue status
        """
        status = self.get_status()
        status["queue"] = [task.to_dict() for task in self.queue]
        status["history"] = [task.to_dict() for task in self.history]
        return status 
