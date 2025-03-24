import pytest
from pathlib import Path
from backend.app.core.settings import settings
from backend.app.core.config import PathConfig
import logging
import os

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

def test_settings_defaults():
    """Test default settings values."""
    logger.info("Testing default settings values")
    
    logger.debug("Checking API settings")
    assert settings.API_HOST == "127.0.0.1"
    assert settings.API_PORT == 8000
    
    logger.debug("Checking Ollama settings")
    assert settings.OLLAMA_MODEL == "gemma3:4b"
    assert settings.OLLAMA_HOST == "http://localhost:11434"
    
    logger.debug("Checking folder settings")
    assert settings.DEFAULT_FOLDER_PATH is None
    assert settings.SUPPORTED_EXTENSIONS == [".png", ".jpg", ".jpeg", ".webp"]
    
    logger.debug("Checking vector store settings")
    assert "vectordb" in settings.VECTOR_DB_DIR_NAME
    assert settings.LOG_LEVEL == "INFO"
    
    logger.info("All default settings verified successfully")

def test_path_config_initialization(path_config):
    """Test that PathConfig initializes with correct directories"""
    logger.info("Testing PathConfig initialization")
    
    logger.debug("Verifying directory existence")
    assert path_config.project_root.exists()
    assert path_config.data_dir.exists()
    assert path_config.temp_dir.exists()
    
    logger.debug("Verifying directory types")
    assert path_config.data_dir.is_dir()
    assert path_config.temp_dir.is_dir()
    
    logger.info("PathConfig initialization verified successfully")

def test_normalize_path(path_config, tmp_path):
    """Test path normalization"""
    logger.info("Testing path normalization")
    
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.touch()
    logger.debug(f"Created test file at {test_file}")
    
    # Test with string path
    logger.debug("Testing string path normalization")
    normalized = path_config.normalize_path(str(test_file))
    assert normalized == test_file.resolve()
    
    # Test with Path object
    logger.debug("Testing Path object normalization")
    normalized = path_config.normalize_path(test_file)
    assert normalized == test_file.resolve()
    
    # Test with non-existent path
    logger.debug("Testing non-existent path normalization")
    with pytest.raises(ValueError):
        path_config.normalize_path("/nonexistent/path")
    
    logger.info("Path normalization tests completed successfully")

def test_path_safety(path_config):
    """Test path safety checks with various scenarios"""
    logger.info("Testing path safety checks")
    
    home = Path.home()
    project_root = path_config.project_root
    tmp = Path("/tmp")
    
    # Test valid paths
    logger.debug("Testing valid paths")
    assert path_config.is_safe_path(home / "test.txt")
    assert path_config.is_safe_path(project_root / "data" / "test.txt")
    assert path_config.is_safe_path(Path("test.txt"))  # Relative path
    assert path_config.is_safe_path(tmp / "test.txt")  # Temp directory
    assert path_config.is_safe_path(Path("/Volumes"))  # External volumes
    assert path_config.is_safe_path(Path("/Volumes/Macintosh HD"))  # System volume
    assert path_config.is_safe_path(Path("/Users"))  # Users directory
    
    # Test invalid paths - system directories that should be protected
    logger.debug("Testing invalid paths")
    # Test with direct string comparison to make sure our restricted paths are properly matched
    # First ensure that the restricted paths list includes what we need
    restricted_paths = [
        Path("/System"), Path("/usr"), Path("/bin"), Path("/sbin"), 
        Path("/etc"), Path("/var"), Path("/etc/passwd"), Path("/etc/hosts")
    ]
    for restricted in restricted_paths:
        path_str = str(restricted)
        test_path = Path(path_str)
        assert not path_config.is_safe_path(test_path), f"Path {test_path} should be restricted"
    
    # Test paths within restricted directories
    assert not path_config.is_safe_path(Path("/usr/bin/python"))
    assert not path_config.is_safe_path(Path("/var/log/system.log"))
    
    # Test edge cases
    logger.debug("Testing edge cases")
    assert not path_config.is_safe_path(Path(".."))
    assert not path_config.is_safe_path(Path("."))
    assert not path_config.is_safe_path(Path("test/../../etc/passwd"))
    assert path_config.is_safe_path(home / "folder_with_dots...")
    assert path_config.is_safe_path(project_root / "file.with.dots.txt")
    
    # Test non-existent paths - these should be allowed if not in system dirs
    logger.debug("Testing non-existent paths")
    assert path_config.is_safe_path(home / "nonexistent" / "file.txt")
    assert path_config.is_safe_path(Path("/Volumes/NonExistentDrive"))
    assert not path_config.is_safe_path(Path("/var/nonexistent"))
    
    # Test current directory variants
    logger.debug("Testing current directory variants")
    assert not path_config.is_safe_path(Path("./././../test.txt"))
    assert path_config.is_safe_path(Path("./test.txt").resolve())
    
    logger.info("Path safety tests completed successfully")

def test_temp_directory_safety(path_config):
    """Test safety of temp directory paths"""
    logger.info("Testing temp directory safety")
    
    tmp = Path("/tmp")
    
    # Valid temporary paths - these should be allowed regardless
    logger.debug("Testing valid temp paths")
    assert path_config.is_safe_path(tmp / "test.txt")
    assert path_config.is_safe_path(tmp / "processing" / "image.jpg")

    # Invalid paths - paths that attempt to traverse outside temp or to system locations
    logger.debug("Testing invalid temp paths")
    assert not path_config.is_safe_path(tmp / ".." / "var" / "log" / "test.txt")
    assert not path_config.is_safe_path(tmp / "subdir" / ".." / ".." / "etc" / "passwd")
    
    # Non-existent paths - should now be allowed as long as they're not in system directories
    logger.debug("Testing non-existent temp paths")
    assert path_config.is_safe_path(tmp / "nonexistent" / "test.txt")
    
    logger.info("Temp directory safety tests completed successfully")

def test_symlink_safety(path_config, tmp_path):
    """Test safety of symlinks"""
    logger.info("Testing symlink safety")
    
    # Create a safe target file
    safe_target = tmp_path / "safe_target.txt"
    safe_target.touch()
    
    # Create a basic symlink in the same directory
    basic_symlink = tmp_path / "basic_symlink.txt"
    os.symlink(safe_target, basic_symlink)
    logger.debug(f"Created basic symlink: {basic_symlink} -> {safe_target}")
    
    # Create an unsafe target path
    unsafe_target = Path("/etc/passwd")
    
    # Create a symlink to an unsafe target
    unsafe_symlink = tmp_path / "unsafe_symlink.txt"
    if not unsafe_target.exists():
        unsafe_target = Path("/etc/hosts")  # Fallback target that should exist
    
    try:
        os.symlink(unsafe_target, unsafe_symlink)
        logger.debug(f"Created unsafe symlink: {unsafe_symlink} -> {unsafe_target}")
    except PermissionError:
        logger.warning(f"Could not create symlink to {unsafe_target} due to permissions, skipping test")
        unsafe_symlink = None
    
    # Create a recursive symlink
    recursive_symlink = tmp_path / "recursive_symlink.txt"
    try:
        os.symlink(recursive_symlink, recursive_symlink)
        logger.debug(f"Created recursive symlink: {recursive_symlink} -> {recursive_symlink}")
    except (PermissionError, OSError):
        logger.warning("Could not create recursive symlink, skipping test")
        recursive_symlink = None
    
    # Create a traversal symlink
    traversal_symlink = tmp_path / "traversal_symlink.txt"
    try:
        os.symlink(tmp_path / ".." / ".." / "etc" / "passwd", traversal_symlink)
        logger.debug(f"Created traversal symlink: {traversal_symlink} -> ../../../etc/passwd")
    except (PermissionError, OSError):
        logger.warning("Could not create traversal symlink, skipping test")
        traversal_symlink = None
    
    # Test basic symlink - should be allowed
    assert path_config.is_safe_path(basic_symlink)
    
    # Test unsafe symlink - should now be checked based on the target's path
    if unsafe_symlink and unsafe_symlink.exists():
        # Should be rejected if it points to a system directory
        assert not path_config.is_safe_path(unsafe_symlink)
    
    # Test recursive symlink - would cause infinite recursion without protection
    if recursive_symlink and recursive_symlink.exists():
        assert path_config.is_safe_path(recursive_symlink)
    
    # Test traversal symlink - attempts directory traversal
    if traversal_symlink and traversal_symlink.exists():
        assert not path_config.is_safe_path(traversal_symlink)
    
    logger.info("Symlink safety tests completed successfully")

def test_relative_path_safety(path_config):
    """Test safety of relative paths"""
    logger.info("Testing relative path safety")
    
    # Test relative path in the current directory - should be safe
    assert path_config.is_safe_path(Path("./test.txt"))
    
    # Test relative paths that attempt traversal - should be unsafe
    assert not path_config.is_safe_path(Path("../test.txt"))
    assert not path_config.is_safe_path(Path("./folder/../../../test.txt"))
    
    # Test normal relative paths - should be safe
    assert path_config.is_safe_path(Path("folder/subfolder/test.txt"))
    assert not path_config.is_safe_path(Path("folder/./subfolder/../../etc/passwd"))
    
    logger.info("Relative path safety tests completed successfully")

def test_make_relative_to_root(path_config):
    """Test converting paths to project root relative"""
    # Test with path under project root
    test_path = path_config.project_root / "test" / "path"
    relative = path_config.make_relative_to_root(test_path)
    assert relative == Path("test/path")
    
    # Test with path outside project root
    outside_path = Path("/tmp/test")
    relative = path_config.make_relative_to_root(outside_path)
    assert relative == outside_path  # Should return original path 
