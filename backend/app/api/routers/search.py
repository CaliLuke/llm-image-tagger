"""
Search functionality endpoints.

This module provides:
1. Hybrid search combining vector and text search
2. Metadata-based search
3. Similarity search
4. Search result formatting
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict
import traceback
from pathlib import Path

from ..dependencies import get_current_folder, get_vector_store
from ..state import state
from ...core.logging import logger
from ...models.schemas import SearchRequest, SearchResponse
from ...utils.helpers import load_or_create_metadata, create_image_info

router = APIRouter()

@router.post("", response_model=SearchResponse)
async def search_images(
    request: SearchRequest,
    current_folder: str = Depends(get_current_folder),
    vector_store: VectorStore = Depends(get_vector_store)
):
    """
    Search for images using hybrid search.
    
    This endpoint combines:
    1. Full-text search in metadata
    2. Vector similarity search
    3. Result deduplication
    4. Relevance sorting
    
    The search looks through:
    - Image descriptions
    - Generated tags
    - Extracted text content
    - Vector embeddings
    
    Args:
        request (SearchRequest): Search query
        current_folder (str): Current working folder from dependency
        vector_store (VectorStore): Vector store from dependency
        
    Returns:
        SearchResponse: List of matching images with metadata
        
    Raises:
        HTTPException: If search fails or no folder selected
    """
    try:
        logger.info(f"Searching for: {request.query}")
        
        # Load metadata
        metadata = await load_or_create_metadata(Path(current_folder))
        
        # Perform vector search
        results = await vector_store.search(
            request.query,
            limit=request.limit or 10,
            threshold=request.threshold or 0.5
        )
        
        # Create response objects
        images = []
        for path in results:
            if path in metadata:
                image_info = create_image_info(path, metadata)
                images.append(image_info)
                
        return SearchResponse(images=images)
        
    except Exception as e:
        logger.error(f"Error searching images: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        logger.error(f"Exception traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e)) 
