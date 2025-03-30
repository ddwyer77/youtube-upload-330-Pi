#!/usr/bin/env python3
"""
YouTube API Upload Diagnostic Tool

This script tests YouTube API functionality with detailed error reporting.
It attempts to:
1. Authenticate with YouTube
2. Get channel info
3. Upload a test video with detailed logging

Usage:
    python youtube_diagnostic.py /path/to/test/video.mp4
"""

import os
import sys
import json
import logging
import googleapiclient.discovery
import googleapiclient.http
import googleapiclient.errors
import google.auth.transport.requests
import pickle
from google.oauth2.credentials import Credentials

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("youtube_diagnostic")
logger.setLevel(logging.DEBUG)

# Constants
TOKEN_FILE = "token.pickle"
CLIENT_SECRETS_FILE = "client_secrets.json"
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube"
]

def load_credentials():
    """Load credentials from the token pickle file."""
    logger.info(f"Looking for credentials in {TOKEN_FILE}")
    
    if not os.path.exists(TOKEN_FILE):
        logger.error(f"Token file not found: {TOKEN_FILE}")
        return None
    
    try:
        with open(TOKEN_FILE, "rb") as token:
            credentials = pickle.load(token)
            logger.info("Credentials loaded from token file")
            
            if credentials.expired and credentials.refresh_token:
                logger.info("Credentials have expired, refreshing...")
                credentials.refresh(google.auth.transport.requests.Request())
                
                # Save the refreshed credentials
                with open(TOKEN_FILE, "wb") as token:
                    pickle.dump(credentials, token)
                logger.info("Refreshed credentials saved")
            
            return credentials
    except Exception as e:
        logger.error(f"Error loading credentials: {str(e)}")
        return None

def get_authenticated_service():
    """Build and return an authorized YouTube API service instance."""
    credentials = load_credentials()
    
    if not credentials:
        logger.error("Unable to get valid credentials")
        return None
    
    try:
        # Build the YouTube API service
        service = googleapiclient.discovery.build(
            API_SERVICE_NAME,
            API_VERSION,
            credentials=credentials,
            cache_discovery=False
        )
        logger.info("YouTube API service initialized")
        return service
    except Exception as e:
        logger.error(f"Error building YouTube API service: {str(e)}")
        return None

def get_channel_info(youtube):
    """Get information about the authenticated user's channel."""
    logger.info("Fetching channel information...")
    
    try:
        # Request channel info
        request = youtube.channels().list(
            part="snippet,statistics,contentDetails",
            mine=True
        )
        response = request.execute()
        
        if response.get("items"):
            channel = response["items"][0]
            logger.info(f"Channel found: {channel['snippet']['title']}")
            logger.info(f"Channel ID: {channel['id']}")
            logger.info(f"Subscriber count: {channel['statistics'].get('subscriberCount', 'hidden')}")
            logger.info(f"Video count: {channel['statistics'].get('videoCount', '0')}")
            
            # Get the uploads playlist
            uploads_playlist_id = channel["contentDetails"]["relatedPlaylists"]["uploads"]
            logger.info(f"Uploads playlist ID: {uploads_playlist_id}")
            
            return channel
        else:
            logger.error("No channel found for the authenticated user")
            return None
    except googleapiclient.errors.HttpError as e:
        error_content = json.loads(e.content.decode())
        logger.error(f"YouTube API HTTP error: {e.resp.status}")
        logger.error(f"Error details: {json.dumps(error_content, indent=2)}")
        return None
    except Exception as e:
        logger.error(f"Error getting channel info: {str(e)}")
        return None

def test_upload_video(youtube, video_path):
    """Attempt to upload a test video with detailed error reporting."""
    logger.info(f"Starting test upload for video: {video_path}")
    
    if not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        return None
    
    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    logger.info(f"Video file size: {file_size_mb:.2f} MB")
    
    try:
        # Define video metadata
        body = {
            "snippet": {
                "title": "API Test Upload - Diagnostic",
                "description": "This is a test upload from the YouTube API diagnostic tool.",
                "tags": ["test", "api", "diagnostic"],
                "categoryId": "22"  # People & Blogs
            },
            "status": {
                "privacyStatus": "unlisted",  # Use unlisted for testing
                "selfDeclaredMadeForKids": False
            }
        }
        
        # Create the media upload
        media = googleapiclient.http.MediaFileUpload(
            video_path,
            mimetype="video/*",
            resumable=True,
            chunksize=1024*1024*5  # 5MB chunks
        )
        
        logger.info("Creating upload request...")
        request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media,
            notifySubscribers=False
        )
        
        # Simple upload approach for diagnostic purposes
        logger.info("Starting upload... (this may take a while)")
        response = None
        
        # Execute the resumable upload
        while response is None:
            status, response = request.next_chunk()
            if status:
                logger.info(f"Upload progress: {int(status.progress() * 100)}%")
        
        video_id = response.get("id")
        logger.info(f"Upload successful! Video ID: {video_id}")
        logger.info(f"Video URL: https://www.youtube.com/watch?v={video_id}")
        
        return video_id
        
    except googleapiclient.errors.HttpError as e:
        error_content = json.loads(e.content.decode("utf-8"))
        logger.error(f"YouTube API HTTP error: {e.resp.status}")
        logger.error(f"Error details: {json.dumps(error_content, indent=2)}")
        
        # Check for specific error cases
        if e.resp.status == 403:
            logger.error("PERMISSION ERROR: The app may not have sufficient permissions or quotas.")
            logger.error("Make sure the YouTube Data API is enabled in your Google Cloud project.")
        elif e.resp.status == 401:
            logger.error("AUTHENTICATION ERROR: Credentials may be invalid or expired.")
            logger.error("Try deleting the token.pickle file and re-authenticating.")
        elif e.resp.status == 400:
            logger.error("REQUEST ERROR: There's a problem with the video or metadata.")
            if "videoFile" in str(error_content):
                logger.error("The video file may be in an unsupported format or damaged.")
        
        return None
    except Exception as e:
        logger.error(f"Unexpected error during upload: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def run_diagnostics(video_path=None):
    """Run a full diagnostic of YouTube API functionality."""
    logger.info("=== YouTube API Diagnostic Tool ===")
    logger.info(f"Credentials file: {TOKEN_FILE}")
    logger.info(f"Client secrets file: {CLIENT_SECRETS_FILE}")
    
    # Check if credentials and client secrets exist
    if not os.path.exists(TOKEN_FILE):
        logger.error(f"Token file not found: {TOKEN_FILE}")
    else:
        logger.info(f"Token file exists: {TOKEN_FILE}")
    
    if not os.path.exists(CLIENT_SECRETS_FILE):
        logger.error(f"Client secrets file not found: {CLIENT_SECRETS_FILE}")
    else:
        logger.info(f"Client secrets file exists: {CLIENT_SECRETS_FILE}")
    
    # Test loading credentials
    credentials = load_credentials()
    if not credentials:
        logger.error("Failed to load credentials")
        return False
    
    logger.info(f"Credentials type: {type(credentials).__name__}")
    logger.info(f"Credentials expired: {credentials.expired if hasattr(credentials, 'expired') else 'Unknown'}")
    logger.info(f"Has refresh token: {bool(credentials.refresh_token) if hasattr(credentials, 'refresh_token') else 'No'}")
    
    # Get authenticated service
    youtube = get_authenticated_service()
    if not youtube:
        logger.error("Failed to initialize YouTube API service")
        return False
    
    # Test getting channel info
    channel = get_channel_info(youtube)
    if not channel:
        logger.error("Failed to get channel information")
        return False
    
    # Test uploading a video if a path was provided
    if video_path:
        logger.info(f"Testing video upload with file: {video_path}")
        video_id = test_upload_video(youtube, video_path)
        if not video_id:
            logger.error("Video upload test failed")
            return False
        logger.info("Video upload test passed")
    else:
        logger.info("Skipping video upload test (no video file provided)")
    
    logger.info("=== Diagnostic tests completed ===")
    return True

def main():
    """Main entry point for the diagnostic tool."""
    # Check if a video path was provided
    video_path = None
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return 1
    
    # Run diagnostics
    success = run_diagnostics(video_path)
    
    if success:
        logger.info("All diagnostics completed successfully!")
        return 0
    else:
        logger.error("Some diagnostic tests failed. See log for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 