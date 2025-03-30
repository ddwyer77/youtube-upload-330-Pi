#!/usr/bin/env python3
"""
Authentication script that uses a specific port (9999)
This script helps authenticate with the YouTube API
"""

import os
import sys
import pickle
import google.auth.transport.requests
import google_auth_oauthlib.flow
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
AUTH_PORT = 9999  # Use a specific port that's less likely to be in use

def clear_tokens():
    """Remove any existing token files."""
    if os.path.exists(TOKEN_FILE):
        try:
            os.remove(TOKEN_FILE)
            print(f"Removed existing token file: {TOKEN_FILE}")
        except Exception as e:
            print(f"Error removing token file: {e}")

def authenticate():
    """Run authentication flow with specified port."""
    print("\n=== YouTube API Authentication ===")
    print("\nIMPORTANT: When the browser opens, make sure to:")
    print("1. Click on 'Use another account' if your preferred account isn't shown")
    print("2. Select the Google account that has access to the YouTube API")
    print("3. Complete the OAuth consent process")
    print(f"\nWill attempt to use port {AUTH_PORT} for authentication")
    print("Starting authentication flow...\n")
    
    try:
        # Update client_secrets.json to include the specific port
        try:
            import json
            with open(CLIENT_SECRETS_FILE, 'r') as f:
                config = json.load(f)
            
            if 'installed' in config:
                # Add our specific port to redirect URIs if it's not there
                redirect_uris = config['installed']['redirect_uris']
                specific_uri = f"http://localhost:{AUTH_PORT}"
                if specific_uri not in redirect_uris:
                    redirect_uris.append(specific_uri)
                    config['installed']['redirect_uris'] = redirect_uris
                    
                    # Write updated file
                    with open(CLIENT_SECRETS_FILE, 'w') as f:
                        json.dump(config, f, indent=2)
                    print(f"Updated {CLIENT_SECRETS_FILE} to include {specific_uri}")
            elif 'web' in config:
                # Add our specific port to redirect URIs if it's not there
                redirect_uris = config['web']['redirect_uris']
                specific_uri = f"http://localhost:{AUTH_PORT}"
                if specific_uri not in redirect_uris:
                    redirect_uris.append(specific_uri)
                    config['web']['redirect_uris'] = redirect_uris
                    
                    # Write updated file
                    with open(CLIENT_SECRETS_FILE, 'w') as f:
                        json.dump(config, f, indent=2)
                    print(f"Updated {CLIENT_SECRETS_FILE} to include {specific_uri}")
        except Exception as e:
            print(f"Warning: Could not update client_secrets.json: {e}")
        
        # Create flow with all required scopes
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, SCOPES
        )
        
        # Try with our specific port first
        try:
            print(f"Attempting authentication with port {AUTH_PORT}...")
            credentials = flow.run_local_server(
                port=AUTH_PORT,
                prompt='consent'
            )
            print(f"Successfully authenticated using port {AUTH_PORT}")
        except Exception as e:
            print(f"Error with port {AUTH_PORT}: {e}")
            print("Will try with a dynamic port...")
            
            # Fall back to dynamically assigned port
            credentials = flow.run_local_server(
                port=0,
                prompt='consent'
            )
            print("Successfully authenticated using a dynamically assigned port")
        
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
    """Test if the credentials work."""
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
    """Main function for authentication."""
    print("\n=== YouTube Shorts Uploader - Authentication Tool ===")
    print("\nThis script will help you authenticate with the correct Google account.")
    
    # Clear existing tokens
    clear_tokens()
    
    # Authenticate
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