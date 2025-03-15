import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

class Settings(BaseModel):
    """Application settings."""
    
    # API settings
    API_HOST: str = Field(default="127.0.0.1", description="API host")
    API_PORT: int = Field(default=8000, description="API port")
    
    # Ollama settings
    OLLAMA_MODEL: str = Field(default="llama3.2-vision", description="Ollama model name")
    OLLAMA_HOST: str = Field(default="http://localhost:11434", description="Ollama host")
    
    # Application settings
    DEFAULT_FOLDER_PATH: Optional[str] = Field(default=None, description="Default folder path")
    SUPPORTED_EXTENSIONS: list[str] = Field(
        default=[".jpg", ".jpeg", ".png", ".webp"], 
        description="Supported image extensions"
    )
    
    # Vector DB settings
    VECTOR_DB_DIR_NAME: str = Field(default=".vectordb", description="Vector database directory name")
    
    # Logging settings
    LOG_LEVEL: str = Field(default="INFO", description="Log level")

def get_settings() -> Settings:
    """Get application settings from environment variables or defaults."""
    return Settings(
        API_HOST=os.getenv("API_HOST", "127.0.0.1"),
        API_PORT=int(os.getenv("API_PORT", "8000")),
        OLLAMA_MODEL=os.getenv("OLLAMA_MODEL", "llama3.2-vision"),
        OLLAMA_HOST=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        DEFAULT_FOLDER_PATH=os.getenv("DEFAULT_FOLDER_PATH"),
        SUPPORTED_EXTENSIONS=[ext.strip() for ext in 
                             os.getenv("SUPPORTED_EXTENSIONS", ".jpg,.jpeg,.png,.webp").split(",")],
        VECTOR_DB_DIR_NAME=os.getenv("VECTOR_DB_DIR_NAME", ".vectordb"),
        LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
    )

# Create a global settings instance
settings = get_settings() 
