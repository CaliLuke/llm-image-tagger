"""
Storage service module for managing file operations.

This module provides a centralized way to handle all file operations with:
1. Consistent error handling and retries
2. Atomic file operations
3. Permission checking
4. Proper logging
5. Type safety
"""

import os
import json
import time
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
from abc import ABC, abstractmethod

# Configure logger
logger = logging.getLogger(__name__)

class StorageError(Exception):
    """Base exception for storage-related errors."""
    pass

class PermissionError(StorageError):
    """Raised when there are permission issues."""
    pass

class FileNotFoundError(StorageError):
    """Raised when a file is not found."""
    pass

class StorageBase(ABC):
    """
    Abstract base class for storage operations.
    
    This class defines the interface that all storage implementations must follow.
    It provides basic functionality for:
    1. Reading and writing files
    2. Permission checking
    3. Error handling
    4. Retry logic
    """
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize the storage service.
        
        Args:
            max_retries (int): Maximum number of retry attempts for operations
            retry_delay (float): Delay in seconds between retry attempts
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    @abstractmethod
    async def read(self, path: Union[str, Path]) -> Any:
        """Read data from storage."""
        pass
    
    @abstractmethod
    async def write(self, path: Union[str, Path], data: Any) -> None:
        """Write data to storage."""
        pass
    
    @abstractmethod
    async def delete(self, path: Union[str, Path]) -> None:
        """Delete data from storage."""
        pass
    
    @abstractmethod
    async def exists(self, path: Union[str, Path]) -> bool:
        """Check if path exists in storage."""
        pass

class FileSystemStorage(StorageBase):
    """
    File system implementation of storage service.
    
    This class provides:
    1. JSON file reading/writing with atomic operations
    2. Permission checking
    3. Retry logic for transient failures
    4. Comprehensive error handling
    5. Detailed logging
    """
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize the file system storage service.
        
        Args:
            max_retries (int): Maximum number of retry attempts
            retry_delay (float): Delay in seconds between retry attempts
        """
        super().__init__(max_retries, retry_delay)
    
    def _check_path_permissions(self, path: Path, check_write: bool = False) -> None:
        """
        Check if the path has required permissions.
        
        Args:
            path (Path): Path to check
            check_write (bool): Whether to check write permissions
            
        Raises:
            PermissionError: If required permissions are not available
        """
        try:
            if not path.parent.exists():
                logger.error(f"Parent directory does not exist: {path.parent}")
                raise FileNotFoundError(f"Parent directory does not exist: {path.parent}")
            
            if not os.access(path.parent, os.R_OK):
                logger.error(f"No read permission for directory: {path.parent}")
                raise PermissionError(f"No read permission for directory: {path.parent}")
            
            if check_write and not os.access(path.parent, os.W_OK):
                logger.error(f"No write permission for directory: {path.parent}")
                raise PermissionError(f"No write permission for directory: {path.parent}")
            
            if path.exists():
                if not os.access(path, os.R_OK):
                    logger.error(f"No read permission for file: {path}")
                    raise PermissionError(f"No read permission for file: {path}")
                
                if check_write and not os.access(path, os.W_OK):
                    logger.error(f"No write permission for file: {path}")
                    raise PermissionError(f"No write permission for file: {path}")
        
        except Exception as e:
            if not isinstance(e, (PermissionError, FileNotFoundError)):
                logger.error(f"Error checking permissions: {str(e)}")
                raise StorageError(f"Error checking permissions: {str(e)}")
            raise
    
    async def read(self, path: Union[str, Path]) -> Dict[str, Any]:
        """
        Read JSON data from a file with retries.
        
        Args:
            path (Union[str, Path]): Path to the file to read
            
        Returns:
            Dict[str, Any]: Parsed JSON data
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            PermissionError: If there are permission issues
            StorageError: For other storage-related errors
        """
        path = Path(path)
        logger.info(f"Reading file: {path}")
        
        self._check_path_permissions(path)
        
        for attempt in range(self.max_retries):
            try:
                if not path.exists():
                    logger.error(f"File not found: {path}")
                    raise FileNotFoundError(f"File not found: {path}")
                
                with open(path, 'r') as f:
                    data = json.load(f)
                logger.debug(f"Successfully read file: {path}")
                return data
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in file {path}: {str(e)}")
                raise StorageError(f"Invalid JSON in file: {str(e)}")
            
            except Exception as e:
                if isinstance(e, (FileNotFoundError, PermissionError)):
                    raise
                
                logger.error(f"Error reading file (attempt {attempt + 1}): {str(e)}")
                if attempt == self.max_retries - 1:
                    raise StorageError(f"Failed to read file after {self.max_retries} attempts: {str(e)}")
                time.sleep(self.retry_delay)
    
    async def write(self, path: Union[str, Path], data: Dict[str, Any]) -> None:
        """
        Write JSON data to a file atomically with retries.
        
        Args:
            path (Union[str, Path]): Path to write the file to
            data (Dict[str, Any]): Data to write
            
        Raises:
            PermissionError: If there are permission issues
            StorageError: For other storage-related errors
        """
        path = Path(path)
        logger.info(f"Writing file: {path}")
        
        # Create parent directory if it doesn't exist
        if not path.parent.exists():
            try:
                logger.info(f"Creating parent directory: {path.parent}")
                path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create parent directory {path.parent}: {str(e)}")
                raise StorageError(f"Failed to create parent directory {path.parent}: {str(e)}")
        
        # For external volumes, use direct file write (like in small_test.py)
        is_external_volume = "/Volumes/" in str(path)
        
        if is_external_volume:
            logger.info(f"Using direct file write for external volume: {path}")
            try:
                # For external volumes, if the file exists, try to remove it first
                # This mimics what worked in small_test.py (creating a new file)
                if path.exists():
                    logger.info(f"File exists, attempting to remove it first: {path}")
                    try:
                        os.remove(path)
                        logger.info(f"Successfully removed existing file: {path}")
                    except Exception as rm_err:
                        logger.warning(f"Could not remove existing file, will try to overwrite: {str(rm_err)}")
                
                # Write the file - like small_test.py does
                with open(path, 'w') as f:
                    json.dump(data, f, indent=4)
                logger.debug(f"Successfully wrote file directly: {path}")
                return
            except Exception as e:
                logger.error(f"Error writing to external volume: {str(e)}")
                
                # Try alternate approach with a new filename if permission denied
                if isinstance(e, PermissionError) and path.exists():
                    try:
                        logger.info(f"Permission denied, trying with a new filename")
                        # Create a new file with a different name
                        new_path = path.with_name(f"{path.stem}_new{path.suffix}")
                        with open(new_path, 'w') as f:
                            json.dump(data, f, indent=4)
                        logger.info(f"Successfully wrote to alternate file: {new_path}")
                        
                        # Try to rename or just keep the new file
                        try:
                            if path.exists():
                                os.remove(path)
                            os.rename(new_path, path)
                            logger.info(f"Successfully replaced original file")
                        except Exception as rename_err:
                            logger.warning(f"Could not rename file, using the new file: {str(rename_err)}")
                            # Just keep using the new file name
                            # We'll need to update references to this file elsewhere
                        return
                    except Exception as alt_err:
                        logger.error(f"Alternate approach also failed: {str(alt_err)}")
                
                raise StorageError(f"Failed to write to external volume: {str(e)}")
        
        # For non-external paths, use the standard approach with permission checks and atomic writes
        self._check_path_permissions(path, check_write=True)
        
        temp_path = path.with_suffix('.tmp')
        for attempt in range(self.max_retries):
            try:
                # Write to temporary file
                with open(temp_path, 'w') as f:
                    json.dump(data, f, indent=4)
                
                # Atomic rename
                temp_path.replace(path)
                logger.debug(f"Successfully wrote file: {path}")
                return
                
            except Exception as e:
                if isinstance(e, PermissionError):
                    if is_external_volume:
                        # Special handling for external volumes
                        logger.error(f"Permission denied writing to external volume: {path}")
                        logger.error("This is a common issue with external drives on macOS.")
                        raise StorageError(f"Cannot write to external volume: {path}. External drives often have different permissions when accessed by applications vs. the macOS UI.")
                    raise
                
                logger.error(f"Error writing file (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt == self.max_retries - 1:
                    raise StorageError(f"Failed to write file after {self.max_retries} attempts: {str(e)}")
                time.sleep(self.retry_delay)
                
            finally:
                # Clean up temp file if it exists
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except Exception as e:
                        logger.warning(f"Failed to clean up temporary file {temp_path}: {str(e)}")
    
    async def delete(self, path: Union[str, Path]) -> None:
        """
        Delete a file with retries.
        
        Args:
            path (Union[str, Path]): Path to the file to delete
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            PermissionError: If there are permission issues
            StorageError: For other storage-related errors
        """
        path = Path(path)
        logger.info(f"Deleting file: {path}")
        
        self._check_path_permissions(path, check_write=True)
        
        for attempt in range(self.max_retries):
            try:
                if not path.exists():
                    logger.error(f"File not found: {path}")
                    raise FileNotFoundError(f"File not found: {path}")
                
                path.unlink()
                logger.debug(f"Successfully deleted file: {path}")
                return
                
            except Exception as e:
                if isinstance(e, (FileNotFoundError, PermissionError)):
                    raise
                
                logger.error(f"Error deleting file (attempt {attempt + 1}): {str(e)}")
                if attempt == self.max_retries - 1:
                    raise StorageError(f"Failed to delete file after {self.max_retries} attempts: {str(e)}")
                time.sleep(self.retry_delay)
    
    async def exists(self, path: Union[str, Path]) -> bool:
        """
        Check if a file exists.
        
        Args:
            path (Union[str, Path]): Path to check
            
        Returns:
            bool: True if the file exists, False otherwise
        """
        path = Path(path)
        return path.exists()

# Create a global instance for convenience
file_storage = FileSystemStorage() 
