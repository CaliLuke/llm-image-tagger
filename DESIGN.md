# Image Processing Queue Implementation Plan

## Current Issues

1. Stop processing only works between images
2. No way to track progress of individual images
3. No way to resume from where we left off
4. State management is scattered
5. No proper queue management

## Implementation Phases

### Phase 1: Add Queue Infrastructure (No Behavior Changes) ✅

- [x] Create new queue module:

  ```python
  # backend/app/services/processing_queue.py
  class ProcessingQueue:
      def __init__(self):
          self.queue: List[ImageTask] = []
          self.current_task: Optional[ImageTask] = None
          self.is_processing: bool = False
          self.should_stop: bool = False
          self.progress: Dict[str, float] = {}
  ```

- [x] Add queue to router state:

  ```python
  # backend/app/api/routes.py
  router.processing_queue: Optional[ProcessingQueue] = None
  ```

- [x] Add tests for queue infrastructure:

  ```python
  # tests/test_processing_queue.py
  def test_queue_initialization():
      queue = ProcessingQueue()
      assert queue.is_processing == False
      assert queue.should_stop == False
  ```

- [x] Add queue endpoints:

  ```python
  @router.post("/queue/add")
  @router.get("/queue/status")
  @router.post("/queue/start")
  @router.post("/queue/stop")
  @router.post("/queue/clear")
  ```

- [x] Verify implementation:

  ```bash
  # Run unit tests
  python -m pytest tests/test_processing_queue.py -v
  
  # Test endpoints
  python tests/test_queue_endpoints.py
  ```

### Phase 2: Add Queue Processing Logic (Parallel to Existing) ✅

- [x] Implement queue processor that runs in background:

  ```python
  # backend/app/services/queue_processor.py
  class QueueProcessor:
      def __init__(self, queue: ProcessingQueue):
          self.queue = queue
          
      async def process_queue(self, background_tasks: BackgroundTasks):
          """Process all tasks in the queue."""
          background_tasks.add_task(self._process_queue_task)
          
      async def _process_queue_task(self):
          """Background task to process the queue."""
          # Process tasks one by one
  ```

- [x] Add endpoint to process the queue:

  ```python
  @router.post("/queue/process")
  async def process_queue(background_tasks: BackgroundTasks):
      """Process all tasks in the queue."""
      # Start processing in background
  ```

- [x] Add tests for queue processing:

  ```python
  def test_queue_processing():
      # Test processing tasks in the queue
  ```

- [x] Verify implementation:

  ```bash
  # Run unit tests
  python -m pytest tests/test_queue_processor.py -v
  
  # Test processing endpoint
  python tests/test_queue_processing.py
  ```

### Phase 3: Modify Frontend to Support Queue (Optional) ✅

- [x] Add queue status display to UI (hidden by default)
- [x] Add queue controls (hidden by default)
- [x] Keep existing UI working as before
- [x] Verify implementation:

  ```bash
  # Test UI components
  python tests/test_queue_ui.py
  
  # Manual testing in browser
  # - Check queue status display
  # - Test queue controls
  # - Verify existing UI still works
  ```

### Phase 4: Switch Processing to Queue (One at a Time) ✅

- [x] Modify `process_image` to optionally use queue:

  ```python
  @router.post("/process-image")
  async def process_image(request: ProcessImageRequest, use_queue: bool = False):
      if use_queue:
          # Use new queue system
          return await process_image_with_queue(request)
      else:
          # Use existing system
          return await process_image_legacy(request)
  ```

- [x] Add tests for both paths:

  ```python
  def test_process_image_both_paths():
      # Test both queue and legacy paths
  ```

- [x] Verify implementation:

  ```bash
  # Run unit tests
  python -m pytest tests/test_process_image.py -v
  
  # Test both paths
  python tests/test_process_image_paths.py
  ```

### Phase 5: Switch Frontend to Queue (Gradually) ✅

- [x] Add feature flag to frontend:

  ```javascript
  const useQueue = ref(false)  // Default to false
  ```

- [x] Modify `processAllImages` to optionally use queue:

  ```javascript
  const processAllImages = async () => {
      if (useQueue.value) {
          await processAllImagesWithQueue()
      } else {
          await processAllImagesLegacy()
      }
  }
  ```

- [x] Add UI toggle for queue feature (hidden by default)
- [x] Verify implementation:

  ```bash
  # Test frontend with feature flag off
  python tests/test_frontend_legacy.py
  
  # Test frontend with feature flag on
  python tests/test_frontend_queue.py
  
  # Manual testing in browser
  # - Test with feature flag off
  # - Test with feature flag on
  # - Test toggling feature flag
  ```

### Phase 6: Queue Persistence, Recovery, and Progress Tracking ✅

- [x] Add queue persistence to save queue state to disk
- [x] Implement recovery from interrupted tasks
- [x] Add progress tracking during image processing
- [x] Update frontend to show progress

**Testing Results:** All tests pass for queue persistence and progress tracking. The implementation successfully saves queue state to disk, recovers from interrupted tasks, and tracks progress during image processing.

**Verification Date:** 2024-03-19

## Phase 7: Frontend Enhancements (Current Phase)

- [ ] Add batch processing capabilities
- [ ] Implement drag-and-drop for image upload
- [ ] Add image preview in results
- [ ] Improve UI/UX for queue management

### Phase 8: Switch to Queue by Default

- [ ] Set `use_queue = true` by default
- [ ] Keep legacy code as fallback
- [ ] Add monitoring for queue usage
- [ ] Verify implementation:

  ```bash
  # Run all tests
  python -m pytest
  
  # Test default behavior
  python tests/test_default_queue.py
  
  # Test fallback to legacy
  python tests/test_legacy_fallback.py
  ```

### Phase 8: Remove Legacy Code

- [ ] Remove legacy endpoints
- [ ] Remove legacy UI code
- [ ] Clean up tests
- [ ] Verify implementation:

  ```bash
  # Run all tests
  python -m pytest
  
  # Verify no legacy code remains
  python tests/test_no_legacy_code.py
  ```

## Critical Issues and Architectural Principles

### ⚠️ CRITICAL: No Hardcoded Paths
- **NEVER** hardcode paths like `/Volumes/screenshots/Datapad`
- All paths must be:
  1. Configurable via environment variables or config files
  2. Relative to project root or user home directory
  3. Platform-independent (use Path objects)
  4. Validated before use
- Current violations:
  - Frontend sending raw paths directly
  - Backend not normalizing paths
  - Test data using absolute paths

### ⚠️ CRITICAL: Ollama Parallel Request Limitation
- Ollama (mllama) does not support parallel requests
- Current symptoms:
  - Warnings: "mllama doesn't support parallel requests yet"
  - Failed requests after ~27s timeout
  - Connection aborts during long operations
- Impact:
  - Batch processing reliability issues
  - Unpredictable timeouts
  - Resource waste from failed requests

## Phase 7.5: Ollama Request Management (NEW)

### Goals
1. Implement proper request queuing for Ollama
2. Prevent parallel request attempts
3. Improve error handling and timeouts
4. Add request metrics and monitoring

### Implementation Plan

1. Create Ollama Request Manager:
```python
class OllamaRequestManager:
    def __init__(self):
        self._semaphore = asyncio.Semaphore(1)  # Only one request at a time
        self._current_request = None
        self._queue = asyncio.Queue()
        self._metrics = {
            'total_requests': 0,
            'failed_requests': 0,
            'avg_processing_time': 0
        }

    async def submit_request(self, request):
        """Queue a request and wait for result."""
        await self._queue.put(request)
        return await self._process_next()
```

2. Add Request Monitoring:
```python
    async def _track_metrics(self, start_time, success):
        duration = time.time() - start_time
        self._metrics['total_requests'] += 1
        if not success:
            self._metrics['failed_requests'] += 1
        # Update rolling average
        self._metrics['avg_processing_time'] = (
            (self._metrics['avg_processing_time'] * 
             (self._metrics['total_requests'] - 1) + duration) /
            self._metrics['total_requests']
        )
```

### Testing Plan

1. Unit Tests:
```python
async def test_ollama_request_manager():
    manager = OllamaRequestManager()
    
    # Test sequential requests
    results = await asyncio.gather(
        manager.submit_request("req1"),
        manager.submit_request("req2")
    )
    assert len(results) == 2
    
    # Test timeout handling
    with pytest.raises(TimeoutError):
        await manager.submit_request("slow_req", timeout=1.0)
```

2. Integration Tests:
```python
async def test_batch_image_processing():
    # Process 10 images
    # Verify:
    # - No parallel requests
    # - All images processed
    # - Metrics collected
    # - No timeouts
```

3. Stress Tests:
```python
async def test_high_concurrency():
    # Submit 100 requests simultaneously
    # Verify:
    # - All processed eventually
    # - No memory leaks
    # - Consistent performance
```

### Verification Checklist
- [ ] No parallel request warnings in logs
- [ ] All requests processed sequentially
- [ ] Proper timeout handling
- [ ] Metrics collection working
- [ ] No resource leaks
- [ ] Graceful shutdown
- [ ] Documentation updated

### Rollback Plan
1. Keep old implementation in `legacy_processor.py`
2. Feature flag for gradual rollout
3. Monitoring for comparison

## Progress Tracking

- Current Phase: 7
- Status: Starting
- Last Updated: 2024-03-18

## Notes

- Each phase must be tested independently
- No phase should break existing functionality
- Each phase can be rolled back if needed
- Each phase must have its own tests
- Each phase must be verified before moving to the next
- Manual testing should complement automated tests

## Phase 1 Testing Results

- Unit tests: All passing (10/10)
- Endpoint tests: All passing (5/5)
- No regressions in existing functionality

## Phase 2 Testing Results

- Unit tests: All passing (9/9)
- Endpoint tests: All passing
- Queue processing works correctly
- Stop processing works correctly
- No regressions in existing functionality

## Phase 4 Testing Results

- Unit tests: All passing
- Both legacy and queue-based paths work correctly
- Queue integration with process_image endpoint successful
- No regressions in existing functionality

## Phase 5 Testing Results

- Frontend successfully modified to support both legacy and queue-based processing
- Feature flag toggle added to UI
- Queue status display added to UI
- Both processing paths work correctly
- No regressions in existing functionality
- ✅ Verified through manual testing on 2024-03-18

## Phase 6 Testing Results

- Queue persistence implemented with auto-save functionality
- Queue recovery from interrupted tasks implemented
- Progress tracking added to image processing
- Comprehensive tests added for persistence and progress tracking
- No regressions in existing functionality
- ✅ Verified through automated tests on 2024-03-18

## Phase 7.4: Path Handling Standardization (CURRENT)

### Goals
1. Remove all hardcoded paths
2. Implement consistent path handling across the application
3. Add path validation and security checks
4. Support cross-platform path handling

### Implementation Steps

1. Create Path Configuration:
```python
# backend/app/core/config.py
class PathConfig:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent.resolve()
        self.data_dir = self.project_root / "data"
        self.temp_dir = self.data_dir / "temp"
        
    def normalize_path(self, path: Union[str, Path]) -> Path:
        """Convert any path to absolute and validate it"""
        path = Path(path).expanduser().resolve()
        if not path.exists():
            raise ValueError(f"Path does not exist: {path}")
        return path
        
    def is_safe_path(self, path: Path) -> bool:
        """Check if path is safe to access"""
        try:
            path.resolve().relative_to(Path.home())
            return True
        except ValueError:
            return False
```

2. Update Frontend Path Handling:
```javascript
// static/index.js
async function submitPath(path) {
    // Convert to platform-independent format
    const normalizedPath = path.replace(/\\/g, '/');
    // Remove any trailing slashes
    const cleanPath = normalizedPath.replace(/\/+$/, '');
    return await api.post('/images', { folder_path: cleanPath });
}
```

3. Update API Routes:
```python
# backend/app/api/routes.py
@router.post("/images")
async def get_images(request: FolderRequest):
    try:
        path = path_config.normalize_path(request.folder_path)
        if not path_config.is_safe_path(path):
            raise HTTPException(403, "Access to this path is not allowed")
        # ... rest of the function
```

### Testing Plan

1. Unit Tests:
```python
def test_path_normalization():
    config = PathConfig()
    
    # Test relative paths
    assert config.normalize_path("./test") == Path.cwd() / "test"
    
    # Test home directory expansion
    home = str(Path.home())
    assert config.normalize_path("~/test").startswith(home)
    
    # Test path validation
    with pytest.raises(ValueError):
        config.normalize_path("/nonexistent/path")
```

2. Security Tests:
```python
def test_path_security():
    config = PathConfig()
    
    # Test path traversal attempts
    assert not config.is_safe_path(Path("/etc/passwd"))
    assert not config.is_safe_path(Path("../../../etc/passwd"))
    
    # Test allowed paths
    assert config.is_safe_path(Path.home() / "Documents")
```

### Migration Plan
1. Add new path handling without removing old code
2. Update tests to use new path handling
3. Gradually migrate endpoints to use new path handling
4. Remove old path handling code

### Verification Checklist
- [ ] All hardcoded paths removed
- [ ] Path validation working
- [ ] Security checks in place
- [ ] Cross-platform tests passing
- [ ] No regressions in existing functionality

### Rollback Plan
1. Keep old path handling in separate module
2. Feature flag for gradual rollout
3. Easy revert path if issues found
