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
import traceback
from typing import Dict, Optional, Any, List, Set, Union
import os
import json
from datetime import datetime
import time
import hashlib
import re
import uuid
from fastapi import HTTPException
import base64

from ..core.logging import logger
from ..models.schemas import ImageInfo
from ..services.storage import file_storage
from ..config import settings

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

async def load_or_create_metadata(folder_path: Path, recursive: bool = False, require_write_access: bool = True) -> Dict[str, Dict]:
    """
    Load metadata from a folder or create it if it doesn't exist.
    
    Args:
        folder_path: Path to the folder
        recursive: If True, search recursively in subdirectories
        require_write_access: If False, don't try to write metadata if dir isn't writable
        
    Returns:
        Dictionary with image metadata
    """
    metadata_file = folder_path / "image_metadata.json"
    
    try:
        # Load existing metadata if it exists
        if metadata_file.exists():
            metadata = await file_storage.read(metadata_file)
            logger.info(f"Loaded existing metadata from {metadata_file}")
            
            # Validate metadata structure
            if not isinstance(metadata, dict):
                logger.warning(f"Invalid metadata format in {metadata_file}, recreating...")
                metadata = {}
        else:
            metadata = {}
            logger.info(f"No existing metadata found at {metadata_file}")
        
        # Find all images in the folder
        image_files = []
        logger.debug(f"Looking for images in {folder_path} with extensions: {settings.SUPPORTED_EXTENSIONS}")
        logger.debug(f"Folder exists: {folder_path.exists()}, Is directory: {folder_path.is_dir()}")
        
        try:
            # Verify the directory actually exists
            if not folder_path.exists() or not folder_path.is_dir():
                logger.warning(f"Directory does not exist or is not a directory: {folder_path}")
                return {}
                
            # List directory contents to verify we can access it
            try:
                dir_contents = list(folder_path.iterdir())
                logger.debug(f"Directory {folder_path} contains {len(dir_contents)} entries")
                # Print first 5 entries for debugging
                for i, entry in enumerate(dir_contents[:5]):
                    logger.debug(f"  Entry {i+1}: {entry.name} ({'dir' if entry.is_dir() else 'file'})")
            except Exception as e:
                logger.error(f"Error listing directory contents: {str(e)}")
            
            # Try with Path.glob first (more reliable)
            for ext in settings.SUPPORTED_EXTENSIONS:
                # Track patterns and counts for debugging
                # Strip the leading dot from the extension since we add it in the pattern
                ext_name = ext[1:] if ext.startswith('.') else ext
                lower_pattern = f"*.{ext_name.lower()}"
                upper_pattern = f"*.{ext_name.upper()}"
                
                lower_count = 0
                upper_count = 0
                
                # Handle case sensitivity and use both lowercase and uppercase patterns
                if recursive:
                    logger.debug(f"  Using rglob with pattern: {lower_pattern}")
                    lower_results = list(folder_path.rglob(lower_pattern))
                    lower_count = len(lower_results)
                    
                    logger.debug(f"  Using rglob with pattern: {upper_pattern}")
                    upper_results = list(folder_path.rglob(upper_pattern))
                    upper_count = len(upper_results)
                    
                    image_files.extend(lower_results)
                    image_files.extend(upper_results)
                else:
                    logger.debug(f"  Using glob with pattern: {lower_pattern}")
                    lower_results = list(folder_path.glob(lower_pattern))
                    lower_count = len(lower_results)
                    
                    logger.debug(f"  Using glob with pattern: {upper_pattern}")
                    upper_results = list(folder_path.glob(upper_pattern))
                    upper_count = len(upper_results)
                    
                    image_files.extend(lower_results)
                    image_files.extend(upper_results)
                
                logger.debug(f"  Found {lower_count} files with lowercase pattern: {lower_pattern}")
                logger.debug(f"  Found {upper_count} files with uppercase pattern: {upper_pattern}")
            
            logger.debug(f"Found {len(image_files)} image files using Path.glob")
            
            # If no files found via Path.glob, try OS-specific alternatives
            if not image_files and os.name == 'posix':
                # On Unix systems, try using os.walk as fallback
                logger.debug("Using os.walk as fallback to find images")
                # Create extension patterns without double dots, removing leading dot if present
                patterns = []
                for ext in settings.SUPPORTED_EXTENSIONS:
                    # Strip the leading dot if present
                    ext_name = ext[1:] if ext.startswith('.') else ext
                    patterns.append(f".{ext_name.lower()}")
                    patterns.append(f".{ext_name.upper()}")
                
                logger.debug(f"Looking for files with these extensions: {patterns}")
                
                if recursive:
                    for root, _, files in os.walk(str(folder_path)):
                        matched_files = []
                        for file in files:
                            if any(file.endswith(pat) for pat in patterns):
                                matched_files.append(file)
                                image_files.append(Path(root) / file)
                        if matched_files:
                            logger.debug(f"  In directory {root}, found matches: {matched_files}")
                else:
                    try:
                        all_files = os.listdir(str(folder_path))
                        logger.debug(f"os.listdir found {len(all_files)} entries in {folder_path}")
                        
                        matched_files = []
                        for file in all_files:
                            file_path = os.path.join(str(folder_path), file)
                            if os.path.isfile(file_path) and any(file.endswith(pat) for pat in patterns):
                                matched_files.append(file)
                                image_files.append(folder_path / file)
                        
                        if matched_files:
                            logger.debug(f"  Matched files: {matched_files}")
                    except Exception as e:
                        logger.error(f"Error listing directory with os.listdir: {str(e)}")
                            
                logger.debug(f"Found {len(image_files)} image files using os.walk")
        except Exception as e:
            logger.error(f"Error finding image files: {str(e)}")
            logger.error(traceback.format_exc())
        
        # Log what we found
        if image_files:
            logger.info(f"Found {len(image_files)} images in {folder_path}")
            if len(image_files) <= 10:  # Only log all files if there aren't too many
                for img in image_files:
                    logger.debug(f"  Image: {img}")
        else:
            logger.warning(f"No images found in {folder_path}")
        
        # Get relative paths
        relative_paths = []
        for img_path in image_files:
            try:
                # Skip macOS resource fork files
                if img_path.name.startswith('._'):
                    continue
                    
                rel_path = str(img_path.relative_to(folder_path))
                relative_paths.append(rel_path)
            except ValueError as e:
                logger.error(f"Error getting relative path for {img_path}: {str(e)}")
        
        # Add any missing images to metadata
        for rel_path in relative_paths:
            if rel_path not in metadata:
                metadata[rel_path] = {
                    "description": "",
                    "tags": [],
                    "text_content": "",
                    "is_processed": False
                }
                logger.debug(f"Added new image to metadata: {rel_path}")
        
        # Remove any images that no longer exist or are macOS resource fork files
        for rel_path in list(metadata.keys()):
            if rel_path not in relative_paths or Path(rel_path).name.startswith('._'):
                logger.debug(f"Removing {'macOS resource fork' if Path(rel_path).name.startswith('._') else 'deleted'} image from metadata: {rel_path}")
                del metadata[rel_path]
        
        # Save metadata only if we have write access and require it
        if require_write_access:
            # Check write access first
            try:
                # Simple test for write permission
                if not metadata_file.exists():
                    test_file = folder_path / ".write_test"
                    test_file.touch()
                    test_file.unlink()
                else:
                    # If metadata file exists, we'll assume it's writable
                    # We'll catch the exception if it's not
                    pass
                    
                # Save metadata
                if not metadata_file.exists() or relative_paths:
                    await file_storage.write(metadata_file, metadata)
                    logger.info(f"Saved metadata to {metadata_file} with {len(metadata)} entries")
            except (PermissionError, OSError) as e:
                logger.warning(f"Cannot write metadata to {folder_path}: {str(e)}")
                # We don't raise an exception here, just log a warning
                
        return metadata
    except Exception as e:
        logger.error(f"Error loading or creating metadata: {str(e)}")
        logger.error(traceback.format_exc())
        
        # If we don't require write access, return empty metadata rather than failing
        if not require_write_access and isinstance(e, (PermissionError, OSError)):
            logger.warning(f"Continuing without metadata due to permission error: {str(e)}")
            return {}
            
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load or create metadata: {str(e)}"
        )

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
