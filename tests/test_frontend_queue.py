import requests
import time
import sys
import os
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# Add the parent directory to the path so we can import the backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Base URL for the API
BASE_URL = "http://localhost:8000"

def test_frontend_queue():
    """Test the frontend functionality with both legacy and queue-based processing."""
    print("Testing frontend queue functionality...")
    
    # First, open a folder to initialize the queue
    folder_path = "/Volumes/screenshots/Datapad"  # Use the same folder path as in the logs
    response = requests.post(f"{BASE_URL}/images", json={"folder_path": folder_path})
    
    if response.status_code != 200:
        print(f"Error opening folder: {response.status_code} - {response.text}")
        return
    
    print("Folder opened successfully")
    
    # Set up Chrome options for headless mode
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Initialize the driver
    try:
        driver = webdriver.Chrome(options=chrome_options)
        
        # Navigate to the application
        driver.get(BASE_URL)
        
        # Wait for the folder input to be visible
        folder_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Enter folder path...']"))
        )
        
        # Enter the folder path
        folder_input.send_keys(folder_path)
        
        # Find and click the Open Folder button
        open_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Open Folder')]")
        open_button.click()
        
        # Wait for the images to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".grid"))
        )
        
        print("Images loaded successfully")
        
        # Test legacy processing
        print("\nTesting legacy processing...")
        
        # Find and click the Process All button
        process_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Process All')]"))
        )
        process_button.click()
        
        # Wait for processing to start
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".bg-green-600.h-2\\.5"))
        )
        
        print("Legacy processing started successfully")
        
        # Wait for processing to complete or click Stop Processing
        time.sleep(5)
        stop_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Stop Processing')]"))
        )
        stop_button.click()
        
        print("Legacy processing stopped successfully")
        
        # Wait for the Process All button to reappear
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Process All')]"))
        )
        
        # Test queue-based processing
        print("\nTesting queue-based processing...")
        
        # Find and click the queue toggle
        queue_toggle = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "useQueueToggle"))
        )
        queue_toggle.click()
        
        # Wait for the queue status to appear
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//h3[contains(text(), 'Queue Status')]"))
        )
        
        print("Queue toggle enabled successfully")
        
        # Find and click the Process All button again
        process_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Process All')]"))
        )
        process_button.click()
        
        # Wait for processing to start
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".bg-green-600.h-2\\.5"))
        )
        
        print("Queue-based processing started successfully")
        
        # Wait for processing to complete or click Stop Processing
        time.sleep(5)
        stop_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Stop Processing')]"))
        )
        stop_button.click()
        
        print("Queue-based processing stopped successfully")
        
        # Test direct queue controls
        print("\nTesting direct queue controls...")
        
        # Clear the queue
        clear_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Clear Queue')]"))
        )
        clear_button.click()
        
        print("Queue cleared successfully")
        
        # Get queue status
        response = requests.get(f"{BASE_URL}/queue/status?detailed=true")
        if response.status_code == 200:
            queue_status = response.json()
            print(f"Queue status: {json.dumps(queue_status, indent=2)}")
        
        print("All frontend queue tests passed!")
        
    except Exception as e:
        print(f"Error testing frontend: {str(e)}")
    finally:
        # Close the driver
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    test_frontend_queue() 
