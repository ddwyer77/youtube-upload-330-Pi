#!/usr/bin/env python3
"""
Script to test the updated authentication flow with the new credentials.
"""

import os
import sys
import logging
import pickle
import google.auth.transport.requests
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import json
import shutil

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# YouTube API settings with both scopes
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube"
]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
JSON_FOLDER = "JSON"
CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_FILE = "token.pickle"

def setup_credentials():
    """Copy the new credentials to the main directory for easier access."""
    # Find the OAuth client secret file in the JSON folder
    if not os.path.exists(JSON_FOLDER):
        print(f"ERROR: {JSON_FOLDER} folder not found!")
        return False
        
    json_files = [f for f in os.listdir(JSON_FOLDER) if f.endswith('.json')]
    if not json_files:
        print(f"ERROR: No JSON files found in {JSON_FOLDER} folder!")
        return False
    
    # Use the first JSON file found (assuming it's the correct one)
    source_file = os.path.join(JSON_FOLDER, json_files[0])
    
    # Copy to client_secrets.json in root directory
    try:
        shutil.copy2(source_file, CLIENT_SECRETS_FILE)
        print(f"Successfully copied {source_file} to {CLIENT_SECRETS_FILE}")
        return True
    except Exception as e:
        print(f"ERROR copying credentials file: {str(e)}")
        return False

def manual_auth():
    """Perform authentication with direct access to the credentials file."""
    # Setup credentials if needed
    if not os.path.exists(CLIENT_SECRETS_FILE):
        if not setup_credentials():
            return None
    
    # Remove existing token
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
        print(f"Removed existing token file: {TOKEN_FILE}")
    
    # Enable insecure transport for local testing
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    
    try:
        # Create flow with the updated scopes
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, SCOPES
        )
        
        # Run the flow
        print("Starting OAuth flow...")
        credentials = flow.run_local_server(
            port=8080,
            prompt="consent",
            open_browser=True
        )
        
        # Save credentials
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(credentials, token)
        print(f"Successfully saved credentials to {TOKEN_FILE}")
        
        # Build the YouTube API service
        youtube = googleapiclient.discovery.build(
            API_SERVICE_NAME, API_VERSION, credentials=credentials
        )
        
        return youtube
    
    except Exception as e:
        print(f"Authentication failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Test authentication with the new credentials."""
    print("\n=== YouTube API Authentication Test ===\n")
    
    # Use direct authentication instead of the AuthManager
    youtube = manual_auth()
    
    if not youtube:
        print("Failed to authenticate with YouTube API")
        return False
    
    try:
        # Test API connection by getting channel info
        print("Testing API connection by retrieving channel info...")
        request = youtube.channels().list(
            part="snippet",
            mine=True
        )
        response = request.execute()
        
        if response.get("items"):
            channel = response["items"][0]
            print(f"\nAuthentication successful! Connected to channel: {channel['snippet']['title']}")
            print(f"Channel ID: {channel['id']}")
            
            # Test app access with a simple playlist retrieval
            print("\nTesting additional permissions...")
            playlists = youtube.playlists().list(
                part="snippet",
                maxResults=5,
                mine=True
            ).execute()
            
            if "items" in playlists:
                print(f"Successfully accessed {len(playlists['items'])} playlists")
                if playlists['items']:
                    print(f"First playlist: {playlists['items'][0]['snippet']['title']}")
            else:
                print("No playlists found, but API access is working")
            
            return True
        else:
            print("No channel found for authenticated user.")
            return False
    
    except Exception as e:
        print(f"\nAPI test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\nTest completed successfully! You can now run the application normally.")
        print("Try running: python run.py")
    else:
        print("\nTest failed. Please check the error messages above and ensure your OAuth consent screen")
        print("in the Google Cloud Console has the following scopes enabled:")
        for scope in SCOPES:
            print(f"  - {scope}")
        print("\nYou may need to go to https://console.cloud.google.com/apis/credentials/consent")
        print("and update your OAuth consent screen configuration.") 