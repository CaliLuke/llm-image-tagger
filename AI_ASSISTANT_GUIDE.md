# AI Assistant Guide

## ⚠️ DEBUGGING CHECKLIST - FOLLOW THIS EXACTLY

1. **RUN TESTS IN ORDER:**
   - First run without verbose: `pytest -v`
   - For failures, run with debug logging: `pytest -vv --log-cli-level=DEBUG path/to/test.py::test_name`
   - Fix ONE issue at a time, verify with specific test
   - Run all tests again for regression checking

2. **CHECK ALL LOGS:**
   - **ALWAYS check logs in logs/ directory**, not just terminal output
   - Look for patterns in failures and error messages
   - Verify logging context is helpful and complete

3. **VERIFY ALL STORAGE LAYERS:**

   ```
   {
       "json_files": "<image_folder>/image_metadata.json",  # Persistent metadata
       "vector_store": ".vectordb",                         # Search index
       "memory_state": "router.current_folder",            # Runtime state
   }
   ```

4. **CRITICAL RULE:**
   - After TWO failed attempts on same test → STOP
   - Review implementation code and test fixtures systematically
   - Document what you've learned
   - Make small, focused changes targeting root causes, not symptoms

## Initial Setup

1. **Python Version Check:**

   ```bash
   grep "python_version" requirements.txt
   python3 --version
   ```

   - Use exactly the Python version from requirements.txt

2. **Virtual Environment:**

   ```bash
   ls venv/
   venv/bin/python --version
   # If incorrect:
   rm -rf venv/
   python<version> -m venv venv
   pip install -r requirements.txt
   ```

3. **Run Commands:**

   ```bash
   source venv/bin/activate
   python run.py --debug
   ```

## Development Principles

1. **Work Methodically:**
   - Complete one component before moving to next
   - Test each change before proceeding
   - Document all changes
   - Add appropriate logging

2. **Endpoint Consistency Checklist:**
   - For metadata-modifying endpoints:
     □ Load current metadata
     □ Validate input
     □ Update vector store
     □ Update JSON storage
     □ Return consistent response

3. **Metadata Synchronization:**
   - Keep all storage layers in sync
   - Store metadata in image folder for portability
   - Use atomic file operations
   - Validate before storing
   - Log all storage operations
   - Test synchronization
   - Handle edge cases
   - Clean up stale data

   ```python
   # Example synchronization pattern
   async def update_metadata(folder_path: Path, image_path: str, metadata: Dict):
       # 1. Update JSON storage
       metadata_file = folder_path / "image_metadata.json"
       with open(metadata_file, 'r') as f:
           json_metadata = json.load(f)
       json_metadata[image_path] = metadata
       with open(metadata_file, 'w') as f:
           json.dump(json_metadata, f, indent=4)
       
       # 2. Update vector store
       await vector_store.add_or_update_image(image_path, metadata)
       
       # 3. Verify consistency
       stored_metadata = vector_store.get_metadata(image_path)
       assert stored_metadata == metadata
   ```

## Testing Best Practices

1. **Vector Store Testing Checklist:**
   □ Test initialization and configuration
   □ Test metadata CRUD operations
   □ Test search functionality
   □ Test sync with JSON storage
   □ Test error handling
   □ Test edge cases
   □ Test concurrent operations if applicable

2. **Mock Configuration Example:**

   ```python
   # Example of proper search mocking
   mock_metadata_operations['metadata'].clear()  # Clear existing state
   mock_metadata_operations['metadata'].update({
       "test_image.png": {
           "description": "A test image for testing",
           "tags": ["test", "example"],
           "text_content": "Test content"
       }
   })
   
   # Mock vector search behavior
   def mock_search_images(query: str):
       if query.lower() == "test":
           return ["test_image.png"]
       return []
   ```

3. **State Modification Test Pattern:**

   ```python
   def test_metadata_update():
       # 1. Set up initial state
       initial_state = setup_initial_state()
       
       # 2. Perform update
       response = await client.post("/update-endpoint", json=update_data)
       
       # 3. Verify ALL storage locations
       verify_vector_store_update()
       verify_json_file_update()
       verify_response_format()
       
       # 4. Verify state consistency
       assert_states_match(
           vector_store_state=get_vector_store_state(),
           json_file_state=get_json_file_state(),
           expected_state=expected_state
       )
   ```

## Common Pitfalls to Avoid

1. DO NOT modify run.py or core infrastructure without explicit request
2. DO NOT make large, sweeping changes across multiple modules
3. DO NOT ignore established project structure
4. DO NOT skip adding logging or documentation
5. DO NOT optimize working code prematurely
6. DO NOT add new dependencies without justification
7. DO NOT modify test files without understanding the test suite
8. DO NOT interrupt normal startup processes
9. DO NOT ignore version requirements - ALWAYS check requirements.txt first
10. DO NOT assume endpoint implementations are consistent without verification
11. DO NOT test state changes without checking all storage layers
12. DO NOT fix symptoms without comparing against similar functionality

## When Things Go Wrong

1. CHECK THE LOGS:
   - Review error messages completely
   - Look for patterns in failures
   - Check log levels are appropriate
   - Verify logging context is helpful

2. SYSTEMATIC DEBUGGING:
   - Isolate the failing component
   - Review recent changes
   - Check dependencies and state
   - Verify configuration
   - Test smallest possible reproduction

3. MAKING FIXES:
   - Address root cause, not symptoms
   - Add tests for the fixed condition
   - Document why the fix works
   - Update related documentation
   - Add logging to prevent similar issues

Remember: Development should be methodical, well-documented, and focused on one task at a time. Always maintain the established patterns and practices of the project.
