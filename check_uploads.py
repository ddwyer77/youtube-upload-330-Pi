#!/usr/bin/env python3
"""
Script to check the current uploads on your YouTube channel.
"""

import os
import sys
import logging
import pickle
import json
import google.auth.transport.requests
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly"
]
CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_FILE = "token.pickle"

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

def get_channel_info(youtube):
    """Get information about the authenticated user's channel."""
    try:
        request = youtube.channels().list(
            part="snippet,statistics,contentDetails",
            mine=True
        )
        response = request.execute()
        
        if response.get("items"):
            return response["items"][0]
        else:
            logger.error("No channel found")
            return None
    except Exception as e:
        logger.error(f"Error getting channel info: {str(e)}")
        return None

def list_uploaded_videos(youtube, playlist_id, max_results=50):
    """List videos uploaded to the channel."""
    try:
        request = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=playlist_id,
            maxResults=max_results
        )
        response = request.execute()
        return response.get("items", [])
    except Exception as e:
        logger.error(f"Error listing videos: {str(e)}")
        return []

def get_video_details(youtube, video_ids):
    """Get detailed information about specific videos."""
    # Split into batches of 50 (API limit)
    video_ids_chunks = [video_ids[i:i+50] for i in range(0, len(video_ids), 50)]
    
    all_videos = []
    
    for chunk in video_ids_chunks:
        try:
            request = youtube.videos().list(
                part="snippet,contentDetails,statistics,status",
                id=",".join(chunk)
            )
            response = request.execute()
            all_videos.extend(response.get("items", []))
        except Exception as e:
            logger.error(f"Error getting video details: {str(e)}")
    
    return all_videos

def format_timestamp(timestamp):
    """Format an ISO timestamp into a readable date."""
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return timestamp

def main():
    """Main function to check YouTube uploads."""
    print("\n=== YouTube Channel Uploads Checker ===\n")
    
    # Enable insecure transport for local testing
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    
    try:
        # Get authenticated service
        youtube = get_authenticated_service()
        
        # Get channel info
        channel = get_channel_info(youtube)
        if not channel:
            print("Failed to get channel information")
            return False
        
        # Print channel info
        print("Channel Information:")
        print(f"- Title: {channel['snippet']['title']}")
        print(f"- ID: {channel['id']}")
        print(f"- Subscribers: {channel['statistics']['subscriberCount']}")
        print(f"- View Count: {channel['statistics']['viewCount']}")
        print(f"- Video Count: {channel['statistics']['videoCount']}")
        
        # Get uploads playlist ID
        uploads_playlist_id = channel['contentDetails']['relatedPlaylists']['uploads']
        
        # List uploaded videos
        videos = list_uploaded_videos(youtube, uploads_playlist_id)
        
        if not videos:
            print("\nNo videos found on this channel")
            return True
        
        # Get video IDs
        video_ids = [video['contentDetails']['videoId'] for video in videos]
        
        # Get detailed information about the videos
        video_details = get_video_details(youtube, video_ids)
        
        # Print video information
        print("\nMost Recent Uploads:")
        for i, video in enumerate(video_details[:10], 1):  # Show only the 10 most recent
            print(f"\n{i}. {video['snippet']['title']}")
            print(f"   ID: {video['id']}")
            print(f"   URL: https://www.youtube.com/watch?v={video['id']}")
            print(f"   Privacy: {video['status']['privacyStatus']}")
            print(f"   Uploaded: {format_timestamp(video['snippet']['publishedAt'])}")
            print(f"   Views: {video['statistics'].get('viewCount', '0')}")
            print(f"   Likes: {video['statistics'].get('likeCount', '0')}")
        
        # Check for video processing issues
        processing_issues = [
            video for video in video_details 
            if video['status'].get('uploadStatus') != 'processed'
        ]
        
        if processing_issues:
            print("\nVideos with Processing Issues:")
            for video in processing_issues:
                print(f"- {video['snippet']['title']} (Status: {video['status'].get('uploadStatus', 'unknown')})")
        
        return True
    
    except Exception as e:
        print(f"\nError checking uploads: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main() 