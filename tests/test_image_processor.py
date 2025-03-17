import pytest
from pathlib import Path
import os
from image_processor import ImageProcessor, ImageDescription, ImageTags, ImageText

@pytest.fixture
def image_processor():
    """Create an ImageProcessor instance for testing."""
    return ImageProcessor(model_name='llama3.2-vision')

def test_image_processor_initialization(image_processor):
    """Test that ImageProcessor initializes with correct model name."""
    assert image_processor.model_name == 'llama3.2-vision'

def test_image_description_model():
    """Test ImageDescription Pydantic model."""
    description = "A test description"
    model = ImageDescription(description=description)
    assert model.description == description

def test_image_tags_model():
    """Test ImageTags Pydantic model."""
    tags = ["tag1", "tag2", "tag3"]
    model = ImageTags(tags=tags)
    assert model.tags == tags

def test_image_text_model():
    """Test ImageText Pydantic model."""
    model = ImageText(has_text=True, text_content="Some text")
    assert model.has_text == True
    assert model.text_content == "Some text"

    model = ImageText(has_text=False, text_content="")
    assert model.has_text == False
    assert model.text_content == ""

@pytest.fixture
def vector_store():
    """Create a temporary vector store for testing."""
    from vector_store import VectorStore
    import tempfile
    import shutil
    
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    store = VectorStore(persist_directory=temp_dir)
    
    yield store
    
    # Cleanup after tests
    shutil.rmtree(temp_dir)

def test_vector_store_add_entry(vector_store):
    """Test adding an entry to the vector store."""
    # Test data
    image_path = "test_image.png"
    metadata = {
        "description": "A test image",
        "tags": ["test", "image"],
        "text_content": "Some text in the image",
        "is_processed": True
    }
    
    # Add entry
    vector_store.add_or_update_image(image_path, metadata)
    
    # Verify entry was added
    results = vector_store.search_images("test image")
    assert len(results) > 0
    stored_metadata = vector_store.get_metadata(image_path)
    assert stored_metadata["description"] == "A test image"
    assert "test" in stored_metadata["tags"]
    assert "image" in stored_metadata["tags"]

def test_vector_store_update_entry(vector_store):
    """Test updating an existing entry in the vector store."""
    # Initial data
    image_path = "test_image.png"
    initial_metadata = {
        "description": "Initial description",
        "tags": ["initial"],
        "text_content": "Initial text",
        "is_processed": True
    }
    
    # Add initial entry
    vector_store.add_or_update_image(image_path, initial_metadata)
    
    # Update metadata
    updated_metadata = {
        "description": "Updated description",
        "tags": ["updated"],
        "text_content": "Updated text",
        "is_processed": True
    }
    vector_store.add_or_update_image(image_path, updated_metadata)
    
    # Verify update
    stored_metadata = vector_store.get_metadata(image_path)
    assert stored_metadata["description"] == "Updated description"
    assert "updated" in stored_metadata["tags"]
    assert len(stored_metadata["tags"]) == 1

def test_vector_store_search(vector_store):
    """Test searching entries in the vector store."""
    # Add multiple entries
    entries = [
        ("image1.png", {"description": "A cat playing with yarn", "tags": ["cat", "pet"], "text_content": "", "is_processed": True}),
        ("image2.png", {"description": "A dog in the park", "tags": ["dog", "pet"], "text_content": "", "is_processed": True}),
        ("image3.png", {"description": "A sunset over mountains", "tags": ["nature", "sunset"], "text_content": "", "is_processed": True})
    ]
    
    for path, metadata in entries:
        vector_store.add_or_update_image(path, metadata)
    
    # Test search functionality
    # Search for specific terms that should match exactly
    cat_results = vector_store.search_images("cat")
    assert len(cat_results) > 0  # Should find the cat image
    
    dog_results = vector_store.search_images("dog")
    assert len(dog_results) > 0  # Should find the dog image
    
    # Search for nature-related terms
    nature_results = vector_store.search_images("sunset mountains")
    assert len(nature_results) > 0  # Should find the sunset image
    
    # Test that irrelevant queries return no results
    irrelevant_results = vector_store.search_images("airplane space rocket")
    assert len(irrelevant_results) == 0

@pytest.fixture
def sample_image(tmp_path):
    """Create a sample image file for testing."""
    from PIL import Image, ImageDraw
    
    # Create a test image with text
    img = Image.new('RGB', (400, 100), color='white')
    d = ImageDraw.Draw(img)
    d.text((10,10), "Test Image Text", fill='black')
    
    # Save the image
    image_path = tmp_path / "test_image_with_text.png"
    img.save(image_path)
    
    return image_path

@pytest.mark.asyncio
async def test_get_text_content(image_processor, sample_image):
    """Test extracting text from an image."""
    result = await image_processor._get_text_content(str(sample_image))
    assert isinstance(result, ImageText)
    # Note: Text detection depends on the Ollama model's response
    # We only verify the response structure, not the actual content
    assert isinstance(result.has_text, bool)
    assert isinstance(result.text_content, str)

@pytest.mark.asyncio
async def test_get_description(image_processor, sample_image):
    """Test generating description for an image."""
    result = await image_processor._get_description(str(sample_image))
    assert isinstance(result, ImageDescription)
    assert result.description
    assert len(result.description) > 0

@pytest.mark.asyncio
async def test_get_tags(image_processor, sample_image):
    """Test generating tags for an image."""
    result = await image_processor._get_tags(str(sample_image))
    assert isinstance(result, ImageTags)
    assert result.tags
    assert len(result.tags) > 0
    assert all(isinstance(tag, str) for tag in result.tags)

@pytest.mark.asyncio
async def test_process_image_full(image_processor, sample_image):
    """Test full image processing pipeline."""
    metadata = await image_processor.process_image(Path(sample_image))
    
    # Check that all components are present
    assert metadata["description"]
    assert isinstance(metadata["description"], str)
    assert len(metadata["description"]) > 0
    
    assert metadata["tags"]
    assert isinstance(metadata["tags"], list)
    assert len(metadata["tags"]) > 0
    
    # Text content may be empty but should be a string
    assert isinstance(metadata["text_content"], str)

@pytest.mark.asyncio
async def test_process_image_no_text(image_processor, tmp_path):
    """Test processing an image without text."""
    from PIL import Image
    
    # Create a simple image without text
    img = Image.new('RGB', (100, 100), color='blue')
    image_path = tmp_path / "test_image_no_text.png"
    img.save(image_path)
    
    metadata = await image_processor.process_image(Path(image_path))
    
    # Should still have description and tags, but minimal text content
    assert metadata["description"]
    assert metadata["tags"]
    assert isinstance(metadata["text_content"], str)  # Should be empty or minimal
