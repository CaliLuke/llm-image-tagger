import pytest
import asyncio
from unittest.mock import MagicMock, patch
from pathlib import Path
from backend.app.services.processing_queue import ProcessingQueue, ImageTask, TaskStatus
from backend.app.services.queue_processor import QueueProcessor
from backend.app.services.image_processor import ImageProcessor

@pytest.fixture
def mock_image_processor():
    """Create a mock image processor for testing."""
    processor = MagicMock(spec=ImageProcessor)
    
    async def mock_process_image(image_path, progress_callback=None):
        """Mock implementation of process_image that calls the progress callback."""
        if progress_callback:
            # Simulate progress updates
            progress_callback(0.0)
            await asyncio.sleep(0.01)
            progress_callback(0.33)
            await asyncio.sleep(0.01)
            progress_callback(0.66)
            await asyncio.sleep(0.01)
            progress_callback(1.0)
        
        return {
            "description": "Test description",
            "tags": ["test", "image"],
            "text_content": "Test text content",
            "is_processed": True
        }
    
    processor.process_image = mock_process_image
    return processor

@pytest.mark.asyncio
async def test_progress_tracking():
    """Test that progress is tracked correctly during processing."""
    # Create a queue
    queue = ProcessingQueue()
    
    # Add a task
    task = queue.add_task("/path/to/test_image.jpg")
    
    # Set the task as the current task
    queue.get_next_task()  # This sets the task as current_task
    
    # Create a processor with a mock image processor
    processor = QueueProcessor(queue, image_processor=MagicMock(spec=ImageProcessor))
    
    # Mock the image processor's process_image method
    async def mock_process_image(image_path, progress_callback=None):
        """Mock implementation that updates progress."""
        if progress_callback:
            progress_callback(0.0)
            await asyncio.sleep(0.01)
            progress_callback(0.5)
            await asyncio.sleep(0.01)
            progress_callback(1.0)
        
        return {
            "description": "Test description",
            "tags": ["test", "image"],
            "text_content": "Test text content",
            "is_processed": True
        }
    
    processor.image_processor.process_image = mock_process_image
    
    # Process the task
    await processor._process_task(queue.current_task)
    
    # Check that the task was completed
    assert task.status == TaskStatus.COMPLETED
    assert task.progress == 1.0
    assert task.result is not None
    assert task.result["description"] == "Test description"
    assert task.result["tags"] == ["test", "image"]
    assert task.result["text_content"] == "Test text content"
    assert task.result["is_processed"] is True

@pytest.mark.asyncio
async def test_progress_callback_in_queue_processor():
    """Test that the progress callback is passed to the image processor."""
    # Create a queue
    queue = ProcessingQueue()
    
    # Add a task
    task = queue.add_task("/path/to/test_image.jpg")
    
    # Create a processor with a mock image processor
    mock_processor = MagicMock(spec=ImageProcessor)
    processor = QueueProcessor(queue, image_processor=mock_processor)
    
    # Set up the mock to return a successful result
    async def mock_process_image(image_path, progress_callback=None):
        """Mock implementation that records the progress callback."""
        # Store the callback for later verification
        mock_process_image.last_callback = progress_callback
        return {
            "description": "Test description",
            "tags": ["test", "image"],
            "text_content": "Test text content",
            "is_processed": True
        }
    
    mock_process_image.last_callback = None
    mock_processor.process_image = mock_process_image
    
    # Process the task
    await processor._process_task(task)
    
    # Verify that a progress callback was passed
    assert mock_process_image.last_callback is not None
    
    # Verify that the callback updates the task's progress
    mock_process_image.last_callback(0.5)
    assert task.progress == 0.5

@pytest.mark.asyncio
async def test_progress_updates_during_queue_processing():
    """Test that progress is updated during queue processing."""
    # Create a queue
    queue = ProcessingQueue()
    
    # Add multiple tasks
    task1 = queue.add_task("/path/to/image1.jpg")
    task2 = queue.add_task("/path/to/image2.jpg")
    
    # Create a processor with a mock image processor
    mock_processor = MagicMock(spec=ImageProcessor)
    processor = QueueProcessor(queue, image_processor=mock_processor)
    
    # Set up the mock to simulate progress updates
    async def mock_process_image(image_path, progress_callback=None):
        """Mock implementation that simulates progress updates."""
        if progress_callback:
            progress_callback(0.0)
            await asyncio.sleep(0.01)
            progress_callback(0.5)
            await asyncio.sleep(0.01)
            progress_callback(1.0)
        
        return {
            "description": "Test description",
            "tags": ["test", "image"],
            "text_content": "Test text content",
            "is_processed": True
        }
    
    mock_processor.process_image = mock_process_image
    
    # Start processing the queue
    queue.start_processing()
    await processor._process_queue_task()
    
    # Check that all tasks were completed with full progress
    assert len(queue.history) == 2
    for task in queue.history:
        assert task.status == TaskStatus.COMPLETED
        assert task.progress == 1.0

@pytest.mark.asyncio
async def test_progress_tracking_with_error():
    """Test that progress is tracked correctly when an error occurs."""
    # Create a queue
    queue = ProcessingQueue()
    
    # Add a task
    task = queue.add_task("/path/to/test_image.jpg")
    
    # Set the task as the current task
    queue.get_next_task()  # This sets the task as current_task
    
    # Create a processor with a mock image processor
    mock_processor = MagicMock(spec=ImageProcessor)
    processor = QueueProcessor(queue, image_processor=mock_processor)
    
    # Set up the mock to simulate an error after some progress
    async def mock_process_image(image_path, progress_callback=None):
        """Mock implementation that simulates an error after some progress."""
        if progress_callback:
            progress_callback(0.0)
            await asyncio.sleep(0.01)
            progress_callback(0.5)
            await asyncio.sleep(0.01)

        raise Exception("Test error")
    
    mock_processor.process_image = mock_process_image
    
    # Process the task
    await processor._process_task(queue.current_task)
    
    # Check that the task failed but progress was tracked
    assert task.status == TaskStatus.FAILED
    assert task.progress == 0.5
    assert task.error == "Test error" 
