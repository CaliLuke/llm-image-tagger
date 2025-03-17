from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from fastapi.responses import FileResponse
from pathlib import Path
import os
import json
from typing import List, Dict, Optional, Any

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
from ..utils.helpers import (
    load_or_create_metadata, 
    create_image_info
)
from pydantic import BaseModel

# Create router
router = APIRouter()

# Initialize router state
router.current_folder: Optional[str] = None
router.vector_store: Optional[VectorStore] = None
router.is_processing: bool = False
router.should_stop_processing: bool = False
router.current_task = None  # Store the current background task

def get_vector_store() -> VectorStore:
    """
    Get the current vector store instance.
    
    Returns:
        VectorStore instance
    
    Raises:
        HTTPException: If no folder is selected
    """
    if router.vector_store is None:
        raise HTTPException(status_code=400, detail="No folder selected")
    return router.vector_store

def get_current_folder() -> str:
    """
    Get the current folder path.
    
    Returns:
        Current folder path
    
    Raises:
        HTTPException: If no folder is selected
    """
    if router.current_folder is None:
        raise HTTPException(status_code=400, detail="No folder selected")
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
    
    # Full-text search
    if query:
        query = query.lower()
        for path, meta in metadata.items():
            # Check if query matches any of the text fields
            if (query in meta.get("description", "").lower() or
                query in meta.get("text_content", "").lower() or
                any(query in tag.lower() for tag in meta.get("tags", []))):
                
                results.add(path)
    else:
        # If no query, return all images
        results.update(metadata.keys())
    
    # Vector search
    vector_results = vector_store.search_images(query)
    results.update(vector_results)
    
    # Convert results to list of dicts with metadata
    search_results = []
    for path in results:
        if path in metadata:  # Ensure the path exists in metadata
            search_results.append({
                "name": Path(path).name,
                "path": path,
                **metadata[path]
            })
    
    return search_results

@router.get("/")
async def read_root():
    """Serve the main web interface."""
    return FileResponse("static/index.html")

@router.post("/images", response_model=ImagesResponse)
async def get_images(request: FolderRequest):
    """
    Get images from a folder.
    
    Args:
        request: FolderRequest object
        
    Returns:
        ImagesResponse object
        
    Raises:
        HTTPException: If the folder does not exist or there is an error processing the folder
    """
    folder_path = Path(request.folder_path)
    
    logger.info(f"Received request to open folder: {folder_path}")
    
    if not folder_path.exists() or not folder_path.is_dir():
        logger.error(f"Folder not found: {folder_path}")
        raise HTTPException(status_code=404, detail="Folder not found")
    
    router.current_folder = str(folder_path)
    
    try:
        # Initialize vector store in the selected folder
        vector_store_path = folder_path / ".vectordb"
        router.vector_store = VectorStore(persist_directory=str(vector_store_path))
        
        metadata = load_or_create_metadata(folder_path)
        images = [create_image_info(rel_path, metadata) 
                  for rel_path in metadata.keys()]
        logger.info(f"Successfully processed folder: {folder_path}")
        return {"images": images}
    except Exception as e:
        logger.error(f"Error processing folder {folder_path}: {str(e)}")
        raise HTTPException(status_code=500, 
                            detail=f"Error processing folder: {str(e)}")

@router.get("/image/{path:path}")
async def get_image(path: str):
    """
    Get an image file.
    
    Args:
        path: Path to the image
        
    Returns:
        FileResponse object
        
    Raises:
        HTTPException: If the image does not exist or there is an error retrieving the image
    """
    try:
        folder_path = get_current_folder()
        
        # Combine the base folder path with the relative image path
        full_path = os.path.join(folder_path, path)
        
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="Image not found")
        
        return FileResponse(full_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search", response_model=SearchResponse)
async def search_endpoint(
    request: SearchRequest,
    vector_store: VectorStore = Depends(get_vector_store)
):
    """
    Search images using hybrid search (full-text + vector).
    
    Args:
        request: SearchRequest object
        vector_store: VectorStore instance
        
    Returns:
        SearchResponse object
        
    Raises:
        HTTPException: If there is an error searching for images
    """
    try:
        folder_path = Path(get_current_folder())
        
        # Load current metadata
        metadata_file = folder_path / "image_metadata.json"
        if not metadata_file.exists():
            raise HTTPException(status_code=400, detail="No metadata file found")
            
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        # Use the instance-specific vector store
        matching_images = search_images(request.query, metadata, vector_store)
        
        # Convert to ImageInfo objects
        images = [ImageInfo(
            name=img["name"],
            path=img["path"],
            description=img.get("description", ""),
            tags=img.get("tags", []),
            text_content=img.get("text_content", ""),
            is_processed=img.get("is_processed", False)
        ) for img in matching_images]
        
        return {"images": images}
    except Exception as e:
        logger.error(f"Error searching images: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching images: {str(e)}")

@router.post("/refresh", response_model=ImagesResponse)
async def refresh_images():
    """
    Refresh images in the current folder.
    
    Returns:
        ImagesResponse object
        
    Raises:
        HTTPException: If there is an error refreshing the images
    """
    try:
        folder_path = Path(get_current_folder())
        
        # Reload metadata
        metadata = load_or_create_metadata(folder_path)
        
        # Sync with vector store
        vector_store = get_vector_store()
        vector_store.sync_with_metadata(folder_path, metadata)
        
        # Convert to ImageInfo objects
        images = [create_image_info(rel_path, metadata) 
                  for rel_path in metadata.keys()]
        
        return {"images": images}
    except Exception as e:
        logger.error(f"Error refreshing images: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error refreshing images: {str(e)}")

@router.post("/process-image", response_model=ProcessResponse)
async def process_image(
    request: ProcessImageRequest,
    background_tasks: BackgroundTasks,
    vector_store: VectorStore = Depends(get_vector_store)
):
    """
    Process a single image.
    
    Args:
        request: ProcessImageRequest object
        background_tasks: BackgroundTasks for async processing
        vector_store: VectorStore instance
        
    Returns:
        ProcessResponse object
        
    Raises:
        HTTPException: If there is an error processing the image
    """
    # Check if processing should be stopped before we even start
    logger.info(f"process_image called with should_stop_processing={router.should_stop_processing}")
    if router.should_stop_processing:
        logger.info("Processing already stopped before starting (should_stop_processing=True)")
        return {
            "success": False,
            "message": "Processing stopped by user",
            "image": None
        }
    
    # Set is_processing first to avoid race conditions
    logger.info(f"Setting is_processing to True (was {router.is_processing})")
    router.is_processing = True
    
    try:
        # Get the current folder path and join it with the image name
        folder_path = Path(get_current_folder())
        image_path = folder_path / request.image_path
        
        if not image_path.exists():
            logger.info(f"Image not found: {image_path}")
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Process the image in the background
        async def process_image_task():
            try:
                logger.info(f"Starting background processing task, is_processing={router.is_processing}, should_stop_processing={router.should_stop_processing}")
                
                # Check if we should stop before starting
                if router.should_stop_processing:
                    logger.info("Processing stopped before starting")
                    router.is_processing = False
                    return
                
                processor = ImageProcessor(stop_check=should_stop)
                
                try:
                    metadata = await processor.process_image(image_path)
                except Exception as e:
                    if str(e) == "Processing stopped by user":
                        logger.info("Processing stopped during image processing")
                        router.is_processing = False  # Reset is_processing flag
                        return
                    else:
                        raise
                
                # Check if processing should be stopped after processing
                if router.should_stop_processing:
                    logger.info("Processing stopped after processing image")
                    router.is_processing = False  # Reset is_processing flag
                    return
                    
                # Update metadata file
                update_image_metadata(get_current_folder(), request.image_path, metadata)
                
                # Update vector store
                vector_store.add_or_update_image(request.image_path, metadata)
                logger.info("Background processing completed successfully")
            except Exception as e:
                logger.error(f"Error in background task: {str(e)}")
            finally:
                # Always reset is_processing to False when the task is done
                logger.info(f"Resetting is_processing to False (was {router.is_processing})")
                router.is_processing = False
        
        background_tasks.add_task(process_image_task)
        logger.debug(f"Added background task, returning response with is_processing={router.is_processing}")
        
        # Create initial ImageInfo object
        image_info = create_image_info(request.image_path, {request.image_path: {
            "description": "",
            "tags": [],
            "text_content": "",
            "is_processed": False
        }})
        
        return {
            "success": True,
            "message": "Image processing started",
            "image": image_info
        }
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        logger.debug("Resetting is_processing to False due to error")
        router.is_processing = False  # Reset on error
        return {
            "success": False,
            "message": f"Error processing image: {str(e)}",
            "image": None
        }

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
    """Force reset the processing state to allow new processing."""
    logger.info(f"force_reset_processing_state called with is_processing={router.is_processing}, should_stop_processing={router.should_stop_processing}")
    
    # Force reset both flags to ensure a clean state
    router.should_stop_processing = False
    router.is_processing = False
    
    logger.info(f"Forced reset processing state to is_processing=False, should_stop_processing=False")
    return {"message": "Processing state force reset"}

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
    try:
        folder_path = Path(get_current_folder())
        
        # Load current metadata
        metadata_file = folder_path / "image_metadata.json"
        if not metadata_file.exists():
            raise HTTPException(status_code=400, detail="No metadata file found")
            
        with open(metadata_file, 'r') as f:
            all_metadata = json.load(f)
        
        # Check if image exists in metadata
        if request.path not in all_metadata:
            raise HTTPException(status_code=404, detail="Image not found in metadata")
        
        # Update metadata
        if request.description is not None:
            all_metadata[request.path]["description"] = request.description
        if request.tags is not None:
            all_metadata[request.path]["tags"] = request.tags
        if request.text_content is not None:
            all_metadata[request.path]["text_content"] = request.text_content
        
        # Mark as processed
        all_metadata[request.path]["is_processed"] = True
        
        # Save updated metadata
        with open(metadata_file, 'w') as f:
            json.dump(all_metadata, f, indent=4)
        
        # Update vector store
        vector_store.add_or_update_image(request.path, all_metadata[request.path])
        
        # Create ImageInfo object
        image_info = create_image_info(request.path, all_metadata)
        
        return {
            "success": True,
            "message": "Metadata updated successfully",
            "image": image_info
        }
    except Exception as e:
        logger.error(f"Error updating metadata: {str(e)}")
        return {
            "success": False,
            "message": f"Error updating metadata: {str(e)}",
            "image": None
        }

class LogActionRequest(BaseModel):
    """Request model for logging user actions."""
    action: str
    button: str
    tag: Optional[str] = None
    image: Optional[str] = None

@router.post("/log-action")
async def log_action(request: LogActionRequest):
    """Log user actions for debugging."""
    logger.info(f"USER ACTION: {request.action} - Button: {request.button}")
    if request.tag:
        logger.info(f"  Tag: {request.tag}")
    if request.image:
        logger.info(f"  Image: {request.image}")
    return {"success": True}

# Function to check if processing should stop
def should_stop():
    """Check if processing should stop."""
    return router.should_stop_processing
