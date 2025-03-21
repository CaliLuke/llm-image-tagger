"""
Application configuration and settings management.

This module provides:
1. Environment-based configuration
2. Type-safe settings validation
3. Default values for all settings
4. Environment variable overrides
5. .env file support

Settings are organized into categories:
- API Configuration
- Ollama Integration
- Application Defaults
- Vector Database
- Logging

All settings can be overridden by:
1. Environment variables
2. .env file
3. Direct assignment
"""

import os
from typing import Optional, List
from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Application settings management using Pydantic.
    
    This class provides:
    1. Type validation for all settings
    2. Environment variable parsing
    3. Default values
    4. Documentation for each setting
    
    Settings can be accessed as attributes:
        settings.API_HOST
        settings.SUPPORTED_EXTENSIONS
        etc.
    
    Environment variables take precedence over defaults:
        export API_PORT=9000
        
    Configuration is loaded in this order:
    1. Default values
    2. .env file
    3. Environment variables
    4. Direct assignment
    """
    
    # API settings
    API_HOST: str = Field(
        default="127.0.0.1",
        description="Host address for the API server",
        examples=["127.0.0.1", "0.0.0.0"]
    )
    API_PORT: int = Field(
        default=8000,
        description="Port number for the API server",
        ge=1024,
        le=65535
    )
    
    # Ollama settings
    OLLAMA_MODEL: str = Field(
        default="llama3.2-vision",
        description="Ollama model name for image processing",
        examples=["llama3.2-vision", "llama2-vision"]
    )
    OLLAMA_HOST: str = Field(
        default="http://localhost:11434",
        description="Ollama API host address",
        examples=["http://localhost:11434", "http://ollama:11434"]
    )
    
    # Application settings
    DEFAULT_FOLDER_PATH: Optional[str] = Field(
        default=None,
        description="Default folder to scan for images",
        examples=["/path/to/images", "./images"]
    )
    SUPPORTED_EXTENSIONS: List[str] = Field(
        default=[".png", ".jpg", ".jpeg", ".webp"],
        description="List of supported image file extensions",
        examples=[[".png", ".jpg", ".jpeg", ".webp"]]
    )
    
    # Vector DB settings
    VECTOR_DB_DIR_NAME: str = Field(
        default=os.getenv("VECTOR_DB_DIR", "data/vectordb"),
        description="Directory for storing vector database files",
        examples=["data/vectordb", "/path/to/vectordb"]
    )
    
    # Logging settings
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level for the application",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"
    )

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        json_schema_extra={
            "title": "Image Tagger Settings",
            "description": "Configuration settings for the Image Tagger application",
            "examples": [
                {
                    "API_HOST": "127.0.0.1",
                    "API_PORT": 8000,
                    "OLLAMA_MODEL": "llama3.2-vision",
                    "OLLAMA_HOST": "http://localhost:11434",
                    "SUPPORTED_EXTENSIONS": [".png", ".jpg", ".jpeg", ".webp"],
                    "VECTOR_DB_DIR_NAME": "data/vectordb",
                    "LOG_LEVEL": "INFO"
                }
            ]
        }
    )

# Initialize settings
settings = Settings() 
