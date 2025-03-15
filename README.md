# Image Tagger

This project is an image tagging and searching application that leverages the power of open-source local multimodal LLM like Llama 3.2 Vision and vector database like ChromaDB to provide a seamless image management experience.

This project has an accompanying blog post [here](https://medium.com/design-bootcamp/local-ai-vision-for-your-photos-build-ai-image-tagger-with-llama-vision-and-chromadb-e3b1e0eeac43).

## Features

- **Folder Selection and Image Discovery**: On first launch, the application prompts users to select a folder by inputting the full path of a folder. It then recursively scans this folder and its subfolders to discover images (supports `png`, `jpg`, `jpeg`, and `webp` formats).
- **Image Indexing**: Initializes a JSON-based index to track images within the selected folder. This index is updated dynamically to reflect new or deleted images.
- **Intelligent Tagging**: Utilizes Llama 3.2 Vision with Ollama to generate descriptive tags for each image. This includes identifying elements/styles, creating a short description, and extracting any text present within the images.
- **Vector Database Storage**: Stores image metadata (path, tags, description, text content) in a ChromaDB vector database for efficient vector search.
- **Natural Language Search**: Enables users to search images using natural language queries. The application performs a hybrid full-text search and vector search on the stored metadata to find relevant images.
- **User Interface**: Provides a user-friendly web interface built with Tailwind CSS and Vue3 for browsing and interacting with images.
  - **Image Grid**: Displays images in a responsive grid layout.
  - **Image Modal**: On clicking a thumbnail, a modal opens, displaying the image along with its tags, description, and extracted text.
  - **Progress Tracking**: Shows real-time progress during batch processing of images, including the number of processed and failed images.

## Prerequisites

- **Python 3.7+**: Ensure Python is installed on your system.
- **Ollama**: Install Ollama to run the Llama model. Follow the instructions on the [Ollama website](https://ollama.com/).
- **ChromaDB**: ChromaDB will be installed as a Python package via pip.

## Project Structure

```
llm-image-tagger/
├── backend/                   # Backend code
│   ├── app/                   # Application package
│   │   ├── api/               # API endpoints
│   │   ├── core/              # Core functionality
│   │   ├── models/            # Data models
│   │   ├── services/          # Business logic
│   │   └── utils/             # Utility functions
│   ├── tests/                 # Test files
│   ├── main.py                # Application entry point
│   └── requirements.txt       # Python dependencies
├── static/                    # Frontend static files
│   └── index.html             # Main HTML file
├── run.py                     # Script to run the application
├── run_with_venv.sh           # Shell script to run with virtual environment (Unix/macOS)
├── run_with_venv.ps1          # PowerShell script to run with virtual environment (Windows)
└── README.md                  # Project documentation
```

## Installation

1. **Clone the repository:**

    ```bash
    git clone https://github.com/Troyanovsky/llama-vision-image-tagger
    cd llama-vision-image-tagger
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

3. **Pull and Start the Ollama model:**

    Ensure the Llama 3.2 Vision model is running in Ollama. You may need to pull and start the model using Ollama's command-line interface.

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

    This will activate the virtual environment, start the server, and open the web interface in your default browser.

    You can also specify host and port:

    ```bash
    ./run_with_venv.sh --host=0.0.0.0 --port=8080
    ```

    Or run without opening a browser:

    ```bash
    ./run_with_venv.sh --no-browser
    ```

    Alternatively, you can run the application directly:

    ```bash
    python run.py
    ```

    Or run the backend directly:

    ```bash
    cd backend
    python main.py
    ```

    Then access the web interface at `http://127.0.0.1:8000`.

2. **Select a folder:**

    Enter the path to the folder containing your images and click "Open Folder". The application will scan the folder and display the found images.

    The first time you open a folder, the application will scan through all the images and process them and initialize the vector database (ChromaDB might also download an embedding model). This might take a while depending on your network speed and the number of images in the folder.

3. **Process images:**

    - **Process All**: Click the "Process All" button to start tagging all unprocessed images. The progress will be displayed on the screen.
    - **Process Individual Images**: Click the "Process Image" button in the image modal for a specific image to process it individually.

4. **Search images:**

    Enter your search query in the search bar and click "Search". The application will display images matching your query.

5. **Refresh images:**

    When new images are added to the folder, you can click the "Refresh" button to rescan the folder and update the image list.

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
cd backend
uvicorn main:app --reload
```

## Testing

To run tests:

```bash
cd backend
pytest
```

## TODO

- [ ] Scan image metadata to add to context for generating descriptions/tags (Idea from Redditor u/JohnnyLovesData/)
- [ ] OCR with tesseract to extract text from images (or hybrid with Llama 3.2 Vision) (Idea from Redditor u/SocialNetworky/)
- [ ] Separate frontend into a proper Vue.js project
- [ ] Add authentication for multi-user support
- [ ] Implement WebSockets for real-time progress updates
- [ ] Add support for video files

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests to improve the project.

## License

This project is licensed under the [MIT License](LICENSE) - see the LICENSE file for details.

## Other Repos That You Might Be Interested In

- [Ollama](https://github.com/ollama/ollama) - Local LLM server
- [ChromaDB](https://github.com/chroma-core/chroma) - Vector database
- [Local-LLM-Comparison-Colab-UI](https://github.com/Troyanovsky/Local-LLM-Comparison-Colab-UI): A collection of Colab Notebooks for running and comparing local LLMs.
- [Building-with-GenAI](https://github.com/Troyanovsky/Building-with-GenAI): A collection of projects and tutorials for building with GenAI.
