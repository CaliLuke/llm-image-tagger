"""
Image processing module that uses Ollama vision model to analyze images.
This module handles image description generation, tag extraction, and text content detection.
"""

import ollama
from ollama import AsyncClient, __version__ as ollama_version
from pathlib import Path
import logging
import traceback
from typing import Dict, List, Optional
import json
from pydantic import BaseModel, ConfigDict

# Configure logger with module name
logger = logging.getLogger(__name__)

class ImageDescription(BaseModel):
    """Model for structured image descriptions."""
    description: str
    model_config = ConfigDict(extra="forbid")

class ImageTags(BaseModel):
    """Model for structured image tags."""
    tags: List[str]
    model_config = ConfigDict(extra="forbid")

class ImageText(BaseModel):
    """Model for structured text content detection."""
    has_text: bool
    text_content: str = ""
    model_config = ConfigDict(extra="forbid")

class ImageProcessor:
    """
    Handles image processing using Ollama vision model.
    
    This class manages the interaction with Ollama's vision model to:
    1. Generate image descriptions
    2. Extract relevant tags
    3. Detect and extract text content
    
    Attributes:
        model_name (str): Name of the Ollama model to use
        client (AsyncClient): Ollama client instance
    """
    
    def __init__(self, model_name: str = 'llama3.2-vision'):
        """
        Initialize the ImageProcessor.
        
        Args:
            model_name (str): Name of the Ollama model to use for image processing
        """
        self.model_name = model_name
        self.client = AsyncClient()
        logger.info(f"Initialized ImageProcessor with Ollama client version {ollama_version}")
        logger.info(f"Using model: {model_name}")
        logger.debug(f"AsyncClient type: {type(self.client)}")
        logger.debug(f"AsyncClient methods: {[m for m in dir(self.client) if not m.startswith('_')]}")

    async def process_image(self, image_path: Path) -> Dict:
        """
        Process an image using Ollama vision model to generate tags, description, and extract text.
        
        This method orchestrates the complete image processing pipeline:
        1. Validates the image path
        2. Gets image description
        3. Extracts tags
        4. Detects and extracts text content
        
        Args:
            image_path (Path): Path to the image file to process
            
        Returns:
            Dict containing:
                - description: Generated image description
                - tags: List of extracted tags
                - text_content: Extracted text content (if any)
                - is_processed: Boolean indicating successful processing
                
        Raises:
            FileNotFoundError: If the image file doesn't exist
            Exception: For any other processing errors
        """
        try:
            logger.info(f"Starting process_image for {image_path}")
            # Ensure image path exists
            if not image_path.exists():
                logger.error(f"Image not found at path: {image_path}")
                raise FileNotFoundError(f"Image not found: {image_path}")

            # Convert image path to string for Ollama
            image_path_str = str(image_path)
            logger.debug(f"Converted path to string: {image_path_str}")

            # Get structured responses using Pydantic models
            logger.info(f"Getting description for image: {image_path}")
            try:
                description_response = await self._get_description(image_path_str)
                logger.debug(f"Successfully got description response: {description_response}")
            except Exception as e:
                logger.error(f"Error getting description: {str(e)}")
                logger.error(f"Description error traceback: {''.join(traceback.format_tb(e.__traceback__))}")
                raise

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
            logger.error(f"Full traceback: {''.join(traceback.format_tb(e.__traceback__))}")
            raise

    async def _get_description(self, image_path: str) -> ImageDescription:
        """
        Get a structured description of the image.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            ImageDescription object containing the generated description
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
            image_path (str): Path to the image file
            
        Returns:
            ImageTags object containing the list of extracted tags
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
            image_path (str): Path to the image file
            
        Returns:
            ImageText object containing:
                - has_text: Boolean indicating if text was found
                - text_content: The extracted text (empty if no text found)
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
            prompt (str): The prompt to send to Ollama
            image_path (str): Path to the image file
            format_schema (dict): JSON schema for the expected response format
            
        Returns:
            str: The raw response from Ollama
            
        Raises:
            Exception: If there's an error communicating with Ollama or processing the response
        """
        try:
            logger.info(f"Starting Ollama query")
            logger.debug(f"Prompt: {prompt[:100]}...")
            logger.debug(f"Image path: {image_path}")
            logger.debug(f"Format schema: {format_schema}")
            
            request_data = {
                'model': self.model_name,
                'messages': [{
                    'role': 'user',
                    'content': prompt,
                    'images': [image_path],
                    'options': {
                        'num_gpu': 41
                    }
                }],
                'format': format_schema
            }
            logger.debug(f"Prepared request data: {json.dumps(request_data, indent=2)}")
            
            logger.info("Sending chat request to Ollama")
            try:
                raw_response = await self.client.chat(**request_data)
                logger.debug(f"Raw response type: {type(raw_response)}")
                logger.debug(f"Raw response dir: {dir(raw_response)}")
                logger.debug(f"Raw response repr: {repr(raw_response)}")
                if hasattr(raw_response, '__dict__'):
                    logger.debug(f"Response __dict__: {raw_response.__dict__}")
            except Exception as chat_error:
                logger.error(f"Error during chat request: {str(chat_error)}")
                logger.error(f"Chat error type: {type(chat_error)}")
                logger.error(f"Chat error traceback: {''.join(traceback.format_tb(chat_error.__traceback__))}")
                raise
            
            logger.info("Processing response")
            try:
                if isinstance(raw_response, dict):
                    logger.debug("Response is a dictionary")
                    content = raw_response['message']['content']
                elif hasattr(raw_response, 'message'):
                    logger.debug("Response has message attribute")
                    content = raw_response.message.content
                else:
                    logger.error(f"Unexpected response format: {type(raw_response)}")
                    raise ValueError(f"Unexpected response format: {type(raw_response)}")
                
                logger.debug(f"Successfully extracted content: {content[:100]}...")
                return content
            except Exception as extract_error:
                logger.error(f"Error extracting content: {str(extract_error)}")
                logger.error(f"Extract error traceback: {''.join(traceback.format_tb(extract_error.__traceback__))}")
                raise
            
        except Exception as e:
            logger.error(f"Ollama query failed with exception type {type(e)}: {str(e)}")
            logger.error(f"Full traceback: {''.join(traceback.format_tb(e.__traceback__))}")
            raise

def update_image_metadata(folder_path: Path, image_path: str, metadata: Dict) -> None:
    """
    Update the metadata file with new image processing results.
    
    Args:
        folder_path (Path): Path to the folder containing the metadata file
        image_path (str): Path to the image relative to the folder
        metadata (Dict): New metadata to store for the image
        
    Raises:
        Exception: If there's an error reading or writing the metadata file
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
