#!/usr/bin/env python3
"""
Script to test YouTube API upload functionality directly.
"""

import os
import sys
import logging
import pickle
import json
import glob
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

# Set up logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube"
]
CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_FILE = "token.pickle"
HOME_DIR = os.path.expanduser("~")
VIDEO_FOLDER = os.path.join(HOME_DIR, "Desktop", "Car Drift David Output")

def find_video_file():
    """Find a video file in the output directory."""
    if not os.path.exists(VIDEO_FOLDER):
        logger.error(f"Video folder not found: {VIDEO_FOLDER}")
        return None
    
    # Find MP4 files
    video_files = glob.glob(os.path.join(VIDEO_FOLDER, "*.mp4"))
    
    if not video_files:
        logger.error(f"No MP4 files found in {VIDEO_FOLDER}")
        return None
    
    # Use the first one found
    return video_files[0]

def get_authenticated_service():
    """Get an authenticated YouTube API service."""
    credentials = None
    
    # Check if token file exists
    if os.path.exists(TOKEN_FILE):
        logger.info(f"Loading credentials from {TOKEN_FILE}")
        with open(TOKEN_FILE, "rb") as token:
            credentials = pickle.load(token)
    
    # If no credentials or invalid, go through the OAuth flow
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            logger.info("Refreshing expired credentials")
            import google.auth.transport.requests
            credentials.refresh(google.auth.transport.requests.Request())
        else:
            logger.info("Getting new credentials")
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES
            )
            credentials = flow.run_local_server(port=8080)
            
            # Save credentials for next run
            with open(TOKEN_FILE, "wb") as token:
                pickle.dump(credentials, token)
    
    logger.info("Building YouTube API service")
    youtube = googleapiclient.discovery.build(
        "youtube", "v3", credentials=credentials
    )
    
    return youtube

def check_channel_info(youtube):
    """Check channel information to verify authentication."""
    logger.info("Checking channel information...")
    try:
        request = youtube.channels().list(
            part="snippet",
            mine=True
        )
        response = request.execute()
        
        if response.get("items"):
            channel = response["items"][0]
            logger.info(f"Connected to channel: {channel['snippet']['title']}")
            logger.info(f"Channel ID: {channel['id']}")
            return True
        else:
            logger.error("No channel found")
            return False
    except Exception as e:
        logger.error(f"Error checking channel: {str(e)}")
        return False

def upload_video(youtube, video_path):
    """Upload a video to YouTube."""
    logger.info(f"Preparing to upload: {video_path}")
    
    if not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        return None
    
    # Get file size and check if it's too large
    file_size = os.path.getsize(video_path) / (1024 * 1024)  # Size in MB
    logger.info(f"Video file size: {file_size:.2f} MB")
    
    # Basic metadata for the video
    body = {
        "snippet": {
            "title": "Test Upload via API",
            "description": "This is a test upload via the YouTube API to diagnose issues.",
            "tags": ["test", "api", "upload"],
            "categoryId": "22"  # People & Blogs
        },
        "status": {
            "privacyStatus": "unlisted",  # Use unlisted for testing
            "selfDeclaredMadeForKids": False
        }
    }
    
    logger.info("Creating upload request...")
    
    # Create the request
    try:
        request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=video_path
        )
        
        logger.info("Executing upload request...")
        response = request.execute()
        
        video_id = response.get("id")
        logger.info(f"Upload successful! Video ID: {video_id}")
        logger.info(f"Video URL: https://www.youtube.com/watch?v={video_id}")
        
        return video_id
    except googleapiclient.errors.HttpError as e:
        error_content = json.loads(e.content.decode())
        logger.error(f"HTTP error occurred: {e.resp.status}")
        logger.error(f"Error details: {error_content}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return None

def main():
    """Main function to test YouTube API upload."""
    print("\n=== YouTube API Upload Test ===\n")
    
    # Enable insecure transport for local testing
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    
    # Find a video file automatically
    video_path = find_video_file()
    if not video_path:
        print("No video file found to upload. Please check the folder path.")
        return False
    
    print(f"Found video file: {video_path}")
    
    try:
        # Get authenticated service
        youtube = get_authenticated_service()
        
        # Check if we can access the channel
        if not check_channel_info(youtube):
            print("Failed to access channel information")
            return False
        
        # Upload test video
        video_id = upload_video(youtube, video_path)
        
        if video_id:
            print("\nTest completed successfully!")
            print(f"Video uploaded with ID: {video_id}")
            print(f"Video URL: https://www.youtube.com/watch?v={video_id}")
            return True
        else:
            print("\nTest failed. Please check the error messages above.")
            return False
    
    except Exception as e:
        print(f"\nTest failed with an unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main() 