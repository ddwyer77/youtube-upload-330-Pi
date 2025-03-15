#!/usr/bin/env python3
"""
Script to fix YouTube OAuth issues by using a different authentication approach.
"""

import os
import sys
import pickle
import logging
import json
import webbrowser
from urllib.parse import urlparse, parse_qs
import google.auth.transport.requests
import google_auth_oauthlib.flow
import googleapiclient.discovery

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# YouTube API settings
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_FILE = "token.pickle"

def manual_auth_flow():
    """Perform a manual OAuth flow, providing instructions to the user."""
    print("\n" + "="*80)
    print("MANUAL YOUTUBE API AUTHENTICATION PROCESS")
    print("="*80)
    
    # Make sure we have a valid client_secrets.json
    if not os.path.exists(CLIENT_SECRETS_FILE):
        print(f"ERROR: {CLIENT_SECRETS_FILE} not found!")
        return None
    
    try:
        # Create a flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, SCOPES
        )
        
        # Generate authorization URL
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        print("\nFollow these steps to authorize the application:")
        print("1. Open this URL in your browser:")
        print(f"\n{auth_url}\n")
        print("2. Log in with your Google account and allow the requested permissions")
        print("3. After authorization, you'll be redirected to a URL that starts with 'http://localhost'")
        print("4. Copy the ENTIRE URL from your browser and paste it below")
        
        # Open the URL automatically if possible
        try:
            webbrowser.open(auth_url)
            print("\nThe URL should have opened automatically in your browser.")
        except Exception:
            print("\nCouldn't open the browser automatically. Please copy and paste the URL manually.")
        
        # Get the authorization code from the user
        redirected_url = input("\nPaste the full redirect URL here: ").strip()
        
        # Extract the authorization code from the URL
        parsed_url = urlparse(redirected_url)
        auth_code = parse_qs(parsed_url.query).get('code', [''])[0]
        
        if not auth_code:
            print("Error: Couldn't extract authorization code from the URL")
            return None
        
        # Use the authorization code to get credentials
        flow.fetch_token(code=auth_code)
        credentials = flow.credentials
        
        # Save the credentials for future use
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(credentials, token)
        
        print(f"\nAuthorization successful! Credentials saved to {TOKEN_FILE}")
        return credentials
        
    except Exception as e:
        print(f"Error during authentication: {str(e)}")
        return None

def test_credentials(credentials):
    """Test if the credentials work by fetching channel info."""
    if not credentials:
        print("No credentials available to test")
        return False
    
    try:
        # Build the YouTube API service
        service = googleapiclient.discovery.build(
            API_SERVICE_NAME, API_VERSION, credentials=credentials
        )
        
        # Try to fetch the channel info
        response = service.channels().list(
            part="snippet",
            mine=True
        ).execute()
        
        if response.get("items"):
            channel = response["items"][0]
            print(f"\nAuthentication verified! Connected to YouTube channel: {channel['snippet']['title']}")
            print("You can now run the application normally.")
            return True
        else:
            print("\nError: No channels found for this account")
            return False
            
    except Exception as e:
        print(f"\nError testing credentials: {str(e)}")
        return False

def main():
    """Main function to fix YouTube API authentication."""
    print("Starting YouTube API authentication fix...")
    
    # Enable OAuthlib's HTTP verification when running locally
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    
    # Remove existing token if it exists
    if os.path.exists(TOKEN_FILE):
        print(f"Removing existing {TOKEN_FILE} file...")
        os.remove(TOKEN_FILE)
    
    # Run the manual authentication flow
    credentials = manual_auth_flow()
    
    # Test the credentials
    if credentials:
        test_credentials(credentials)
    else:
        print("\nAuthentication failed. Please try again or check your Google Cloud Console settings.")
        print("Make sure your OAuth consent screen is configured properly and that the application has the")
        print("necessary YouTube API access.")

if __name__ == "__main__":
    main() 