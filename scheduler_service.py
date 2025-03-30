#!/usr/bin/env python3
"""
YouTube Shorts Uploader Scheduler Service for Raspberry Pi

This service runs in the background and processes scheduled uploads
even when the main computer is turned off. It's designed to be run
as a systemd service on a Raspberry Pi or other always-on device.
"""

import os
import sys
import json
import time
import logging
import datetime
import traceback
from pathlib import Path
import pickle
import google.auth.transport.requests
from google.oauth2.credentials import Credentials
import googleapiclient.discovery
import googleapiclient.http

# Configure logging
LOG_FILE = os.path.expanduser("~/youtube_uploader_logs.txt")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("uploader_service")

# Constants
TOKEN_FILE = "token.pickle"
CONFIG_DIR = os.path.expanduser("~/.youtube_shorts_uploader")
SCHEDULED_UPLOADS_FILE = os.path.join(CONFIG_DIR, "scheduled_uploads.json")
CHECK_INTERVAL = 300  # Check for uploads every 5 minutes (300 seconds)

class YouTubeUploader:
    """
    Simple YouTube video uploader class.
    """
    
    def __init__(self, token_file=TOKEN_FILE):
        """
        Initialize the YouTube uploader.
        
        Args:
            token_file (str): Path to the token pickle file.
        """
        self.token_file = token_file
        self.youtube = None
        self.credentials = None
        
        # Initialize the YouTube API service
        self._initialize()
    
    def _initialize(self):
        """Initialize the YouTube API service."""
        try:
            if not os.path.exists(self.token_file):
                logger.error(f"Token file not found: {self.token_file}")
                return False
            
            # Load credentials
            with open(self.token_file, "rb") as token:
                self.credentials = pickle.load(token)
            
            # Refresh if expired
            if self.credentials.expired and self.credentials.refresh_token:
                logger.info("Refreshing expired credentials")
                self.credentials.refresh(google.auth.transport.requests.Request())
                # Save the refreshed credentials
                with open(self.token_file, "wb") as token:
                    pickle.dump(self.credentials, token)
            
            # Build the YouTube API service
            self.youtube = googleapiclient.discovery.build(
                "youtube", "v3",
                credentials=self.credentials,
                cache_discovery=False
            )
            
            logger.info("YouTube API service initialized")
            return True
        
        except Exception as e:
            logger.error(f"Error initializing YouTube API: {str(e)}")
            traceback.print_exc()
            return False
    
    def upload_video(self, video_file, title, description, tags=None,
                     category_id="22", privacy_status="unlisted", 
                     made_for_kids=False, notify_subscribers=False):
        """
        Upload a video to YouTube.
        
        Args:
            video_file (str): Path to the video file.
            title (str): Video title.
            description (str): Video description.
            tags (list, optional): List of tags.
            category_id (str, optional): YouTube category ID (default: "22" for People & Blogs).
            privacy_status (str, optional): Privacy status (default: "unlisted").
            made_for_kids (bool, optional): Whether the video is made for kids (default: False).
            notify_subscribers (bool, optional): Whether to notify subscribers (default: False).
            
        Returns:
            dict: YouTube API response, or None if upload failed.
        """
        if not self.youtube:
            logger.error("YouTube API service not initialized")
            return None
        
        if not os.path.exists(video_file):
            logger.error(f"Video file not found: {video_file}")
            return None
        
        try:
            # Define video metadata
            body = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags or [],
                    "categoryId": category_id
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "selfDeclaredMadeForKids": made_for_kids,
                    "notifySubscribers": notify_subscribers
                }
            }
            
            # Setup for resumable upload
            logger.info(f"Preparing to upload: {video_file}")
            file_size_mb = os.path.getsize(video_file) / (1024 * 1024)
            logger.info(f"Video file size: {file_size_mb:.2f} MB")
            
            # Create a MediaFileUpload object
            media = googleapiclient.http.MediaFileUpload(
                video_file,
                mimetype="video/*",
                resumable=True,
                chunksize=1024*1024*5  # 5MB chunks
            )
            
            # Create the API request
            request = self.youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media,
                notifySubscribers=notify_subscribers
            )
            
            # Execute the resumable upload with progress reporting
            logger.info(f"Starting video upload for '{title}'...")
            response = None
            
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.info(f"Upload progress: {progress}%")
            
            video_id = response.get("id")
            if video_id:
                logger.info(f"Upload successful! Video ID: {video_id}")
                logger.info(f"Video URL: https://www.youtube.com/watch?v={video_id}")
                return response
            else:
                logger.error("Upload failed: No video ID in response")
                return None
        
        except googleapiclient.errors.HttpError as e:
            import json
            error_content = json.loads(e.content.decode("utf-8"))
            logger.error(f"YouTube API HTTP error {e.resp.status}: {error_content}")
            return None
        
        except Exception as e:
            logger.error(f"Error uploading video: {str(e)}")
            traceback.print_exc()
            return None

def ensure_config_dir():
    """Ensure the configuration directory exists."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    
    # Create the scheduled uploads file if it doesn't exist
    if not os.path.exists(SCHEDULED_UPLOADS_FILE):
        with open(SCHEDULED_UPLOADS_FILE, 'w') as f:
            json.dump({"scheduled_uploads": []}, f)
        logger.info(f"Created empty scheduled uploads file: {SCHEDULED_UPLOADS_FILE}")

def load_scheduled_uploads():
    """Load the scheduled uploads from the configuration file."""
    try:
        with open(SCHEDULED_UPLOADS_FILE, 'r') as f:
            data = json.load(f)
        
        scheduled_uploads = data.get("scheduled_uploads", [])
        logger.info(f"Loaded {len(scheduled_uploads)} scheduled uploads")
        return scheduled_uploads
    
    except Exception as e:
        logger.error(f"Error loading scheduled uploads: {str(e)}")
        return []

def save_scheduled_uploads(scheduled_uploads):
    """Save the scheduled uploads to the configuration file."""
    try:
        with open(SCHEDULED_UPLOADS_FILE, 'w') as f:
            json.dump({"scheduled_uploads": scheduled_uploads}, f, indent=2)
        
        logger.info(f"Saved {len(scheduled_uploads)} scheduled uploads")
        return True
    
    except Exception as e:
        logger.error(f"Error saving scheduled uploads: {str(e)}")
        return False

def process_scheduled_uploads():
    """Process any scheduled uploads that are due."""
    logger.info("Checking for scheduled uploads...")
    
    # Get the current time
    now = datetime.datetime.now()
    
    # Load the scheduled uploads
    scheduled_uploads = load_scheduled_uploads()
    
    # Track which uploads were processed
    processed_uploads = []
    uploads_to_keep = []
    
    # Create the YouTube uploader
    uploader = YouTubeUploader()
    
    # Process each scheduled upload
    for upload in scheduled_uploads:
        try:
            # Parse the scheduled time
            scheduled_time = datetime.datetime.fromisoformat(upload["scheduled_time"])
            
            # Check if the upload is due
            if now >= scheduled_time:
                logger.info(f"Processing scheduled upload: {upload['title']}")
                
                # Upload the video
                response = uploader.upload_video(
                    video_file=upload["file_path"],
                    title=upload["title"],
                    description=upload["description"],
                    tags=upload.get("tags", []),
                    privacy_status=upload.get("privacy", "unlisted")
                )
                
                if response:
                    logger.info(f"Successfully uploaded: {upload['title']}")
                    
                    # Record the upload as processed
                    upload["video_id"] = response.get("id")
                    upload["uploaded_at"] = datetime.datetime.now().isoformat()
                    upload["status"] = "completed"
                    processed_uploads.append(upload)
                else:
                    logger.error(f"Failed to upload: {upload['title']}")
                    
                    # Keep the upload but mark it as failed
                    upload["status"] = "failed"
                    upload["failure_time"] = datetime.datetime.now().isoformat()
                    uploads_to_keep.append(upload)
            else:
                # This upload is not yet due
                logger.info(f"Upload not yet due: {upload['title']} (scheduled for {scheduled_time})")
                uploads_to_keep.append(upload)
        
        except Exception as e:
            logger.error(f"Error processing upload {upload.get('title', 'unknown')}: {str(e)}")
            traceback.print_exc()
            
            # Keep the upload but mark it as error
            upload["status"] = "error"
            upload["error_message"] = str(e)
            upload["error_time"] = datetime.datetime.now().isoformat()
            uploads_to_keep.append(upload)
    
    # Save the updated scheduled uploads
    save_scheduled_uploads(uploads_to_keep)
    
    # Save processed uploads to a history file
    if processed_uploads:
        history_file = os.path.join(CONFIG_DIR, "upload_history.json")
        
        try:
            # Load existing history
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    history = json.load(f)
            else:
                history = {"uploads": []}
            
            # Add the processed uploads
            history["uploads"].extend(processed_uploads)
            
            # Save the updated history
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=2)
            
            logger.info(f"Saved {len(processed_uploads)} uploads to history")
        
        except Exception as e:
            logger.error(f"Error saving upload history: {str(e)}")
    
    logger.info(f"Processed {len(processed_uploads)} uploads, {len(uploads_to_keep)} remaining")

def main():
    """Main entry point for the scheduler service."""
    logger.info("Starting YouTube Shorts Uploader Scheduler Service")
    
    # Ensure the configuration directory exists
    ensure_config_dir()
    
    # Main service loop
    while True:
        try:
            # Process any scheduled uploads
            process_scheduled_uploads()
        
        except Exception as e:
            logger.error(f"Error in scheduler service: {str(e)}")
            traceback.print_exc()
        
        # Sleep for the check interval
        logger.info(f"Sleeping for {CHECK_INTERVAL} seconds")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main() 