"""
API router package.

This package contains all API route handlers organized by functionality:
- images: Image serving and metadata endpoints
- search: Search functionality endpoints
- queue: Queue management endpoints
- processing: Image processing endpoints
- status: Status and initialization endpoints
- logging: Frontend logging endpoints
"""

from fastapi import APIRouter
from . import (
    images,
    search,
    queue,
    processing,
    status,
    logging
)

# Create main router
router = APIRouter()

# Include all sub-routers
router.include_router(status.router, tags=["status"])
router.include_router(images.router, prefix="/images", tags=["images"])
router.include_router(search.router, prefix="/search", tags=["search"])
router.include_router(queue.router, prefix="/queue", tags=["queue"])
router.include_router(processing.router, prefix="/processing", tags=["processing"])
router.include_router(logging.router, prefix="/log", tags=["logging"]) 
