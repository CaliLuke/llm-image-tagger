import asyncio
import sys
sys.path.append(".")
from backend.app.services.storage import file_storage

async def test_storage():
    path = "./data/test_dir/test_file2.json"
    data = {"test": "value"}
    
    print(f"Writing to {path}")
    await file_storage.write(path, data)
    print("Write successful")
    
    print(f"Reading from {path}")
    read_data = await file_storage.read(path)
    print(f"Read successful: {read_data}")

asyncio.run(test_storage()) 
