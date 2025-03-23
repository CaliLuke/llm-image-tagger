from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List

class Settings(BaseSettings):
    # Supported image extensions
    SUPPORTED_EXTENSIONS: List[str] = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
    
    # Ollama settings
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama2-vision"
    
    # Vector store settings
    VECTOR_STORE_PATH: str = "data/vector_store"
    vector_db_dir_name: str = ".vectordb"
    
    # API settings
    api_host: str = "127.0.0.1"
    api_port: str = "8000"
    
    # Logging settings
    log_level: str = "INFO"
    
    # Queue settings
    MAX_QUEUE_SIZE: int = 100
    PROCESSING_INTERVAL: float = 1.0  # seconds
    
    model_config = ConfigDict(env_file=".env", extra="allow")

settings = Settings() 
