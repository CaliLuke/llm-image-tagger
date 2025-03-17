import pytest
import os
from pathlib import Path

@pytest.fixture
def test_data_dir():
    """Create and return a temporary test data directory."""
    current_dir = Path(__file__).parent
    test_data = current_dir / "test_data"
    test_data.mkdir(exist_ok=True)
    return test_data

@pytest.fixture
def cleanup_test_data(test_data_dir):
    """Cleanup test data after tests."""
    yield
    # Clean up any test files
    for file in test_data_dir.glob("*"):
        if file.is_file():
            file.unlink() 
