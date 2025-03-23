"""
Vector store module for managing image metadata using ChromaDB.
This module provides:
- Vector-based image search using embeddings
- Metadata persistence and synchronization
- Image metadata management
- Similarity-based search with configurable thresholds
"""

import chromadb
from chromadb.utils import embedding_functions
from chromadb.config import Settings
from pathlib import Path
from typing import Dict, List, Optional
import logging
import traceback
import json
import time

# Configure logger with module name
logger = logging.getLogger(__name__)

class VectorStore:
    """
    A class that manages image metadata using ChromaDB for vector-based search.
    
    This class provides:
    1. Vector-based image search using embeddings
    2. Persistent storage of image metadata
    3. Synchronization with metadata files
    4. Similarity-based search with configurable thresholds
    
    The class uses ChromaDB's default embedding function (all-MiniLM-L6-v2)
    to convert text descriptions into vectors for similarity search.
    
    Attributes:
        client (chromadb.PersistentClient): ChromaDB client instance
        embedding_function (embedding_functions.DefaultEmbeddingFunction): Function for text embedding
        collection (chromadb.Collection): Collection for storing image metadata
    """
    
    def __init__(self, persist_directory: str = ".vectordb"):
        """
        Initialize ChromaDB client with persistence.
        
        This method:
        1. Creates a persistent ChromaDB client
        2. Initializes the default embedding function
        3. Gets or creates the image metadata collection
        4. Handles initialization errors
        
        Args:
            persist_directory (str): Directory for storing ChromaDB data (default: ".vectordb")
            
        Raises:
            Exception: If initialization fails after retries
        """
        logger.info(f"Initializing VectorStore with persist directory: {persist_directory}")
        max_retries = 3
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                # Ensure the directory exists
                Path(persist_directory).mkdir(parents=True, exist_ok=True)
                
                # Create ChromaDB client with explicit settings
                self.client = chromadb.PersistentClient(
                    path=persist_directory,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True,
                        is_persistent=True
                    )
                )
                logger.debug("Created ChromaDB PersistentClient")
                
                # Use ChromaDB's default embedding function all-MiniLM-L6-v2
                self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
                logger.debug("Initialized default embedding function")
                
                # Get or create collection with retries
                collection_created = False
                collection_retries = 3
                
                while not collection_created and collection_retries > 0:
                    try:
                        self.collection = self.client.get_or_create_collection(
                            name="image_metadata",
                            embedding_function=self.embedding_function
                        )
                        collection_created = True
                        logger.debug("Successfully created/got collection")
                    except Exception as ce:
                        collection_retries -= 1
                        if collection_retries == 0:
                            raise ce
                        logger.warning(f"Retrying collection creation. Attempts left: {collection_retries}")
                
                # Verify the collection is properly initialized
                if not self.collection:
                    raise RuntimeError("Collection initialization failed")
                
                # Test the collection with a simple operation
                test_id = "__test_init__"
                try:
                    self.collection.add(
                        ids=[test_id],
                        documents=["test document"],
                        metadatas=[{"test": "true"}]
                    )
                    self.collection.delete(ids=[test_id])
                    logger.debug("Successfully tested collection operations")
                except Exception as te:
                    raise RuntimeError(f"Collection operation test failed: {str(te)}")
                
                logger.info("Successfully initialized VectorStore")
                return
                
            except Exception as e:
                last_error = e
                retry_count += 1
                logger.warning(f"Initialization attempt {retry_count} failed: {str(e)}")
                if retry_count < max_retries:
                    time.sleep(1)  # Wait before retrying
        
        # If we get here, all retries failed
        error_msg = f"Failed to initialize VectorStore after {max_retries} attempts. Last error: {str(last_error)}"
        logger.error(error_msg)
        logger.error(f"Error type: {type(last_error)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise RuntimeError(error_msg)

    async def add_or_update_image(self, image_path: str, metadata: Dict) -> None:
        """
        Add or update image metadata in the vector store.
        
        This method:
        1. Combines text fields for embedding
        2. Prepares metadata for storage
        3. Updates existing entry or creates new one
        
        Args:
            image_path (str): Path to the image file
            metadata (Dict): Image metadata including description, tags, and text content
            
        Raises:
            Exception: If there's an error adding/updating the vector store entry
        """
        try:
            logger.info(f"Adding/updating vector store entry for: {image_path}")
            logger.debug(f"Input metadata: {json.dumps(metadata, indent=2)}")
            
            # Combine all text fields for embedding
            text_to_embed = f"{metadata.get('description', '')} {' '.join(metadata.get('tags', []))} {metadata.get('text_content', '')}"
            logger.debug(f"Combined text for embedding: {text_to_embed}")
            
            # Prepare metadata dict
            meta_dict = {
                "description": metadata.get("description", ""),
                "tags": ",".join(metadata.get("tags", [])),  # ChromaDB metadata must be string
                "text_content": metadata.get("text_content", ""),
                "is_processed": str(metadata.get("is_processed", False))  # Convert bool to string
            }
            logger.debug(f"Prepared metadata dict: {json.dumps(meta_dict, indent=2)}")
            
            # Check if document exists
            results = self.collection.get(
                ids=[image_path],
                include=['documents', 'metadatas']
            )
            
            if results and results['ids']:  # Document exists
                logger.debug(f"Document exists, updating: {image_path}")
                self.collection.update(
                    ids=[image_path],
                    documents=[text_to_embed],
                    metadatas=[meta_dict]
                )
            else:  # Document doesn't exist
                logger.debug(f"Document doesn't exist, adding new: {image_path}")
                self.collection.add(
                    ids=[image_path],
                    documents=[text_to_embed],
                    metadatas=[meta_dict]
                )
                
            logger.info(f"Successfully added/updated vector store entry for: {image_path}")
            
        except Exception as e:
            logger.error(f"Error adding/updating to vector store: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise

    def delete_image(self, image_path: str) -> None:
        """
        Delete image metadata from the vector store.
        
        This method:
        1. Deletes the document with the given image path
        2. Handles deletion errors
        
        Args:
            image_path (str): Path to the image file to delete
            
        Raises:
            Exception: If deletion fails
        """
        try:
            logger.info(f"Deleting vector store entry for: {image_path}")
            self.collection.delete(ids=[image_path])
            logger.info(f"Successfully deleted vector store entry for: {image_path}")
        except Exception as e:
            logger.error(f"Error deleting from vector store: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise

    async def sync_with_metadata(self, folder_path: Path, metadata: Dict[str, Dict]) -> None:
        """
        Synchronize vector store with metadata JSON.
        
        This method:
        1. Gets existing documents in vector store
        2. Gets documents from metadata
        3. Deletes documents not in metadata
        4. Adds or updates documents from metadata
        
        Args:
            folder_path (Path): Path to the folder containing metadata
            metadata (Dict[str, Dict]): Dictionary of image metadata
            
        Raises:
            Exception: If synchronization fails
        """
        try:
            logger.info(f"Starting vector store sync for folder: {folder_path}")
            logger.debug(f"Metadata entries to sync: {len(metadata)}")
            
            # Get all existing documents in vector store
            existing_docs = self.collection.get()
            existing_ids = set(existing_docs['ids']) if existing_docs else set()
            logger.debug(f"Existing documents in vector store: {len(existing_ids)}")
            
            # Get all ids from metadata
            metadata_ids = set(metadata.keys())
            logger.debug(f"Documents in metadata: {len(metadata_ids)}")
            
            # Delete documents that are in vector store but not in metadata
            ids_to_delete = existing_ids - metadata_ids
            if ids_to_delete:
                logger.info(f"Deleting {len(ids_to_delete)} documents not in metadata")
                self.collection.delete(ids=list(ids_to_delete))
            
            # Add or update documents from metadata
            for image_path, meta in metadata.items():
                await self.add_or_update_image(image_path, meta)
                
            logger.info("Successfully synchronized vector store with metadata")
            
        except Exception as e:
            logger.error(f"Error synchronizing vector store: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise

    def get_metadata(self, image_path: str) -> Optional[Dict]:
        """
        Retrieve metadata for a specific image.
        
        This method:
        1. Retrieves the document with the given image path
        2. Processes the metadata into the expected format
        3. Handles missing metadata
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            Optional[Dict]: Processed metadata if found, None otherwise
        """
        try:
            logger.info(f"Retrieving metadata for: {image_path}")
            result = self.collection.get(ids=[image_path])
            if result and result['metadatas']:
                metadata = result['metadatas'][0]
                processed_metadata = {
                    "description": metadata.get("description", ""),
                    "tags": metadata.get("tags", "").split(",") if metadata.get("tags") else [],
                    "text_content": metadata.get("text_content", ""),
                    "is_processed": metadata.get("is_processed", "False") == "True"
                }
                logger.debug(f"Retrieved metadata: {json.dumps(processed_metadata, indent=2)}")
                return processed_metadata
            logger.debug(f"No metadata found for: {image_path}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving metadata from vector store: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None 

    def search_images(self, query: str, limit: int = 5) -> List[str]:
        """
        Search for images using vector similarity.
        
        This method:
        1. Performs vector similarity search
        2. Filters results based on distance threshold
        3. Returns ordered list of image paths
        
        The search uses a balanced threshold of 0.9 to filter results.
        Lower distances indicate better matches.
        
        Args:
            query (str): Text query to search for
            limit (int): Maximum number of results to return (default: 5)
            
        Returns:
            List[str]: List of image paths ordered by relevance
        """
        try:
            logger.info(f"Starting vector search for query: '{query}' (limit: {limit})")
            
            # Handle empty or invalid queries
            if not query or not isinstance(query, str):
                logger.debug("Empty or invalid query, returning empty results")
                return []
            
            # Query the collection
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                include=['documents', 'metadatas', 'distances']
            )
            
            filtered_results = []
            if results['ids'] and results['distances']:
                logger.debug("Raw vector search results:")
                
                # Filter and collect results with distance < 0.9 (balanced threshold)
                for image_id, distance, metadata in zip(results['ids'][0], results['distances'][0], results['metadatas'][0]):
                    logger.debug(f"  Image: {image_id}")
                    logger.debug(f"  Distance: {distance:.4f}")
                    logger.debug(f"  Description: {metadata.get('description', '')}")
                    logger.debug(f"  Tags: {metadata.get('tags', '')}")
                    
                    if distance < 0.9:  # Balanced threshold
                        filtered_results.append(image_id)
                        logger.debug(f"  Status: Included (distance {distance:.4f} < 0.9)")
                    else:
                        logger.debug(f"  Status: Excluded (distance {distance:.4f} >= 0.9)")
                    logger.debug("  ---")
            else:
                logger.debug("No results from vector search")
            
            logger.info(f"Vector search completed. Found {len(filtered_results)} results within distance threshold")
            logger.debug(f"Final results: {filtered_results}")
            # Return only up to the requested limit
            return filtered_results[:limit]
            
        except Exception as e:
            logger.error(f"Error performing vector search: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return []
