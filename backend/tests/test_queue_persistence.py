import pytest
import os
import tempfile
import json
from pathlib import Path
from backend.app.services.processing_queue import ProcessingQueue, ImageTask, TaskStatus
from backend.app.services.queue_persistence import QueuePersistence
import logging
import shutil
import traceback

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    logger.info("Setting up temporary directory for testing")
    try:
        temp_path = Path(tempfile.mkdtemp())
        logger.debug(f"Created temporary directory at {temp_path}")
        yield temp_path
        # Clean up
        shutil.rmtree(temp_path)
        logger.debug(f"Cleaned up temporary directory at {temp_path}")
    except Exception as e:
        logger.error(f"Error in temp_dir fixture: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

def test_queue_persistence_initialization(temp_dir):
    """Test that queue persistence initializes correctly."""
    logger.info("Starting test_queue_persistence_initialization")
    try:
        logger.debug(f"Creating QueuePersistence with base folder: {temp_dir}")
        persistence = QueuePersistence(temp_dir)
        
        logger.debug("Verifying persistence attributes")
        assert persistence.base_folder == temp_dir
        assert persistence.queue_file == temp_dir / ".queue_state.json"
        assert temp_dir.exists()
        
        logger.info("Queue persistence initialization test completed successfully")
    except Exception as e:
        logger.error(f"Error in test_queue_persistence_initialization: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

def test_save_and_load_empty_queue(temp_dir):
    """Test saving and loading an empty queue."""
    persistence = QueuePersistence(temp_dir)
    queue = ProcessingQueue(persistence=persistence)
    
    # Save the queue
    result = queue.save()
    assert result is True
    assert (temp_dir / ".queue_state.json").exists()
    
    # Load the queue
    loaded_queue = ProcessingQueue.load(persistence)
    assert loaded_queue is not None
    assert len(loaded_queue.queue) == 0
    assert len(loaded_queue.history) == 0
    assert loaded_queue.is_processing is False
    assert loaded_queue.should_stop is False

def test_save_and_load_queue_with_tasks(temp_dir):
    """Test saving and loading a queue with tasks."""
    persistence = QueuePersistence(temp_dir)
    queue = ProcessingQueue(persistence=persistence)
    
    # Add tasks to the queue
    task1 = queue.add_task("/path/to/image1.jpg")
    task2 = queue.add_task("/path/to/image2.jpg")
    
    # Start processing and complete a task
    queue.start_processing()
    next_task = queue.get_next_task()
    assert next_task is not None
    queue.finish_current_task(True, {"result": "success"})
    
    # Save the queue
    result = queue.save()
    assert result is True
    
    # Load the queue
    loaded_queue = ProcessingQueue.load(persistence)
    assert loaded_queue is not None
    assert len(loaded_queue.queue) == 1
    assert len(loaded_queue.history) == 1
    assert loaded_queue.is_processing is False  # Should reset to False on load
    
    # Check that the remaining task is preserved
    assert loaded_queue.queue[0].image_path == "/path/to/image2.jpg"
    
    # Check that the history is preserved
    assert loaded_queue.history[0].image_path == "/path/to/image1.jpg"
    assert loaded_queue.history[0].status == TaskStatus.COMPLETED

def test_auto_save(temp_dir):
    """Test that auto-save works correctly."""
    persistence = QueuePersistence(temp_dir)
    queue = ProcessingQueue(persistence=persistence)
    
    # Add a task (should trigger auto-save)
    queue.add_task("/path/to/image.jpg")
    
    # Check that the file exists
    assert (temp_dir / ".queue_state.json").exists()
    
    # Load the queue and check the task is there
    loaded_queue = ProcessingQueue.load(persistence)
    assert len(loaded_queue.queue) == 1
    assert loaded_queue.queue[0].image_path == "/path/to/image.jpg"

def test_recovery_from_interrupted_task(temp_dir):
    """Test recovery from an interrupted task."""
    persistence = QueuePersistence(temp_dir)
    queue = ProcessingQueue(persistence=persistence)
    
    # Add a task and start processing
    queue.add_task("/path/to/image.jpg")
    queue.start_processing()
    task = queue.get_next_task()
    assert task is not None
    
    # Explicitly mark the task as processing
    task.start()
    
    # Save the queue with a task in progress
    queue.save()
    
    # Load the queue and check that the task was moved to history
    # and marked as interrupted since it was in progress but not completed
    loaded_queue = ProcessingQueue.load(persistence)
    assert len(loaded_queue.history) == 1
    assert loaded_queue.history[0].status == TaskStatus.INTERRUPTED
    assert loaded_queue.history[0].image_path == "/path/to/image.jpg"

def test_clear_saved_state(temp_dir):
    """Test clearing the saved state."""
    persistence = QueuePersistence(temp_dir)
    queue = ProcessingQueue(persistence=persistence)
    
    # Add a task and save
    queue.add_task("/path/to/image.jpg")
    queue.save()
    
    # Clear the saved state
    result = persistence.clear_saved_state()
    assert result is True
    assert not (temp_dir / ".queue_state.json").exists()
    
    # Load the queue (should create a new empty queue)
    loaded_queue = ProcessingQueue.load(persistence)
    assert len(loaded_queue.queue) == 0
    assert len(loaded_queue.history) == 0 

def test_queue_persistence_save_load(temp_dir):
    """Test saving and loading queue state."""
    logger.info("Starting test_queue_persistence_save_load")
    try:
        # Create test data
        queue = ProcessingQueue()
        task1 = ImageTask("image1.jpg")
        task2 = ImageTask("image2.png")
        task3 = ImageTask("image3.webp")
        queue.queue.extend([task1, task2, task3])
        logger.debug(f"Created test queue with {len(queue.queue)} tasks")
        
        # Initialize persistence
        logger.debug("Creating QueuePersistence instance")
        persistence = QueuePersistence(temp_dir)
        
        # Save queue state
        logger.debug("Saving queue state")
        success = persistence.save_queue(queue)
        assert success, "Failed to save queue state"
        
        # Verify file exists
        queue_file = temp_dir / ".queue_state.json"
        logger.debug(f"Verifying queue file exists at {queue_file}")
        assert queue_file.exists()
        
        # Load and verify state
        logger.debug("Loading queue state")
        loaded_queue = persistence.load_queue()
        assert loaded_queue is not None, "Failed to load queue state"
        logger.debug(f"Loaded queue with {len(loaded_queue.queue)} tasks")
        
        # Verify queue contents
        assert len(loaded_queue.queue) == len(queue.queue)
        for orig_task, loaded_task in zip(queue.queue, loaded_queue.queue):
            assert orig_task.image_path == loaded_task.image_path
            assert orig_task.status == loaded_task.status
        
        logger.info("Queue persistence save/load test completed successfully")
    except Exception as e:
        logger.error(f"Error in test_queue_persistence_save_load: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

def test_queue_persistence_empty_state(temp_dir):
    """Test handling of empty or non-existent queue state."""
    logger.info("Starting test_queue_persistence_empty_state")
    try:
        logger.debug("Creating QueuePersistence instance")
        persistence = QueuePersistence(temp_dir)
        
        # Test loading non-existent state
        logger.debug("Testing load of non-existent queue state")
        empty_queue = persistence.load_queue()
        assert empty_queue is None
        
        # Test saving empty queue
        logger.debug("Testing save of empty queue")
        empty_queue = ProcessingQueue()
        success = persistence.save_queue(empty_queue)
        assert success
        
        # Verify empty queue loads correctly
        logger.debug("Verifying empty queue loads correctly")
        loaded_queue = persistence.load_queue()
        assert loaded_queue is not None
        assert len(loaded_queue.queue) == 0
        assert len(loaded_queue.history) == 0
        
        logger.info("Empty queue state test completed successfully")
    except Exception as e:
        logger.error(f"Error in test_queue_persistence_empty_state: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

def test_queue_persistence_invalid_data(temp_dir):
    """Test handling of invalid queue state data."""
    logger.info("Starting test_queue_persistence_invalid_data")
    try:
        logger.debug("Creating QueuePersistence instance")
        persistence = QueuePersistence(temp_dir)
        
        # Write invalid JSON
        queue_file = temp_dir / ".queue_state.json"
        logger.debug(f"Writing invalid JSON to {queue_file}")
        queue_file.write_text("invalid json data")
        
        # Verify loading invalid data returns None
        logger.debug("Testing load of invalid queue state")
        result = persistence.load_queue()
        assert result is None
        
        logger.info("Invalid queue state test completed successfully")
    except Exception as e:
        logger.error(f"Error in test_queue_persistence_invalid_data: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise 
