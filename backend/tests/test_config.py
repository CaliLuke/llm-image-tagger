import pytest
from pathlib import Path
from backend.app.core.settings import settings
from backend.app.core.config import PathConfig
import logging

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
    assert settings.OLLAMA_MODEL == "llama3.2-vision"
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
    
    # Test invalid paths
    logger.debug("Testing invalid paths")
    assert not path_config.is_safe_path(Path("/etc/passwd"))
    assert not path_config.is_safe_path(Path("../../../etc/passwd"))
    assert not path_config.is_safe_path(home / ".." / "other_user" / "file.txt")
    assert not path_config.is_safe_path(Path("/var/log/system.log"))
    
    # Test edge cases
    logger.debug("Testing edge cases")
    assert not path_config.is_safe_path(Path(".."))
    assert not path_config.is_safe_path(Path("."))
    assert not path_config.is_safe_path(Path("test/../../etc/passwd"))
    assert path_config.is_safe_path(home / "folder_with_dots...")
    assert path_config.is_safe_path(project_root / "file.with.dots.txt")
    
    # Test non-existent paths
    logger.debug("Testing non-existent paths")
    assert not path_config.is_safe_path(home / "nonexistent" / ".." / "file.txt")
    assert not path_config.is_safe_path(Path("/nonexistent/path"))
    
    # Test current directory variants
    logger.debug("Testing current directory variants")
    assert not path_config.is_safe_path(Path("./././../test.txt"))
    assert path_config.is_safe_path(Path("./test.txt").resolve())
    
    logger.info("Path safety tests completed successfully")

def test_temp_directory_safety(path_config):
    """Test handling of temporary directory paths"""
    logger.info("Testing temporary directory safety")
    
    tmp = Path("/tmp")
    
    # Test valid temp paths
    logger.debug("Testing valid temporary paths")
    assert path_config.is_safe_path(tmp / "test.txt")
    assert path_config.is_safe_path(tmp / "processing" / "image.jpg")
    
    # Test temp traversal attempts
    logger.debug("Testing temporary directory traversal attempts")
    assert not path_config.is_safe_path(tmp / ".." / "var" / "log" / "test.txt")
    assert not path_config.is_safe_path(tmp / "subdir" / ".." / ".." / "etc" / "passwd")
    
    # Test non-existent temp paths
    logger.debug("Testing non-existent temporary paths")
    assert not path_config.is_safe_path(tmp / "nonexistent" / "test.txt")
    
    logger.info("Temporary directory safety tests completed successfully")

def test_symlink_safety(path_config, tmp_path):
    """Test symlink handling with various scenarios"""
    # Add tmp_path to safe directories
    path_config.add_safe_dir(tmp_path)
    
    # Create test directory structure
    safe_dir = tmp_path / "safe"
    unsafe_dir = tmp_path / "unsafe"
    safe_dir.mkdir()
    unsafe_dir.mkdir()
    
    # Create test files
    safe_file = safe_dir / "test.txt"
    unsafe_file = unsafe_dir / "test.txt"
    safe_file.write_text("safe")
    unsafe_file.write_text("unsafe")
    
    # Test basic symlink
    basic_symlink = safe_dir / "basic_symlink"
    basic_symlink.symlink_to(safe_file)
    assert path_config.is_safe_path(basic_symlink)
    
    # Test unsafe symlink
    unsafe_symlink = safe_dir / "unsafe_symlink"
    unsafe_symlink.symlink_to(unsafe_file)
    assert not path_config.is_safe_path(unsafe_symlink)
    
    # Test recursive symlink (should fail safely)
    recursive_symlink = safe_dir / "recursive"
    recursive_symlink.symlink_to(recursive_symlink)
    assert not path_config.is_safe_path(recursive_symlink)
    
    # Test symlink to path with traversal
    traversal_symlink = safe_dir / "traversal"
    traversal_target = unsafe_dir / ".." / ".." / "etc" / "passwd"
    try:
        traversal_symlink.symlink_to(traversal_target)
        assert not path_config.is_safe_path(traversal_symlink)
    except OSError:
        # Some systems might not allow creating this symlink
        pass

def test_relative_path_safety(path_config):
    """Test relative path handling"""
    # Test current directory
    assert path_config.is_safe_path(Path("./test.txt"))
    
    # Test parent directory references
    assert not path_config.is_safe_path(Path("../test.txt"))
    assert not path_config.is_safe_path(Path("./folder/../../../test.txt"))
    
    # Test complex relative paths
    assert not path_config.is_safe_path(Path("folder/./subfolder/../../test.txt"))
    assert path_config.is_safe_path(Path("folder/subfolder/test.txt"))

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
