"""
Global router state management.

This module provides:
1. State initialization and management
2. Global state access
3. State validation methods
4. Safe state updates

The RouterState class is a singleton that maintains the global state
of the application, including:
- Current folder being processed
- Vector store instance
- Processing status
- Queue management
- Persistence handlers
"""

from typing import Optional, Any
from pathlib import Path
from ..services.vector_store import VectorStore
from ..services.processing_queue import ProcessingQueue
from ..services.queue_persistence import QueuePersistence
from ..core.logging import logger

class RouterState:
    """
    Global router state management.
    
    This class maintains the global state of the application and provides
    methods for safe state access and modification.
    
    Attributes:
        current_folder (Optional[str]): Path to current working folder
        vector_store (Optional[VectorStore]): Vector store instance
        is_processing (bool): Whether image processing is active
        should_stop_processing (bool): Signal to stop processing
        current_task (Any): Reference to current background task
        processing_queue (Optional[ProcessingQueue]): Queue instance
        queue_persistence (Optional[QueuePersistence]): Queue persistence handler
    """
    
    def __init__(self):
        """Initialize router state with default values."""
        self.current_folder: Optional[str] = None
        self.vector_store: Optional[VectorStore] = None
        self.is_processing: bool = False
        self.should_stop_processing: bool = False
        self.current_task: Any = None
        self.processing_queue: Optional[ProcessingQueue] = None
        self.queue_persistence: Optional[QueuePersistence] = None
        logger.info("Initialized RouterState")
    
    def reset(self) -> None:
        """
        Reset all state to default values.
        
        This method:
        1. Clears the current folder
        2. Resets processing flags
        3. Clears task references
        4. Resets queue state
        """
        self.__init__()
        logger.info("Reset RouterState to initial values")
    
    def validate_folder(self) -> bool:
        """
        Validate that current folder is set and exists.
        
        Returns:
            bool: True if folder is valid, False otherwise
        """
        if not self.current_folder:
            logger.warning("No current folder set")
            return False
            
        folder = Path(self.current_folder)
        if not folder.exists() or not folder.is_dir():
            logger.error(f"Invalid current folder: {self.current_folder}")
            return False
            
        return True
    
    def set_current_folder(self, folder_path: str) -> None:
        """
        Set the current working folder.
        
        Args:
            folder_path (str): Path to the folder
        """
        self.current_folder = folder_path
        logger.info(f"Set current folder to: {folder_path}")
    
    def initialize_vector_store(self, persist_directory: str) -> None:
        """
        Initialize the vector store.
        
        Args:
            persist_directory (str): Directory for vector store persistence
        """
        self.vector_store = VectorStore(persist_directory=persist_directory)
        logger.info(f"Initialized vector store at: {persist_directory}")
    
    def initialize_queue(self, persistence: QueuePersistence) -> None:
        """
        Initialize the processing queue with persistence.
        
        Args:
            persistence (QueuePersistence): Queue persistence handler
        """
        self.queue_persistence = persistence
        self.processing_queue = ProcessingQueue.load(persistence)
        logger.info("Initialized processing queue with persistence")

# Create global state instance
state = RouterState() 
