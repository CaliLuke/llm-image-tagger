import ollama
from pathlib import Path
import logging
from typing import Dict, List, Optional
import json
import subprocess
import time
from backend.app.models.schemas import ImageDescription, ImageTags, ImageText

logger = logging.getLogger(__name__)

class ImageProcessor:
    def __init__(self, model_name: str = 'llama3.2-vision', stop_check: Optional[callable] = None):
        self.model_name = model_name
        self.stop_check = stop_check
        self._ensure_ollama_running()

    def _ensure_ollama_running(self):
        """Ensure Ollama service is running, start it if not."""
        try:
            # Try to make a simple request to check if Ollama is running
            ollama.list()
            logger.info("Ollama service is running")
        except Exception as e:
            logger.info("Ollama service not running, attempting to start...")
            try:
                # Start Ollama service in the background
                subprocess.Popen(['ollama', 'serve'], 
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
                
                # Wait for service to start (up to 10 seconds)
                start_time = time.time()
                while time.time() - start_time < 10:
                    try:
                        ollama.list()
                        logger.info("Ollama service started successfully")
                        return
                    except:
                        time.sleep(0.5)
                        
                raise TimeoutError("Ollama service failed to start within timeout")
            except Exception as start_error:
                logger.error(f"Failed to start Ollama service: {start_error}")
                raise

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
        return ImageDescription.model_validate(response)

    async def _get_tags(self, image_path: str) -> ImageTags:
        """Get structured tags for the image."""
        response = await self._query_ollama(
            "List 5-10 relevant tags for this image. Include both objects, artistic style, type of image, color, etc.",
            image_path,
            ImageTags.model_json_schema()
        )
        return ImageTags.model_validate(response)

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
        result = ImageText.model_validate(response)
        
        # Ensure text_content is empty if has_text is False
        if not result.has_text:
            result.text_content = ""
        
        return result

    async def _query_ollama(self, prompt: str, image_path: str, format_schema: dict) -> dict:
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
            content = response['message']['content']
            
            # If content is already a dict, return it
            if isinstance(content, dict):
                return content
                
            # Try to parse the content as JSON
            if isinstance(content, str):
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    # If parsing fails, wrap the content in the expected format
                    if 'description' in format_schema['properties']:
                        return {'description': content.strip()}
                    elif 'tags' in format_schema['properties']:
                        # Split by commas and clean up each tag
                        tags = [tag.strip() for tag in content.split(',') if tag.strip()]
                        return {'tags': tags}
                    elif 'has_text' in format_schema['properties']:
                        content = content.strip()
                        return {
                            'has_text': bool(content),
                            'text_content': content if content else ''
                        }
                    else:
                        raise ValueError(f"Unexpected response format: {content}")
            return content
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
