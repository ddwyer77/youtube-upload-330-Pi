#!/usr/bin/env python3
"""
Simplified YouTube Video Uploader for the YouTube Shorts Uploader app.
This script provides a cleaner interface to upload videos to YouTube.
"""

import os
import sys
import logging
import pickle
import google.auth.transport.requests
from google.oauth2.credentials import Credentials
import googleapiclient.discovery
import googleapiclient.http
import googleapiclient.errors

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("youtube_uploader")

class YouTubeUploader:
    """
    Simple YouTube video uploader class.
    """
    
    def __init__(self, token_file="token.pickle"):
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
            return False
    
    def upload_video(self, video_file, title, description, tags=None,
                     category_id="22", privacy_status="unlisted", 
                     made_for_kids=False, notify_subscribers=False,
                     progress_callback=None):
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
            progress_callback (callable, optional): Callback function for upload progress.
            
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
            logger.info("Starting video upload...")
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status and progress_callback:
                    progress_callback(int(status.progress() * 100))
            
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
            import traceback
            traceback.print_exc()
            return None
    
    def get_channel_info(self):
        """
        Get information about the authenticated user's channel.
        
        Returns:
            dict: Channel information, or None if retrieval failed.
        """
        if not self.youtube:
            logger.error("YouTube API service not initialized")
            return None
        
        try:
            # Get the authenticated user's channel
            request = self.youtube.channels().list(
                part="snippet,statistics,contentDetails",
                mine=True
            )
            response = request.execute()
            
            if response.get("items"):
                channel = response["items"][0]
                logger.info(f"Channel found: {channel['snippet']['title']}")
                return channel
            else:
                logger.error("No channel found for the authenticated user")
                return None
        
        except Exception as e:
            logger.error(f"Error getting channel info: {str(e)}")
            return None

# Example usage
def main():
    """Example usage of the YouTubeUploader class."""
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <video_file>")
        return 1
    
    video_file = sys.argv[1]
    if not os.path.exists(video_file):
        print(f"Error: Video file not found: {video_file}")
        return 1
    
    # Create the uploader
    uploader = YouTubeUploader()
    
    # Define progress callback
    def on_progress(percentage):
        print(f"Upload progress: {percentage}%")
    
    # Upload a video
    response = uploader.upload_video(
        video_file=video_file,
        title="Test Upload from Simple Uploader",
        description="This is a test upload from the simplified YouTube uploader script.",
        tags=["test", "upload", "api"],
        privacy_status="unlisted",
        progress_callback=on_progress
    )
    
    if response:
        print(f"Upload successful! Video ID: {response['id']}")
        return 0
    else:
        print("Upload failed. Check logs for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 