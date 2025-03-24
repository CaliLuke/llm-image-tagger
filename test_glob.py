from pathlib import Path
import os

def main():
    folder_path = Path('/Volumes/screenshots/Dremio')
    print(f"Testing path: {folder_path}")
    print(f"Path exists: {folder_path.exists()}")
    print(f"Is directory: {folder_path.is_dir()}")
    
    # Extensions to test - match the app's settings
    # In settings.py: SUPPORTED_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp"]
    extensions = ['.png', '.jpg', '.jpeg', '.webp']
    
    # Test with Path.glob exactly as the app does
    print("\nTesting with Path.glob EXACTLY as the app does:")
    image_files = []
    for ext in extensions:
        # The app has a bug here - it uses ext.lower() instead of ext[1:].lower()
        # But ext already has a leading dot, so we end up with "*.png" not "*.png"
        # Let's see if this is the issue:
        
        # This is what the app actually does:
        lower_pattern = f"*.{ext.lower()}"
        upper_pattern = f"*.{ext.upper()}"
        
        # What the app should do is:
        # lower_pattern = f"*.{ext[1:].lower()}"  # Remove the leading dot first
        # upper_pattern = f"*.{ext[1:].upper()}"  # Remove the leading dot first
        
        print(f"  Using pattern: {lower_pattern}")
        lower_results = list(folder_path.glob(lower_pattern))
        print(f"  Using pattern: {upper_pattern}")
        upper_results = list(folder_path.glob(upper_pattern))
        
        print(f"  Extension {ext}: {len(lower_results)} files (lowercase), {len(upper_results)} files (uppercase)")
        
        if lower_results:
            print(f"    First few files: {[f.name for f in lower_results[:3]]}")
            
        image_files.extend(lower_results)
        image_files.extend(upper_results)
    
    print(f"Total files found with app's current Path.glob pattern: {len(image_files)}")
    
    # Now test with the correct pattern format
    print("\nTesting with CORRECT Path.glob pattern:")
    correct_image_files = []
    for ext in extensions:
        # The correct pattern should be:
        correct_lower = f"*.{ext[1:].lower()}"  # Remove the leading dot
        correct_upper = f"*.{ext[1:].upper()}"  # Remove the leading dot
        
        print(f"  Using pattern: {correct_lower}")
        lower_results = list(folder_path.glob(correct_lower))
        print(f"  Using pattern: {correct_upper}")
        upper_results = list(folder_path.glob(correct_upper))
        
        print(f"  Extension {ext}: {len(lower_results)} files (lowercase), {len(upper_results)} files (uppercase)")
        
        if lower_results:
            print(f"    First few files: {[f.name for f in lower_results[:3]]}")
            
        correct_image_files.extend(lower_results)
        correct_image_files.extend(upper_results)
    
    print(f"Total files found with corrected Path.glob pattern: {len(correct_image_files)}")

if __name__ == "__main__":
    main() 
