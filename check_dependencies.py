#!/usr/bin/env python3
"""
Dependency checker for llm-image-tagger
This script checks for all required dependencies and provides
detailed diagnostic information.
"""

import os
import sys
import platform
import subprocess
from pathlib import Path
import importlib.util
import pkg_resources
from pkg_resources import DistributionNotFound, VersionConflict
import json

def print_header(text):
    """Print a section header."""
    print("\n" + "=" * 60)
    print(f" {text}")
    print("=" * 60)

def check_python_version():
    """Check if the Python version meets requirements."""
    print_header("Python Version")
    
    # Get Python version
    py_version = sys.version_info
    print(f"Current Python version: {sys.version}")
    
    # Check if version is 3.11+
    if py_version.major == 3 and py_version.minor >= 11:
        print("✅ Python 3.11+ requirement met")
        return True
    else:
        print("❌ Python 3.11+ required, but running %d.%d" % (py_version.major, py_version.minor))
        return False

def check_virtual_env():
    """Check if running in a virtual environment."""
    print_header("Virtual Environment")
    
    if sys.prefix != sys.base_prefix:
        print(f"✅ Virtual environment detected: {sys.prefix}")
        return True
    else:
        print("❌ Not running in a virtual environment")
        print("Please activate your virtual environment:")
        print("   source venv/bin/activate  # On Unix/macOS")
        print("   venv\\Scripts\\activate  # On Windows")
        return False

def check_exempi():
    """Check Exempi installation."""
    print_header("Exempi Installation")
    
    # Try to import libxmp
    try:
        import libxmp
        from libxmp import XMPMeta
        # Create a simple XMP object as a test
        xmp = XMPMeta()
        print("✅ XMP support is available (python-xmp-toolkit and Exempi working)")
        return True
    except ImportError as e:
        if "libxmp" in str(e):
            print("❌ python-xmp-toolkit package is missing")
            print("   Run: pip install python-xmp-toolkit")
        else:
            print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ XMP support is not available: {e}")
        
        # Check for Exempi installation
        system = platform.system().lower()
        
        if system == "darwin":  # macOS
            print("\nChecking for Exempi on macOS:")
            paths = [
                "/opt/homebrew/lib/libexempi.dylib",
                "/usr/local/lib/libexempi.dylib",
                "/opt/local/lib/libexempi.dylib",
            ]
            
            found = False
            for path in paths:
                if Path(path).exists():
                    print(f"✅ Found Exempi at: {path}")
                    print(f"   DYLD_LIBRARY_PATH should include: {Path(path).parent}")
                    found = True
                    break
            
            if not found:
                print("❌ Exempi library not found")
                print("   Install it with: brew install exempi")
            
            # Check if environment variable is set
            if "DYLD_LIBRARY_PATH" in os.environ:
                print(f"ℹ️ DYLD_LIBRARY_PATH is set to: {os.environ['DYLD_LIBRARY_PATH']}")
            else:
                print("ℹ️ DYLD_LIBRARY_PATH is not set")
            
        elif system == "linux":  # Linux
            print("\nChecking for Exempi on Linux:")
            paths = [
                "/usr/lib/libexempi.so",
                "/usr/lib/x86_64-linux-gnu/libexempi.so",
                "/usr/lib64/libexempi.so",
            ]
            
            found = False
            for path in paths:
                if Path(path).exists():
                    print(f"✅ Found Exempi at: {path}")
                    print(f"   LD_LIBRARY_PATH should include: {Path(path).parent}")
                    found = True
                    break
            
            if not found:
                print("❌ Exempi library not found")
                print("   Install it with: sudo apt-get install libexempi3 libexempi-dev")
            
            # Check if environment variable is set
            if "LD_LIBRARY_PATH" in os.environ:
                print(f"ℹ️ LD_LIBRARY_PATH is set to: {os.environ['LD_LIBRARY_PATH']}")
            else:
                print("ℹ️ LD_LIBRARY_PATH is not set")
                
        elif system == "windows":  # Windows
            print("\nChecking for Exempi on Windows:")
            print("ℹ️ On Windows, Exempi should be in your PATH")
            print("   Check if exempi.dll is accessible")
            
        print("\nSolution:")
        print("1. Ensure Exempi is installed")
        print("2. Run: source setup_exempi.sh")
        print("3. If that doesn't work, set the environment variable manually:")
        if system == "darwin":
            print("   export DYLD_LIBRARY_PATH=/path/to/exempi/lib:$DYLD_LIBRARY_PATH")
        elif system == "linux":
            print("   export LD_LIBRARY_PATH=/path/to/exempi/lib:$LD_LIBRARY_PATH")
        elif system == "windows":
            print("   Add the Exempi directory to your PATH")
        
        return False

def check_pip_packages():
    """Check if all required pip packages are installed."""
    print_header("Pip Packages")
    
    # Read requirements from requirements.txt
    try:
        with open("requirements.txt", "r") as f:
            requirements = []
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("-"):
                    # Ignore markers/conditions for now (e.g. ;python_version>=...)
                    req = line.split(";")[0].strip()
                    if req:
                        requirements.append(req)
        
        print(f"Found {len(requirements)} requirements in requirements.txt")
        
        # Check each requirement
        missing = []
        for req in requirements:
            try:
                pkg_resources.require(req)
                # print(f"✅ {req}")
            except (DistributionNotFound, VersionConflict) as e:
                missing.append((req, str(e)))
        
        if missing:
            print(f"❌ {len(missing)} packages missing or version mismatch:")
            for req, error in missing:
                print(f"  • {req}: {error}")
            print("\nRun: pip install -r requirements.txt")
            return False
        else:
            print("✅ All required packages are installed with correct versions")
            return True
                
    except FileNotFoundError:
        print("❌ requirements.txt not found")
        return False

def check_ollama():
    """Check Ollama installation and models."""
    print_header("Ollama Installation")
    
    try:
        # Check if ollama is in PATH
        result = subprocess.run(["which", "ollama"], 
                               capture_output=True, text=True, check=False)
        
        if result.returncode == 0:
            ollama_path = result.stdout.strip()
            print(f"✅ Ollama found at: {ollama_path}")
            
            # Check if the ollama service is running
            ps_result = subprocess.run(["ps", "aux"], 
                                      capture_output=True, text=True, check=False)
            
            if "ollama serve" in ps_result.stdout:
                print("✅ Ollama service is running")
            else:
                print("❌ Ollama service doesn't appear to be running")
                print("   Start it with: ollama serve")
            
            # Check for required models
            try:
                models_result = subprocess.run(["ollama", "list"], 
                                            capture_output=True, text=True, check=False)
                
                if models_result.returncode == 0:
                    print("\nInstalled models:")
                    for line in models_result.stdout.strip().split("\n")[1:]:  # Skip header
                        print(f"  • {line}")
                    
                    required_models = ["gemma3:4b"]
                    optional_models = ["llama3:8b-vision"]
                    missing_required = []
                    missing_optional = []
                    
                    for model in required_models:
                        if model not in models_result.stdout:
                            missing_required.append(model)
                    
                    for model in optional_models:
                        if model not in models_result.stdout:
                            missing_optional.append(model)
                    
                    if missing_required:
                        print("\n❌ Required models not found:")
                        for model in missing_required:
                            print(f"   Pull with: ollama pull {model}")
                    else:
                        print("\n✅ All required models are installed")
                    
                    if missing_optional:
                        print("\nℹ️ Optional models not found (but not required):")
                        for model in missing_optional:
                            print(f"   Pull with: ollama pull {model}")
                    
                else:
                    print(f"❌ Failed to list Ollama models: {models_result.stderr}")
            
            except Exception as e:
                print(f"❌ Error checking Ollama models: {e}")
            
            return not missing_required
        else:
            print("❌ Ollama not found in PATH")
            print("   Install from: https://ollama.com/")
            return False
            
    except Exception as e:
        print(f"❌ Error checking Ollama: {e}")
        return False

def check_system_info():
    """Display system information."""
    print_header("System Information")
    
    print(f"OS: {platform.system()} {platform.release()} ({platform.version()})")
    print(f"Architecture: {platform.machine()}")
    print(f"Python executable: {sys.executable}")
    
    # Check if path contains spaces or non-ASCII characters
    if " " in sys.executable or not all(ord(c) < 128 for c in sys.executable):
        print("⚠️ Warning: Python path contains spaces or non-ASCII characters")
        print("   This may cause issues with some libraries")

def main():
    """Run all checks and provide a summary."""
    print("\n" + "=" * 80)
    print(" LLM Image Tagger - Dependency Checker".center(80))
    print("=" * 80)
    
    # Run all checks
    check_system_info()
    python_ok = check_python_version()
    venv_ok = check_virtual_env()
    packages_ok = check_pip_packages()
    ollama_ok = check_ollama()
    exempi_ok = check_exempi()
    
    # Summary
    print_header("Summary")
    results = {
        "Python 3.11+": python_ok,
        "Virtual Environment": venv_ok,
        "Required Packages": packages_ok,
        "Ollama": ollama_ok,
        "Exempi/XMP Support": exempi_ok
    }
    
    all_ok = all(results.values())
    
    for check, ok in results.items():
        status = "✅" if ok else "❌"
        print(f"{status} {check}")
    
    if all_ok:
        print("\n✅ All dependencies are correctly installed and configured.")
        print("   Ready to run the application with: python run.py")
    else:
        print("\n❌ Some dependencies are missing or improperly configured.")
        print("   Please fix the issues above before running the application.")
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main()) 