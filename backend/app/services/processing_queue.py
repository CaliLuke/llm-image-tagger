"""
Processing queue module for managing image processing tasks.
This module provides:
- Task status tracking and management
- Progress monitoring and updates
- Queue state management
- Task history tracking
- State persistence and recovery
- Graceful interruption handling
"""

from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Union
import time
import json
import traceback
from ..core.logging import logger

class TaskStatus(Enum):
    """
    Status of a task in the processing queue.
    
    Possible states:
    - PENDING: Task is waiting to be processed
    - PROCESSING: Task is currently being processed
    - COMPLETED: Task has been successfully processed
    - FAILED: Task processing failed
    - INTERRUPTED: Task was interrupted during processing
    
    Each state represents a different phase in the task's lifecycle,
    allowing for proper tracking and handling of task progress.
    """
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"

class ImageTask:
    """
    Represents a single image processing task in the queue.
    
    This class tracks:
    1. Task status and progress
    2. Timing information (creation, start, completion)
    3. Results and errors
    4. Task metadata
    
    The class provides methods for:
    - Starting and completing tasks
    - Updating progress
    - Handling failures and interruptions
    - Serializing task state
    
    Attributes:
        image_path (str): Path to the image to process
        status (TaskStatus): Current status of the task
        progress (float): Progress value between 0 and 1
        error (Optional[str]): Error message if task failed
        result (Optional[Dict]): Task result data
        created_at (float): Timestamp of task creation
        started_at (Optional[float]): Timestamp when task started
        completed_at (Optional[float]): Timestamp when task completed
    """
    
    def __init__(self, image_path: str):
        """
        Initialize a new image task.
        
        This method:
        1. Sets initial task state
        2. Initializes timing information
        3. Sets default progress and status
        
        Args:
            image_path (str): Path to the image to process
        """
        self.image_path: str = image_path
        self.status: TaskStatus = TaskStatus.PENDING
        self.progress: float = 0.0
        self.error: Optional[str] = None
        self.result: Optional[Dict] = None
        self.created_at: float = time.time()
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None
        logger.debug(f"Created new ImageTask for: {image_path}")
    
    def start(self) -> None:
        """
        Mark the task as started.
        
        This method:
        1. Updates the task status to PROCESSING
        2. Records the start time
        3. Logs the state change
        """
        logger.debug(f"Starting task: {self.image_path}")
        self.status = TaskStatus.PROCESSING
        self.started_at = time.time()
        logger.debug(f"Task started at: {self.started_at}")
    
    def complete(self, result: Dict) -> None:
        """
        Mark the task as completed.
        
        This method:
        1. Updates the task status to COMPLETED
        2. Stores the result
        3. Sets progress to 100%
        4. Records the completion time
        5. Logs the completion details
        
        Args:
            result (Dict): Result of the task
        """
        logger.debug(f"Completing task: {self.image_path}")
        logger.debug(f"Task result: {json.dumps(result, indent=2)}")
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.progress = 1.0
        self.completed_at = time.time()
        logger.debug(f"Task completed at: {self.completed_at}")
    
    def fail(self, error: str) -> None:
        """
        Mark the task as failed.
        
        This method:
        1. Updates the task status to FAILED
        2. Stores the error message
        3. Records the failure time
        4. Logs the error details
        
        Args:
            error (str): Error message
        """
        logger.error(f"Task failed: {self.image_path}")
        logger.error(f"Error message: {error}")
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = time.time()
        logger.debug(f"Task failed at: {self.completed_at}")
    
    def interrupt(self) -> None:
        """
        Mark the task as interrupted.
        
        This method:
        1. Updates the task status to INTERRUPTED
        2. Records the interruption time
        3. Logs the interruption
        """
        logger.warning(f"Task interrupted: {self.image_path}")
        self.status = TaskStatus.INTERRUPTED
        self.completed_at = time.time()
        logger.debug(f"Task interrupted at: {self.completed_at}")
    
    def update_progress(self, progress: float) -> None:
        """
        Update the progress of the task.
        
        This method:
        1. Clamps the progress value between 0 and 1
        2. Updates the task progress
        3. Logs the progress update
        
        Args:
            progress (float): Progress value between 0 and 1
        """
        self.progress = max(0.0, min(1.0, progress))
        logger.debug(f"Task progress updated: {self.image_path} - {progress:.2%}")
    
    def to_dict(self) -> Dict:
        """
        Convert the task to a dictionary.
        
        This method:
        1. Serializes the task state
        2. Includes all relevant task information
        3. Formats timestamps and status values
        
        Returns:
            Dict: Dictionary representation of the task containing:
                - image_path: Path to the image
                - status: Current task status
                - progress: Current progress value
                - error: Error message if any
                - created_at: Creation timestamp
                - started_at: Start timestamp if started
                - completed_at: Completion timestamp if completed
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
    """
    Queue for processing images.
    
    This class manages:
    1. A queue of image processing tasks
    2. Task status and progress tracking
    3. Queue state (processing, stopped)
    4. Task history
    5. State persistence
    
    The class provides methods for:
    - Adding and removing tasks
    - Starting and stopping processing
    - Managing task state
    - Persisting queue state
    - Retrieving queue status
    
    Attributes:
        queue (List[ImageTask]): List of pending tasks
        current_task (Optional[ImageTask]): Currently processing task
        is_processing (bool): Whether the queue is being processed
        should_stop (bool): Whether processing should stop
        progress (Dict[str, float]): Progress tracking for all tasks
        history (List[ImageTask]): History of completed tasks
        persistence: Optional queue persistence handler
        auto_save_enabled (bool): Whether auto-saving is enabled
    """
    
    def __init__(self, persistence=None):
        """
        Initialize a new processing queue.
        
        This method:
        1. Initializes queue state
        2. Sets up persistence if provided
        3. Configures auto-save functionality
        
        Args:
            persistence: Optional queue persistence handler for saving/loading queue state
        """
        logger.info("Initializing new ProcessingQueue")
        self.queue: List[ImageTask] = []
        self.current_task: Optional[ImageTask] = None
        self.is_processing: bool = False
        self.should_stop: bool = False
        self.progress: Dict[str, float] = {}
        self.history: List[ImageTask] = []
        self.persistence = persistence
        self.auto_save_enabled = persistence is not None
        logger.debug(f"Queue initialized with persistence: {persistence is not None}")
    
    def add_task(self, image_path: str) -> ImageTask:
        """
        Add a new task to the queue.
        
        This method:
        1. Creates a new ImageTask
        2. Adds it to the queue
        3. Triggers auto-save if enabled
        4. Logs the task addition
        
        Args:
            image_path (str): Path to the image to process
            
        Returns:
            ImageTask: The created task
        """
        task = ImageTask(image_path)
        self.queue.append(task)
        logger.info(f"Added task to queue: {image_path}")
        logger.debug(f"Current queue length: {len(self.queue)}")
        self._auto_save()
        return task
    
    def get_next_task(self) -> Optional[ImageTask]:
        """
        Get the next task from the queue.
        
        This method:
        1. Safely checks if queue has tasks
        2. Removes and returns the next task from the queue
        3. Updates the current task reference
        4. Triggers auto-save if enabled
        5. Logs the task retrieval
        
        Returns:
            Optional[ImageTask]: The next task if available, None if queue is empty
        """
        try:
            if not self.queue:
                logger.debug("Queue is empty, no next task available")
                return None
                
            task = self.queue.pop(0)
            self.current_task = task
            logger.info(f"Retrieved next task: {task.image_path}")
            logger.debug(f"Remaining queue length: {len(self.queue)}")
            self._auto_save()
            return task
        except IndexError:
            logger.warning("Attempted to get task from empty queue")
            return None
        except Exception as e:
            logger.error(f"Error getting next task: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None
    
    def start_processing(self) -> None:
        """
        Start processing the queue.
        
        This method:
        1. Sets the processing flag
        2. Clears the stop flag
        3. Logs the state change
        """
        logger.info("Starting queue processing")
        self.is_processing = True
        self.should_stop = False
        logger.debug("Queue processing state updated")
    
    def stop_processing(self) -> None:
        """
        Stop processing the queue.
        
        This method:
        1. Sets the stop flag
        2. Logs the state change
        """
        logger.info("Stopping queue processing")
        self.should_stop = True
        logger.debug("Queue stop flag set")
    
    def finish_current_task(self, success: bool, metadata_or_error: Union[Dict, str] = None) -> None:
        """
        Finish the current task and move it to history.

        This method:
        1. Updates task status based on success
        2. Stores metadata or error message
        3. Moves current task to history
        4. Clears current task reference
        5. Triggers auto-save if enabled
        6. Logs the task completion

        Args:
            success (bool): Whether the task completed successfully
            metadata_or_error (Union[Dict, str], optional): Task metadata if successful, error message if failed
        """
        if self.current_task:
            logger.info(f"Finishing current task: {self.current_task.image_path}")
            if success:
                self.current_task.complete(metadata_or_error)
            else:
                self.current_task.fail(metadata_or_error)
            self.history.append(self.current_task)
            self.current_task = None
            self._auto_save()
            logger.debug("Current task moved to history")
        else:
            logger.debug("No current task to finish")
    
    def interrupt_current_task(self) -> None:
        """
        Interrupt the current task.
        
        This method:
        1. Interrupts the current task if exists
        2. Moves it to history
        3. Clears current task reference
        4. Triggers auto-save if enabled
        5. Logs the interruption
        """
        if self.current_task:
            logger.info(f"Interrupting current task: {self.current_task.image_path}")
            self.current_task.interrupt()
            self.history.append(self.current_task)
            self.current_task = None
            self._auto_save()
            logger.debug("Current task interrupted and moved to history")
        else:
            logger.debug("No current task to interrupt")
    
    def clear_queue(self) -> None:
        """
        Clear all tasks from the queue.
        
        This method:
        1. Clears the queue list
        2. Triggers auto-save if enabled
        3. Logs the queue clearing
        """
        logger.info("Clearing queue")
        self.queue.clear()
        self._auto_save()
        logger.debug("Queue cleared")
    
    def get_status(self) -> Dict:
        """
        Get the current status of the queue.
        
        This method:
        1. Collects queue statistics
        2. Includes current task information
        3. Provides processing state
        
        Returns:
            Dict: Dictionary containing:
                - queue_length: Number of pending tasks
                - is_processing: Whether queue is being processed
                - current_task: Current task info if any
                - history_length: Number of completed tasks
        """
        status = {
            "queue_length": len(self.queue),
            "is_processing": self.is_processing,
            "current_task": self.current_task.to_dict() if self.current_task else None,
            "history_length": len(self.history)
        }
        logger.debug(f"Queue status: {json.dumps(status, indent=2)}")
        return status
    
    def get_detailed_status(self) -> Dict:
        """
        Get detailed status of the queue.
        
        This method:
        1. Collects comprehensive queue statistics
        2. Includes all task information
        3. Provides detailed processing state
        
        Returns:
            Dict: Dictionary containing:
                - queue: List of pending tasks
                - current_task: Current task info if any
                - history: List of completed tasks
                - is_processing: Whether queue is being processed
                - should_stop: Whether processing should stop
        """
        status = {
            "queue": [task.to_dict() for task in self.queue],
            "current_task": self.current_task.to_dict() if self.current_task else None,
            "history": [task.to_dict() for task in self.history],
            "is_processing": self.is_processing,
            "should_stop": self.should_stop
        }
        logger.debug(f"Detailed queue status: {json.dumps(status, indent=2)}")
        return status
    
    def _auto_save(self) -> None:
        """
        Save queue state if auto-save is enabled.
        
        This method:
        1. Checks if auto-save is enabled
        2. Saves queue state if enabled
        3. Logs the save operation
        """
        if self.auto_save_enabled and self.persistence:
            logger.debug("Auto-saving queue state")
            self.persistence.save_queue(self)
            logger.debug("Queue state auto-saved")
    
    def save(self) -> bool:
        """
        Save queue state to persistent storage.

        This method:
        1. Saves queue state if persistence is available
        2. Logs the save operation

        Returns:
            bool: True if successful, False otherwise
        """
        if self.persistence:
            logger.info("Saving queue state")
            success = self.persistence.save_queue(self)
            if success:
                logger.info("Queue state saved")
            else:
                logger.error("Failed to save queue state")
            return success
        else:
            logger.warning("Cannot save queue state: No persistence handler configured")
            return False
    
    def load(self) -> None:
        """
        Load queue state from persistent storage.

        This method:
        1. Loads queue state if persistence is available
        2. Restores queue and history
        3. Logs the load operation
        """
        if self.persistence:
            logger.info("Loading queue state")
            loaded_queue = self.persistence.load_queue()
            if loaded_queue:
                self.queue = loaded_queue.queue
                self.history = loaded_queue.history
                logger.info("Queue state loaded")
                logger.debug(f"Loaded {len(self.queue)} tasks in queue and {len(self.history)} in history")
            else:
                logger.warning("No saved queue state found")
        else:
            logger.warning("Cannot load queue state: No persistence handler configured")

    @classmethod
    def load(cls, persistence=None):
        """Load queue state from persistence.

        Args:
            persistence (QueuePersistence, optional): Persistence handler. Defaults to None.

        Returns:
            ProcessingQueue: A new queue instance with loaded state or empty if no state found.
        """
        queue = cls(persistence=persistence)
        if persistence:
            try:
                state = persistence.load_queue_state()
                if state:
                    # Use _create_task_from_dict to properly restore tasks
                    queue.queue = [persistence._create_task_from_dict(task) for task in state.get('queue', [])]
                    queue.queue = [task for task in queue.queue if task is not None]  # Filter out any failed task creations
                    
                    queue.history = [persistence._create_task_from_dict(task) for task in state.get('history', [])]
                    queue.history = [task for task in queue.history if task is not None]  # Filter out any failed task creations
                    
                    # Handle current task - if it was processing, mark as interrupted and move to history
                    if state.get('current_task'):
                        current_task = persistence._create_task_from_dict(state['current_task'])
                        if current_task and current_task.status == TaskStatus.PROCESSING:
                            current_task.interrupt()
                            queue.history.append(current_task)
                            queue.current_task = None
                        else:
                            # If task wasn't processing, add it back to the front of the queue
                            if current_task:
                                queue.queue.insert(0, current_task)
                            queue.current_task = None
                    else:
                        queue.current_task = None
                        
                    # Always start with processing disabled, regardless of saved state
                    queue.is_processing = False
                    queue.should_stop = False
                    
                    logger.info("Queue state loaded")
                    logger.debug(f"Loaded {len(queue.queue)} tasks in queue and {len(queue.history)} in history")
                else:
                    logger.warning("No saved queue state found")
            except Exception as e:
                logger.error(f"Error loading queue state: {str(e)}")
                logger.debug(traceback.format_exc())
        else:
            logger.warning("Cannot load queue state: No persistence handler configured")
        
        return queue 
