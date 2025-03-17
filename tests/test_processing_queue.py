import pytest
import sys
import os

# Add the parent directory to the path so we can import the backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.services.processing_queue import ProcessingQueue, ImageTask, TaskStatus

def test_queue_initialization():
    """Test that the queue initializes with the correct default values."""
    queue = ProcessingQueue()
    assert queue.is_processing == False
    assert queue.should_stop == False
    assert len(queue.queue) == 0
    assert queue.current_task is None
    assert len(queue.history) == 0

def test_add_task():
    """Test adding a task to the queue."""
    queue = ProcessingQueue()
    task = queue.add_task("test_image.png")
    
    assert len(queue.queue) == 1
    assert queue.queue[0] == task
    assert task.image_path == "test_image.png"
    assert task.status == TaskStatus.PENDING
    assert task.progress == 0.0

def test_get_next_task():
    """Test getting the next task from the queue."""
    queue = ProcessingQueue()
    task1 = queue.add_task("image1.png")
    task2 = queue.add_task("image2.png")
    
    next_task = queue.get_next_task()
    
    assert next_task == task1
    assert queue.current_task == task1
    assert len(queue.queue) == 1
    
    next_task = queue.get_next_task()
    
    assert next_task == task2
    assert queue.current_task == task2
    assert len(queue.queue) == 0
    
    next_task = queue.get_next_task()
    
    assert next_task is None
    assert queue.current_task is None

def test_start_stop_processing():
    """Test starting and stopping queue processing."""
    queue = ProcessingQueue()
    
    assert queue.is_processing == False
    assert queue.should_stop == False
    
    queue.start_processing()
    
    assert queue.is_processing == True
    assert queue.should_stop == False
    
    queue.stop_processing()
    
    assert queue.should_stop == True

def test_finish_current_task():
    """Test finishing the current task."""
    queue = ProcessingQueue()
    queue.add_task("image.png")
    task = queue.get_next_task()
    
    # Test successful completion
    queue.finish_current_task(True, {"result": "success"})
    
    assert task.status == TaskStatus.COMPLETED
    assert task.result == {"result": "success"}
    assert task.progress == 1.0
    assert queue.current_task is None
    assert len(queue.history) == 1
    
    # Test failure
    queue.add_task("image2.png")
    task = queue.get_next_task()
    
    queue.finish_current_task(False, error="Test error")
    
    assert task.status == TaskStatus.FAILED
    assert task.error == "Test error"
    assert queue.current_task is None
    assert len(queue.history) == 2

def test_interrupt_current_task():
    """Test interrupting the current task."""
    queue = ProcessingQueue()
    queue.add_task("image.png")
    task = queue.get_next_task()
    
    queue.interrupt_current_task()
    
    assert task.status == TaskStatus.INTERRUPTED
    assert queue.current_task is None
    assert len(queue.history) == 1

def test_clear_queue():
    """Test clearing the queue."""
    queue = ProcessingQueue()
    queue.add_task("image1.png")
    queue.add_task("image2.png")
    
    assert len(queue.queue) == 2
    
    queue.clear_queue()
    
    assert len(queue.queue) == 0

def test_get_status():
    """Test getting the queue status."""
    queue = ProcessingQueue()
    queue.add_task("image1.png")
    task = queue.get_next_task()
    
    status = queue.get_status()
    
    assert status["is_processing"] == False
    assert status["should_stop"] == False
    assert status["queue_length"] == 0
    assert status["current_task"] is not None
    assert status["history_length"] == 0
    
    detailed_status = queue.get_detailed_status()
    
    assert "queue" in detailed_status
    assert "history" in detailed_status
    assert len(detailed_status["queue"]) == 0
    assert len(detailed_status["history"]) == 0

def test_task_update_progress():
    """Test updating task progress."""
    task = ImageTask("test_image.jpg")
    
    task.update_progress(0.5)
    assert task.progress == 0.5
    
    # Test bounds
    task.update_progress(-0.1)
    assert task.progress == 0.0
    
    task.update_progress(1.5)
    assert task.progress == 1.0

def test_task_lifecycle():
    """Test the full lifecycle of a task."""
    task = ImageTask("test_image.jpg")
    
    assert task.status == TaskStatus.PENDING
    
    task.start()
    assert task.status == TaskStatus.PROCESSING
    assert task.started_at is not None
    
    task.update_progress(0.5)
    assert task.progress == 0.5
    
    result = {"description": "Test description", "tags": ["test"]}
    task.complete(result)
    assert task.status == TaskStatus.COMPLETED
    assert task.result == result
    assert task.progress == 1.0
    assert task.completed_at is not None 
