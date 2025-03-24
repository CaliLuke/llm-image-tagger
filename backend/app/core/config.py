import os
from pathlib import Path
from typing import Union
from .logging import logger

class PathConfig:
    """Configuration for path handling and validation."""
    
    def __init__(self):
        """Initialize path configuration."""
        self.project_root = Path.cwd()
        self.data_dir = self.project_root / "data"
        self.temp_dir = self.project_root / "temp"
        
        # Create directories if they don't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Safe directories
        self.safe_dirs = [
            self.project_root,
            self.data_dir,
            self.temp_dir,
            Path("/tmp"),
            Path("/private/tmp"),
            Path.home(),
            Path.cwd(),
            Path("/Volumes"),  # Add /Volumes to allow navigation to external drives
            Path("/Volumes/Macintosh HD")  # Also add Macintosh HD specifically
        ]
    
    def add_safe_dir(self, directory: Path):
        """Add a directory to the list of safe directories."""
        self.safe_dirs.append(directory)
    
    def normalize_path(self, path: Union[str, Path]) -> Path:
        """Convert a path string to a resolved Path object."""
        if isinstance(path, str):
            path = Path(path)
        
        try:
            resolved = path.resolve()
            if not resolved.exists():
                raise ValueError(f"Path does not exist: {path}")
            return resolved
        except (RuntimeError, OSError) as e:
            raise ValueError(f"Failed to resolve path: {e}")
    
    def normalize_tmp_path(self, path: Path) -> Path:
        """Normalize /private/tmp to /tmp on macOS."""
        path_str = str(path)
        if path_str.startswith("/private/tmp"):
            return Path("/tmp") / path_str[12:].lstrip("/")
        return path
    
    def is_within_dir(self, path: Path, directory: Path) -> bool:
        """Check if a path is within a directory."""
        try:
            resolved_path = self.normalize_tmp_path(path.resolve())
            resolved_dir = self.normalize_tmp_path(directory.resolve())
            
            # Check if path is the directory or is within it
            try:
                resolved_path.relative_to(resolved_dir)
                return True
            except ValueError:
                return False
        except (RuntimeError, OSError):
            return False
    
    def is_safe_path(self, path: Union[str, Path]) -> bool:
        """
        Check if a path is safe to access.
        We're being permissive with path access but still protecting critical system directories.
        """
        try:
            # Convert to Path if string
            if isinstance(path, str):
                path = Path(path)
            logger.debug(f"Checking safety of path: {path}")

            # Reject current directory references and parent traversal in path parts
            if path.name == "." or str(path) == "." or ".." in path.parts:
                logger.debug(f"Rejecting path with . or .. references: {path}")
                return False

            # First normalize /private/tmp to /tmp
            path = self.normalize_tmp_path(path)
            logger.debug(f"Normalized path: {path}")

            # If it's a relative path, make it absolute from current directory
            if not path.is_absolute():
                path = Path.cwd() / path
                logger.debug(f"Made relative path absolute: {path}")

            # Get resolved path for better comparisons
            resolved_path = path.resolve()
            path_str = str(resolved_path)
            logger.debug(f"Resolved path: {path_str}")
            
            # Allow access to temp folders
            temp_paths = [
                '/tmp',
                '/private/tmp',
                '/var/folders',  # macOS temp folders
                '/private/var/folders'  # macOS temp folders
            ]
            for temp_path in temp_paths:
                if path_str.startswith(temp_path):
                    logger.debug(f"Allowing access to temp path: {path_str}")
                    return True
                    
            # Always allow access to home directory
            home_dir = str(Path.home())
            if path_str.startswith(home_dir):
                logger.debug(f"Allowing access to home directory path: {path_str}")
                return True
                
            # Always allow access to the project directory
            if path_str.startswith(str(self.project_root)):
                logger.debug(f"Allowing access to project directory path: {path_str}")
                return True
                
            # Allow access to Volumes for external drives
            if path_str.startswith('/Volumes'):
                logger.debug(f"Allowing access to Volumes path: {path_str}")
                return True
                
            # Define restricted system paths 
            restricted_paths = [
                # Base system directories
                Path("/System"),
                Path("/private/System"),
                Path("/usr"),
                Path("/private/usr"),
                Path("/bin"),
                Path("/private/bin"),
                Path("/sbin"),
                Path("/private/sbin"),
                Path("/etc"),
                Path("/private/etc"),
                Path("/var"),
                Path("/private/var"),
                # Specific files for test compatibility
                Path("/etc/passwd"),
                Path("/private/etc/passwd"),
                Path("/etc/hosts"),
                Path("/private/etc/hosts")
            ]
            
            # Handle symlinks specially
            if path.is_symlink():
                try:
                    target = Path(os.readlink(path))
                    logger.debug(f"Path is symlink pointing to: {target}")
                    
                    # If target is relative, make it absolute from symlink's parent
                    if not target.is_absolute():
                        target = (path.parent / target).resolve()
                    
                    # Check if the target of the symlink is safe
                    # Since we've already done the temp directory check above,
                    # we can call is_safe_path recursively on the target
                    return self.is_safe_path(target)
                    
                except (RuntimeError, OSError) as e:
                    logger.warning(f"Error checking symlink target: {e}")
                    # Default to allow for symlinks we can't evaluate, as long as
                    # the symlink itself is in a safe location (which we already checked above)
                    return True
            
            # First, check if path exactly matches a restricted path
            for restricted in restricted_paths:
                restricted_str = str(restricted)
                if path_str == restricted_str:
                    logger.debug(f"Path matches restricted path: {restricted_str}")
                    return False
            
            # Then check if path is within a restricted directory
            for restricted in restricted_paths:
                restricted_str = str(restricted)
                # Check if path starts with the restricted directory path followed by a separator
                # This handles subdirectories properly
                if path_str.startswith(restricted_str + os.sep):
                    logger.debug(f"Path is within restricted directory: {restricted_str}")
                    return False
            
            # For all other paths, allow access
            logger.debug(f"Path allowed: {path_str}")
            return True

        except (RuntimeError, OSError) as e:
            logger.warning(f"Error during path safety check: {e}")
            return False
    
    def make_relative_to_root(self, path: Union[str, Path]) -> Path:
        """Convert a path to be relative to the project root."""
        if isinstance(path, str):
            path = Path(path)
        
        try:
            resolved = path.resolve()
            resolved = self.normalize_tmp_path(resolved)
            
            if self.project_root in resolved.parents:
                return resolved.relative_to(self.project_root)
            return path
        except (ValueError, RuntimeError):
            return path
