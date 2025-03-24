from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.app.core.logging import logger, cleanup_old_logs
import os

from backend.app.api.routes import router

# Clean up logs on startup
logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(logs_dir, exist_ok=True)
app_log_path = os.path.join(logs_dir, 'app.log')
cleanup_old_logs(app_log_path)

app = FastAPI()

# Mount static files (your frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include the router
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000) 
    # or in command line: uvicorn main:app --host 127.0.0.1 --port 8000 --reload
