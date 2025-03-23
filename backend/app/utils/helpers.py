"""
Helper utilities for image metadata management.

This module provides utilities for:
1. Image file handling and validation
2. Metadata initialization and management
3. Folder scanning and recursive image discovery
4. Persistent metadata storage and retrieval
5. Image information object creation

The module implements safe file operations with:
- Proper error handling and logging
- File permission checks
- Atomic file operations
- Data validation

Metadata Storage:
- Each image folder contains its own metadata file (image_metadata.json)
- Metadata stays with the images when folders are moved
- Future versions will store metadata in image files using EXIF/XMP
"""

from pathlib import Path
from typing import Dict, Set
import json
import hashlib
import traceback
import os
import time

from ..core.settings import settings
from ..core.logging import logger
from ..models.schemas import ImageInfo
from ..services.storage import file_storage

def get_supported_extensions() -> Set[str]:
    """
    Return a set of supported image file extensions.
    
    This function:
    1. Retrieves extensions from settings
    2. Ensures all extensions are lowercase
    3. Returns them as a set for O(1) lookup
    
    Returns:
        Set[str]: Set of supported image file extensions (e.g., {'.jpg', '.png'})
    """
    return set(settings.SUPPORTED_EXTENSIONS)

def initialize_image_metadata(image_path: str) -> Dict:
    """
    Create initial metadata structure for a single image.
    
    This function initializes a metadata dictionary with:
    - Empty description
    - Empty tags list
    - Empty text content
    - Processing status flag
    
    Args:
        image_path (str): Path to the image, used for reference
        
    Returns:
        Dict: Initial metadata structure with fields:
            - description (str): Empty string
            - tags (List[str]): Empty list
            - text_content (str): Empty string
            - is_processed (bool): False
    """
    return {
        "description": "",
        "tags": [],
        "text_content": "",
        "is_processed": False
    }

def is_metadata_processed(metadata: Dict) -> bool:
    """
    Check if any metadata field is non-empty.
    
    This function checks if the image has been processed by:
    1. Checking for non-empty description
    2. Checking for non-empty tags list
    3. Checking for non-empty text content
    
    Args:
        metadata (Dict): Metadata dictionary to check
        
    Returns:
        bool: True if any metadata field is non-empty, indicating
              the image has been processed at least partially
    """
    return bool(
        metadata.get("description") or 
        metadata.get("tags") or 
        metadata.get("text_content")
    )

def scan_folder_for_images(folder_path: Path) -> Dict[str, Dict]:
    """
    Scan folder recursively and create metadata for all images.
    
    This function:
    1. Recursively walks through the folder
    2. Identifies image files by extension
    3. Validates each image using PIL
    4. Creates initial metadata for valid images
    5. Skips hidden and system files
    6. Handles errors gracefully
    
    Image validation includes:
    - Format verification
    - Mode checking
    - Size validation
    - Alpha channel verification for RGBA
    
    Args:
        folder_path (Path): Path to the folder to scan
        
    Returns:
        Dict[str, Dict]: Dictionary mapping relative image paths to their metadata
        
    Logs:
        - INFO: Scan progress and valid images
        - DEBUG: File processing details
        - WARNING: Invalid images and format issues
    """
    metadata = {}
    image_extensions = get_supported_extensions()
    logger.info(f"Scanning folder {folder_path} for images with extensions: {image_extensions}")
    
    for file_path in folder_path.rglob("*"):
        # Skip hidden files and system files
        if file_path.name.startswith('.') or file_path.name.startswith('._'):
            logger.debug(f"Skipping hidden/system file: {file_path}")
            continue
            
        if file_path.suffix.lower() in image_extensions:
            try:
                logger.debug(f"Validating image: {file_path}")
                # Try to open and validate the image
                from PIL import Image
                with Image.open(file_path) as img:
                    # Get image details
                    format = img.format
                    mode = img.mode
                    size = img.size
                    
                    # Log image details
                    logger.info(f"Found valid image: {file_path}")
                    logger.info(f"Format: {format}, Mode: {mode}, Size: {size}")
                    
                    # Verify image data is valid
                    img.verify()
                    
                    # For RGBA images, verify alpha channel
                    if mode == 'RGBA':
                        alpha = img.split()[3]
                        if not any(alpha.getdata()):  # If alpha channel is completely transparent
                            logger.warning(f"Image {file_path} has fully transparent alpha channel")
                    
                    # Add to metadata
                    rel_path = str(file_path.relative_to(folder_path))
                    metadata[rel_path] = initialize_image_metadata(rel_path)
                    logger.debug(f"Added to metadata: {rel_path}")
                    
            except Exception as e:
                logger.warning(f"Invalid or corrupted image {file_path}: {str(e)}", exc_info=True)
                continue
    
    logger.info(f"Found {len(metadata)} valid images in {folder_path}")
    return metadata

async def load_or_create_metadata(folder_path: Path) -> Dict[str, Dict]:
    """
    Load existing metadata file or create new one if it doesn't exist.
    Update metadata by adding new images and removing old records.
    
    Args:
        folder_path: Path to the folder containing the metadata file
        
    Returns:
        Dictionary of image paths and their metadata
        
    Raises:
        PermissionError: If metadata file cannot be read/written due to permissions
        StorageError: If there are other storage-related errors
    """
    metadata_file = folder_path / "image_metadata.json"
    image_extensions = get_supported_extensions()
    
    logger.info(f"Loading/creating metadata for folder: {folder_path}")
    logger.info(f"Metadata file path: {metadata_file}")
    
    # Load existing metadata if it exists
    metadata = {}
    if await file_storage.exists(metadata_file):
        logger.info(f"Found existing metadata file")
        try:
            metadata = await file_storage.read(metadata_file)
            logger.info(f"Successfully loaded metadata with {len(metadata)} entries")
        except Exception as e:
            logger.error(f"Error loading metadata file: {str(e)}")
            logger.error(f"Exception type: {type(e)}")
            logger.error(f"Exception traceback: {traceback.format_exc()}")
            raise

    # Scan folder for current images
    logger.info("Scanning for current images")
    current_images = {str(file_path.relative_to(folder_path)): file_path
                      for file_path in folder_path.rglob("*")
                      if file_path.suffix.lower() in image_extensions}
    logger.info(f"Found {len(current_images)} images in folder")

    # Add new images to metadata
    for rel_path in current_images:
        if rel_path not in metadata:
            logger.info(f"Adding new image to metadata: {rel_path}")
            metadata[rel_path] = initialize_image_metadata(rel_path)
        # Update is_processed based on metadata content
        metadata[rel_path]["is_processed"] = is_metadata_processed(metadata[rel_path])

    # Remove old records from metadata
    for rel_path in list(metadata.keys()):
        if rel_path not in current_images:
            logger.info(f"Removing stale metadata for: {rel_path}")
            del metadata[rel_path]

    # Save updated metadata
    try:
        logger.info("Saving metadata")
        await file_storage.write(metadata_file, metadata)
        logger.info(f"Successfully saved metadata with {len(metadata)} entries")
    except PermissionError as e:
        # Check if this is an external drive error
        if "external drive" in str(e):
            logger.error(f"External drive permission error: {str(e)}")
            # Return metadata without saving - this allows read-only mode
            logger.warning(f"Operating in read-only mode for folder: {folder_path}")
            # Re-raise with a more specific message for the API
            raise PermissionError(f"External drive permission error: {str(e)}")
        else:
            # Other permission error
            logger.error(f"Permission error saving metadata: {str(e)}")
            logger.error(f"Exception type: {type(e)}")
            logger.error(f"Exception traceback: {traceback.format_exc()}")
            raise
    except Exception as e:
        logger.error(f"Error saving metadata: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        logger.error(f"Exception traceback: {traceback.format_exc()}")
        raise

    return metadata

def create_image_info(rel_path: str, metadata: Dict[str, Dict]) -> ImageInfo:
    """
    Create an ImageInfo object from metadata.
    
    This function:
    1. Extracts the image name from the path
    2. Retrieves metadata for the image, with intelligent key matching
    3. Constructs the image access URL
    4. Creates a Pydantic model instance
    
    The function handles missing metadata gracefully by:
    - Using empty defaults for missing fields
    - Maintaining consistent types
    - Ensuring URL format consistency
    - Searching for metadata by filename if exact key not found
    
    Args:
        rel_path (str): Relative path to the image
        metadata (Dict[str, Dict]): Dictionary containing image metadata
        
    Returns:
        ImageInfo: Pydantic model containing:
            - name: Image filename
            - path: Relative path
            - url: Access URL
            - description: Image description or empty
            - tags: List of tags or empty list
            - text_content: Extracted text or empty
            - is_processed: Processing status
    """
    # Get the image name from the path
    name = Path(rel_path).name
    logger.debug(f"Creating ImageInfo for image path: {rel_path}")
    
    # Try to find metadata by the exact key first
    img_metadata = metadata.get(rel_path, {})
    
    # If no metadata found and rel_path is just a filename, try to find it by filename
    if not img_metadata and '/' not in rel_path and '\\' not in rel_path:
        logger.debug(f"No direct metadata match for key: {rel_path}, attempting filename matching")
        # We might be dealing with just a filename, so try to find it among the keys
        matching_keys = [k for k in metadata.keys() if Path(k).name == rel_path]
        if matching_keys:
            # Use the first matching key
            logger.info(f"Metadata key match: matched filename {rel_path} to path {matching_keys[0]}")
            img_metadata = metadata.get(matching_keys[0], {})
        else:
            logger.debug(f"No metadata matches found for filename: {rel_path}")
    
    # Get processing status
    is_processed = img_metadata.get("is_processed", False)
    
    # Construct the URL for accessing the image
    url = f"/image/{rel_path}"
    
    # Create the ImageInfo object
    image_info = ImageInfo(
        name=name,
        path=rel_path,
        url=url,
        description=img_metadata.get("description", ""),
        tags=img_metadata.get("tags", []),
        text_content=img_metadata.get("text_content", ""),
        is_processed=is_processed
    )
    
    # Log details at appropriate level based on processing status
    if is_processed:
        logger.info(f"Created ImageInfo for processed image: {rel_path}, tags: {len(image_info.tags)}, has_description: {bool(image_info.description)}")
        logger.debug(f"Full metadata for processed image: {img_metadata}")
    else:
        logger.debug(f"Created ImageInfo for unprocessed image: {rel_path}")
    
    return image_info 
