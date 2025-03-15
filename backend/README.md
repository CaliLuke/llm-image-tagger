# Image Tagger Backend

This is the backend for the Image Tagger application, which provides API endpoints for image processing, tagging, and searching.

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── routes.py          # API routes
│   │   └── dependencies.py    # API dependencies
│   ├── core/
│   │   ├── config.py          # Configuration settings
│   │   └── logging.py         # Logging configuration
│   ├── models/
│   │   └── schemas.py         # Pydantic models
│   ├── services/
│   │   ├── image_processor.py # Image processing service
│   │   └── vector_store.py    # Vector database service
│   └── utils/
│       └── helpers.py         # Utility functions
├── tests/                     # Test files
├── main.py                    # Application entry point
├── requirements.txt           # Python dependencies
└── .env                       # Environment variables
```

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Configure environment variables:

Copy the `.env.example` file to `.env` and modify the values as needed.

## Running the Application

```bash
python main.py
```

This will start the FastAPI server at http://127.0.0.1:8000.

## API Endpoints

- `GET /`: Serves the main web interface
- `POST /images`: Scans a folder for images and returns their metadata
- `GET /image/{path}`: Retrieves a specific image file
- `POST /search`: Performs hybrid (full-text + vector) search on images
- `POST /refresh`: Rescans the current folder for new or removed images
- `POST /process-image`: Processes a single image using Ollama to generate tags, description, and extract text
- `POST /update-metadata`: Updates metadata for a specific image
- `GET /check-init-status`: Checks if the vector database needs initialization

## Development

To run the application in development mode with auto-reload:

```bash
uvicorn main:app --reload
```

## Testing

To run tests:

```bash
pytest
``` 
