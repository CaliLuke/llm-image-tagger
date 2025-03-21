import pytest
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import logging

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

@pytest.mark.skip(reason="Frontend tests require a running browser and server")
def test_frontend_queue(mock_server, test_dir, test_images):
    """Test the frontend functionality with both legacy and queue-based processing."""
    logger.info("Starting frontend queue functionality test")
    
    # Set the current folder
    mock_server.app.state.current_folder = test_dir
    logger.debug(f"Set current folder to: {test_dir}")
    
    # First, open a folder to initialize the queue
    logger.debug("Opening folder to initialize queue")
    response = mock_server.post("/images", json={"folder_path": str(test_dir)})
    assert response.status_code == 200
    logger.info("Folder opened successfully")
    
    # Set up Chrome options for headless mode
    logger.debug("Setting up Chrome options for headless mode")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Initialize the driver
    try:
        driver = webdriver.Chrome(options=chrome_options)
        
        # Navigate to the application
        driver.get("http://localhost:8000")
        
        # Wait for the folder input to be visible
        folder_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Enter folder path...']"))
        )
        
        # Enter the folder path
        folder_input.send_keys(str(test_dir))
        
        # Find and click the Open Folder button
        open_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Open Folder')]")
        open_button.click()
        
        # Wait for the images to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".grid"))
        )
        
        logger.info("Images loaded successfully")
        
        # Test legacy processing
        logger.info("\nTesting legacy processing...")
        
        # Find and click the Process All button
        process_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Process All')]"))
        )
        process_button.click()
        
        # Wait for processing to start
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".bg-green-600.h-2\\.5"))
        )
        
        logger.info("Legacy processing started successfully")
        
        # Wait for the Process All button to reappear
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Process All')]"))
        )
        
        # Test queue-based processing
        logger.info("\nTesting queue-based processing...")
        
        # Find and click the queue toggle
        queue_toggle = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "useQueueToggle"))
        )
        queue_toggle.click()
        
        # Wait for the queue status to appear
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//h3[contains(text(), 'Queue Status')]"))
        )
        
        logger.info("Queue toggle enabled successfully")
        
        # Find and click the Process All button again
        process_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Process All')]"))
        )
        process_button.click()
        
        # Wait for processing to start
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".bg-green-600.h-2\\.5"))
        )
        
        logger.info("Queue-based processing started successfully")
        
        # Test direct queue controls
        logger.info("\nTesting direct queue controls...")
        
        # Clear the queue
        clear_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Clear Queue')]"))
        )
        clear_button.click()
        
        logger.info("Queue cleared successfully")
        
        # Get queue status
        response = mock_server.get("/queue/status", params={"detailed": "true"})
        assert response.status_code == 200
        logger.info("Queue status:", response.json())
        
        logger.info("All frontend queue tests passed!")
        
    except Exception as e:
        logger.error(f"Error testing frontend: {str(e)}")
        raise
    finally:
        # Close the driver
        if 'driver' in locals():
            driver.quit() 
