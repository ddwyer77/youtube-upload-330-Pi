#!/usr/bin/env python3
"""
Re-authentication script for YouTube Shorts Uploader.
Use this script to authenticate with the correct Google account.
"""

import os
import sys
import pickle
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

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

def clear_session():
    """Clear any existing sessions, tokens, and cached credentials."""
    files_to_remove = [TOKEN_FILE]
    
    for file in files_to_remove:
        if os.path.exists(file):
            try:
                os.remove(file)
                print(f"Removed {file}")
            except Exception as e:
                print(f"Error removing {file}: {e}")
    
    print("\nAll existing authentication data cleared.")

def authenticate():
    """Run authentication flow, ensuring user selects the correct account."""
    print("\n=== YouTube API Re-Authentication ===")
    print("\nIMPORTANT: When the browser opens, make sure to:")
    print("1. Click on 'Use another account' if your preferred account isn't shown")
    print("2. Select the Google account that has access to the YouTube API")
    print("3. Complete the OAuth consent process")
    
    # List of potential ports to try, starting with the most common
    ports_to_try = [8080, 8090, 8000, 8888, 9000]
    
    # Check client_secrets.json to see if it contains redirect URIs
    try:
        import json
        with open(CLIENT_SECRETS_FILE, 'r') as f:
            client_data = json.load(f)
            if 'web' in client_data and 'redirect_uris' in client_data['web']:
                print("\nAuthorized redirect URIs in client_secrets.json:")
                for uri in client_data['web']['redirect_uris']:
                    print(f"  - {uri}")
                    if uri.startswith('http://localhost:'):
                        port = int(uri.split(':')[-1].rstrip('/'))
                        if port not in ports_to_try:
                            ports_to_try.insert(0, port)
            elif 'installed' in client_data and 'redirect_uris' in client_data['installed']:
                print("\nAuthorized redirect URIs in client_secrets.json:")
                for uri in client_data['installed']['redirect_uris']:
                    print(f"  - {uri}")
                    if uri.startswith('http://localhost:'):
                        port = int(uri.split(':')[-1].rstrip('/'))
                        if port not in ports_to_try:
                            ports_to_try.insert(0, port)
    except Exception as e:
        print(f"\nCould not check redirect URIs in client_secrets.json: {e}")
    
    print("\nStarting authentication flow...\n")
    
    # Create flow with all required scopes
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, SCOPES
    )
    
    # Try each port until one works
    for port in ports_to_try:
        try:
            print(f"Trying port {port}...")
            
            # Run the authorization flow with browser open
            # Setting prompt='consent' forces Google to show the account selection screen
            credentials = flow.run_local_server(
                port=port,
                prompt="consent",
                open_browser=True
            )
            
            # If we get here, the port worked
            print(f"\nSuccessfully used port {port} for authentication.")
            
            # Save credentials
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(credentials, token)
            print(f"Credentials saved to {TOKEN_FILE}")
            
            # Test the credentials
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
                
        except OSError as e:
            if "Address already in use" in str(e):
                print(f"Port {port} is already in use. Trying another port...")
            else:
                print(f"Error with port {port}: {e}")
        except Exception as e:
            print(f"\nAuthentication error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    print("\nError: All ports are unavailable. Please close other applications that might be using these ports.")
    return False

def main():
    """Main function to handle re-authentication."""
    print("\n=== YouTube Shorts Uploader Re-Authentication ===")
    print("\nThis script will help you authenticate with the correct Google account.")
    
    # Clear existing sessions
    clear_session()
    
    # Run authentication
    success = authenticate()
    
    if success:
        print("\nRe-authentication completed successfully!")
        print("You can now run the application with: python run_fixed.py")
    else:
        print("\nRe-authentication failed. Please try again.")
        
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 