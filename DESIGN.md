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

### Phase 3: Modify Frontend to Support Queue (Optional) 🔄
- [ ] Add queue status display to UI (hidden by default)
- [ ] Add queue controls (hidden by default)
- [ ] Keep existing UI working as before
- [ ] Verify implementation:
  ```bash
  # Test UI components
  python tests/test_queue_ui.py
  
  # Manual testing in browser
  # - Check queue status display
  # - Test queue controls
  # - Verify existing UI still works
  ```

### Phase 4: Switch Processing to Queue (One at a Time)
- [ ] Modify `process_image` to optionally use queue:
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
- [ ] Add tests for both paths:
  ```python
  def test_process_image_both_paths():
      # Test both queue and legacy paths
  ```
- [ ] Verify implementation:
  ```bash
  # Run unit tests
  python -m pytest tests/test_process_image.py -v
  
  # Test both paths
  python tests/test_process_image_paths.py
  ```

### Phase 5: Switch Frontend to Queue (Gradually)
- [ ] Add feature flag to frontend:
  ```javascript
  const useQueue = ref(false)  // Default to false
  ```
- [ ] Modify `processAllImages` to optionally use queue:
  ```javascript
  const processAllImages = async () => {
      if (useQueue.value) {
          await processAllImagesWithQueue()
      } else {
          await processAllImagesLegacy()
      }
  }
  ```
- [ ] Add UI toggle for queue feature (hidden by default)
- [ ] Verify implementation:
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

### Phase 6: Complete Queue Implementation
- [ ] Add queue persistence
- [ ] Add queue recovery
- [ ] Add queue progress tracking
- [ ] Add comprehensive tests
- [ ] Verify implementation:
  ```bash
  # Run all tests
  python -m pytest
  
  # Test persistence
  python tests/test_queue_persistence.py
  
  # Test recovery
  python tests/test_queue_recovery.py
  
  # Test progress tracking
  python tests/test_queue_progress.py
  ```

### Phase 7: Switch to Queue by Default
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

## Progress Tracking
- Current Phase: 3
- Status: Starting
- Last Updated: 2024-03-17

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
