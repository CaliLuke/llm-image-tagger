"""
Vector store module for managing image metadata and similarity search.
This module uses ChromaDB to store and retrieve vector embeddings of image metadata.
"""

import chromadb
from chromadb.utils import embedding_functions
from chromadb.config import Settings
from pathlib import Path
from typing import Dict, List, Optional
import logging

# Configure logger with module name
logger = logging.getLogger(__name__)

class VectorStore:
    """
    Manages vector storage and similarity search for image metadata.
    
    This class uses ChromaDB to:
    1. Store vector embeddings of image metadata
    2. Perform similarity searches
    3. Maintain synchronization with metadata files
    
    Attributes:
        client (PersistentClient): ChromaDB client instance
        embedding_function (DefaultEmbeddingFunction): Function to generate embeddings
        collection (Collection): ChromaDB collection for storing vectors
    """
    
    def __init__(self, persist_directory: str = ".vectordb"):
        """
        Initialize ChromaDB client with persistence.
        
        Args:
            persist_directory (str): Directory to store the vector database
        """
        self.client = chromadb.PersistentClient(path=persist_directory, settings=Settings(anonymized_telemetry=False))
        
        # Use ChromaDB's default embedding function all-MiniLM-L6-v2
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="image_metadata",
            embedding_function=self.embedding_function
        )
        logger.info(f"Initialized VectorStore with persistence directory: {persist_directory}")

    def add_or_update_image(self, image_path: str, metadata: Dict) -> None:
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
            # Combine all text fields for embedding
            text_to_embed = f"{metadata.get('description', '')} {' '.join(metadata.get('tags', []))} {metadata.get('text_content', '')}"
            
            # Prepare metadata dict
            meta_dict = {
                "description": metadata.get("description", ""),
                "tags": ",".join(metadata.get("tags", [])),  # ChromaDB metadata must be string
                "text_content": metadata.get("text_content", ""),
                "is_processed": str(metadata.get("is_processed", False))  # Convert bool to string
            }
            
            # Check if document exists
            results = self.collection.get(
                ids=[image_path],
                include=['documents', 'metadatas']
            )
            
            if results and results['ids']:  # Document exists
                logger.debug(f"Updating existing vector store entry for: {image_path}")
                self.collection.update(
                    ids=[image_path],
                    documents=[text_to_embed],
                    metadatas=[meta_dict]
                )
            else:  # Document doesn't exist
                logger.debug(f"Creating new vector store entry for: {image_path}")
                self.collection.add(
                    ids=[image_path],
                    documents=[text_to_embed],
                    metadatas=[meta_dict]
                )
                
            logger.info(f"Successfully added/updated vector store entry for: {image_path}")
            
        except Exception as e:
            logger.error(f"Error adding/updating to vector store: {str(e)}")
            raise

    def delete_image(self, image_path: str) -> None:
        """
        Delete image metadata from the vector store.
        
        Args:
            image_path (str): Path to the image file to delete
            
        Raises:
            Exception: If there's an error deleting the vector store entry
        """
        try:
            self.collection.delete(ids=[image_path])
            logger.info(f"Successfully deleted vector store entry for: {image_path}")
        except Exception as e:
            logger.error(f"Error deleting from vector store: {str(e)}")
            raise

    def sync_with_metadata(self, folder_path: Path, metadata: Dict[str, Dict]) -> None:
        """
        Synchronize vector store with metadata JSON.
        
        This method:
        1. Gets all existing documents in vector store
        2. Deletes documents that are in vector store but not in metadata
        3. Adds or updates documents from metadata
        
        Args:
            folder_path (Path): Path to the folder containing metadata
            metadata (Dict[str, Dict]): Dictionary of image metadata
            
        Raises:
            Exception: If there's an error synchronizing the vector store
        """
        try:
            # Get all existing documents in vector store
            existing_docs = self.collection.get()
            existing_ids = set(existing_docs['ids']) if existing_docs else set()
            
            # Get all ids from metadata
            metadata_ids = set(metadata.keys())
            
            # Delete documents that are in vector store but not in metadata
            ids_to_delete = existing_ids - metadata_ids
            if ids_to_delete:
                logger.info(f"Deleting {len(ids_to_delete)} stale entries from vector store")
                self.collection.delete(ids=list(ids_to_delete))
            
            # Add or update documents from metadata
            for image_path, meta in metadata.items():
                self.add_or_update_image(image_path, meta)
                
            logger.info("Successfully synchronized vector store with metadata")
            
        except Exception as e:
            logger.error(f"Error synchronizing vector store: {str(e)}")
            raise

    def get_metadata(self, image_path: str) -> Optional[Dict]:
        """
        Retrieve metadata for a specific image.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            Optional[Dict]: Image metadata if found, None otherwise
        """
        try:
            result = self.collection.get(ids=[image_path])
            if result and result['metadatas']:
                metadata = result['metadatas'][0]
                return {
                    "description": metadata.get("description", ""),
                    "tags": metadata.get("tags", "").split(",") if metadata.get("tags") else [],
                    "text_content": metadata.get("text_content", ""),
                    "is_processed": metadata.get("is_processed", "False") == "True"
                }
            logger.debug(f"No metadata found for image: {image_path}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving metadata from vector store: {str(e)}")
            return None 

    def search_images(self, query: str, limit: int = 5) -> List[str]:
        """
        Search for images using vector similarity.
        
        This method:
        1. Queries the collection using the provided search query
        2. Filters results based on similarity threshold
        3. Returns a list of image paths ordered by relevance
        
        Args:
            query (str): Search query text
            limit (int): Maximum number of results to return
            
        Returns:
            List[str]: List of image paths ordered by relevance
        """
        try:
            # Query the collection
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                include=['documents', 'metadatas', 'distances']  # Add distances to results
            )
            
            filtered_results = []
            if results['ids'] and results['distances']:
                logger.debug("Search results for query: %s", query)
                
                # Filter and collect results with distance < 1.1
                for image_id, distance in zip(results['ids'][0], results['distances'][0]):
                    if distance < 1.1:
                        filtered_results.append(image_id)
                        logger.debug(f"  Included: {image_id} (distance: {distance:.4f})")
                    else:
                        logger.debug(f"  Excluded: {image_id} (distance: {distance:.4f})")
            
            # Return only up to the requested limit
            logger.info(f"Found {len(filtered_results)} matching images for query: {query}")
            return filtered_results[:limit]
            
        except Exception as e:
            logger.error(f"Error performing vector search: {str(e)}")
            return []
