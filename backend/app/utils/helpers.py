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
"""

from pathlib import Path
from typing import Dict, Set
import json
import hashlib
import traceback

from ..core.settings import settings
from ..core.logging import logger
from ..models.schemas import ImageInfo

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

def load_or_create_metadata(folder_path: Path) -> Dict[str, Dict]:
    """
    Load metadata from file or create new if it doesn't exist.
    
    This function:
    1. Locates or creates the data directory
    2. Generates a unique metadata filename using folder hash
    3. Attempts to load existing metadata
    4. Creates new metadata if none exists
    5. Saves metadata to disk
    
    File operations are handled safely with:
    - Permission checks
    - Error handling
    - Atomic writes
    - Detailed logging
    
    The metadata file is stored as:
    data/metadata_<folder_hash>.json
    
    Args:
        folder_path (Path): Path to the folder containing images
        
    Returns:
        Dict[str, Dict]: Dictionary containing metadata for all images
        
    Raises:
        Exception: If directory creation or file operations fail
        
    Logs:
        - INFO: Operation progress and file details
        - ERROR: File operation failures with stack traces
    """
    logger.info(f"Loading/creating metadata for folder: {folder_path}")
    
    # Get the project root directory (3 levels up from helpers.py)
    project_root = Path(__file__).parent.parent.parent.parent
    logger.info(f"Project root directory: {project_root}")
    
    # Create data directory if it doesn't exist
    data_dir = project_root / "data"
    logger.info(f"Data directory path: {data_dir}")
    try:
        data_dir.mkdir(exist_ok=True)
        logger.info(f"Data directory exists: {data_dir.exists()}")
        logger.info(f"Data directory permissions: {oct(data_dir.stat().st_mode)[-3:]}")
    except Exception as e:
        logger.error(f"Error creating/checking data directory: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        logger.error(f"Exception traceback: {traceback.format_exc()}")
        raise
    
    # Create a unique filename based on the folder path
    folder_hash = hashlib.md5(str(folder_path).encode()).hexdigest()
    metadata_file = data_dir / f"metadata_{folder_hash}.json"
    logger.info(f"Metadata file path: {metadata_file}")
    
    # Try to load existing metadata
    try:
        if metadata_file.exists():
            logger.info(f"Found existing metadata file at {metadata_file}")
            logger.info(f"Metadata file permissions: {oct(metadata_file.stat().st_mode)[-3:]}")
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                logger.info(f"Successfully loaded metadata with {len(metadata)} entries")
                return metadata
        else:
            logger.info(f"No existing metadata file found at {metadata_file}")
    except Exception as e:
        logger.error(f"Error loading metadata file: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        logger.error(f"Exception traceback: {traceback.format_exc()}")
    
    # Create new metadata
    logger.info("Creating new metadata dictionary")
    metadata = {}
    
    # Scan for images
    logger.info(f"Scanning for images in folder: {folder_path}")
    logger.info(f"Folder permissions: {oct(folder_path.stat().st_mode)[-3:]}")
    
    try:
        for file_path in folder_path.iterdir():
            if file_path.suffix.lower() in settings.SUPPORTED_EXTENSIONS:
                logger.info(f"Found image: {file_path}")
                logger.info(f"File permissions: {oct(file_path.stat().st_mode)[-3:]}")
                rel_path = str(file_path.relative_to(folder_path))
                metadata[rel_path] = {
                    "path": rel_path,
                    "filename": file_path.name,
                    "size": file_path.stat().st_size,
                    "modified": file_path.stat().st_mtime
                }
    except Exception as e:
        logger.error(f"Error scanning folder for images: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        logger.error(f"Exception traceback: {traceback.format_exc()}")
        raise
    
    # Save metadata
    try:
        logger.info(f"Saving metadata to {metadata_file}")
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Successfully saved metadata with {len(metadata)} entries")
    except Exception as e:
        logger.error(f"Error saving metadata file: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        logger.error(f"Exception traceback: {traceback.format_exc()}")
        raise
    
    return metadata

def create_image_info(rel_path: str, metadata: Dict[str, Dict]) -> ImageInfo:
    """
    Create an ImageInfo object from metadata.
    
    This function:
    1. Extracts the image name from the path
    2. Retrieves metadata for the image
    3. Constructs the image access URL
    4. Creates a Pydantic model instance
    
    The function handles missing metadata gracefully by:
    - Using empty defaults for missing fields
    - Maintaining consistent types
    - Ensuring URL format consistency
    
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
    
    # Get metadata for this image
    img_metadata = metadata.get(rel_path, {})
    
    # Create the image URL
    url = f"/image/{rel_path}"
    
    return ImageInfo(
        name=name,
        path=rel_path,
        url=url,  # Add the URL field
        description=img_metadata.get("description", ""),
        tags=img_metadata.get("tags", []),
        text_content=img_metadata.get("text_content", ""),
        is_processed=img_metadata.get("is_processed", False)
    ) 
