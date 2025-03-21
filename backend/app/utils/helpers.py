from pathlib import Path
from typing import Dict, Set
import json

from ..core.settings import settings
from ..core.logging import logger
from ..models.schemas import ImageInfo

def get_supported_extensions() -> Set[str]:
    """
    Return a set of supported image file extensions.
    
    Returns:
        Set of supported image file extensions
    """
    return set(settings.SUPPORTED_EXTENSIONS)

def initialize_image_metadata(image_path: str) -> Dict:
    """
    Create initial metadata structure for a single image.
    
    Args:
        image_path: Path to the image
        
    Returns:
        Initial metadata structure
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
    
    Args:
        metadata: Metadata to check
        
    Returns:
        True if any metadata field is non-empty, False otherwise
    """
    return bool(
        metadata.get("description") or 
        metadata.get("tags") or 
        metadata.get("text_content")
    )

def scan_folder_for_images(folder_path: Path) -> Dict[str, Dict]:
    """
    Scan folder recursively and create metadata for all images.
    
    Args:
        folder_path: Path to the folder to scan
        
    Returns:
        Dictionary of image paths and their metadata
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
    Load existing metadata file or create new one if it doesn't exist.
    Update metadata by adding new images and removing old records.
    
    Args:
        folder_path: Path to the folder containing the metadata file
        
    Returns:
        Dictionary of image paths and their metadata
    """
    metadata_file = folder_path / "image_metadata.json"
    image_extensions = get_supported_extensions()
    
    # Load existing metadata if it exists
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
    else:
        metadata = {}

    # Scan folder for current images
    current_images = {str(file_path.relative_to(folder_path)): file_path
                      for file_path in folder_path.rglob("*")
                      if file_path.suffix.lower() in image_extensions}

    # Add new images to metadata
    for rel_path in current_images:
        if rel_path not in metadata:
            metadata[rel_path] = initialize_image_metadata(rel_path)
        # Update is_processed based on metadata content
        metadata[rel_path]["is_processed"] = is_metadata_processed(metadata[rel_path])

    # Remove old records from metadata
    for rel_path in list(metadata.keys()):
        if rel_path not in current_images:
            del metadata[rel_path]

    # Save updated metadata
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=4)

    return metadata

def create_image_info(rel_path: str, metadata: Dict) -> ImageInfo:
    """
    Create ImageInfo object from metadata.
    
    Args:
        rel_path: Relative path to the image
        metadata: Metadata for the image
        
    Returns:
        ImageInfo object
    """
    info = metadata.get(rel_path, {})
    return ImageInfo(
        name=Path(rel_path).name,
        path=rel_path,
        description=info.get("description", ""),
        tags=info.get("tags", []),
        text_content=info.get("text_content", ""),
        is_processed=info.get("is_processed", False)
    ) 
