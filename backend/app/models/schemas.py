"""
Data models and schemas for the image tagging application.

This module defines:
1. Request Models: Schemas for incoming API requests
2. Response Models: Schemas for API responses
3. Ollama Models: Schemas for Ollama vision model responses

All models use Pydantic for:
- Data validation
- Schema generation
- Documentation
- Serialization/deserialization

Each model has strict validation with ConfigDict(extra="forbid") to prevent
unexpected fields from being processed.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict

# Request Models
class FolderRequest(BaseModel):
    """
    Request model for folder operations.
    
    Used for:
    - Scanning folders for images
    - Processing all images in a folder
    - Managing folder-level operations
    
    Attributes:
        folder_path (str): Absolute or relative path to the target folder
    """
    folder_path: str = Field(..., description="Path to the folder")
    model_config = ConfigDict(extra="forbid")

class SearchRequest(BaseModel):
    """
    Request model for search operations.
    
    Used for:
    - Searching images by description
    - Finding images by tags
    - Querying text content
    
    Attributes:
        query (str): Search query string for finding relevant images
    """
    query: str = Field(..., description="Search query")
    model_config = ConfigDict(extra="forbid")

class ProcessImageRequest(BaseModel):
    """
    Request model for processing a single image.
    
    Used for:
    - Initiating image analysis
    - Generating descriptions
    - Extracting tags and text
    
    Attributes:
        image_path (str): Path to the image file to process
    """
    image_path: str = Field(..., description="Path to the image")
    model_config = ConfigDict(extra="forbid")

class UpdateImageMetadata(BaseModel):
    """
    Request model for updating image metadata.
    
    Used for:
    - Modifying image descriptions
    - Updating tags
    - Correcting text content
    - Manual metadata adjustments
    
    Attributes:
        path (str): Path to the image file
        description (Optional[str]): New image description
        tags (Optional[List[str]]): New list of tags
        text_content (Optional[str]): New text content
    """
    path: str = Field(..., description="Path to the image")
    description: Optional[str] = Field(None, description="Image description")
    tags: Optional[List[str]] = Field(None, description="Image tags")
    text_content: Optional[str] = Field(None, description="Text content in the image")
    model_config = ConfigDict(extra="forbid")

# Response Models
class ImageInfo(BaseModel):
    """
    Response model for image information.
    
    Used for:
    - Returning image details
    - Displaying image metadata
    - Presenting search results
    
    Attributes:
        name (str): Image filename
        path (str): Full path to the image
        url (str): URL to access the image via API
        description (str): Generated or updated description
        tags (List[str]): List of relevant tags
        text_content (str): Extracted text from the image
        is_processed (bool): Whether image has been analyzed
    """
    name: str = Field(..., description="Image name")
    path: str = Field(..., description="Image path")
    url: str = Field(..., description="URL to access the image")
    description: str = Field("", description="Image description")
    tags: List[str] = Field(default_factory=list, description="Image tags")
    text_content: str = Field("", description="Text content in the image")
    is_processed: bool = Field(False, description="Whether the image has been processed")
    model_config = ConfigDict(extra="forbid")

class ImagesResponse(BaseModel):
    """
    Response model for multiple images.
    
    Used for:
    - Listing folder contents
    - Batch processing results
    - Collection operations
    
    Attributes:
        images (List[ImageInfo]): List of image information objects
    """
    images: List[ImageInfo] = Field(..., description="List of images")
    model_config = ConfigDict(extra="forbid")

class SearchResponse(BaseModel):
    """
    Response model for search results.
    
    Used for:
    - Returning search matches
    - Filtering results
    - Similarity searches
    
    Attributes:
        images (List[ImageInfo]): List of matching image information objects
    """
    images: List[ImageInfo] = Field(..., description="List of matching images")
    model_config = ConfigDict(extra="forbid")

class ProcessResponse(BaseModel):
    """
    Response model for processing operations.
    
    Used for:
    - Processing status updates
    - Error reporting
    - Success confirmation
    
    Attributes:
        success (bool): Operation success status
        message (str): Status or error message
        image (Optional[ImageInfo]): Processed image details if available
    """
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Operation message")
    image: Optional[ImageInfo] = Field(None, description="Processed image information")
    model_config = ConfigDict(extra="forbid")

# Ollama Models
class ImageDescription(BaseModel):
    """
    Model for image description from Ollama.
    
    Used for:
    - Storing generated descriptions
    - Validating model output
    - Consistent description format
    
    Attributes:
        description (str): Generated image description text
    """
    description: str = Field(..., description="Image description")
    model_config = ConfigDict(extra="forbid")

class ImageTags(BaseModel):
    """
    Model for image tags from Ollama.
    
    Used for:
    - Storing extracted tags
    - Categorizing images
    - Search indexing
    
    Attributes:
        tags (List[str]): List of extracted image tags
    """
    tags: List[str] = Field(..., description="Image tags")
    model_config = ConfigDict(extra="forbid")

class ImageText(BaseModel):
    """
    Model for text content in an image from Ollama.
    
    Used for:
    - OCR results storage
    - Text presence detection
    - Content extraction
    
    Attributes:
        has_text (bool): Whether text was detected
        text_content (str): Extracted text content
    """
    has_text: bool = Field(..., description="Whether the image contains text")
    text_content: str = Field("", description="Text content in the image")
    model_config = ConfigDict(extra="forbid")

class DirectoryInfo(BaseModel):
    """
    Model for directory information.
    
    Used for:
    - Directory browser in the UI
    - Filesystem navigation
    - Image collection organization
    
    Attributes:
        name (str): Directory name
        path (str): Full path to the directory
        hasImages (bool): Whether the directory contains images
        hasMetadata (bool): Whether the directory has metadata file
        imageCount (Optional[int]): Count of images if present
        error (Optional[str]): Error message if there was a problem
    """
    name: str = Field(..., description="Directory name")
    path: str = Field(..., description="Directory path")
    hasImages: bool = Field(False, description="Whether the directory contains images")
    hasMetadata: bool = Field(False, description="Whether the directory has a metadata file")
    imageCount: Optional[int] = Field(None, description="Number of images in the directory")
    error: Optional[str] = Field(None, description="Error accessing the directory if any")
    model_config = ConfigDict(extra="forbid")

class DirectoriesResponse(BaseModel):
    """
    Response model for directory listing.
    
    Used for:
    - Directory browser in the UI
    - Filesystem navigation response
    - Tree view construction
    
    Attributes:
        directories (List[DirectoryInfo]): List of directory information objects
    """
    directories: List[DirectoryInfo] = Field(..., description="List of directories")
    model_config = ConfigDict(extra="forbid") 
