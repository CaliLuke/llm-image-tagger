import os
from typing import Optional, List
from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings."""
    
    # API settings
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    
    # Ollama settings
    OLLAMA_MODEL: str = Field(default="llama3.2-vision", description="Ollama model name")
    OLLAMA_HOST: str = Field(default="http://localhost:11434", description="Ollama host")
    
    # Application settings
    DEFAULT_FOLDER_PATH: Optional[str] = None
    SUPPORTED_EXTENSIONS: List[str] = Field(
        default=[".png", ".jpg", ".jpeg", ".webp"],
        description="List of supported image file extensions"
    )
    
    # Vector DB settings
    VECTOR_DB_DIR_NAME: str = Field(
        default=os.getenv("VECTOR_DB_DIR", "data/vectordb"),
        description="Vector database directory name"
    )
    
    # Logging settings
    LOG_LEVEL: str = Field(default="INFO", description="Log level")

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        json_schema_extra={
            "examples": [
                {
                    "SUPPORTED_EXTENSIONS": [".png", ".jpg", ".jpeg", ".webp"]
                }
            ]
        }
    )

# Initialize settings
settings = Settings() 