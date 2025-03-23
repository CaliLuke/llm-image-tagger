"""Tests for the storage service module."""

import os
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from backend.app.services.storage import (
    StorageBase,
    FileSystemStorage,
    StorageError,
    PermissionError,
    FileNotFoundError
)

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

@pytest.fixture
def storage():
    """Create a FileSystemStorage instance for testing."""
    return FileSystemStorage(max_retries=1, retry_delay=0)

@pytest.fixture
def test_data():
    """Create test data for file operations."""
    return {
        "test_key": "test_value",
        "nested": {
            "key": "value"
        }
    }

@pytest.mark.asyncio
async def test_read_existing_file(temp_dir, storage, test_data):
    """Test reading an existing JSON file."""
    test_file = temp_dir / "test.json"
    with open(test_file, 'w') as f:
        json.dump(test_data, f)
    
    result = await storage.read(test_file)
    assert result == test_data

@pytest.mark.asyncio
async def test_read_nonexistent_file(temp_dir, storage):
    """Test reading a nonexistent file raises FileNotFoundError."""
    test_file = temp_dir / "nonexistent.json"
    
    with pytest.raises(FileNotFoundError):
        await storage.read(test_file)

@pytest.mark.asyncio
async def test_read_invalid_json(temp_dir, storage):
    """Test reading an invalid JSON file raises StorageError."""
    test_file = temp_dir / "invalid.json"
    with open(test_file, 'w') as f:
        f.write("invalid json")
    
    with pytest.raises(StorageError):
        await storage.read(test_file)

@pytest.mark.asyncio
async def test_write_new_file(temp_dir, storage, test_data):
    """Test writing data to a new file."""
    test_file = temp_dir / "new.json"
    
    await storage.write(test_file, test_data)
    
    assert test_file.exists()
    with open(test_file, 'r') as f:
        saved_data = json.load(f)
    assert saved_data == test_data

@pytest.mark.asyncio
async def test_write_existing_file(temp_dir, storage, test_data):
    """Test overwriting an existing file."""
    test_file = temp_dir / "existing.json"
    
    # Write initial data
    with open(test_file, 'w') as f:
        json.dump({"old": "data"}, f)
    
    # Overwrite with new data
    await storage.write(test_file, test_data)
    
    with open(test_file, 'r') as f:
        saved_data = json.load(f)
    assert saved_data == test_data

@pytest.mark.asyncio
async def test_write_permission_error(temp_dir, storage, test_data):
    """Test writing to a read-only directory raises PermissionError."""
    test_file = temp_dir / "readonly" / "test.json"
    os.makedirs(test_file.parent, exist_ok=True)
    os.chmod(test_file.parent, 0o444)  # Read-only
    
    try:
        with pytest.raises(PermissionError):
            await storage.write(test_file, test_data)
    finally:
        os.chmod(test_file.parent, 0o755)  # Restore permissions

@pytest.mark.asyncio
async def test_delete_existing_file(temp_dir, storage):
    """Test deleting an existing file."""
    test_file = temp_dir / "to_delete.json"
    test_file.touch()
    
    await storage.delete(test_file)
    assert not test_file.exists()

@pytest.mark.asyncio
async def test_delete_nonexistent_file(temp_dir, storage):
    """Test deleting a nonexistent file raises FileNotFoundError."""
    test_file = temp_dir / "nonexistent.json"
    
    with pytest.raises(FileNotFoundError):
        await storage.delete(test_file)

@pytest.mark.asyncio
async def test_exists(temp_dir, storage):
    """Test checking file existence."""
    test_file = temp_dir / "exists.json"
    
    assert not await storage.exists(test_file)
    
    test_file.touch()
    assert await storage.exists(test_file)

@pytest.mark.asyncio
async def test_atomic_write(temp_dir, storage, test_data):
    """Test that write operations are atomic."""
    test_file = temp_dir / "atomic.json"
    
    # Write initial data
    with open(test_file, 'w') as f:
        json.dump({"initial": "data"}, f)
    
    # Mock an error during write to test atomicity
    with patch('builtins.open', side_effect=Exception("Write error")):
        with pytest.raises(StorageError):
            await storage.write(test_file, test_data)
    
    # Original file should be unchanged
    with open(test_file, 'r') as f:
        saved_data = json.load(f)
    assert saved_data == {"initial": "data"}
    
    # No temporary files should be left
    temp_files = list(temp_dir.glob("*.tmp"))
    assert len(temp_files) == 0

@pytest.mark.asyncio
async def test_retry_logic(temp_dir, storage, test_data):
    """Test that operations are retried on failure."""
    test_file = temp_dir / "retry.json"
    storage.max_retries = 3
    storage.retry_delay = 0  # Don't wait in tests
    
    # Mock open to fail twice then succeed
    real_open = open
    fail_count = 0
    
    def mock_open(*args, **kwargs):
        nonlocal fail_count
        if fail_count < 2:  # Fail twice
            fail_count += 1
            raise OSError("Temporary failure")
        return real_open(*args, **kwargs)
    
    with patch('builtins.open', side_effect=mock_open):
        await storage.write(test_file, test_data)
    
    assert fail_count == 2  # Verify that it failed twice before succeeding
    assert test_file.exists()
    with real_open(test_file, 'r') as f:
        saved_data = json.load(f)
    assert saved_data == test_data 
