#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Install dependencies if needed
pip install -r requirements.txt

# Create resources directory if it doesn't exist
mkdir -p youtube_shorts_uploader/resources

# Copy necessary files
cp client_secrets.json youtube_shorts_uploader/
cp yolov8n.pt youtube_shorts_uploader/

# Build the application
pyinstaller --windowed \
    --name "YouTube Shorts Uploader" \
    --add-data "youtube_shorts_uploader/client_secrets.json:." \
    --add-data "youtube_shorts_uploader/yolov8n.pt:." \
    run.py

echo "Build complete! The application is in the dist folder." 