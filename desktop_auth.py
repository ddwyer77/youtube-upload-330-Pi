#!/usr/bin/env python3
"""
Desktop authentication for YouTube API
Uses a flow designed for desktop applications with manual copy/paste
"""

import os
import sys
import pickle
import json
from google_auth_oauthlib.flow import Flow 
from google.oauth2.credentials import Credentials
import googleapiclient.discovery

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

def create_desktop_flow():
    """Create a flow instance with console-based auth."""
    # Load client secrets
    with open(CLIENT_SECRETS_FILE, 'r') as f:
        client_config = json.load(f)
    
    # Determine the config type (web or installed)
    if 'installed' in client_config:
        client_type = 'installed'
    elif 'web' in client_config:
        client_type = 'web'
    else:
        raise ValueError("Unknown client type in client_secrets.json")
    
    # Create new config with OOB redirect
    flow_config = {
        client_type: {
            "client_id": client_config[client_type]["client_id"],
            "client_secret": client_config[client_type]["client_secret"],
            "auth_uri": client_config[client_type]["auth_uri"],
            "token_uri": client_config[client_type]["token_uri"],
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"]
        }
    }
    
    # Create flow from the config
    flow = Flow.from_client_config(
        flow_config,
        scopes=SCOPES
    )
    flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
    
    return flow

def authenticate():
    """Perform authentication with manual code entry."""
    print("\n=== YouTube API Authentication (Desktop Flow) ===")
    print("\nThis flow requires you to:")
    print("1. Open the authorization URL in your browser")
    print("2. Sign in with the correct Google account")
    print("3. Copy the authorization code provided")
    print("4. Paste the code back into this terminal\n")
    
    # Remove existing token if any
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
        print(f"Removed existing {TOKEN_FILE}")
    
    try:
        # Create the flow
        flow = create_desktop_flow()
        
        # Generate authorization URL
        auth_url, _ = flow.authorization_url(prompt='consent')
        
        # Print instructions
        print(f"Please go to the following URL in your browser:\n")
        print(f"{auth_url}\n")
        print("After authorization, you'll receive a code. Copy that code.")
        
        # Get authorization code from user
        code = input("\nEnter the authorization code: ").strip()
        
        # Exchange code for tokens
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Save the credentials for future use
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(credentials, token)
        
        print(f"\nCredentials saved to {TOKEN_FILE}")
        return credentials
    
    except Exception as e:
        print(f"Authentication error: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_credentials(credentials):
    """Test the credentials by fetching channel info."""
    print("\nTesting YouTube API credentials...")
    
    try:
        # Build the YouTube API service
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
            print("Authentication failed. No channel found.")
            return False
    
    except Exception as e:
        print(f"Error testing credentials: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n=== YouTube Shorts Uploader Authentication ===")
    
    # Run authentication
    credentials = authenticate()
    
    if credentials:
        # Test the credentials
        success = test_credentials(credentials)
        
        if success:
            print("\nAuthentication completed successfully!")
            print("You can now run the application with: python run_fixed.py")
            return 0
    
    print("\nAuthentication failed. Please try again.")
    return 1

if __name__ == "__main__":
    sys.exit(main()) 