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
        logger.info(f"Processing search request: {request.query}")
        
        # Load metadata
        metadata = load_or_create_metadata(Path(current_folder))
        logger.debug(f"Loaded metadata with {len(metadata)} entries")
        
        # Perform hybrid search
        results = set()
        query = request.query.lower()
        
        # Full-text search
        if query:
            logger.debug("Performing full-text search")
            for path, meta in metadata.items():
                # Check each metadata field
                if (query in meta.get("description", "").lower() or
                    query in meta.get("text_content", "").lower() or
                    any(query in tag.lower() for tag in meta.get("tags", []))):
                    
                    results.add(path)
                    logger.debug(f"Full-text match: {path}")
        else:
            # If no query, return all images
            logger.debug("No query provided, including all images")
            results.update(metadata.keys())
        
        # Vector search
        logger.debug("Performing vector similarity search")
        vector_results = vector_store.search_images(query)
        logger.debug(f"Vector search found {len(vector_results)} matches")
        results.update(vector_results)
        
        # Create response
        search_results = []
        for path in results:
            if path in metadata:
                image_info = create_image_info(path, metadata)
                search_results.append(image_info)
                logger.debug(f"Added result: {path}")
        
        logger.info(f"Search complete. Found {len(search_results)} results")
        return {"images": search_results}
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        ) 
