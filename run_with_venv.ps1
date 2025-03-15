# PowerShell script to run the Image Tagger application with the virtual environment

# Determine the script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Parse command line arguments
param(
    [string]$Host = "127.0.0.1",
    [string]$Port = "8000",
    [switch]$NoBrowser
)

# Check if virtual environment exists
if (-not (Test-Path "$ScriptDir\venv")) {
    Write-Host "Virtual environment not found. Creating one..."
    python -m venv "$ScriptDir\venv"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to create virtual environment. Make sure Python is installed."
        exit 1
    }
}

# Activate the virtual environment
Write-Host "Activating virtual environment..."
try {
    & "$ScriptDir\venv\Scripts\Activate.ps1"
}
catch {
    Write-Host "Failed to activate virtual environment. Make sure it exists and is properly set up."
    Write-Host "You can create it with: python -m venv venv"
    exit 1
}

# Install dependencies if needed
if (-not (Test-Path "$ScriptDir\venv\Lib\site-packages\fastapi")) {
    Write-Host "Installing dependencies..."
    pip install -r "$ScriptDir\backend\requirements.txt"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install dependencies."
        exit 1
    }
}

# Set environment variables
$env:API_HOST = $Host
$env:API_PORT = $Port

# Change to the backend directory
Set-Location "$ScriptDir\backend"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to change to backend directory."
    exit 1
}

# Run the application
Write-Host "Starting server at http://$Host`:$Port"
if ($NoBrowser) {
    python main.py
}
else {
    # Start the server
    $ServerProcess = Start-Process -FilePath python -ArgumentList "main.py" -PassThru -NoNewWindow
    
    # Wait a moment for the server to start
    Start-Sleep -Seconds 2
    
    # Open the browser
    Start-Process "http://$Host`:$Port"
    
    # Wait for the server process to finish
    Wait-Process -InputObject $ServerProcess
}

# Deactivate the virtual environment when done
deactivate 
