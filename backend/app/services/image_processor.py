"""
Image processing module that uses Ollama vision model to analyze images.
This module provides:
- Image description generation
- Tag extraction
- Text content detection
- Progress tracking
- Error handling
- Ollama service management
"""

import ollama
from pathlib import Path
import logging
from typing import Dict, List, Optional, Any, AsyncGenerator
import json
import subprocess
import time
from backend.app.models.schemas import ImageDescription, ImageTags, ImageText
import hashlib
import traceback
import base64
from PIL import Image
import io
import jsonschema
import os
from ..core.logging import logger
from .storage import file_storage

# Configure logger with module name
logger = logging.getLogger(__name__)

class AsyncResponseGenerator:
    """A class to simulate async iteration for streaming responses."""
    def __init__(self, response_data):
        self.response_data = response_data
        self._index = 0
        logger.debug(f"Initialized AsyncResponseGenerator with {len(response_data)} items")

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self.response_data):
            logger.debug("AsyncResponseGenerator iteration complete")
            raise StopAsyncIteration
        item = self.response_data[self._index]
        self._index += 1
        logger.debug(f"Yielding item {self._index}/{len(self.response_data)}: {item}")
        return item

class ImageProcessor:
    """
    A class that processes images using the Ollama vision model to extract descriptions, tags, and text content.
    
    This class provides:
    1. Asynchronous image processing with progress tracking
    2. Structured output using Pydantic models
    3. Automatic Ollama service management
    4. Graceful error handling and logging
    
    The processing pipeline consists of three sequential steps:
    1. Description generation (33% of progress)
    2. Tag extraction (33% of progress)
    3. Text detection (33% of progress)
    
    Each step yields progress updates scaled to its portion of the total progress.
    
    Attributes:
        model_name (str): Name of the Ollama vision model to use
        stop_check (Optional[callable]): Callback to check if processing should stop
    """
    
    def __init__(self, model_name: str = 'gemma3:4b', stop_check: Optional[callable] = None):
        """
        Initialize the ImageProcessor.
        
        Args:
            model_name (str): Name of the Ollama model to use (default: gemma3:4b)
            stop_check (Optional[callable]): Optional callback to check if processing should be stopped
        """
        self.model_name = model_name
        self.stop_check = stop_check
        logger.info(f"Initializing ImageProcessor with model: {model_name}")
        logger.debug(f"Stop check callback: {'provided' if stop_check else 'None'}")
        self._ensure_ollama_running()

    def _ensure_ollama_running(self):
        """
        Ensure Ollama service is running, start it if not.
        
        This method:
        1. Checks if Ollama is running by making a test request
        2. If not running, starts the Ollama service in the background
        3. Waits for the service to become available
        4. Handles errors and provides detailed logging
        
        Raises:
            TimeoutError: If Ollama service fails to start within timeout
            Exception: For other service-related errors
        """
        try:
            # Try to make a simple request to check if Ollama is running
            ollama.list()
            logger.info("Ollama service is running")
        except Exception as e:
            logger.warning(f"Ollama service not running: {str(e)}")
            logger.info("Attempting to start Ollama service...")
            try:
                # Start Ollama service in the background
                process = subprocess.Popen(['ollama', 'serve'], 
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
                logger.debug(f"Started Ollama process with PID: {process.pid}")
                
                # Wait for service to start (up to 10 seconds)
                start_time = time.time()
                while time.time() - start_time < 10:
                    try:
                        ollama.list()
                        logger.info("Ollama service started successfully")
                        return
                    except Exception as check_error:
                        logger.debug(f"Waiting for Ollama to start: {str(check_error)}")
                        time.sleep(0.5)
                        
                raise TimeoutError("Ollama service failed to start within timeout")
            except Exception as start_error:
                logger.error(f"Failed to start Ollama service: {str(start_error)}")
                logger.error(f"Process output: {process.stdout.read().decode() if process.stdout else 'No output'}")
                logger.error(f"Process error: {process.stderr.read().decode() if process.stderr else 'No error'}")
                raise

    async def process_image(self, image_path: Path):
        """
        Process an image and yield progress updates.
        
        This method orchestrates the complete image processing pipeline:
        1. Validates the image path
        2. Processes the image in three sequential steps
        3. Yields progress updates for each step
        4. Returns the final metadata
        
        The processing steps are:
        1. Get image description (33% of total progress)
        2. Extract tags (33% of total progress)
        3. Detect and extract text (33% of total progress)
        
        For each step, progress updates are scaled to fit within that step's portion
        of the overall progress (e.g., 0-0.33 for step 1, 0.33-0.66 for step 2, etc.)
        
        Args:
            image_path (Path): Path to the image file to process
            
        Yields:
            Dict containing either:
                - {'progress': float} for progress updates (0.0 to 1.0)
                - {'image': Dict} with the final metadata when complete
            
        Raises:
            FileNotFoundError: If the image file doesn't exist
            Exception: For any other processing errors
        """
        try:
            if not image_path.exists():
                logger.error(f"Image not found at path: {image_path}")
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            image_path_str = str(image_path)
            logger.info(f"Starting image processing for: {image_path_str}")

            # Process each aspect of the image with progress tracking
            total_steps = 3  # description, tags, text
            current_step = 0
            
            # Get structured responses using Pydantic models
            logger.info(f"Step {current_step + 1}/{total_steps}: Getting description for image: {image_path}")
            description = None
            async for update in self._get_description(image_path_str):
                if 'content' in update:
                    description = update['content']
                    logger.debug(f"Received description: {description.description}")
                else:
                    # Scale the progress within the current step's range
                    step_progress = update['progress']
                    step_start = current_step / total_steps
                    step_size = 1 / total_steps
                    overall_progress = step_start + (step_progress * step_size)
                    logger.debug(f"Description progress: {overall_progress:.2%}")
                    yield {"progress": overall_progress}
            
            if description is None:
                raise ValueError("Failed to get image description")
            
            current_step += 1
            
            # Get tags
            logger.info(f"Step {current_step + 1}/{total_steps}: Getting tags for image: {image_path}")
            tags = None
            async for update in self._get_tags(image_path_str):
                if 'content' in update:
                    tags = update['content']
                    logger.debug(f"Received tags: {tags.tags}")
                else:
                    # Scale the progress within the current step's range
                    step_progress = update['progress']
                    step_start = current_step / total_steps
                    step_size = 1 / total_steps
                    overall_progress = step_start + (step_progress * step_size)
                    logger.debug(f"Tags progress: {overall_progress:.2%}")
                    yield {"progress": overall_progress}
            
            if tags is None:
                raise ValueError("Failed to get image tags")
            
            current_step += 1
            
            # Get text content
            logger.info(f"Step {current_step + 1}/{total_steps}: Getting text content for image: {image_path}")
            text = None
            async for update in self._get_text_content(image_path_str):
                if 'content' in update:
                    text = update['content']
                    logger.debug(
                        f"Received text content - has_text: {text.has_text}, "
                        f"content: {text.text_content if text.has_text else 'None'}"
                    )
                else:
                    # Scale the progress within the current step's range
                    step_progress = update['progress']
                    step_start = current_step / total_steps
                    step_size = 1 / total_steps
                    overall_progress = step_start + (step_progress * step_size)
                    logger.debug(f"Text content progress: {overall_progress:.2%}")
                    yield {"progress": overall_progress}
            
            if text is None:
                raise ValueError("Failed to get image text content")

            metadata = {
                "description": description.description,
                "tags": tags.tags,
                "text_content": text.text_content if text.has_text else "",
                "is_processed": True
            }
            
            logger.info(f"Completed processing image: {image_path}")
            logger.debug(f"Final metadata: {json.dumps(metadata, indent=2)}")
            yield {"progress": 1.0, "image": metadata}

        except Exception as e:
            logger.error(f"Error processing image {image_path}: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise

    async def _get_description(self, image_path: str):
        """
        Get a structured description of the image.
        
        This method:
        1. Queries Ollama for an image description
        2. Validates the response using Pydantic model
        3. Yields progress updates and final content
        
        Args:
            image_path (str): Path to the image file
            
        Yields:
            Dict containing either:
                - {'progress': float} for progress updates
                - {'content': ImageDescription} for the final description
        """
        async for update in self._query_ollama(
            "Describe this image in one or two sentences.",
            image_path,
            ImageDescription.model_json_schema()
        ):
            if 'content' in update:
                yield {"content": ImageDescription.model_validate(update['content'])}
            else:
                yield update

    async def _get_tags(self, image_path: str):
        """
        Get structured tags for the image.
        
        This method:
        1. Queries Ollama for image tags
        2. Validates the response using Pydantic model
        3. Yields progress updates and final content
        
        Args:
            image_path (str): Path to the image file
            
        Yields:
            Dict containing either:
                - {'progress': float} for progress updates
                - {'content': ImageTags} for the final tags
        """
        async for update in self._query_ollama(
            "List 5-10 relevant tags for this image. Include both objects, artistic style, type of image, color, etc.",
            image_path,
            ImageTags.model_json_schema()
        ):
            if 'content' in update:
                yield {"content": ImageTags.model_validate(update['content'])}
            else:
                yield update

    async def _get_text_content(self, image_path: str):
        """
        Extract structured text content from the image.
        
        This method:
        1. Queries Ollama for text content
        2. Validates the response using Pydantic model
        3. Ensures text_content is empty if no text is found
        4. Yields progress updates and final content
        
        Args:
            image_path (str): Path to the image file
            
        Yields:
            Dict containing either:
                - {'progress': float} for progress updates
                - {'content': ImageText} for the final text content
        """
        async for update in self._query_ollama(
            "Identify if there is visible text in the image. Respond with JSON where 'has_text' is true only if there is actual text visible in the image, and 'text_content' contains the extracted text. If no text is visible, set 'has_text' to false and 'text_content' to empty string.",
            image_path,
            ImageText.model_json_schema()
        ):
            if 'content' in update:
                result = ImageText.model_validate(update['content'])
                # Ensure text_content is empty if has_text is False
                if not result.has_text:
                    result.text_content = ""
                yield {"content": result}
            else:
                yield update

    async def _query_ollama(self, prompt: str, image_path: str, format_schema: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Send a query to Ollama with an image and expect structured output.
        
        This method handles the core interaction with the Ollama API, including:
        1. Setting up the request with the image and format schema
        2. Streaming the response to get real-time progress updates
        3. Parsing the response content into the expected format
        4. Error handling and logging
        
        The streaming response from Ollama includes both progress information
        (eval_count/prompt_eval_count) and content chunks. This method processes
        both types of information and yields appropriate updates.
        
        Args:
            prompt (str): The text prompt to send to Ollama
            image_path (str): Path to the image file to analyze
            format_schema (Dict[str, Any]): JSON schema defining the expected response format
            
        Yields:
            Dict containing either:
                - {'progress': float} for progress updates (0.0 to 1.0)
                - {'content': Dict} for the final structured response
            
        Raises:
            ValueError: If the response format is unexpected
            Exception: For any other API or processing errors
        """
        try:
            logger.info(f"Starting Ollama query for image: {image_path}")
            logger.debug(f"Prompt: {prompt[:100]}...")
            logger.debug(f"Format schema: {json.dumps(format_schema, indent=2)}")
            
            # Prepare the request
            request_data = {
                'model': self.model_name,
                'messages': [{
                    'role': 'user',
                    'content': prompt,
                    'images': [image_path]
                }],
                'format': format_schema,
                'stream': True  # Ensure streaming is enabled
            }
            
            # Get the response
            client = ollama.AsyncClient()
            response = await client.chat(**request_data)
            
            # Process the streaming response
            accumulated_content = ""
            if isinstance(response, dict):
                # Single response
                if 'message' in response and 'content' in response['message']:
                    content = response['message']['content']
                    try:
                        parsed_content = json.loads(content) if isinstance(content, str) else content
                        jsonschema.validate(parsed_content, format_schema)
                        yield {'content': parsed_content}
                    except (json.JSONDecodeError, jsonschema.ValidationError) as e:
                        logger.error(f"Error parsing response content: {e}")
                        raise ValueError(f"Invalid response format: {e}")
            else:
                # Streaming response
                async for chunk in response:
                    # Check for progress information
                    if 'eval_count' in chunk and 'prompt_eval_count' in chunk:
                        progress = chunk['eval_count'] / chunk['prompt_eval_count']
                        yield {'progress': progress}
                        continue

                    # Accumulate content
                    if 'message' in chunk and 'content' in chunk['message']:
                        content = chunk['message']['content']
                        if isinstance(content, dict):
                            # If it's already a dict, validate and yield it
                            try:
                                jsonschema.validate(content, format_schema)
                                yield {'content': content}
                            except jsonschema.ValidationError as e:
                                logger.error(f"Error validating response content: {e}")
                                raise ValueError(f"Invalid response format: {e}")
                        else:
                            # If it's a string, accumulate it
                            accumulated_content += str(content)

                # Try to parse accumulated content if any
                if accumulated_content:
                    try:
                        parsed_content = json.loads(accumulated_content)
                        jsonschema.validate(parsed_content, format_schema)
                        yield {'content': parsed_content}
                    except (json.JSONDecodeError, jsonschema.ValidationError) as e:
                        logger.error(f"Error parsing accumulated content: {e}")
                        raise ValueError(f"Invalid accumulated content format: {e}")

        except Exception as e:
            logger.error(f"Error in Ollama query: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise

async def update_image_metadata(folder_path: Path, image_path: str, metadata: Dict[str, Any]) -> None:
    """
    Update the metadata file with new image processing results.
    
    This method:
    1. Loads existing metadata if available
    2. Updates metadata for the specified image
    3. Saves the updated metadata back to file
    
    Args:
        folder_path (Path): Path to the folder containing the metadata file
        image_path (str): Path to the image relative to the folder
        metadata (Dict[str, Any]): New metadata to store for the image
        
    Raises:
        PermissionError: If metadata file cannot be read/written due to permissions
        StorageError: If there are other storage-related errors
    """
    metadata_file = folder_path / "image_metadata.json"
    logger.info(f"Updating metadata for image: {image_path}")
    
    try:
        # Load existing metadata if available
        all_metadata = {}
        if await file_storage.exists(metadata_file):
            all_metadata = await file_storage.read(metadata_file)
            logger.debug(f"Loaded existing metadata for {len(all_metadata)} images")
        
        # Update the metadata for this image
        all_metadata[image_path] = metadata
        logger.debug(f"Updated metadata for image: {image_path}")
        
        # Save the updated metadata
        await file_storage.write(metadata_file, all_metadata)
        logger.info(f"Saved metadata for {len(all_metadata)} images")
        
    except Exception as e:
        logger.error(f"Error updating metadata: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise
