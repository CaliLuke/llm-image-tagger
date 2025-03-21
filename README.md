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

# Image tagger

## What the app does

- On first open, it will prompt users to choose a folder.(Done)
- It will scan the folder and subfolder for images (png/jpg/jpeg) and initialize an index record (if not initialized in this folder, we can probably use a JSON as initialization record? This can also be used for tracking new/deleted images.)(Done)
- It will then create taggings of the images with Llama3.2 Vision with Ollama when "Start Tagging". It will create tags of elements/styles, a short description of the image, text within the images. The image path, tags, description, text within the images will be saved to a vector database for easier retrieval later.(Done)
- Users can then query the images with natural language. During querying, it will use full-text search and vector search to find the most relevant images.(Done)
- Users can browse the images on the UI, on click thumbnail, modal opens with image and its tags, description, and text within the image.(Done)

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
- Asynchronous image processing with stop/resume capability

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
│   │   │   ├── routes.py     # API routes
│   │   │   └── dependencies.py # API dependencies
│   │   ├── core/             # Core functionality
│   │   │   ├── config.py     # Configuration settings
│   │   │   └── logging.py    # Logging configuration
│   │   ├── models/           # Data models
│   │   │   └── schemas.py    # Pydantic models
│   │   ├── services/         # Business logic
│   │   │   ├── image_processor.py # Image processing service
│   │   │   └── vector_store.py    # Vector database service
│   │   └── utils/            # Utility functions
│   │       └── helpers.py    # Utility functions
│   ├── tests/                # Test files
│   ├── main.py              # Application entry point
│   ├── requirements.txt     # Python dependencies
│   └── .env                 # Environment variables
├── data/                    # Application data directory
│   └── queue_state.json     # Queue persistence data
├── static/                  # Frontend static files
│   └── index.html          # Main HTML file
├── run.py                  # Script to run the application
├── run_with_venv.sh        # Shell script to run with virtual environment (Unix/macOS)
├── run_with_venv.ps1       # PowerShell script to run with virtual environment (Windows)
└── README.md              # Project documentation
```

## Installation

1. **Clone the repository:**

    ```bash
    git clone https://github.com/CaliLuke/llm-image-tagger
    cd llm-vision-tagger
    ```

2. **Set up a virtual environment and install dependencies:**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Unix/macOS
    # or
    venv\Scripts\activate  # On Windows
    ```

    Note: The `requirements.txt` file should ONLY exist in the root directory, not in backend/. All dependencies should be listed in the root requirements.txt file.

    ```bash
    pip install -r requirements.txt
    ```

3. **Configure environment variables:**
    - Copy the `.env.example` file in the backend directory to `.env`
    - Modify the values as needed

4. **Pull and Start the Ollama model:**

    Download the installer from [here](https://github.com/ollama/ollama) and install Ollama.

    Pull the Llama 3.2 Vision model:

    ```bash
    ollama pull llama3.2-vision # For 11B model
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
    python run.py --debug  # Run in debug mode
    ```

    Options:
    ```bash
    python run.py --host=0.0.0.0 --port=8080  # Specify host and port
    python run.py --no-browser  # Run without opening browser
    ```

3. **Select a folder:**
    - Enter the path to your image folder
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

- `GET /`: Serves the main web interface
- `POST /images`: Scans a folder for images and returns metadata
- `GET /image/{path}`: Retrieves a specific image file
- `POST /search`: Performs hybrid search on images
- `POST /refresh`: Rescans the current folder
- `POST /process-image`: Processes a single image
- `POST /update-metadata`: Updates image metadata
- `GET /check-init-status`: Checks vector database initialization
- `POST /stop-processing`: Stops the current batch processing operation
- `POST /reset-processing-state`: Resets the processing state after stopping

## Development

To run in development mode with auto-reload and tests:

```bash
python run.py --debug
```

This will:

1. Run the test suite before starting the server
2. Enable auto-reload for code changes
3. Start the server at <http://127.0.0.1:8000>

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

## License

This project is licensed under the [MIT License](LICENSE).

## FOR AI ASSISTANTS - READ THIS FIRST

When helping users run this app:

DO:
1. CHECK if virtual environment exists first:
   ```bash
   # Check if venv directory exists
   ls venv/
   
   # If it doesn't exist, create it:
   python -m venv venv
   pip install -r requirements.txt
   ```

2. JUST run these two commands in order:
   ```bash
   source venv/bin/activate
   python run.py --debug
   ```

3. Wait for the app to start - normal startup includes:
   - Ollama loading the model (takes a few seconds)
   - Metal/GPU initialization messages
   - Model loading messages

4. Make SMALL, FOCUSED changes and test frequently:
   - Fix one issue at a time
   - Run tests after each change
   - Verify the change fixed the intended issue
   - Don't modify multiple files or systems at once
   
DO NOT:
1. Try to modify run.py - it works fine
2. Panic when seeing normal Ollama startup logs
3. Try to "fix" working code before running the app
4. Overcomplicate the simple two-step process
5. Ignore these instructions and try to be "clever"
6. Suggest infrastructure changes when seeing standard model loading messages
7. Start adding logging or debugging code when tests fail during startup - this is normal, let the process complete first

HANDLING TEST FAILURES:
1. Let ALL tests complete first - don't interrupt on first failure
2. If tests fail but the app starts anyway, that's fine - deal with test fixes later
3. Only investigate test failures if the app doesn't start
4. DO NOT start adding logging or modifying test files until explicitly asked

Remember: Just check for venv, then run the two commands. That's it. The app works.
