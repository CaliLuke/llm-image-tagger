# Image Tagger

This project is an image tagging and searching application that leverages the power of open-source local multimodal LLM like Llama 3.2 Vision and vector database like ChromaDB to provide a seamless image management experience.

This project has an accompanying blog post [here](https://medium.com/design-bootcamp/local-ai-vision-for-your-photos-build-ai-image-tagger-with-llama-vision-and-chromadb-e3b1e0eeac43).

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
    git clone https://github.com/Troyanovsky/llama-vision-image-tagger
    cd llama-vision-tagger
    ```

2. **Set up a virtual environment and install dependencies:**

    **Unix/macOS:**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Unix/macOS
    pip install -r backend/requirements.txt
    ```

    **Windows:**

    ```powershell
    python -m venv venv
    venv\Scripts\Activate.ps1  # On Windows with PowerShell
    pip install -r backend\requirements.txt
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

1. **Run the application with virtual environment:**

    **Unix/macOS:**

    ```bash
    ./run_with_venv.sh
    ```

    **Windows:**

    ```powershell
    .\run_with_venv.ps1
    ```

    Options:

    ```bash
    ./run_with_venv.sh --host=0.0.0.0 --port=8080  # Specify host and port
    ./run_with_venv.sh --no-browser                 # Run without opening browser
    ```

    Alternative methods:

    ```bash
    python run.py                # Run directly
    cd backend && python main.py # Run backend directly
    ```

2. **Select a folder:**
    - Enter the path to your image folder
    - Wait for initial scanning and processing
    - First-time processing may take longer due to model downloads

3. **Process images:**
    - Use "Process All" for batch processing
    - Use "Process Image" for individual images
    - Monitor progress in real-time

4. **Search images:**
    - Enter natural language queries
    - View results in the responsive grid
    - Click images for detailed metadata

5. **Refresh images:**
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
- [ ] Add support for video files

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is licensed under the [MIT License](LICENSE).

## Related Projects

- [Ollama](https://github.com/ollama/ollama) - Local LLM server
- [ChromaDB](https://github.com/chroma-core/chroma) - Vector database
- [Local-LLM-Comparison-Colab-UI](https://github.com/Troyanovsky/Local-LLM-Comparison-Colab-UI) - Compare local LLMs
- [Building-with-GenAI](https://github.com/Troyanovsky/Building-with-GenAI) - GenAI project tutorials
