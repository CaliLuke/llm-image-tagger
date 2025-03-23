import asyncio
import sys
import os
import logging
from pathlib import Path
sys.path.append(".")
from backend.app.services.storage import file_storage

# Configure logging
logging.basicConfig(level=logging.DEBUG)

async def test_nested_storage():
    # Create a deep nested path that might not exist
    nested_path = "./data/test_nested/subfolder1/subfolder2/test_file.json"
    path = Path(nested_path)
    data = {"test": "nested value"}
    
    print(f"Testing with nested path: {path}")
    print(f"Parent exists before: {path.parent.exists()}")
    
    try:
        print(f"Writing to {path}")
        await file_storage.write(path, data)
        print("Write successful")
        
        print(f"Parent exists after: {path.parent.exists()}")
        print(f"File exists: {path.exists()}")
        
        print(f"Reading from {path}")
        read_data = await file_storage.read(path)
        print(f"Read successful: {read_data}")
        
        # Test with a path that has permissions issues
        if os.name == 'posix':  # Unix-like systems
            restricted_path = "/root/test_restricted.json"
            print(f"\nTesting with restricted path: {restricted_path}")
            try:
                await file_storage.write(restricted_path, data)
                print("Write successful (unexpected!)")
            except Exception as e:
                print(f"Got expected error: {type(e).__name__}: {str(e)}")
        
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {str(e)}")

asyncio.run(test_nested_storage()) 
