# Image Tagger

This project is an image tagging and searching application that leverages the power of open-source local multimodal LLM like Llama 3.2 Vision and vector database like ChromaDB to provide a seamless image management experience.

This project is an extensive rewrite of "llama vision image tagger" by Guodong Zhao, where I aim to

- make the llm backend selectable to take advantage of more recent models like Gemma3 vision
- improve the usability by making the processing queue asynchronous and add file system navigation and bookmarking
- add the ability to save tags and descriptions to the images' metadata to supplement local search engines and photo organizers that don't have llm based tagging

## Overview

The application provides an intuitive way to organize and search through your image collection using AI-powered tagging and natural language search. When you first open the application, it will:

1. Prompt you to choose a folder containing your images
2. Scan the folder and subfolders for images (png/jpg/jpeg/webp)
3. Initialize an index record (using JSON) to track new/deleted images
4. Process images with Llama 3.2 Vision to generate:
   - Tags for elements and styles
   - Short descriptions
   - Text extracted from images
5. Store all metadata in a vector database for efficient retrieval
6. Enable natural language search using both full-text and vector search
7. Provide a modern web interface for browsing and managing images

## What the app does

- On first open, it will prompt users to choose a folder
- It will scan the folder and subfolder for images (png/jpg/jpeg/webp) and initialize an index record (stored as image_metadata.json in the selected folder)
- It will then create taggings of the images with Llama3.2 Vision with Ollama when "Start Tagging". It will create tags of elements/styles, a short description of the image, text within the images. The image path, tags, description, text within the images will be saved to a vector database for easier retrieval later
- Users can then query the images with natural language. During querying, it will use full-text search and vector search to find the most relevant images
- Users can browse the images on the UI, on click thumbnail, modal opens with image and its tags, description, and text within the image

## Project Structure Notes

- requirements.txt should ONLY exist in the root directory, not in backend/
- All dependencies should be listed in the root requirements.txt file

## Features

- **Folder Selection and Image Discovery**:
  - Select any folder on your system
  - Recursive scanning of subfolders
  - Support for multiple image formats (png, jpg, jpeg, webp)
  - Automatic tracking of new and deleted images

- **Intelligent Tagging**:
  - AI-powered image analysis using Llama 3.2 Vision
  - Generation of descriptive tags
  - Extraction of image content and style information
  - Text extraction from images
  - Interruptible batch processing with progress tracking
  - Real-time progress updates for each processing step:
    - Description generation (0-33%)
    - Tag extraction (33-67%)
    - Text content analysis (67-100%)

- **Vector Database Storage**:
  - Efficient storage using ChromaDB
  - Fast vector-based similarity search
  - Persistent storage of metadata
  - Automatic synchronization with file system

- **Natural Language Search**:
  - Hybrid search combining full-text and vector similarity
  - Search by description, tags, or extracted text
  - Semantic understanding of search queries
  - Ranked results based on relevance

- **User Interface**:
  - Modern web interface built with Vue3 and Tailwind CSS
  - Responsive image grid layout
  - Detailed image modal with metadata
  - Real-time processing progress tracking
  - Stop/Resume batch processing capability

- **External Volume Support**:
  - Handles external drives and network shares
  - Graceful handling of permission limitations
  - Robust file operations with appropriate error messages
  - Support for metadata read/write operations on various filesystem types

## Technical Architecture

### Frontend

- Local server web page with Tailwind CSS, Vue3, and HTML.
  - Tailwind CSS CDN:   <script src="https://cdn.tailwindcss.com"></script>
  - Vue3 CDN: <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>

- Built with Vue3 and Tailwind CSS
- Responsive and modern UI design
- Real-time updates and progress tracking
- Modal-based image viewing
- Interruptible batch processing controls

### Backend

- FastAPI server for robust API endpoints
- Ollama integration for running Llama 3.2 Vision model
- ChromaDB for vector storage and similarity search
- File system storage service for robust file operations with retry mechanisms
- Asynchronous image processing with stop/resume capability

### Storage Service Details

The application includes a dedicated storage service that:

- Handles all file system interactions with robust error handling
- Provides atomic file operations with retry mechanisms
- Validates file permissions before operations
- Handles JSON metadata serialization/deserialization
- Ensures metadata consistency across operations
- Creates parent directories as needed for file operations
- Manages temporary files for atomic writes
- Provides both synchronous and asynchronous interfaces
- Implements proper cleanup for failed operations
- Handles external volumes and their specific requirements

This service isolates file system interactions from business logic, making the code more testable and robust against filesystem errors like permission issues or concurrent access problems.

### Metadata Management

The application stores metadata in two primary locations:

1. **JSON File**: A `image_metadata.json` file is created in each image folder, containing all metadata for images in that folder. This allows metadata to stay with the images even when moved.

2. **Vector Database**: Metadata is also stored in a ChromaDB instance for efficient semantic searching.

The app ensures synchronization between these storage locations, with intelligent matching between filenames and paths to maintain metadata consistency.

### Image Processing Details

The application processes each image in three distinct steps, providing real-time progress updates throughout:

1. **Description Generation (0-33%)**
   - Sends the image to Ollama with a prompt for a concise description
   - Returns a structured description in JSON format
   - Progress updates reflect both step completion and Ollama's processing status

2. **Tag Extraction (33-67%)**
   - Analyzes the image for relevant tags (objects, styles, colors, etc.)
   - Generates 5-10 descriptive tags in JSON format
   - Progress updates combine step position and Ollama's processing status

3. **Text Content Analysis (67-100%)**
   - Detects and extracts any visible text in the image
   - Returns a structured response with text content and presence flag
   - Final progress update (100%) includes complete metadata

Each step yields progress updates that are scaled within its range, ensuring smooth progress tracking in the UI. The process can be interrupted at any point, and all progress is persisted to enable resuming from the last completed step.

## Prerequisites

- **Python 3.11+**: Ensure Python 3.11 or newer is installed on your system
- **Ollama**: Install Ollama to run the Llama model ([Ollama website](https://ollama.com/))
- **ChromaDB**: Will be installed via pip
- **Data Directory**: The application requires write access to create and manage a data directory for queue persistence and other operational data. By default, this is created at:
  - `$PROJECT_ROOT/data` (where $PROJECT_ROOT is the root directory of the project)
  - Ensure your user has write permissions to this location

## Project Structure

```
llm-image-tagger/
├── backend/                   # Backend code
│   ├── app/                   # Application package
│   │   ├── api/              # API endpoints
│   │   │   ├── routes.py     # API route definitions
│   │   │   └── dependencies.py # API dependencies
│   │   ├── core/             # Core functionality
│   │   │   ├── config.py     # Configuration settings
│   │   │   └── logging.py    # Logging configuration
│   │   ├── models/           # Data models
│   │   │   └── schemas.py    # Pydantic models
│   │   ├── services/         # Business logic
│   │   │   ├── image_processor.py # Image processing service
│   │   │   ├── vector_store.py    # Vector database service
│   │   │   ├── storage.py         # File system storage service
│   │   │   ├── processing_queue.py # Queue management
│   │   │   └── queue_persistence.py # Queue state persistence
│   │   └── utils/            # Utility functions
│   │       └── helpers.py    # Utility functions
│   ├── tests/                # Test files
│   ├── main.py              # Application entry point
│   └── .env                 # Environment variables
├── data/                    # Application data directory
│   └── queue_state.json     # Queue persistence data
├── static/                  # Frontend static files
│   └── index.html          # Main HTML file
├── run.py                  # Script to run the application
├── requirements.txt        # Python dependencies
└── README.md              # Project documentation
```

## Installation

1. **Clone the repository:**

    ```bash
    git clone https://github.com/CaliLuke/llm-image-tagger
    cd llm-image-tagger
    ```

2. **Set up a virtual environment and install dependencies:**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Unix/macOS
    # or
    venv\Scripts\activate  # On Windows
    pip install -r requirements.txt
    ```

3. **Configure environment variables:**
    - Copy the `.env.example` file in the backend directory to `.env`
    - Modify the values as needed

4. **Install Ollama and pull the model:**
    - Download and install Ollama from [ollama.com](https://ollama.com/)
    - Pull the Llama 3.2 Vision model:

    ```bash
    ollama pull llama3.2-vision
    ```

## Usage

1. **Activate the virtual environment:**

    ```bash
    source venv/bin/activate  # On Unix/macOS
    # or
    venv\Scripts\activate  # On Windows
    ```

2. **Run the application:**

    ```bash
    python run.py  # Run with default settings
    python run.py --debug  # Run in debug mode with auto-reload
    ```

    Options:

    ```bash
    python run.py --host=0.0.0.0 --port=8080  # Specify host and port
    python run.py --no-browser  # Run without opening browser
    python run.py --skip-tests  # Skip running tests in debug mode
    python run.py --force  # Force start even if port is in use
    ```

3. **Select a folder:**
    - Enter the path to your image folder (including external drives like `/Volumes/...`)
    - Wait for initial scanning and processing
    - First-time processing may take longer due to model downloads

4. **Process images:**
    - Use "Process All" for batch processing
    - Use "Process Image" for individual images
    - Monitor progress in real-time

5. **Search images:**
    - Enter natural language queries
    - View results in the responsive grid
    - Click images for detailed metadata

6. **Refresh images:**
    - Use "Refresh" to scan for new/removed images
    - Metadata is preserved across sessions

## API Endpoints

### Search Endpoints

- `POST /search`: Performs hybrid search combining vector similarity and full-text search
  - Searches through descriptions, tags, and extracted text
  - Returns ranked results based on relevance
  - Supports natural language queries

### Queue Management

- `GET /queue/status`: Returns current queue status (size, active/completed/failed tasks)
- `GET /queue/tasks`: Lists all tasks in the queue with their status
- `POST /queue/clear`: Clears all tasks from the queue and task history

### Image Processing

- `POST /processing/start`: Starts batch image processing
  - Processes images in queue
  - Provides real-time progress updates
  - Supports background processing
- `POST /processing/stop`: Stops current processing operation
- `GET /processing/status`: Returns current processing status and progress

### Frontend Logging

- `POST /logging/error`: Logs frontend errors with stack traces
- `POST /logging/info`: Logs frontend information messages
- `POST /logging/debug`: Logs frontend debug information

Each endpoint includes:

- Comprehensive error handling
- Detailed logging
- Progress tracking where applicable
- Type validation
- Authentication (if configured)

For detailed API documentation, visit `/docs` when the server is running.

## Development

To run in development mode with auto-reload and tests:

```bash
python run.py --debug
```

This will:

1. Run the test suite before starting the server
2. Enable auto-reload for code changes (no manual restarts needed)
3. Start the server at <http://127.0.0.1:8000>

The application uses uvicorn's auto-reload feature, which automatically detects code changes and restarts the server, making development much faster. You'll see "WatchFiles detected changes" messages in the console when files are modified.

Additional options:

```bash
python run.py --debug --no-browser  # Don't open browser automatically
python run.py --debug --port 8080   # Use a different port
```

## Testing

The project uses pytest for testing. Tests are organized by component:

```
tests/
├── conftest.py          # Shared test fixtures
├── test_data/          # Test data directory
├── test_image_processor.py  # Image processor tests
└── test_api.py         # API endpoint tests
```

To run tests manually:

```bash
# Run all tests
pytest

# Run tests with output
pytest -v

# Run specific test file
pytest tests/test_image_processor.py

# Run specific test
pytest tests/test_api.py::test_stop_processing
```

## TODO

- [ ] Scan image metadata for context in descriptions/tags
- [ ] Hybrid OCR with tesseract and Llama Vision
- [ ] Separate frontend into proper Vue.js project
- [ ] Add authentication for multi-user support
- [ ] Implement WebSockets for real-time updates

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## For AI Assistants

If you are an AI assistant helping with this project, please read [AI_ASSISTANT_GUIDE.md](AI_ASSISTANT_GUIDE.md) before proceeding.

## License

This project is licensed under the [MIT License](LICENSE).
