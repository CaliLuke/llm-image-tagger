from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pathlib import Path
import os
import json
from typing import List, Dict, Optional, Any, Union
import traceback
from PIL import Image
import hashlib
import asyncio
import random

from ..core.logging import logger
from ..models.schemas import (
    FolderRequest, 
    ImageInfo, 
    SearchRequest, 
    ProcessImageRequest, 
    UpdateImageMetadata,
    ImagesResponse,
    SearchResponse,
    ProcessResponse
)
from ..services.image_processor import ImageProcessor, update_image_metadata
from ..services.vector_store import VectorStore
from ..services.processing_queue import ProcessingQueue
from ..services.queue_processor import QueueProcessor
from ..services.queue_persistence import QueuePersistence
from ..services.storage import file_storage
from ..utils.helpers import (
    load_or_create_metadata, 
    create_image_info
)
from pydantic import BaseModel, ConfigDict
from ..config import settings

# Create router
router = APIRouter()

# Initialize router state
router.current_folder: Optional[str] = None
router.vector_store: Optional[VectorStore] = None
router.is_processing: bool = False
router.should_stop_processing: bool = False
router.current_task = None  # Store the current background task
router.processing_queue: Optional[ProcessingQueue] = None
router.queue_persistence: Optional[QueuePersistence] = None

# Get the project root directory (3 levels up from routes.py)
project_root = Path(__file__).parent.parent.parent.parent
data_dir = project_root / "data"

def get_vector_store() -> VectorStore:
    """Get or create a VectorStore instance."""
    try:
        if not router.vector_store:
            # Initialize vector store in the data directory
            vector_store_path = data_dir / "vectordb"
            if not vector_store_path.exists():
                vector_store_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created vector store directory at {vector_store_path}")
            
            # Create a new vector store
            logger.info("Initializing vector store...")
            router.vector_store = VectorStore(persist_directory=str(vector_store_path))
            
            # Verify initialization
            if not router.vector_store:
                raise RuntimeError("Vector store initialization failed")
            
            # Test the collection with a simple operation
            test_id = "__test_init__"
            try:
                router.vector_store.collection.add(
                    ids=[test_id],
                    documents=["test document"],
                    metadatas=[{"test": "true"}]
                )
                router.vector_store.collection.delete(ids=[test_id])
                logger.info("Successfully verified vector store initialization")
            except Exception as e:
                logger.error(f"Vector store verification failed: {str(e)}")
                router.vector_store = None
                raise RuntimeError(f"Vector store verification failed: {str(e)}")
            
        return router.vector_store
    except Exception as e:
        logger.error(f"Error in get_vector_store: {str(e)}")
        router.vector_store = None
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize vector store: {str(e)}"
        )

def get_image_processor() -> ImageProcessor:
    """Get or create an ImageProcessor instance."""
    if not hasattr(router, "image_processor"):
        router.image_processor = ImageProcessor()
    return router.image_processor

def get_current_folder() -> str:
    """Get the current folder path."""
    if not hasattr(router, "current_folder"):
        router.current_folder = None
    return router.current_folder

def search_images(query: str, metadata: Dict[str, Dict], vector_store: VectorStore) -> List[Dict]:
    """
    Hybrid search combining full-text and vector search.
    
    Args:
        query: Search query
        metadata: Metadata to search
        vector_store: VectorStore instance
        
    Returns:
        List of matching images with their metadata
    """
    results = set()
    logger.debug(f"Starting search with query: '{query}'")
    logger.debug(f"Total images in metadata: {len(metadata)}")
    
    # Full-text search
    if query:
        query = query.lower()
        logger.debug("Performing full-text search")
        for path, meta in metadata.items():
            logger.debug(f"Checking {path}:")
            logger.debug(f"  Description: {meta.get('description', '')}")
            logger.debug(f"  Tags: {meta.get('tags', [])}")
            logger.debug(f"  Text content: {meta.get('text_content', '')}")
            
            # Check if query matches any of the text fields
            if (query in meta.get("description", "").lower() or
                query in meta.get("text_content", "").lower() or
                any(query in tag.lower() for tag in meta.get("tags", []))):
                
                results.add(path)
                logger.debug(f"  MATCH: Added {path} from full-text search")
            else:
                logger.debug("  NO MATCH")
    else:
        # If no query, return all images
        logger.debug("No query provided, adding all images")
        results.update(metadata.keys())
    
    logger.debug(f"Full-text search results: {results}")
    
    # Vector search
    logger.debug("Performing vector search")
    vector_results = vector_store.search_images(query)
    logger.debug(f"Vector search returned: {vector_results}")
    results.update(vector_results)
    
    # Convert results to list of dicts with metadata
    search_results = []
    logger.debug(f"Final combined results before metadata: {results}")
    for path in results:
        if path in metadata:  # Ensure the path exists in metadata
            search_results.append({
                "name": Path(path).name,
                "path": path,
                **metadata[path]
            })
            logger.debug(f"Added {path} to final results with metadata")
        else:
            logger.debug(f"Skipped {path} - not found in metadata")
    
    logger.debug(f"Final search results count: {len(search_results)}")
    return search_results

@router.get("/")
async def read_root():
    """Serve the main web interface."""
    return FileResponse("static/index.html")

@router.post("/images", response_model=ImagesResponse)
async def open_folder(folder: FolderRequest):
    """
    Open a folder and load its images.
    
    This endpoint:
    1. Validates the provided folder path
    2. Sets the current folder in application state
    3. Initializes the vector store
    4. Loads or creates metadata from the folder
    5. Synchronizes the vector store with the metadata (async)
    6. Creates ImageInfo objects for all images
    
    Args:
        folder: Folder request with path
        
    Returns:
        ImagesResponse with list of images
        
    Raises:
        HTTPException: If folder not found or other errors occur
    """
    try:
        folder_path = Path(folder.folder_path)
        if not folder_path.exists():
            logger.error(f"Folder not found: {folder_path}")
            raise HTTPException(status_code=404, detail="Folder not found")
        
        logger.info(f"API: Received request to open folder: {folder_path}")
        router.current_folder = str(folder_path.resolve())
        logger.info(f"STATE: Current folder set to: {router.current_folder}")
        
        # Initialize vector store
        logger.info(f"VECTOR_STORE: Initializing for folder: {folder_path}")
        vector_store = get_vector_store()
        
        # Load metadata from folder
        logger.info(f"METADATA: Loading from folder: {folder_path}")
        metadata = await load_or_create_metadata(folder_path)
        logger.info(f"METADATA: Loaded {len(metadata)} entries from {folder_path}")
        
        # Log the processed images count
        processed_count = sum(1 for img_data in metadata.values() if img_data.get('is_processed', False))
        logger.info(f"METADATA: Found {processed_count}/{len(metadata)} processed images")
        
        # Sync the vector store with the metadata (async operation)
        logger.info(f"VECTOR_STORE: Synchronizing with metadata ({len(metadata)} entries)")
        await vector_store.sync_with_metadata(folder_path, metadata)
        logger.info(f"VECTOR_STORE: Synchronization complete for folder: {folder_path}")
        
        # Convert metadata to image info objects
        logger.info("PROCESSING: Creating ImageInfo objects")
        images = [create_image_info(rel_path, metadata) for rel_path in metadata.keys()]
        
        # Log the processed image count in the response
        processed_images = sum(1 for img in images if img.is_processed)
        logger.info(f"API: Returning {len(images)} images ({processed_images} processed) to client")
        
        # Verify consistency between metadata and ImageInfo objects 
        if processed_count != processed_images:
            logger.warning(f"CONSISTENCY: Mismatch between processed count in metadata ({processed_count}) and ImageInfo objects ({processed_images})")
        
        return {"images": images}
    except Exception as e:
        logger.error(f"ERROR: Failed to open folder: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/image/{path:path}")
async def get_image(path: str):
    """
    Serve an image file.
    
    Args:
        path: Path to the image file
        
    Returns:
        FileResponse containing the image
    """
    try:
        logger.info(f"Received request for image: {path}")
        
        # Get the current folder path
        current_folder = getattr(router, 'current_folder', None)
        if not current_folder:
            logger.error("No current folder set")
            raise HTTPException(status_code=400, detail="No folder selected")
            
        logger.info(f"Current folder: {current_folder}")
        
        # Construct full path
        full_path = Path(current_folder) / path
        logger.info(f"Full image path: {full_path}")
        
        # Check if file exists
        if not full_path.exists():
            logger.error(f"Image file not found: {full_path}")
            raise HTTPException(status_code=404, detail="Image not found")
            
        # Check file permissions
        try:
            logger.info(f"Checking file permissions for: {full_path}")
            logger.info(f"File is readable: {os.access(full_path, os.R_OK)}")
            logger.info(f"File is executable: {os.access(full_path, os.X_OK)}")
            logger.info(f"File stats: {os.stat(full_path)}")
            logger.info(f"File size: {os.path.getsize(full_path)} bytes")
        except Exception as e:
            logger.error(f"Error checking file permissions: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error checking file permissions: {str(e)}")
            
        # Check if it's a file (not a directory)
        if not full_path.is_file():
            logger.error(f"Path is not a file: {full_path}")
            raise HTTPException(status_code=400, detail="Path is not a file")
            
        # Check file extension
        if full_path.suffix.lower() not in settings.SUPPORTED_EXTENSIONS:
            logger.error(f"Unsupported file extension: {full_path.suffix}")
            raise HTTPException(status_code=400, detail="Unsupported file type")
            
        # Validate image format using PIL
        try:
            with Image.open(full_path) as img:
                # Log image format and mode
                logger.info(f"Image format: {img.format}")
                logger.info(f"Image mode: {img.mode}")
                logger.info(f"Image size: {img.size}")
                # Try to verify the image
                img.verify()
                # Reset the file pointer after verify
                img.seek(0)
        except Exception as e:
            logger.error(f"Invalid image format: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid image format")
            
        logger.info(f"Serving image file: {full_path}")
        response = FileResponse(full_path)
        logger.info(f"Response headers: {response.headers}")
        return response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving image {path}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search", response_model=SearchResponse)
async def search_endpoint(
    request: SearchRequest,
    vector_store: VectorStore = Depends(get_vector_store)
):
    """
    Search for images using metadata and vector search.
    
    Args:
        request: SearchRequest object
        vector_store: VectorStore instance
        
    Returns:
        SearchResponse object
        
    Raises:
        HTTPException: If search fails
    """
    try:
        # Get current folder
        current_folder = get_current_folder()
        if current_folder is None:
            raise HTTPException(status_code=400, detail="No folder selected")
            
        folder_path = Path(current_folder)
        if not folder_path.exists():
            raise HTTPException(status_code=400, detail="Selected folder no longer exists")
        
        # Load current metadata
        metadata = await load_or_create_metadata(folder_path)
        
        # Use the instance-specific vector store
        matching_images = search_images(request.query, metadata, vector_store)
        
        return SearchResponse(images=matching_images)
    
    except HTTPException:
        # Re-raise HTTP exceptions without wrapping
        raise    
    except Exception as e:
        logger.error(f"Error searching images: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        logger.error(f"Exception traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refresh", response_model=ImagesResponse)
async def refresh_images():
    """
    Refresh images in the current folder.
    
    This endpoint:
    1. Gets the current folder from application state
    2. Reloads metadata from the folder
    3. Synchronizes the vector store with the metadata (async)
    4. Creates ImageInfo objects for all images
    
    Returns:
        ImagesResponse with updated list of images
        
    Raises:
        HTTPException: If there is an error refreshing the images
    """
    try:
        folder_path = Path(get_current_folder())
        logger.info(f"API: Refreshing images in folder: {folder_path}")
        
        # Reload metadata
        logger.info(f"METADATA: Reloading from folder: {folder_path}")
        metadata = await load_or_create_metadata(folder_path)
        logger.info(f"METADATA: Reloaded {len(metadata)} entries from {folder_path}")
        
        # Log the processed images count
        processed_count = sum(1 for img_data in metadata.values() if img_data.get('is_processed', False))
        logger.info(f"METADATA: Found {processed_count}/{len(metadata)} processed images")
        
        # Sync with vector store (async operation)
        logger.info(f"VECTOR_STORE: Synchronizing with metadata ({len(metadata)} entries)")
        vector_store = get_vector_store()
        await vector_store.sync_with_metadata(folder_path, metadata)
        logger.info(f"VECTOR_STORE: Synchronization complete for folder: {folder_path}")
        
        # Convert to ImageInfo objects
        logger.info("PROCESSING: Creating ImageInfo objects")
        images = [create_image_info(rel_path, metadata) 
                  for rel_path in metadata.keys()]
        
        # Log the processed image count in the response
        processed_images = sum(1 for img in images if img.is_processed)
        logger.info(f"API: Returning {len(images)} images ({processed_images} processed) to client")
        
        # Verify consistency between metadata and ImageInfo objects
        if processed_count != processed_images:
            logger.warning(f"CONSISTENCY: Mismatch between processed count in metadata ({processed_count}) and ImageInfo objects ({processed_images})")
        
        return {"images": images}
    except Exception as e:
        logger.error(f"ERROR: Failed to refresh images: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error refreshing images: {str(e)}")

@router.post("/process-image", response_model=None)
async def process_image(
    request: Request,
    image_processor: ImageProcessor = Depends(get_image_processor),
    vector_store: VectorStore = Depends(get_vector_store),
    use_queue: bool = False
) -> Union[StreamingResponse, JSONResponse]:
    """Process a single image and return its metadata."""
    try:
        # Parse request body
        body = await request.json()
        image_path = body.get("image_path")
        if not image_path:
            return JSONResponse(
                status_code=200,
                content={"success": False, "message": "image_path is required"}
            )
        
        # Convert to Path object and resolve relative to current folder
        image_path = Path(get_current_folder()) / Path(image_path)
        
        # Ensure image exists
        if not image_path.exists():
            logger.error(f"Image not found: {image_path}")
            return JSONResponse(
                status_code=200,
                content={"success": False, "message": f"Image not found: {image_path}"}
            )
        
        async def process_and_stream():
            try:
                # Initialize progress
                yield json.dumps({"success": True, "progress": 0}) + "\n"
                
                # Process the image
                async for update in image_processor.process_image(image_path):
                    update["success"] = True
                    
                    # If this is the final update with metadata, update storage
                    if "image" in update:
                        # Get the relative path for the image
                        rel_path = str(image_path.relative_to(Path(get_current_folder())))
                        
                        # Load current metadata
                        metadata = await load_or_create_metadata(Path(get_current_folder()))
                        
                        # Update metadata for this image
                        metadata[rel_path] = update["image"]
                        
                        # Save updated metadata to image folder
                        metadata_file = Path(get_current_folder()) / "image_metadata.json"
                        await file_storage.write(metadata_file, metadata)
                        
                        # Update vector store
                        await vector_store.add_or_update_image(rel_path, update["image"])
                    
                    yield json.dumps(update) + "\n"
            
            except HTTPException:
                # Re-raise HTTP exceptions without wrapping
                raise
            except Exception as e:
                logger.error(f"Error processing image: {str(e)}")
                logger.error(f"Error type: {type(e)}")
                logger.error(f"Full traceback: {traceback.format_exc()}")
                yield json.dumps({"success": False, "message": str(e)}) + "\n"
        
        return StreamingResponse(
            process_and_stream(),
            media_type="application/x-ndjson"
        )
        
    except Exception as e:
        logger.error(f"Error in process_image endpoint: {str(e)}")
        return JSONResponse(
            status_code=200,
            content={"success": False, "message": str(e)}
        )

@router.post("/stop-processing")
async def stop_processing():
    """Stop the current image processing operation."""
    logger.info(f"stop_processing called with is_processing={router.is_processing}, should_stop_processing={router.should_stop_processing}")
    
    # Always set should_stop_processing to True, even if is_processing is False
    # This ensures that any subsequent processing attempts will be stopped
    old_should_stop_processing = router.should_stop_processing
    router.should_stop_processing = True
    logger.info(f"Set should_stop_processing from {old_should_stop_processing} to True")
    
    # We don't reset is_processing here, it will be reset by the background task
    # when it checks should_stop_processing and stops
    
    if not router.is_processing:
        logger.info("No processing was in progress, but should_stop_processing is now True")
        return {"message": "No processing operation in progress"}
    
    logger.info("Processing was in progress, will be stopped")
    return {"message": "Processing will be stopped"}

@router.post("/reset-processing-state")
async def reset_processing_state():
    """Reset the processing state."""
    logger.info(f"reset_processing_state called with is_processing={router.is_processing}, should_stop_processing={router.should_stop_processing}")
    
    # Always reset both flags to ensure a clean state
    old_is_processing = router.is_processing
    old_should_stop_processing = router.should_stop_processing
    
    router.should_stop_processing = False  # Reset to false to allow new processing
    router.is_processing = False  # Then set is_processing to false
    
    logger.info(f"Reset processing state from is_processing={old_is_processing}, should_stop_processing={old_should_stop_processing} to is_processing=False, should_stop_processing=False")
    return {"message": "Processing state reset"}

@router.post("/force-reset-processing-state")
async def force_reset_processing_state():
    """Force reset the processing state."""
    logger.info(f"force_reset_processing_state called with is_processing={router.is_processing}, should_stop_processing={router.should_stop_processing}")
    
    old_is_processing = router.is_processing
    old_should_stop_processing = router.should_stop_processing
    
    router.is_processing = False
    router.should_stop_processing = False
    
    logger.info(f"Forced reset processing state to is_processing=False, should_stop_processing=False")
    
    return {
        "old_is_processing": old_is_processing,
        "old_should_stop_processing": old_should_stop_processing,
        "is_processing": router.is_processing,
        "should_stop_processing": router.should_stop_processing
    }

@router.get("/check-init-status")
async def check_init_status(request: Request):
    """Check if this is the first time initialization."""
    try:
        # First check if current_folder exists
        logger.debug(f"Checking if current_folder exists: {router.current_folder is not None}")
        if router.current_folder is None:
            logger.debug("current_folder is None, returning False")
            return {"initialized": False, "message": "No folder selected"}
        
        # Check if the folder exists and is valid
        folder_path = Path(router.current_folder)
        logger.debug(f"Checking if folder exists: {folder_path}")
        if not folder_path.exists() or not folder_path.is_dir():
            logger.debug("Folder does not exist or is not a directory")
            return {"initialized": False, "message": "Selected folder does not exist or is not a directory"}
        
        # Check if vector store exists and is initialized
        vector_store_path = folder_path / ".vectordb"
        logger.debug(f"Checking vector store path: {vector_store_path}")
        if not vector_store_path.exists() or not vector_store_path.is_dir():
            logger.debug("Vector store path does not exist or is not a directory")
            return {"initialized": False, "message": "Vector database not initialized"}
        
        # Check if vector_store instance exists
        logger.debug(f"Checking if vector_store exists: {router.vector_store is not None}")
        if router.vector_store is None:
            logger.debug("vector_store does not exist")
            return {"initialized": False, "message": "Vector store not initialized"}
        
        # Only return True if we have both a valid folder and initialized vector store
        logger.debug("All checks passed, returning True")
        return {"initialized": True, "message": "Vector database initialized"}
    except Exception as e:
        logger.error(f"Error checking init status: {str(e)}")
        return {"initialized": False, "message": f"Error: {str(e)}"}

@router.post("/update-metadata", response_model=ProcessResponse)
async def update_metadata(
    request: UpdateImageMetadata,
    vector_store: VectorStore = Depends(get_vector_store)
):
    """
    Update metadata for a specific image.
    
    Args:
        request: UpdateImageMetadata object
        vector_store: VectorStore instance
        
    Returns:
        ProcessResponse object
        
    Raises:
        HTTPException: If there is an error updating the metadata
    """
    logger.info(f"Received metadata update request for image: {request.path}")
    logger.info(f"Update data: description={request.description}, tags={request.tags}, text_content={request.text_content}")
    
    try:
        folder_path = Path(get_current_folder())
        logger.info(f"Current folder path: {folder_path}")
        
        # Load current metadata from image folder
        metadata = await load_or_create_metadata(folder_path)
        logger.info(f"Loaded metadata with {len(metadata)} entries")
        
        # Check if image exists in metadata
        if request.path not in metadata:
            logger.error(f"Image not found in metadata: {request.path}")
            logger.error(f"Available paths: {list(metadata.keys())}")
            raise HTTPException(status_code=404, detail="Image not found in metadata")
        
        logger.info("Updating metadata fields")
        # Update metadata
        if request.description is not None:
            metadata[request.path]["description"] = request.description
            logger.info(f"Updated description: {request.description}")
        if request.tags is not None:
            metadata[request.path]["tags"] = request.tags
            logger.info(f"Updated tags: {request.tags}")
        if request.text_content is not None:
            metadata[request.path]["text_content"] = request.text_content
            logger.info(f"Updated text content: {request.text_content}")
        
        # Mark as processed
        metadata[request.path]["is_processed"] = True
        logger.info("Marked image as processed")
        
        # Save updated metadata to image folder
        metadata_file = folder_path / "image_metadata.json"
        await file_storage.write(metadata_file, metadata)
        logger.info("Successfully saved metadata to file")
        
        # Update vector store
        logger.info("Updating vector store")
        await vector_store.add_or_update_image(request.path, metadata[request.path])
        logger.info("Successfully updated vector store")
        
        # Create ImageInfo object
        logger.info("Creating ImageInfo object")
        image_info = create_image_info(request.path, metadata)
        logger.info("Successfully created ImageInfo object")
        
        return {
            "success": True,
            "message": "Metadata updated successfully",
            "image": image_info
        }
    except HTTPException as e:
        # Re-raise HTTP exceptions
        logger.error(f"HTTP Exception in update_metadata: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error updating metadata: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        logger.error(f"Exception traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

class LogActionRequest(BaseModel):
    """Request model for logging user actions."""
    action: str
    message: Optional[str] = None
    button: Optional[str] = None
    tag: Optional[str] = None
    image: Optional[str] = None
    error: Optional[dict] = None
    model_config = ConfigDict(extra="allow")  # Allow additional fields for flexibility

@router.post("/log-action")
async def log_action(request: LogActionRequest):
    """Log user actions and events from the frontend."""
    if request.action == "ERROR":
        if request.error:
            logger.error(f"FRONTEND ERROR: {request.message}")
            logger.error(f"Error details: {request.error}")
        else:
            logger.error(f"FRONTEND ERROR: {request.message}")
    elif request.action == "PROCESSING":
        logger.info(f"FRONTEND PROCESSING: {request.message}")
    elif request.action == "METADATA":
        logger.info(f"FRONTEND METADATA: {request.message}")
    elif request.action == "BUTTON_CLICK":
        log_msg = f"FRONTEND BUTTON CLICK: {request.button}"
        if request.tag:
            log_msg += f" - Tag: {request.tag}"
        logger.info(log_msg)
    else:
        # Log any other actions
        log_msg = f"FRONTEND {request.action}"
        if request.message:
            log_msg += f": {request.message}"
        if request.button:
            log_msg += f" - Button: {request.button}"
        if request.tag:
            log_msg += f" - Tag: {request.tag}"
        if request.image:
            log_msg += f" - Image: {request.image}"
        logger.info(log_msg)
    
    return {"success": True}

# Function to check if processing should stop
def should_stop():
    """Check if processing should stop."""
    return router.should_stop_processing

# Queue endpoints
@router.post("/queue/add")
async def add_to_queue(request: ProcessImageRequest):
    """
    Add an image to the processing queue.
    
    Args:
        request: ProcessImageRequest object
        
    Returns:
        Dictionary with task information
        
    Raises:
        HTTPException: If no folder is selected or the queue is not initialized
    """
    if not router.current_folder:
        raise HTTPException(status_code=400, detail="No folder selected")
    
    if not router.processing_queue:
        raise HTTPException(status_code=400, detail="Queue not initialized")
    
    logger.info(f"Adding image to queue: {request.image_path}")
    
    task = router.processing_queue.add_task(request.image_path)
    
    return {
        "success": True,
        "message": "Image added to queue",
        "task": task.to_dict()
    }

@router.get("/queue/status")
async def get_queue_status(detailed: bool = False):
    """
    Get the status of the processing queue.
    
    Args:
        detailed: Whether to include detailed information about the queue
        
    Returns:
        Dictionary with queue status
        
    Raises:
        HTTPException: If no folder is selected or the queue is not initialized
    """
    if not router.current_folder:
        raise HTTPException(status_code=400, detail="No folder selected")
    
    if not router.processing_queue:
        raise HTTPException(status_code=400, detail="Queue not initialized")
    
    logger.info("Getting queue status")
    
    if detailed:
        return router.processing_queue.get_detailed_status()
    else:
        return router.processing_queue.get_status()

@router.post("/queue/start")
async def start_queue():
    """
    Start processing the queue.
    
    Returns:
        Dictionary with success status
        
    Raises:
        HTTPException: If no folder is selected or the queue is not initialized
    """
    if not router.current_folder:
        raise HTTPException(status_code=400, detail="No folder selected")
    
    if not router.processing_queue:
        raise HTTPException(status_code=400, detail="Queue not initialized")
    
    logger.info("Starting queue processing")
    
    router.processing_queue.start_processing()
    
    return {
        "success": True,
        "message": "Queue processing started"
    }

@router.post("/queue/stop")
async def stop_queue():
    """
    Stop processing the queue.
    
    Returns:
        Dictionary with success status
        
    Raises:
        HTTPException: If no folder is selected or the queue is not initialized
    """
    if not router.current_folder:
        raise HTTPException(status_code=400, detail="No folder selected")
    
    if not router.processing_queue:
        raise HTTPException(status_code=400, detail="Queue not initialized")
    
    logger.info("Stopping queue processing")
    
    router.processing_queue.stop_processing()
    
    return {
        "success": True,
        "message": "Queue processing stopped"
    }

@router.post("/queue/clear")
async def clear_queue():
    """
    Clear the queue.
    
    Returns:
        Dictionary with success status
        
    Raises:
        HTTPException: If no folder is selected or the queue is not initialized
    """
    if not router.current_folder:
        raise HTTPException(status_code=400, detail="No folder selected")
    
    if not router.processing_queue:
        raise HTTPException(status_code=400, detail="Queue not initialized")
    
    logger.info("Clearing queue")
    
    router.processing_queue.clear_queue()
    
    return {
        "success": True,
        "message": "Queue cleared"
    }

@router.post("/queue/process")
async def process_queue(background_tasks: BackgroundTasks):
    """
    Process all tasks in the queue.
    
    Args:
        background_tasks: FastAPI background tasks
        
    Returns:
        Dictionary with success status
        
    Raises:
        HTTPException: If no folder is selected or the queue is not initialized
    """
    if not router.current_folder:
        raise HTTPException(status_code=400, detail="No folder selected")
    
    if not router.processing_queue:
        raise HTTPException(status_code=400, detail="Queue not initialized")
    
    logger.info("Processing queue")
    
    processor = QueueProcessor(router.processing_queue)
    result = await processor.process_queue(background_tasks)
    
    return result

@router.post("/test-process-batch")
async def test_process_batch(
    sample_size: int = 5,
    vector_store: VectorStore = Depends(get_vector_store)
) -> Dict:
    """
    Test endpoint to automatically process a batch of images.
    
    Args:
        sample_size: Number of images to process (default: 5)
        vector_store: VectorStore instance
        
    Returns:
        Dict containing test results
    """
    try:
        if not router.current_folder:
            raise HTTPException(status_code=400, detail="No folder selected")
            
        folder_path = Path(get_current_folder())
        logger.info(f"Starting batch processing test in folder: {folder_path}")
        
        # Get list of all images
        image_files = []
        for ext in settings.SUPPORTED_EXTENSIONS:
            image_files.extend(folder_path.glob(f"*{ext}"))
            image_files.extend(folder_path.glob(f"*{ext.upper()}"))
        
        if not image_files:
            raise HTTPException(status_code=404, detail="No images found in folder")
            
        # Take a random sample
        test_images = random.sample(image_files, min(sample_size, len(image_files)))
        logger.info(f"Selected {len(test_images)} images for testing")
        
        results = {
            "total_images": len(test_images),
            "successful": 0,
            "failed": 0,
            "errors": [],
            "processed": []
        }
        
        # Process each image
        image_processor = get_image_processor()
        for img_path in test_images:
            try:
                logger.info(f"Processing test image: {img_path}")
                rel_path = img_path.relative_to(folder_path)
                
                # Process the image
                async for update in image_processor.process_image(img_path):
                    if "image" in update:
                        # Update metadata and vector store
                        metadata = await load_or_create_metadata(folder_path)
                        metadata[str(rel_path)] = update["image"]
                        
                        # Save metadata to image folder
                        metadata_file = folder_path / "image_metadata.json"
                        await file_storage.write(metadata_file, metadata)
                            
                        # Update vector store
                        await vector_store.add_or_update_image(str(rel_path), update["image"])
                        
                        results["successful"] += 1
                        results["processed"].append({
                            "path": str(rel_path),
                            "metadata": update["image"]
                        })
                        logger.info(f"Successfully processed: {rel_path}")
                        
            except Exception as e:
                results["failed"] += 1
                error_info = {
                    "path": str(rel_path),
                    "error": str(e),
                    "type": type(e).__name__
                }
                results["errors"].append(error_info)
                logger.error(f"Error processing {rel_path}: {str(e)}")
                logger.error(traceback.format_exc())
                
        logger.info(f"Batch processing complete. Success: {results['successful']}, Failed: {results['failed']}")
        return results
        
    except Exception as e:
        logger.error(f"Error in batch processing test: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
