#!/usr/bin/env python3
"""
Simple authentication script for YouTube Shorts Uploader.
This script handles YouTube authentication with minimal dependencies.
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

def clear_tokens():
    """Remove any existing token files."""
    if os.path.exists(TOKEN_FILE):
        try:
            os.remove(TOKEN_FILE)
            print(f"Removed existing token file: {TOKEN_FILE}")
        except Exception as e:
            print(f"Error removing token file: {e}")

def authenticate():
    """Run authentication flow."""
    print("\n=== YouTube API Authentication ===")
    print("\nIMPORTANT: When the browser opens, make sure to:")
    print("1. Click on 'Use another account' if your preferred account isn't shown")
    print("2. Select the Google account that has access to the YouTube API")
    print("3. Complete the OAuth consent process")
    print("\nStarting authentication flow...\n")
    
    try:
        # Create flow with all required scopes
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, SCOPES
        )
        
        # Attempt different ports until one works
        # Port 0 means the OS will pick an available port
        try:
            credentials = flow.run_local_server(port=0, prompt='consent')
            port_used = "dynamically assigned"
        except Exception as e:
            print(f"Error with automatic port: {e}")
            print("Trying specific ports...")
            
            # Try specific ports
            for port in [8080, 8090, 8000, 8888]:
                try:
                    print(f"Trying port {port}...")
                    credentials = flow.run_local_server(port=port, prompt='consent')
                    port_used = port
                    break
                except Exception as e:
                    print(f"Error with port {port}: {e}")
            else:
                print("All ports failed")
                return None
        
        print(f"Successfully authenticated using port {port_used}")
        
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