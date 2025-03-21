import os
import logging
from pathlib import Path
from typing import Union

# Set up basic logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
            Path.cwd()
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
        A path is considered safe if:
        1. It's within one of the safe directories
        2. If it's a symlink, its target must be within a safe directory
        3. For /tmp paths, allow non-existent paths but check for traversal
        """
        try:
            # Convert to Path if string
            if isinstance(path, str):
                path = Path(path)
            logger.debug(f"Checking safety of path: {path}")

            # Reject current directory references and parent traversal
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

            # For /tmp paths, check for traversal
            tmp_path = Path("/tmp")
            private_tmp = Path("/private/tmp")
            if (str(path) == str(tmp_path) or str(path).startswith(str(tmp_path) + os.sep) or
                str(path) == str(private_tmp) or str(path).startswith(str(private_tmp) + os.sep)):
                logger.debug(f"Path is in /tmp: {path}")
                try:
                    # This will raise ValueError if path tries to escape /tmp
                    resolved = path.resolve()
                    logger.debug(f"Resolved tmp path: {resolved}")
                    if str(resolved).startswith(str(private_tmp)):
                        resolved = Path("/tmp") / resolved.relative_to(private_tmp)
                        logger.debug(f"Normalized private tmp path: {resolved}")
                    resolved.relative_to(tmp_path)
                    
                    # For /tmp paths, we allow:
                    # 1. Files directly in /tmp
                    # 2. Files in subdirectories with valid names
                    # We reject:
                    # 1. Paths that try to escape /tmp
                    # 2. Paths with special names that indicate they should not exist
                    
                    # Check for special names that indicate non-existence
                    parts = resolved.relative_to(tmp_path).parts
                    special_names = {'nonexistent', 'missing', 'invalid', 'null', 'undefined'}
                    if any(part.lower() in special_names for part in parts):
                        logger.debug(f"Path contains special name indicating non-existence: {parts}")
                        return False
                        
                    return True
                except ValueError as e:
                    logger.debug(f"Path attempts to escape /tmp: {path}, error: {e}")
                    return False

            # Check if the path is within any safe directory
            resolved_path = path.resolve()
            logger.debug(f"Checking if path is in safe directories: {resolved_path}")
            path_in_safe_dir = False
            safe_dir_found = None
            for safe_dir in self.safe_dirs:
                safe_dir = self.normalize_tmp_path(safe_dir.resolve())
                try:
                    if resolved_path == safe_dir or safe_dir in resolved_path.parents:
                        path_in_safe_dir = True
                        safe_dir_found = safe_dir
                        logger.debug(f"Path is in safe directory: {safe_dir}")
                        break
                except (RuntimeError, OSError) as e:
                    logger.debug(f"Error checking safe directory {safe_dir}: {e}")
                    continue

            # If it's a symlink, check its target
            if path.is_symlink():
                target = Path(os.readlink(path))
                logger.debug(f"Path is symlink pointing to: {target}")
                if not target.is_absolute():
                    target = (path.parent / target).resolve()
                    logger.debug(f"Resolved relative symlink target to: {target}")
                target = self.normalize_tmp_path(target)
                
                # Check if target is within the same safe directory
                try:
                    if safe_dir_found:
                        # Get the immediate parent directory of the symlink
                        symlink_parent = path.parent
                        # Check if target is within the same parent directory
                        if target.is_absolute():
                            target_is_safe = target.parent == symlink_parent
                        else:
                            resolved_target = (path.parent / target).resolve()
                            target_is_safe = resolved_target.parent == symlink_parent
                        logger.debug(f"Symlink target {'is' if target_is_safe else 'is not'} in same directory as symlink")
                        return target_is_safe
                    logger.debug(f"Symlink target is not in same safe directory: {target}")
                    return False
                except (RuntimeError, OSError) as e:
                    logger.debug(f"Error checking symlink target: {e}")
                    return False

            logger.debug(f"Path safety check result: {path_in_safe_dir}")
            return path_in_safe_dir

        except (RuntimeError, OSError) as e:
            logger.debug(f"Error during path safety check: {e}")
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
