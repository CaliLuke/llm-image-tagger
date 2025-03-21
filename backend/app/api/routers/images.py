"""
Image serving and metadata endpoints.

This module provides:
1. Image file serving
2. Folder scanning and initialization
3. Metadata management
4. Image information retrieval
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pathlib import Path
from typing import Dict, List
import traceback

from ..dependencies import (
    get_current_folder,
    get_vector_store,
    validate_folder_exists
)
from ..state import state
from ...core.logging import logger
from ...models.schemas import (
    FolderRequest,
    ImageInfo,
    UpdateImageMetadata,
    ImagesResponse
)
from ...utils.helpers import (
    load_or_create_metadata,
    create_image_info
)

router = APIRouter()

@router.get("/{path:path}")
async def get_image(
    path: str,
    current_folder: str = Depends(get_current_folder)
):
    """
    Serve an image file.
    
    This endpoint:
    1. Validates the image path
    2. Checks file permissions
    3. Returns the image file
    
    Args:
        path (str): Path to the image file
        current_folder (str): Current working folder from dependency
        
    Returns:
        FileResponse: The image file
        
    Raises:
        HTTPException: If image not found or inaccessible
    """
    try:
        logger.info(f"Serving image: {path}")
        full_path = Path(current_folder) / path
        
        if not full_path.exists():
            logger.error(f"Image not found: {full_path}")
            raise HTTPException(status_code=404, detail="Image not found")
            
        return FileResponse(full_path)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving image {path}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error serving image: {str(e)}"
        )

@router.post("", response_model=ImagesResponse)
async def get_images(request: FolderRequest):
    """
    Get images from a folder.
    
    This endpoint:
    1. Validates and initializes the folder
    2. Sets up vector store and queue
    3. Loads or creates metadata
    4. Returns image information
    
    Args:
        request (FolderRequest): Folder request with path
        
    Returns:
        ImagesResponse: List of image information
        
    Raises:
        HTTPException: If folder invalid or error occurs
    """
    try:
        # Validate folder
        folder_path = await validate_folder_exists(request.folder_path)
        logger.info(f"Processing folder request: {folder_path}")
        
        # Set current folder
        state.set_current_folder(str(folder_path))
        
        # Initialize vector store
        vector_store_path = Path("data/vectordb")
        vector_store_path.mkdir(parents=True, exist_ok=True)
        state.initialize_vector_store(str(vector_store_path))
        
        # Initialize queue
        queue_persistence_path = Path("data")
        queue_persistence_path.mkdir(parents=True, exist_ok=True)
        state.initialize_queue(queue_persistence_path)
        
        # Load metadata
        metadata = load_or_create_metadata(folder_path)
        images = [
            create_image_info(rel_path, metadata)
            for rel_path in metadata.keys()
        ]
        
        logger.info(f"Found {len(images)} images in {folder_path}")
        return {"images": images}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing folder {request.folder_path}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error processing folder: {str(e)}"
        )

@router.post("/update")
async def update_metadata(
    request: UpdateImageMetadata,
    current_folder: str = Depends(get_current_folder),
    vector_store: VectorStore = Depends(get_vector_store)
):
    """
    Update image metadata.
    
    This endpoint:
    1. Validates the image exists
    2. Updates metadata fields
    3. Updates vector store
    4. Saves changes
    
    Args:
        request (UpdateImageMetadata): Update request with new metadata
        current_folder (str): Current working folder from dependency
        vector_store (VectorStore): Vector store from dependency
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If image not found or error occurs
    """
    try:
        logger.info(f"Updating metadata for: {request.path}")
        image_path = Path(current_folder) / request.path
        
        if not image_path.exists():
            logger.error(f"Image not found: {image_path}")
            raise HTTPException(status_code=404, detail="Image not found")
            
        # Load current metadata
        metadata = load_or_create_metadata(Path(current_folder))
        
        # Update metadata
        if request.path in metadata:
            if request.description is not None:
                metadata[request.path]["description"] = request.description
            if request.tags is not None:
                metadata[request.path]["tags"] = request.tags
            if request.text_content is not None:
                metadata[request.path]["text_content"] = request.text_content
                
            # Update vector store
            vector_store.add_or_update_image(
                request.path,
                metadata[request.path]
            )
            
            logger.info(f"Updated metadata for {request.path}")
            return {"message": "Metadata updated successfully"}
        else:
            logger.error(f"Image not found in metadata: {request.path}")
            raise HTTPException(
                status_code=404,
                detail="Image not found in metadata"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating metadata for {request.path}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error updating metadata: {str(e)}"
        ) 
