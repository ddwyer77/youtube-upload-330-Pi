#!/usr/bin/env python3
"""
Script to troubleshoot YouTube API authentication and upload.
"""

import os
import sys
import pickle
import logging
import traceback
import google.auth
import google.auth.transport.requests
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import json

# Set up logging - INCREASED TO DEBUG LEVEL
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# YouTube API settings
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_FILE = "token.pickle"

def check_client_secrets():
    """Check if client_secrets.json exists and is properly formatted."""
    if not os.path.exists(CLIENT_SECRETS_FILE):
        logger.error(f"client_secrets.json not found at {os.path.abspath(CLIENT_SECRETS_FILE)}")
        return False

    try:
        with open(CLIENT_SECRETS_FILE, 'r') as f:
            data = json.load(f)
        
        # Check if it's a web or installed app format
        if 'web' in data:
            client_type = 'web'
        elif 'installed' in data:
            client_type = 'installed'
        else:
            logger.error("client_secrets.json is missing both 'web' and 'installed' keys")
            return False
        
        # Check required fields
        required_fields = ['client_id', 'client_secret', 'auth_uri', 'token_uri']
        for field in required_fields:
            if field not in data[client_type]:
                logger.error(f"client_secrets.json is missing '{field}' in '{client_type}' section")
                return False
        
        # Check redirect URIs
        redirect_uris = data[client_type].get('redirect_uris', [])
        if not redirect_uris:
            logger.error("No redirect URIs found in client_secrets.json")
            return False
        
        if 'http://localhost:8080/' not in redirect_uris:
            logger.warning("http://localhost:8080/ not in redirect_uris. Current URIs:")
            for uri in redirect_uris:
                logger.warning(f"  - {uri}")
            return False
        
        logger.info(f"client_secrets.json looks good ({client_type} app type)")
        logger.info(f"Client ID: {data[client_type]['client_id'][:5]}...{data[client_type]['client_id'][-5:]}")
        return True
    
    except json.JSONDecodeError:
        logger.error("client_secrets.json is not valid JSON")
        return False
    except Exception as e:
        logger.error(f"Error checking client_secrets.json: {str(e)}")
        return False

def get_authenticated_service():
    """Get authenticated YouTube API service."""
    # First check if client_secrets.json is valid
    if not check_client_secrets():
        logger.error("Invalid client_secrets.json file. Please fix the issues above.")
        return None
    
    credentials = None
    
    # Check if we have token stored
    if os.path.exists(TOKEN_FILE):
        logger.info(f"Found existing token.pickle at {os.path.abspath(TOKEN_FILE)}")
        try:
            with open(TOKEN_FILE, "rb") as token:
                credentials = pickle.load(token)
            logger.info("Loaded credentials from token file")
        except Exception as e:
            logger.error(f"Error loading credentials: {str(e)}")
            # If token file exists but is corrupted, remove it
            os.remove(TOKEN_FILE)
            logger.info("Removed corrupted token file")
    
    # If no valid credentials, start OAuth flow
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            logger.info("Refreshing expired credentials")
            try:
                credentials.refresh(google.auth.transport.requests.Request())
                logger.info("Successfully refreshed credentials")
            except Exception as e:
                logger.error(f"Error refreshing credentials: {str(e)}")
                # If refresh failed, we'll fall through to the OAuth flow
        else:
            logger.info("Starting OAuth flow")
            try:
                flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                    CLIENT_SECRETS_FILE, SCOPES
                )
                logger.info("Created OAuth flow, starting local server...")
                credentials = flow.run_local_server(
                    port=8080, 
                    prompt="consent", 
                    authorization_prompt_message="Please authorize this application to access your YouTube account",
                    open_browser=True
                )
                logger.info("OAuth flow completed successfully")
                
                # Save the credentials for the next run
                with open(TOKEN_FILE, "wb") as token:
                    pickle.dump(credentials, token)
                logger.info(f"Saved new credentials to {TOKEN_FILE}")
            except Exception as e:
                logger.error(f"Error during OAuth flow: {str(e)}")
                logger.error(traceback.format_exc())
                return None
    
    try:
        logger.info("Building YouTube API service...")
        service = googleapiclient.discovery.build(
            API_SERVICE_NAME, API_VERSION, credentials=credentials
        )
        logger.info("YouTube API service built successfully")
        return service
    except Exception as e:
        logger.error(f"Error building YouTube API service: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def list_my_channel(youtube):
    """Get and display the authenticated user's channel info."""
    if not youtube:
        logger.error("YouTube API service not available")
        return
        
    try:
        logger.info("Requesting channel information...")
        request = youtube.channels().list(
            part="snippet,contentDetails,statistics",
            mine=True
        )
        response = request.execute()
        
        if not response.get("items"):
            logger.error("No channel found for authenticated user")
            return
            
        channel = response["items"][0]
        logger.info("Authentication successful!")
        logger.info(f"Channel Title: {channel['snippet']['title']}")
        logger.info(f"Channel ID: {channel['id']}")
        return channel
    except googleapiclient.errors.HttpError as e:
        logger.error(f"HTTP error during API call: {e.resp.status} - {e.content}")
    except Exception as e:
        logger.error(f"Unexpected error getting channel info: {str(e)}")
        logger.error(traceback.format_exc())

def main():
    """Main function to test YouTube API authentication."""
    logger.info("Starting YouTube API authentication test")
    
    # Enable OAuthlib's HTTPS verification when running locally
    # *DO NOT* leave this option enabled in production
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    
    # Get authenticated service
    youtube = get_authenticated_service()
    if not youtube:
        logger.error("Failed to create YouTube API service")
        return
    
    # Test authentication by listing the channel info
    channel = list_my_channel(youtube)
    if channel:
        logger.info("YouTube API authentication successful!")
    else:
        logger.error("Could not verify YouTube API authentication")

if __name__ == "__main__":
    main() 