from fastapi.testclient import TestClient
import pytest
from pathlib import Path
import os
import sys

# Add the parent directory to the path so we can import the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

client = TestClient(app)

def test_read_root():
    """Test that the root endpoint returns the index.html file."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_folder_not_found():
    """Test that the images endpoint returns 404 for a non-existent folder."""
    response = client.post("/images", json={"folder_path": "/path/that/does/not/exist"})
    assert response.status_code == 404
    assert "Folder not found" in response.json()["detail"]

def test_search_no_folder():
    """Test that the search endpoint returns 400 when no folder is selected."""
    response = client.post("/search", json={"query": "test"})
    assert response.status_code == 400
    assert "No folder selected" in response.json()["detail"] 
