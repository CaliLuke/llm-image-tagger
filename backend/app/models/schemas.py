from pydantic import BaseModel, Field
from typing import List, Optional, Dict

# Request Models
class FolderRequest(BaseModel):
    """Request model for folder operations."""
    folder_path: str = Field(..., description="Path to the folder")

class SearchRequest(BaseModel):
    """Request model for search operations."""
    query: str = Field(..., description="Search query")

class ProcessImageRequest(BaseModel):
    """Request model for processing a single image."""
    image_path: str = Field(..., description="Path to the image")

class UpdateImageMetadata(BaseModel):
    """Request model for updating image metadata."""
    path: str = Field(..., description="Path to the image")
    description: Optional[str] = Field(None, description="Image description")
    tags: Optional[List[str]] = Field(None, description="Image tags")
    text_content: Optional[str] = Field(None, description="Text content in the image")

# Response Models
class ImageInfo(BaseModel):
    """Response model for image information."""
    name: str = Field(..., description="Image name")
    path: str = Field(..., description="Image path")
    description: str = Field("", description="Image description")
    tags: List[str] = Field(default_factory=list, description="Image tags")
    text_content: str = Field("", description="Text content in the image")
    is_processed: bool = Field(False, description="Whether the image has been processed")

class ImagesResponse(BaseModel):
    """Response model for multiple images."""
    images: List[ImageInfo] = Field(..., description="List of images")

class SearchResponse(BaseModel):
    """Response model for search results."""
    images: List[ImageInfo] = Field(..., description="List of matching images")

class ProcessResponse(BaseModel):
    """Response model for processing operations."""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Operation message")
    image: Optional[ImageInfo] = Field(None, description="Processed image information")

# Ollama Models
class ImageDescription(BaseModel):
    """Model for image description from Ollama."""
    description: str = Field(..., description="Image description")

class ImageTags(BaseModel):
    """Model for image tags from Ollama."""
    tags: List[str] = Field(..., description="Image tags")

class ImageText(BaseModel):
    """Model for text content in an image from Ollama."""
    has_text: bool = Field(..., description="Whether the image contains text")
    text_content: str = Field("", description="Text content in the image") 
