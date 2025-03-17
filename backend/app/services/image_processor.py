import ollama
from pathlib import Path
from typing import Dict, List, Optional, Callable
import json
import os

from ..core.config import settings
from ..core.logging import logger
from ..models.schemas import ImageDescription, ImageTags, ImageText

class ImageProcessor:
    """Service for processing images using Ollama vision model."""
    
    def __init__(self, model_name: Optional[str] = None, stop_check=None):
        """
        Initialize the image processor with the specified model.
        
        Args:
            model_name: Name of the Ollama model to use
            stop_check: Function that returns True if processing should stop
        """
        self.model_name = model_name or settings.OLLAMA_MODEL
        self.stop_check = stop_check
        # Set Ollama host if specified in settings
        if settings.OLLAMA_HOST:
            os.environ["OLLAMA_HOST"] = settings.OLLAMA_HOST

    async def process_image(self, image_path: Path, progress_callback: Optional[Callable[[float], None]] = None) -> Dict:
        """
        Process an image using Ollama vision model to generate tags, description, and extract text.
        
        Args:
            image_path: Path to the image file
            progress_callback: Optional callback function to report progress (0.0 to 1.0)
            
        Returns:
            Dict containing description, tags, and text_content
        
        Raises:
            FileNotFoundError: If the image file does not exist
            Exception: If there is an error processing the image
        """
        try:
            # Ensure image path exists
            if not image_path.exists():
                raise FileNotFoundError(f"Image not found: {image_path}")

            # Check if processing should stop
            if self.stop_check and self.stop_check():
                logger.info(f"Stopping image processing for {image_path} due to stop request")
                return {
                    "description": "",
                    "tags": [],
                    "text_content": "",
                    "is_processed": False
                }
            
            # Initialize progress
            if progress_callback:
                progress_callback(0.0)

            # Get description (33% of progress)
            logger.info(f"Getting description for image: {image_path}")
            description_result = await self._get_description(str(image_path))
            
            # Update progress
            if progress_callback:
                progress_callback(0.33)
            
            # Check if processing should stop
            if self.stop_check and self.stop_check():
                logger.info(f"Stopping image processing for {image_path} after description due to stop request")
                return {
                    "description": description_result.description,
                    "tags": [],
                    "text_content": "",
                    "is_processed": False
                }

            # Get tags (66% of progress)
            logger.info(f"Getting tags for image: {image_path}")
            tags_result = await self._get_tags(str(image_path))
            
            # Update progress
            if progress_callback:
                progress_callback(0.66)
            
            # Check if processing should stop
            if self.stop_check and self.stop_check():
                logger.info(f"Stopping image processing for {image_path} after tags due to stop request")
                return {
                    "description": description_result.description,
                    "tags": tags_result.tags,
                    "text_content": "",
                    "is_processed": False
                }

            # Get text content (100% of progress)
            logger.info(f"Getting text content for image: {image_path}")
            text_result = await self._get_text_content(str(image_path))
            
            # Update progress to complete
            if progress_callback:
                progress_callback(1.0)

            # Return combined results
            return {
                "description": description_result.description,
                "tags": tags_result.tags,
                "text_content": text_result.text_content,
                "is_processed": True
            }
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {str(e)}")
            # Update progress to indicate failure
            if progress_callback:
                progress_callback(1.0)  # Still mark as complete even if failed
            raise

    async def _get_description(self, image_path: str) -> ImageDescription:
        """
        Get a structured description of the image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            ImageDescription object containing the description
        """
        response = await self._query_ollama(
            "Describe this image in one or two sentences.",
            image_path,
            ImageDescription.model_json_schema()
        )
        return ImageDescription.model_validate_json(response)

    async def _get_tags(self, image_path: str) -> ImageTags:
        """
        Get structured tags for the image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            ImageTags object containing the tags
        """
        response = await self._query_ollama(
            "List 5-10 relevant tags for this image. Include both objects, artistic style, type of image, color, etc.",
            image_path,
            ImageTags.model_json_schema()
        )
        return ImageTags.model_validate_json(response)

    async def _get_text_content(self, image_path: str) -> ImageText:
        """
        Extract structured text content from the image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            ImageText object containing the text content
        """
        response = await self._query_ollama(
            "Identify if there is visible text in the image. Respond with JSON where 'has_text' is true only if there is actual text visible in the image, and 'text_content' contains the extracted text. If no text is visible, set 'has_text' to false and 'text_content' to empty string.",
            image_path,
            ImageText.model_json_schema()
        )
        result = ImageText.model_validate_json(response)
        
        # Ensure text_content is empty if has_text is False
        if not result.has_text:
            result.text_content = ""
        
        return result

    async def _query_ollama(self, prompt: str, image_path: str, format_schema: dict) -> str:
        """
        Send a query to Ollama with an image and expect structured output.
        
        Args:
            prompt: The prompt to send to Ollama
            image_path: Path to the image file
            format_schema: JSON schema for the expected response format
            
        Returns:
            JSON string containing the response
            
        Raises:
            Exception: If there is an error querying Ollama
        """
        try:
            # Check if processing should stop before making the API call
            if self.stop_check and self.stop_check():
                logger.info(f"Skipping Ollama query due to stop request")
                raise Exception("Processing stopped by user")
                
            response = ollama.chat(
                model=self.model_name,
                messages=[{
                    'role': 'user',
                    'content': prompt,
                    'images': [image_path],
                    'options': {
                        'num_gpu': 41
                    }
                }],
                format=format_schema
            )
            return response['message']['content']
        except Exception as e:
            logger.error(f"Ollama query failed: {str(e)}")
            raise

def update_image_metadata(folder_path: Path, image_path: str, metadata: Dict) -> None:
    """
    Update the metadata file with new image processing results.
    
    Args:
        folder_path: Path to the folder containing the metadata file
        image_path: Relative path to the image
        metadata: Metadata to update
        
    Raises:
        Exception: If there is an error updating the metadata file
    """
    metadata_file = folder_path / "image_metadata.json"
    
    try:
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                all_metadata = json.load(f)
        else:
            all_metadata = {}

        # Update the metadata for this image
        all_metadata[image_path] = metadata

        # Save the updated metadata
        with open(metadata_file, 'w') as f:
            json.dump(all_metadata, f, indent=4)

    except Exception as e:
        logger.error(f"Error updating metadata file: {str(e)}")
        raise 
