from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.app.core.logging import logger

from backend.app.api.routes import router

app = FastAPI()

# Mount static files (your frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include the router
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000) 
    # or in command line: uvicorn main:app --host 127.0.0.1 --port 8000 --reload
