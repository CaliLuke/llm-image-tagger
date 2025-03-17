from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import logging

from backend.app.api.routes import router
from backend.app.core.logging import logger

app = FastAPI()

# Mount static files (your frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include the router
app.include_router(router)

# Set up basic logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000) 
    # or in command line: uvicorn main:app --host 127.0.0.1 --port 8000 --reload
