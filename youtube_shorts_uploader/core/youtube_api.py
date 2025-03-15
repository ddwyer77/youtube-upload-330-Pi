import os
import logging
import time
import json
import googleapiclient.discovery
import googleapiclient.errors
import googleapiclient.http
from googleapiclient.http import MediaFileUpload
from pathlib import Path
from .auth_manager import AuthManager

logger = logging.getLogger(__name__)

class YouTubeAPI:
    """
    Handles interactions with the YouTube API.
    Supports video uploads, metadata updates, and channel info.
    """
    
    # API service constants
    API_SERVICE_NAME = "youtube"
    API_VERSION = "v3"
    
    def __init__(self, auth_manager):
        """
        Initialize the YouTube API client.
        
        Args:
            auth_manager (AuthManager): Authentication manager for accessing the API.
        """
        self.auth_manager = auth_manager
        self.service = None
        self._initialize_service()
        
        logger.info("YouTube API client initialized")
    
    def _initialize_service(self):
        """
        Initialize the YouTube API service.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # Get credentials from auth manager
            credentials = self.auth_manager.get_credentials()
            
            if not credentials:
                logger.error("No credentials available for the YouTube API service")
                return False
            
            # Build the YouTube API service
            self.service = googleapiclient.discovery.build(
                self.API_SERVICE_NAME, 
                self.API_VERSION, 
                credentials=credentials,
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
            media = MediaFileUpload(
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
            
            # Upload the video
            video_id = self._resumable_upload(request, on_progress=on_progress)
            
            if video_id:
                logger.info(f"Video uploaded successfully: {video_id}")
                return {"id": video_id, "title": title}
            else:
                logger.error("Video upload failed")
                return None
                
        except googleapiclient.errors.HttpError as e:
            error_content = json.loads(e.content.decode("utf-8"))
            logger.error(f"YouTube API error: {error_content}")
            return None
            
        except Exception as e:
            logger.error(f"Error uploading video: {str(e)}")
            return None
    
    def _resumable_upload(self, request, max_retries=10, on_progress=None):
        """
        Execute a resumable upload with progress tracking and retries.
        
        Args:
            request: The YouTube API request to execute.
            max_retries (int, optional): Maximum number of retries on failure.
            on_progress (callable, optional): Callback for upload progress.
            
        Returns:
            str: The video ID if successful, None otherwise.
        """
        response = None
        error = None
        retry = 0
        
        while response is None and retry < max_retries:
            try:
                status, response = request.next_chunk()
                
                if status and on_progress:
                    # Call the progress callback
                    on_progress(status.progress() * 100)
                    
            except googleapiclient.errors.HttpError as e:
                if e.resp.status in [500, 502, 503, 504]:
                    # Server error, retry after a delay
                    retry += 1
                    logger.warning(f"Retry {retry}/{max_retries} after server error: {e.resp.status}")
                    time.sleep(2 ** retry)  # Exponential backoff
                    error = e
                else:
                    # Client error, don't retry
                    logger.error(f"Client error during upload: {e.resp.status}")
                    error = e
                    break
                    
            except Exception as e:
                # Other error, retry
                retry += 1
                logger.warning(f"Retry {retry}/{max_retries} after error: {str(e)}")
                time.sleep(2 ** retry)  # Exponential backoff
                error = e
        
        # Final progress update
        if on_progress:
            on_progress(100)
            
        if error:
            logger.error(f"Upload failed after {retry} retries: {str(error)}")
            return None
            
        if response:
            return response.get("id")
            
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
    
    def get_upload_status(self, video_id):
        """
        Get the upload status of a video.
        
        Args:
            video_id (str): YouTube video ID.
            
        Returns:
            dict: Video status information.
        """
        if not self.service:
            success = self._initialize_service()
            if not success:
                logger.error("Failed to initialize YouTube API service")
                return None
        
        try:
            # Get the video status
            request = self.service.videos().list(
                part="status,processingDetails",
                id=video_id
            )
            response = request.execute()
            
            if not response.get("items"):
                logger.warning(f"No video found with ID: {video_id}")
                return None
            
            # Extract status information
            video = response["items"][0]
            status_info = {
                "uploadStatus": video["status"].get("uploadStatus", ""),
                "privacyStatus": video["status"].get("privacyStatus", ""),
                "processingStatus": video.get("processingDetails", {}).get("processingStatus", ""),
                "processingProgress": video.get("processingDetails", {}).get("processingProgress", {})
            }
            
            logger.info(f"Retrieved status for video {video_id}: {status_info['uploadStatus']}")
            return status_info
            
        except googleapiclient.errors.HttpError as e:
            error_content = json.loads(e.content.decode("utf-8"))
            logger.error(f"YouTube API error: {error_content}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting video status: {str(e)}")
            return None
    
    def update_video_metadata(self, video_id, title=None, description=None, tags=None, 
                              category_id=None, privacy_status=None):
        """
        Update metadata for an existing video.
        
        Args:
            video_id (str): YouTube video ID.
            title (str, optional): New video title.
            description (str, optional): New video description.
            tags (list, optional): New list of tags.
            category_id (str, optional): New YouTube category ID.
            privacy_status (str, optional): New privacy status.
            
        Returns:
            bool: True if the update was successful, False otherwise.
        """
        if not self.service:
            success = self._initialize_service()
            if not success:
                logger.error("Failed to initialize YouTube API service")
                return False
        
        try:
            # Get the current video data
            request = self.service.videos().list(
                part="snippet,status",
                id=video_id
            )
            response = request.execute()
            
            if not response.get("items"):
                logger.warning(f"No video found with ID: {video_id}")
                return False
            
            # Get the existing data
            video = response["items"][0]
            snippet = video["snippet"]
            status = video["status"]
            
            # Update the data
            if title is not None:
                snippet["title"] = title
            
            if description is not None:
                snippet["description"] = description
            
            if tags is not None:
                snippet["tags"] = tags
            
            if category_id is not None:
                snippet["categoryId"] = category_id
            
            if privacy_status is not None:
                status["privacyStatus"] = privacy_status
            
            # Update the video
            request = self.service.videos().update(
                part="snippet,status",
                body={
                    "id": video_id,
                    "snippet": snippet,
                    "status": status
                }
            )
            response = request.execute()
            
            logger.info(f"Updated metadata for video {video_id}")
            return True
            
        except googleapiclient.errors.HttpError as e:
            error_content = json.loads(e.content.decode("utf-8"))
            logger.error(f"YouTube API error: {error_content}")
            return False
            
        except Exception as e:
            logger.error(f"Error updating video metadata: {str(e)}")
            return False
