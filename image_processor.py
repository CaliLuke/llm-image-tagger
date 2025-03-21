import ollama
from pathlib import Path
import logging
from typing import Dict, List, Optional
import json
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ImageDescription(BaseModel):
    description: str

class ImageTags(BaseModel):
    tags: List[str]

class ImageText(BaseModel):
    has_text: bool
    text_content: str

class ImageProcessor:
    def __init__(self, model_name: str = 'llama3.2-vision'):
        self.model_name = model_name

    async def process_image(self, image_path: Path) -> Dict:
        """
        Process an image using Ollama vision model to generate tags, description, and extract text.
        
        Returns:
            Dict containing description, tags, and text_content
        """
        try:
            # Ensure image path exists
            if not image_path.exists():
                raise FileNotFoundError(f"Image not found: {image_path}")

            # Convert image path to string for Ollama
            image_path_str = str(image_path)

            # Get structured responses using Pydantic models
            logger.info(f"Getting description for image: {image_path}")
            description_response = await self._get_description(image_path_str)
            logger.debug(f"Received description: {description_response.description}")
            
            # Get tags
            logger.info(f"Getting tags for image: {image_path}")
            tags_response = await self._get_tags(image_path_str)
            logger.debug(f"Received tags: {tags_response.tags}")
            
            # Get text content
            logger.info(f"Getting text content for image: {image_path}")
            text_response = await self._get_text_content(image_path_str)
            logger.debug(
                f"Received text content - has_text: {text_response.has_text}, "
                f"content: {text_response.text_content if text_response.has_text else 'None'}"
            )

            return {
                "description": description_response.description,
                "tags": tags_response.tags,
                "text_content": text_response.text_content if text_response.has_text else "",
                "is_processed": True
            }

        except Exception as e:
            logger.error(f"Error processing image {image_path}: {str(e)}")
            raise

    async def _get_description(self, image_path: str) -> ImageDescription:
        """Get a structured description of the image."""
        response = await self._query_ollama(
            "Describe this image in one or two sentences.",
            image_path,
            ImageDescription.model_json_schema()
        )
        return ImageDescription.model_validate_json(response)

    async def _get_tags(self, image_path: str) -> ImageTags:
        """Get structured tags for the image."""
        response = await self._query_ollama(
            "List 5-10 relevant tags for this image. Include both objects, artistic style, type of image, color, etc.",
            image_path,
            ImageTags.model_json_schema()
        )
        return ImageTags.model_validate_json(response)

    async def _get_text_content(self, image_path: str) -> ImageText:
        """
        Extract structured text content from the image.
        Returns a model with has_text boolean flag and text_content string.
        If has_text is False, text_content will be ignored.
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
        """Send a query to Ollama with an image and expect structured output."""
        try:
            response = await ollama.chat(
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
    """Update the metadata file with new image processing results."""
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
