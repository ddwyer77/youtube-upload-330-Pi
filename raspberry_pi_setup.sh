#!/bin/bash
# Setup script for YouTube Shorts Uploader on Raspberry Pi
# This script sets up the necessary dependencies and service configuration

set -e  # Exit on error

echo "=== YouTube Shorts Uploader for Raspberry Pi Setup ==="
echo ""

# Create directories
echo "Creating directories..."
mkdir -p ~/videos
mkdir -p ~/.youtube_shorts_uploader

# Install dependencies
echo "Updating package lists..."
sudo apt update

echo "Installing dependencies..."
sudo apt install -y python3 python3-pip git

echo "Installing Python packages..."
pip3 install google-auth google-auth-oauthlib google-api-python-client

# Check if we're in the right directory
if [ ! -f "scheduler_service.py" ]; then
    echo "Error: scheduler_service.py not found"
    echo "Please run this script from the root of the youtube-upload-330-Pi repository"
    exit 1
fi

# Make scheduler service executable
chmod +x scheduler_service.py

# Setup config directory
CONFIG_DIR=~/.youtube_shorts_uploader
mkdir -p $CONFIG_DIR

# Create an empty scheduled uploads file if it doesn't exist
if [ ! -f "$CONFIG_DIR/scheduled_uploads.json" ]; then
    echo "Creating empty scheduled uploads file..."
    cp scheduled_uploads_example.json $CONFIG_DIR/scheduled_uploads.json
    # Replace example paths with actual paths
    sed -i "s|/home/pi/videos|$HOME/videos|g" $CONFIG_DIR/scheduled_uploads.json
fi

# Setup systemd service
echo "Setting up systemd service..."
sudo cp youtube-uploader.service /etc/systemd/system/
sudo systemctl daemon-reload

echo "Checking for token.pickle..."
if [ ! -f "token.pickle" ]; then
    echo "WARNING: token.pickle not found. You need to transfer this file from your desktop."
    echo "Run this on your desktop computer:"
    echo "scp token.pickle pi@raspberrypi:~/youtube-upload-330-Pi/"
    echo ""
    echo "Setup will continue, but you'll need the token.pickle file before starting the service."
fi

echo "Checking for client_secrets.json..."
if [ ! -f "client_secrets.json" ]; then
    echo "WARNING: client_secrets.json not found. You need to transfer this file from your desktop."
    echo "Run this on your desktop computer:"
    echo "scp client_secrets.json pi@raspberrypi:~/youtube-upload-330-Pi/"
    echo ""
    echo "Setup will continue, but you'll need the client_secrets.json file before starting the service."
fi

echo ""
echo "=== Setup completed ==="
echo ""
echo "To start the service, run:"
echo "sudo systemctl start youtube-uploader.service"
echo ""
echo "To enable the service to start on boot, run:"
echo "sudo systemctl enable youtube-uploader.service"
echo ""
echo "To check the service status, run:"
echo "sudo systemctl status youtube-uploader.service"
echo ""
echo "Log files will be available at:"
echo "~/youtube_uploader_logs.txt - Main application logs"
echo "~/youtube_uploader_output.log - Service standard output"
echo "~/youtube_uploader_error.log - Service error output"
echo ""
echo "To add videos for uploading, edit the scheduled uploads file:"
echo "nano ~/.youtube_shorts_uploader/scheduled_uploads.json"
echo ""
echo "Copy your videos to the ~/videos directory"
echo "" 