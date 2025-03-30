#!/usr/bin/env python3
"""
Manual authentication script for YouTube Shorts Uploader.
This script uses the manual flow that doesn't require a redirect URI.
"""

import os
import sys
import pickle
import json
from google_auth_oauthlib.flow import InstalledAppFlow
import googleapiclient.discovery
import google.auth.transport.requests

# Enable insecure transport for local testing
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# Constants
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube"
]
CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_FILE = "token.pickle"

def clear_tokens():
    """Remove any existing token files."""
    if os.path.exists(TOKEN_FILE):
        try:
            os.remove(TOKEN_FILE)
            print(f"Removed existing token file: {TOKEN_FILE}")
        except Exception as e:
            print(f"Error removing token file: {e}")

def get_client_config():
    """Load client configuration from client_secrets.json and modify for manual auth."""
    try:
        with open(CLIENT_SECRETS_FILE, 'r') as f:
            config = json.load(f)
        
        # Check if it's a web or installed app config
        if 'web' in config:
            client_type = 'web'
        elif 'installed' in config:
            client_type = 'installed'
        else:
            print("Error: Unsupported client_secrets.json format")
            return None
        
        # Create a copy of the config to modify
        manual_config = {client_type: dict(config[client_type])}
        
        # Update redirect URIs to use out-of-band for manual auth
        manual_config[client_type]['redirect_uris'] = ['urn:ietf:wg:oauth:2.0:oob']
        
        return manual_config
    
    except Exception as e:
        print(f"Error loading client configuration: {e}")
        return None

def authenticate_manually():
    """Perform manual authentication without using a local webserver."""
    print("\n=== Manual YouTube API Authentication ===")
    
    # Get modified client config
    client_config = get_client_config()
    if not client_config:
        return None
    
    try:
        # Create the flow using the modified config
        flow = InstalledAppFlow.from_client_config(
            client_config, 
            scopes=SCOPES
        )
        
        # Run the console flow
        flow.run_console(authorization_prompt_message="""
Please visit this URL to authorize this application:
{url}

After granting permission, you'll receive a verification code.
Enter that code below:
""")
        
        # Get credentials
        credentials = flow.credentials
        
        # Save credentials to pickle file
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(credentials, token)
        print(f"Credentials saved to {TOKEN_FILE}")
        
        return credentials
    
    except Exception as e:
        print(f"Authentication error: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_credentials(credentials):
    """Test if the credentials work by retrieving channel info."""
    try:
        print("Testing credentials...")
        
        # Build YouTube API service
        youtube = googleapiclient.discovery.build(
            "youtube", "v3", credentials=credentials
        )
        
        # Get channel info
        request = youtube.channels().list(
            part="snippet",
            mine=True
        )
        response = request.execute()
        
        if response.get("items"):
            channel = response["items"][0]
            print(f"\nAuthentication successful! Connected to channel: {channel['snippet']['title']}")
            print(f"Channel ID: {channel['id']}")
            return True
        else:
            print("\nAuthentication failed. No channel found.")
            return False
    
    except Exception as e:
        print(f"Error testing credentials: {e}")
        return False

def main():
    """Main function to run manual authentication."""
    print("\n=== YouTube Shorts Uploader Manual Authentication ===")
    print("\nThis script will help you authenticate with the correct Google account")
    print("using a manual process that doesn't require redirect URIs.")
    
    # Clear existing tokens
    clear_tokens()
    
    # Authenticate
    credentials = authenticate_manually()
    
    if credentials:
        # Test the credentials
        success = test_credentials(credentials)
        
        if success:
            print("\nManual authentication completed successfully!")
            print("You can now run the application with: python run_fixed.py")
            return 0
    
    print("\nAuthentication failed. Please try again.")
    return 1

if __name__ == "__main__":
    sys.exit(main()) 