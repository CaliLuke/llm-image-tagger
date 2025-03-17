import json
import os
from pathlib import Path
from typing import Dict, List, Optional
import time

from ..core.logging import logger
from .processing_queue import ProcessingQueue, ImageTask, TaskStatus

class QueuePersistence:
    """Handles persistence of the processing queue."""
    
    def __init__(self, base_folder: Path):
        """
        Initialize queue persistence.
        
        Args:
            base_folder: Base folder for storing queue data
        """
        self.base_folder = base_folder
        self.queue_file = base_folder / ".queue_state.json"
        self.ensure_folder_exists()
    
    def ensure_folder_exists(self) -> None:
        """Ensure the base folder exists."""
        os.makedirs(self.base_folder, exist_ok=True)
    
    def save_queue(self, queue: ProcessingQueue) -> bool:
        """
        Save the queue state to disk.
        
        Args:
            queue: The queue to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create a serializable representation of the queue
            queue_data = {
                "is_processing": queue.is_processing,
                "should_stop": queue.should_stop,
                "queue": [task.to_dict() for task in queue.queue],
                "current_task": queue.current_task.to_dict() if queue.current_task else None,
                "history": [task.to_dict() for task in queue.history],
                "saved_at": time.time()
            }
            
            # Save to a temporary file first to avoid corruption
            temp_file = self.queue_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(queue_data, f, indent=2)
            
            # Rename to the actual file
            os.replace(temp_file, self.queue_file)
            
            logger.info(f"Queue state saved to {self.queue_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving queue state: {str(e)}")
            return False
    
    def load_queue(self) -> Optional[ProcessingQueue]:
        """
        Load the queue state from disk.
        
        Returns:
            The loaded queue, or None if loading failed
        """
        if not self.queue_file.exists():
            logger.info(f"No queue state file found at {self.queue_file}")
            return None
        
        try:
            with open(self.queue_file, "r") as f:
                queue_data = json.load(f)
            
            # Create a new queue
            queue = ProcessingQueue()
            
            # Restore queue state
            queue.is_processing = False  # Always start as not processing
            queue.should_stop = False    # Always start as not stopped
            
            # Restore tasks in the queue
            for task_data in queue_data.get("queue", []):
                task = self._create_task_from_dict(task_data)
                if task:
                    queue.queue.append(task)
            
            # Restore current task (if any) by adding it back to the queue
            if queue_data.get("current_task"):
                task = self._create_task_from_dict(queue_data["current_task"])
                if task:
                    # If task was processing, mark it as interrupted and add to history
                    if task.status == TaskStatus.PROCESSING:
                        task.interrupt()
                        queue.history.append(task)
                    else:
                        # Otherwise, add it back to the queue
                        queue.queue.insert(0, task)
            
            # Restore history
            for task_data in queue_data.get("history", []):
                task = self._create_task_from_dict(task_data)
                if task:
                    queue.history.append(task)
            
            logger.info(f"Queue state loaded from {self.queue_file} with {len(queue.queue)} pending tasks and {len(queue.history)} in history")
            return queue
        except Exception as e:
            logger.error(f"Error loading queue state: {str(e)}")
            return None
    
    def _create_task_from_dict(self, task_data: Dict) -> Optional[ImageTask]:
        """
        Create an ImageTask from a dictionary.
        
        Args:
            task_data: Dictionary representation of the task
            
        Returns:
            The created task, or None if creation failed
        """
        try:
            task = ImageTask(task_data["image_path"])
            
            # Restore task state
            task.status = TaskStatus(task_data["status"])
            task.progress = task_data["progress"]
            task.error = task_data["error"]
            task.created_at = task_data["created_at"]
            task.started_at = task_data["started_at"]
            task.completed_at = task_data["completed_at"]
            
            return task
        except Exception as e:
            logger.error(f"Error creating task from dict: {str(e)}")
            return None
    
    def clear_saved_state(self) -> bool:
        """
        Clear the saved queue state.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.queue_file.exists():
                os.remove(self.queue_file)
                logger.info(f"Queue state file removed: {self.queue_file}")
            return True
        except Exception as e:
            logger.error(f"Error removing queue state file: {str(e)}")
            return False 
