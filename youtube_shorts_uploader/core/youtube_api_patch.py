"""
YouTubeAPI patch module for the YouTube Shorts Uploader app.
This module provides a simplified implementation of the YouTubeAPI class
that works with the current authentication setup.
"""

import os
import logging
import pickle
import json
import google.auth.transport.requests
from google.oauth2.credentials import Credentials
import googleapiclient.discovery
import googleapiclient.http
import googleapiclient.errors

logger = logging.getLogger(__name__)

class YouTubeAPISimple:
    """
    Simplified implementation of the YouTubeAPI class.
    Uses direct token file access instead of the auth_manager.
    """
    
    # API service constants
    API_SERVICE_NAME = "youtube"
    API_VERSION = "v3"
    
    def __init__(self, token_file="token.pickle"):
        """
        Initialize the YouTube API client.
        
        Args:
            token_file (str): Path to the token pickle file.
        """
        self.token_file = token_file
        self.service = None
        self.credentials = None
        self._initialize_service()
    
    def _initialize_service(self):
        """
        Initialize the YouTube API service.
        
        Returns:
            bool: True if successful, False otherwise.
        """
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
            self.service = googleapiclient.discovery.build(
                self.API_SERVICE_NAME,
                self.API_VERSION,
                credentials=self.credentials,
                cache_discovery=False
            )
            
            logger.info("YouTube API service initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize YouTube API service: {str(e)}")
            self.service = None
            return False
    
    def upload_video(self, video_file, title, description, tags=None, category_id="22", 
                     privacy_status="public", notify_subscribers=True, on_progress=None):
        """
        Upload a video to YouTube.
        
        Args:
            video_file (str): Path to the video file.
            title (str): Video title.
            description (str): Video description.
            tags (list, optional): List of tags.
            category_id (str, optional): YouTube category ID. Default is "22" for People & Blogs.
            privacy_status (str, optional): Privacy status. One of "public", "private", "unlisted".
            notify_subscribers (bool, optional): Whether to notify subscribers.
            on_progress (callable, optional): Callback for upload progress.
            
        Returns:
            dict: Response from the YouTube API or None if the upload failed.
        """
        if not os.path.exists(video_file):
            logger.error(f"Video file not found: {video_file}")
            return None
        
        if not self.service:
            success = self._initialize_service()
            if not success:
                logger.error("Failed to initialize YouTube API service for video upload")
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
                    "selfDeclaredMadeForKids": False,
                    "notifySubscribers": notify_subscribers
                }
            }
            
            # Create a MediaFileUpload object for the video file
            media = googleapiclient.http.MediaFileUpload(
                video_file,
                mimetype="video/*",
                resumable=True,
                chunksize=1024*1024*5  # 5MB chunks
            )
            
            # Create the API request
            request = self.service.videos().insert(
                part=",".join(list(body.keys())),
                body=body,
                media_body=media,
                notifySubscribers=notify_subscribers
            )
            
            # Execute the resumable upload with progress reporting
            logger.info(f"Starting upload for video: {title}")
            response = None
            
            while response is None:
                status, response = request.next_chunk()
                if status and on_progress:
                    on_progress(int(status.progress() * 100))
            
            video_id = response.get("id")
            if video_id:
                logger.info(f"Video uploaded successfully: {video_id}")
                return {"id": video_id, "title": title}
            else:
                logger.error("Video upload failed: No video ID in response")
                return None
                
        except googleapiclient.errors.HttpError as e:
            error_content = json.loads(e.content.decode("utf-8"))
            logger.error(f"YouTube API error: {error_content}")
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
            dict: Channel information.
        """
        if not self.service:
            success = self._initialize_service()
            if not success:
                logger.error("Failed to initialize YouTube API service")
                return None
        
        try:
            # Get the authenticated user's channel
            request = self.service.channels().list(
                part="snippet,statistics",
                mine=True
            )
            response = request.execute()
            
            if not response.get("items"):
                logger.warning("No channel found for the authenticated user")
                return None
            
            # Extract relevant channel information
            channel = response["items"][0]
            channel_info = {
                "id": channel["id"],
                "title": channel["snippet"]["title"],
                "description": channel["snippet"].get("description", ""),
                "customUrl": channel["snippet"].get("customUrl", ""),
                "thumbnails": channel["snippet"].get("thumbnails", {}),
                "statistics": channel.get("statistics", {})
            }
            
            logger.info(f"Retrieved channel info for {channel_info['title']}")
            return channel_info
            
        except googleapiclient.errors.HttpError as e:
            error_content = json.loads(e.content.decode("utf-8"))
            logger.error(f"YouTube API error: {error_content}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting channel info: {str(e)}")
            return None

# Function to apply the patch
def patch_youtube_api():
    """
    Apply the YouTube API patch to the application.
    
    This function should be called before using the YouTube API,
    typically at application startup.
    """
    try:
        from youtube_shorts_uploader.core.youtube_api import YouTubeAPI
        import types
        
        # Replace the YouTubeAPI class with our simplified version
        original_init = YouTubeAPI.__init__
        
        # Define the patched init method
        def patched_init(self, auth_manager):
            """Patched init method that initializes with direct token access."""
            self.auth_manager = auth_manager
            self.service = None
            
            # Initialize with simpler API
            simple_api = YouTubeAPISimple()
            self.service = simple_api.service
            self.credentials = simple_api.credentials
            
            logger.info("Patched YouTube API client initialized")
        
        # Define the patched upload method
        def patched_upload_video(self, video_file, title, description, tags=None, category_id="22", 
                             privacy_status="public", notify_subscribers=True, on_progress=None):
            """Patched upload method that uses the simplified implementation."""
            simple_api = YouTubeAPISimple()
            return simple_api.upload_video(
                video_file, title, description, tags, category_id, 
                privacy_status, notify_subscribers, on_progress
            )
        
        # Apply the patches
        YouTubeAPI.__init__ = patched_init
        YouTubeAPI.upload_video = patched_upload_video
        
        logger.info("Applied YouTube API patch")
        return True
    
    except Exception as e:
        logger.error(f"Error applying YouTube API patch: {str(e)}")
        return False 