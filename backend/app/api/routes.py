from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pathlib import Path
import os
import json
from typing import List, Dict, Optional

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

# Create router
router = APIRouter()

# Global state
current_folder: Optional[str] = None
vector_store: Optional[VectorStore] = None

def get_vector_store() -> VectorStore:
    """
    Get the current vector store instance.
    
    Returns:
        VectorStore instance
    
    Raises:
        HTTPException: If no folder is selected
    """
    if vector_store is None:
        raise HTTPException(status_code=400, detail="No folder selected")
    return vector_store

def get_current_folder() -> str:
    """
    Get the current folder path.
    
    Returns:
        Current folder path
    
    Raises:
        HTTPException: If no folder is selected
    """
    if current_folder is None:
        raise HTTPException(status_code=400, detail="No folder selected")
    return current_folder

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
    global current_folder, vector_store
    
    folder_path = Path(request.folder_path)
    
    logger.info(f"Received request to open folder: {folder_path}")
    
    if not folder_path.exists() or not folder_path.is_dir():
        logger.error(f"Folder not found: {folder_path}")
        raise HTTPException(status_code=404, detail="Folder not found")
    
    current_folder = str(folder_path)
    
    try:
        # Initialize vector store in the selected folder
        vector_store_path = folder_path / ".vectordb"
        vector_store = VectorStore(persist_directory=str(vector_store_path))
        
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
    vector_store: VectorStore = Depends(get_vector_store)
):
    """
    Process a single image.
    
    Args:
        request: ProcessImageRequest object
        vector_store: VectorStore instance
        
    Returns:
        ProcessResponse object
        
    Raises:
        HTTPException: If there is an error processing the image
    """
    try:
        folder_path = Path(get_current_folder())
        image_path = folder_path / request.image_path
        
        if not image_path.exists():
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Process the image
        processor = ImageProcessor()
        metadata = await processor.process_image(image_path)
        
        # Update metadata file
        update_image_metadata(folder_path, request.image_path, metadata)
        
        # Update vector store
        vector_store.add_or_update_image(request.image_path, metadata)
        
        # Create ImageInfo object
        image_info = create_image_info(request.image_path, {request.image_path: metadata})
        
        return {
            "success": True,
            "message": "Image processed successfully",
            "image": image_info
        }
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        return {
            "success": False,
            "message": f"Error processing image: {str(e)}",
            "image": None
        }

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

@router.get("/check-init-status")
async def check_init_status():
    """
    Check if the vector database needs initialization.
    
    Returns:
        Dict with initialization status
    """
    try:
        if current_folder is None:
            return {"initialized": False, "message": "No folder selected"}
        
        folder_path = Path(current_folder)
        vector_db_path = folder_path / ".vectordb"
        
        if not vector_db_path.exists():
            return {"initialized": False, "message": "Vector database not initialized"}
        
        return {"initialized": True, "message": "Vector database initialized"}
    except Exception as e:
        logger.error(f"Error checking initialization status: {str(e)}")
        return {"initialized": False, "message": f"Error: {str(e)}"} 
