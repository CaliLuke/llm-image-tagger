import chromadb
from chromadb.utils import embedding_functions
from chromadb.config import Settings
from pathlib import Path
from typing import Dict, List, Optional, Set

from ..core.config import settings
from ..core.logging import logger

class VectorStore:
    """Service for managing the vector database."""
    
    def __init__(self, persist_directory: Optional[str] = None):
        """
        Initialize ChromaDB client with persistence.
        
        Args:
            persist_directory: Directory to persist the vector database
        """
        self.persist_directory = persist_directory or settings.VECTOR_DB_DIR_NAME
        self.client = chromadb.PersistentClient(
            path=self.persist_directory, 
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Use ChromaDB's default embedding function all-MiniLM-L6-v2
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="image_metadata",
            embedding_function=self.embedding_function
        )
        
        logger.info(f"Initialized vector store at {self.persist_directory}")

    def add_or_update_image(self, image_path: str, metadata: Dict) -> None:
        """
        Add or update image metadata in the vector store.
        
        Args:
            image_path: Path to the image
            metadata: Metadata to add or update
            
        Raises:
            Exception: If there is an error adding or updating the metadata
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
                self.collection.update(
                    ids=[image_path],
                    documents=[text_to_embed],
                    metadatas=[meta_dict]
                )
                logger.debug(f"Updated vector store entry for: {image_path}")
            else:  # Document doesn't exist
                self.collection.add(
                    ids=[image_path],
                    documents=[text_to_embed],
                    metadatas=[meta_dict]
                )
                logger.debug(f"Added vector store entry for: {image_path}")
                
            logger.info(f"Successfully added/updated vector store entry for: {image_path}")
            
        except Exception as e:
            logger.error(f"Error adding/updating to vector store: {str(e)}")
            raise

    def delete_image(self, image_path: str) -> None:
        """
        Delete image metadata from the vector store.
        
        Args:
            image_path: Path to the image
            
        Raises:
            Exception: If there is an error deleting the metadata
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
        
        Args:
            folder_path: Path to the folder containing the metadata file
            metadata: Metadata to synchronize
            
        Raises:
            Exception: If there is an error synchronizing the metadata
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
                self.collection.delete(ids=list(ids_to_delete))
                logger.info(f"Deleted {len(ids_to_delete)} entries from vector store")
            
            # Add or update documents from metadata
            for image_path, meta in metadata.items():
                if meta.get("is_processed", False):
                    self.add_or_update_image(image_path, meta)
                
            logger.info("Successfully synchronized vector store with metadata")
            
        except Exception as e:
            logger.error(f"Error synchronizing vector store: {str(e)}")
            raise

    def get_metadata(self, image_path: str) -> Optional[Dict]:
        """
        Retrieve metadata for a specific image.
        
        Args:
            image_path: Path to the image
            
        Returns:
            Metadata for the image or None if not found
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
            return None
        except Exception as e:
            logger.error(f"Error retrieving metadata from vector store: {str(e)}")
            return None 

    def search_images(self, query: str, limit: int = 20) -> List[str]:
        """
        Search for images using vector similarity.
        
        Args:
            query: Search query
            limit: Maximum number of results to return
            
        Returns:
            List of image paths ordered by relevance
        """
        try:
            if not query.strip():
                return []
                
            # Query the collection
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                include=['documents', 'metadatas', 'distances']  # Add distances to results
            )
            
            filtered_results = []
            if results['ids'] and results['distances']:
                logger.debug(f"Search results for query: {query}")
                
                # Filter and collect results with distance < 1.1
                for image_id, distance in zip(results['ids'][0], results['distances'][0]):
                    if distance < 1.1:
                        filtered_results.append(image_id)
                        logger.debug(f"  Included: {image_id} (distance: {distance:.4f})")
                    else:
                        logger.debug(f"  Excluded: {image_id} (distance: {distance:.4f})")
            
            # Return only up to the requested limit
            return filtered_results[:limit]
            
        except Exception as e:
            logger.error(f"Error performing vector search: {str(e)}")
            return [] 
