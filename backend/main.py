import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.api.routes import router
from app.core.settings import settings
from app.core.logging import logger

# Create FastAPI application
app = FastAPI(
    title="Image Tagger",
    description="An image tagging and searching application using Llama 3.2 Vision and ChromaDB",
    version="1.0.0"
)

# Include API routes
app.include_router(router)

# Mount static files (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    # Get host and port from settings
    host = settings.API_HOST
    port = settings.API_PORT
    
    logger.info(f"Starting server at http://{host}:{port}")
    
    # Start the server with logging configuration
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,  # Enable auto-reload during development
        log_config=None  # Use our custom logging config
    ) 
