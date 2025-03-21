import pytest
import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

# Add the parent directory to the path so we can import the backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.services.processing_queue import ProcessingQueue, ImageTask, TaskStatus
from backend.app.services.queue_processor import QueueProcessor
from backend.app.services.image_processor import ImageProcessor

class MockBackgroundTasks:
    """Mock for FastAPI BackgroundTasks."""
    
    def __init__(self):
        self.tasks = []
    
    def add_task(self, func, *args, **kwargs):
        """Add a task to the list."""
        self.tasks.append((func, args, kwargs))
        
    async def run_tasks(self):
        """Run all tasks."""
        for func, args, kwargs in self.tasks:
            await func(*args, **kwargs)

class MockImageProcessor:
    """Mock for ImageProcessor."""
    
    async def process_image(self, image_path, progress_callback=None):
        """Mock processing an image."""
        # Call progress callback if provided to simulate progress
        if progress_callback:
            progress_callback(0.0)  # Start
            progress_callback(0.5)  # Middle
            progress_callback(1.0)  # Complete
            
        return {
            "description": f"Description for {image_path}",
            "tags": ["test", "mock"],
            "text_content": "Mock text content",
            "is_processed": True
        }

@pytest.mark.asyncio
async def test_queue_processor_init():
    """Test initializing the queue processor."""
    queue = ProcessingQueue()
    processor = QueueProcessor(queue)
    
    assert processor.queue == queue
    assert isinstance(processor.image_processor, ImageProcessor)

@pytest.mark.asyncio
async def test_process_queue():
    """Test processing the queue."""
    queue = ProcessingQueue()
    processor = QueueProcessor(queue, MockImageProcessor())
    
    # Add tasks to the queue
    queue.add_task("image1.png")
    queue.add_task("image2.png")
    
    # Process the queue
    background_tasks = MockBackgroundTasks()
    result = await processor.process_queue(background_tasks)
    
    assert result["success"] == True
    assert result["message"] == "Queue processing started"
    assert queue.is_processing == True
    assert len(background_tasks.tasks) == 1
    
    # Run the background tasks
    await background_tasks.run_tasks()
    
    # Check that the tasks were processed
    assert queue.is_processing == False
    assert len(queue.queue) == 0
    assert len(queue.history) == 2
    assert queue.history[0].status == TaskStatus.COMPLETED
    assert queue.history[1].status == TaskStatus.COMPLETED

@pytest.mark.asyncio
async def test_process_queue_already_processing():
    """Test processing the queue when it's already being processed."""
    queue = ProcessingQueue()
    processor = QueueProcessor(queue)
    
    # Set the queue as already processing
    queue.is_processing = True
    
    # Try to process the queue
    background_tasks = MockBackgroundTasks()
    result = await processor.process_queue(background_tasks)
    
    assert result["success"] == False
    assert result["message"] == "Queue is already being processed"
    assert len(background_tasks.tasks) == 0

@pytest.mark.asyncio
async def test_stop_processing():
    """Test stopping queue processing."""
    queue = ProcessingQueue()
    processor = QueueProcessor(queue)
    
    # Set the queue as processing
    queue.is_processing = True
    
    # Stop processing
    result = await processor.stop_processing()
    
    assert result["success"] == True
    assert result["message"] == "Queue processing stopped"
    assert queue.should_stop == True

@pytest.mark.asyncio
async def test_stop_processing_not_processing():
    """Test stopping queue processing when it's not being processed."""
    queue = ProcessingQueue()
    processor = QueueProcessor(queue)
    
    # Try to stop processing
    result = await processor.stop_processing()
    
    assert result["success"] == False
    assert result["message"] == "Queue is not being processed"

@pytest.mark.asyncio
async def test_process_task():
    """Test processing a single task."""
    queue = ProcessingQueue()
    processor = QueueProcessor(queue, MockImageProcessor())
    
    # Add a task to the queue
    task = queue.add_task("image1.png")
    queue.get_next_task()  # Set current_task
    
    # Process the task
    await processor._process_task(task)
    
    assert task.status == TaskStatus.COMPLETED
    assert task.result is not None
    assert task.progress == 1.0
    assert len(queue.history) == 1

@pytest.mark.asyncio
async def test_process_task_error():
    """Test processing a task that fails."""
    queue = ProcessingQueue()
    
    # Create a mock image processor that raises an exception
    mock_processor = MockImageProcessor()
    mock_processor.process_image = MagicMock(side_effect=Exception("Test error"))
    
    processor = QueueProcessor(queue, mock_processor)
    
    # Add a task to the queue
    task = queue.add_task("image1.png")
    queue.get_next_task()  # Set current_task
    
    # Process the task
    await processor._process_task(task)
    
    assert task.status == TaskStatus.FAILED
    assert task.error == "Test error"
    assert len(queue.history) == 1

@pytest.mark.asyncio
async def test_process_task_stop_before():
    """Test stopping processing before a task is processed."""
    queue = ProcessingQueue()
    processor = QueueProcessor(queue, MockImageProcessor())
    
    # Add a task to the queue
    task = queue.add_task("image1.png")
    queue.get_next_task()  # Set current_task
    
    # Set should_stop to True
    queue.should_stop = True
    
    # Process the task
    await processor._process_task(task)
    
    assert task.status == TaskStatus.INTERRUPTED
    assert len(queue.history) == 1

@pytest.mark.asyncio
async def test_process_task_stop_after():
    """Test stopping processing after a task is processed."""
    queue = ProcessingQueue()
    processor = QueueProcessor(queue, MockImageProcessor())
    
    # Add a task to the queue
    task = queue.add_task("image1.png")
    queue.get_next_task()  # Set current_task
    
    # Create a mock image processor that sets should_stop to True after processing
    async def mock_process_image(image_path, progress_callback=None):
        if progress_callback:
            progress_callback(0.0)
        queue.should_stop = True
        if progress_callback:
            progress_callback(1.0)
        return {
            "description": f"Description for {image_path}",
            "tags": ["test", "mock"],
            "text_content": "Mock text content",
            "is_processed": True
        }
    
    processor.image_processor.process_image = mock_process_image
    
    # Process the task
    await processor._process_task(task)
    
    assert task.status == TaskStatus.INTERRUPTED
    assert len(queue.history) == 1 
