# AI Assistant Guide

**IMPORTANT: READ THIS GUIDE COMPLETELY BEFORE HELPING USERS WITH THIS PROJECT**

This guide outlines the development practices and procedures to follow when assisting users with the Image Tagger project.

## Initial Setup

1. CHECK Python version requirements FIRST:

   ```bash
   # Check required Python version from requirements.txt
   grep "python_version" requirements.txt
   
   # Check current Python version
   python3 --version
   
   # If version doesn't match requirements:
   # Use the correct Python version as specified in requirements.txt
   # Either through direct command (pythonX.Y) or version manager like pyenv
   ```

2. CHECK if virtual environment exists and uses correct Python:

   ```bash
   # Check if venv directory exists
   ls venv/
   
   # If it exists, verify Python version matches requirements:
   venv/bin/python --version
   
   # If wrong Python version or venv doesn't exist:
   # Remove existing venv if needed
   rm -rf venv/
   # Create new venv with correct Python version from requirements.txt
   python<version> -m venv venv
   pip install -r requirements.txt
   ```

3. JUST run these two commands in order:

   ```bash
   source venv/bin/activate
   python run.py --debug
   ```

## Development Best Practices

1. METHODICAL APPROACH:
   - Work on one component at a time
   - Complete and test each change before moving to the next
   - Document changes as you make them
   - Add appropriate logging statements for each significant operation
   - Review code changes before suggesting them
   - ENDPOINT CONSISTENCY:
     - Group related endpoints (e.g., all metadata-modifying endpoints)
     - Create a checklist of common operations they should perform
     - Compare implementation patterns between similar endpoints
     - Example checklist for metadata-modifying endpoints:
       □ Load current metadata state
       □ Validate input
       □ Update vector store
       □ Update JSON storage
       □ Return consistent response format

2. CODE ORGANIZATION:
   - Follow the established module structure
   - Keep routers focused on their specific functionality
   - Use appropriate dependencies from dependencies.py
   - Maintain consistent error handling patterns
   - Add docstrings to all new functions and classes

3. METADATA PERSISTENCE AND SYNCHRONIZATION:
   - ALWAYS maintain consistency between storage layers:
     ```python
     # Storage layers that must be kept in sync:
     {
         "json_files": "<image_folder>/image_metadata.json",  # Persistent metadata
         "vector_store": ".vectordb",                         # Search index
         "memory_state": "router.current_folder",            # Runtime state
     }
     ```

   - Synchronization checklist:
     □ Load metadata from JSON when opening folder
     □ Sync vector store with loaded metadata
     □ Update both JSON and vector store when processing images
     □ Verify all storage layers after updates
     □ Handle reloading scenarios properly

   - Common synchronization pitfalls:
     - Not syncing vector store after loading metadata
     - Not updating all storage layers consistently
     - Not handling file deletion properly
     - Not verifying metadata consistency after updates
     - Not testing folder reload scenarios

   - Best practices:
     1. Store metadata in the image folder for portability
     2. Use atomic file operations for metadata updates
     3. Validate metadata before storing
     4. Log all storage operations
     5. Add synchronization tests
     6. Handle edge cases (empty folders, invalid metadata)
     7. Clean up stale data

   - Example synchronization pattern:
     ```python
     async def update_metadata(folder_path: Path, image_path: str, metadata: Dict):
         # 1. Update JSON storage in image folder
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

   Note: This is an interim solution. In the future, metadata will be stored directly 
   in the image files themselves using standard formats like EXIF/XMP.

4. LOGGING AND DOCUMENTATION:
   - Add logging statements at appropriate levels (debug/info/error)
   - Include context in log messages (e.g., file paths, operation details)
   - Document all API endpoints in both docstrings and README
   - Keep documentation in sync with code changes
   - Update type hints and schemas as needed

5. TESTING AND VALIDATION:
   - Make small, testable changes
   - Verify each change works before proceeding
   - Let tests complete before diagnosing issues
   - Use the auto-reload feature during development
   - Test error cases and edge conditions
   - Follow this testing workflow:
     1. Run all tests without verbose logging first: `pytest -v`
     2. If failures found, run individual failing tests with debug logging:
        `pytest -vv --log-cli-level=DEBUG path/to/test.py::test_name`
     3. Fix issues one at a time, verifying each fix with the specific test
     4. After fixes, run all tests again to ensure no regressions
   - Keep test output focused and manageable
   - Document any test modifications or additions
   - Ensure test names and assertions are clear and descriptive

## Testing Best Practices

1. METHODICAL APPROACH:
   - Work on one component at a time
   - Complete and test each change before moving to the next
   - Document changes as you make them
   - Add appropriate logging statements for each significant operation
   - Review code changes before suggesting them

2. WHEN REPEATED TEST FIXES FAIL:
   - Stop after two failed attempts to fix a test
   - Systematically review the implementation code and test fixtures
   - Document learnings and update this guide
   - Make small, focused changes
   - Verify fixes with targeted test runs

3. TESTING SEARCH FUNCTIONALITY:
   - Understand all search components (both vector and full-text search)
   - Mock all necessary components:

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

   - Control test data carefully:
     - Use distinct terms for relevant vs irrelevant content
     - Ensure metadata won't accidentally match irrelevant queries
     - Consider case sensitivity in search terms
   - Test both positive and negative cases:
     - Verify relevant results are found
     - Confirm irrelevant queries return no results
     - Check returned metadata matches expectations
   - Common pitfalls to avoid:
     - Incomplete mocking (remember both vector and full-text search)
     - Uncleared test state between runs
     - Ambiguous test data that could match unintended queries
     - Missing metadata fields that should be searched

4. STATE MANAGEMENT CONSISTENCY:
   - Map out all state storage locations before modifying state:

     ```python
     # Example state mapping for image metadata:
     {
         "vector_store": "Real-time searchable metadata",
         "json_files": "Persistent metadata storage",
         "memory": "In-memory cache/state"
     }
     ```

   - When testing state modifications:
     - Verify ALL storage locations are updated
     - Compare behavior across similar endpoints
     - Check both read and write operations
   - Common state management patterns to verify:
     - Create/Update operations should update ALL relevant storage
     - Delete operations should clean up ALL storage locations
     - Read operations should be consistent across storage types

5. CODE ORGANIZATION:
   - Follow the established module structure
   - Keep routers focused on their specific functionality
   - Use appropriate dependencies from dependencies.py
   - Maintain consistent error handling patterns
   - Add docstrings to all new functions and classes

## Implementation Patterns

1. METADATA MANAGEMENT:
   - ALL metadata updates must:

     ```python
     # 1. Load current state
     metadata = load_or_create_metadata(folder_path)
     
     # 2. Update in-memory state
     metadata[image_path] = new_metadata
     
     # 3. Save to persistent storage
     save_metadata_to_file(metadata_file, metadata)
     
     # 4. Update search indices
     await vector_store.add_or_update_image(image_path, new_metadata)
     ```

   - ALL metadata deletions must:
     - Remove from JSON storage
     - Remove from vector store
     - Clear any cached state

2. ENDPOINT IMPLEMENTATION:
   - Use consistent patterns for similar operations
   - Share common functionality through utility functions
   - Document any deviations from standard patterns
   - Example pattern for metadata modification:

     ```python
     async def modify_metadata_endpoint():
         # 1. Input validation
         validate_input()
         
         # 2. Load current state
         current_metadata = load_current_state()
         
         # 3. Perform modifications
         updated_metadata = modify_metadata()
         
         # 4. Save ALL state changes
         await save_all_state_changes(updated_metadata)
         
         # 5. Return consistent response
         return format_response()
     ```

## Test Design Patterns

1. STATE MODIFICATION TESTS:
   - ALWAYS verify ALL storage locations:

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

2. MOCK CONFIGURATION:
   - Use fixtures that maintain realistic state
   - Mock ALL storage operations
   - Verify mock calls for ALL storage updates
   - Example mock setup:

     ```python
     @pytest.fixture
     def mock_storage_operations():
         mock_state = {}
         return {
             'memory_state': mock_state,
             'file_ops': setup_file_mocks(mock_state),
             'vector_ops': setup_vector_mocks(mock_state),
             'verify_state': lambda: verify_all_storage(mock_state)
         }
     ```

3. VECTOR STORE TESTING:
   - ALWAYS verify both metadata and vector store consistency:

     ```python
     def test_vector_store_operations():
         # 1. Verify metadata synchronization
         await vector_store.sync_with_metadata(folder_path, metadata)
         
         # 2. Verify all entries were added correctly
         for image_path, expected_meta in metadata.items():
             stored_meta = vector_store.get_metadata(image_path)
             assert stored_meta is not None
             assert stored_meta == expected_meta
         
         # 3. Verify search functionality
         results = vector_store.search_images(query)
         assert expected_image in results
         
         # 4. Verify updates propagate correctly
         await vector_store.add_or_update_image(image_path, new_metadata)
         updated_meta = vector_store.get_metadata(image_path)
         assert updated_meta == new_metadata
         
         # 5. Verify deletions are handled
         vector_store.delete_image(image_path)
         assert vector_store.get_metadata(image_path) is None
     ```

   - Common vector store testing pitfalls:
     - Not verifying both metadata and search consistency
     - Not testing deletion scenarios
     - Not checking edge cases (empty metadata, invalid paths)
     - Not verifying search relevance
     - Not testing synchronization with JSON storage

   - Vector store test checklist:
     □ Test initialization and configuration
     □ Test metadata CRUD operations
     □ Test search functionality
     □ Test synchronization with JSON storage
     □ Test error handling
     □ Test edge cases
     □ Test concurrent operations if applicable

   - Best practices:
     1. Use temporary directories for test vector stores
     2. Clean up after tests
     3. Test both individual operations and bulk synchronization
     4. Verify search relevance with carefully chosen test data
     5. Include negative test cases
     6. Test with realistic metadata structures

## Common Pitfalls to Avoid

DO NOT:

1. Modify run.py or core infrastructure without explicit request
2. Make large, sweeping changes across multiple modules
3. Ignore the established project structure
4. Skip adding logging or documentation
5. Try to "optimize" working code prematurely
6. Add new dependencies without clear justification
7. Modify test files without understanding the test suite
8. Interrupt normal startup processes
9. EVER ignore or bypass version requirements - always check requirements.txt first and ensure exact version matches
10. Assume endpoint implementations are consistent without verification
11. Test state changes in isolation without checking all storage locations
12. Fix symptoms (test failures) without comparing against similar functionality

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
