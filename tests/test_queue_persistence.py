import pytest
import os
import tempfile
import json
from pathlib import Path
from backend.app.services.processing_queue import ProcessingQueue, ImageTask, TaskStatus
from backend.app.services.queue_persistence import QueuePersistence

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

def test_queue_persistence_initialization(temp_dir):
    """Test that queue persistence initializes correctly."""
    persistence = QueuePersistence(temp_dir)
    assert persistence.base_folder == temp_dir
    assert persistence.queue_file == temp_dir / ".queue_state.json"
    assert temp_dir.exists()

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
