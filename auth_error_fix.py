#!/usr/bin/env python3
"""
Script to troubleshoot and fix "Access blocked: Authorization Error" for YouTube API.
"""

import os
import sys
import pickle
import logging
import json
import webbrowser
import subprocess
from urllib.parse import urlparse, parse_qs
import google.auth.transport.requests
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import shutil

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# YouTube API settings
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
JSON_FOLDER = "JSON"
CLIENT_SECRETS_FILE = "client_secrets.json"  # Target file name
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

def check_client_secrets():
    """Check if client_secrets.json exists and extract relevant configuration information."""
    if not os.path.exists(CLIENT_SECRETS_FILE):
        print(f"ERROR: {CLIENT_SECRETS_FILE} not found!")
        return None
    
    try:
        with open(CLIENT_SECRETS_FILE, 'r') as f:
            data = json.load(f)
        
        # Check if it's a web or installed app
        client_type = None
        client_info = None
        
        if 'web' in data:
            client_type = 'web'
            client_info = data['web']
        elif 'installed' in data:
            client_type = 'installed'
            client_info = data['installed']
        else:
            print("ERROR: client_secrets.json has invalid format - missing 'web' or 'installed' key")
            return None
        
        return {
            'client_type': client_type,
            'client_id': client_info.get('client_id'),
            'project_id': client_info.get('project_id'),
            'auth_uri': client_info.get('auth_uri'),
            'redirect_uris': client_info.get('redirect_uris', [])
        }
            
    except Exception as e:
        print(f"ERROR parsing client_secrets.json: {str(e)}")
        return None

def print_auth_info(client_info):
    """Print information about the OAuth configuration."""
    print("\n" + "="*80)
    print("OAUTH CONFIGURATION INFORMATION")
    print("="*80)
    
    if not client_info:
        print("No valid client information found.")
        return
    
    print(f"Client Type: {client_info['client_type']}")
    print(f"Project ID: {client_info.get('project_id', 'Not found')}")
    
    # Print partial client ID for verification while preserving security
    client_id = client_info.get('client_id', '')
    if client_id:
        masked_id = f"{client_id[:5]}...{client_id[-5:]}" if len(client_id) > 10 else "Invalid"
        print(f"Client ID: {masked_id}")
    
    # Print redirect URIs
    print("\nRedirect URIs:")
    for uri in client_info.get('redirect_uris', []):
        print(f"  - {uri}")

def explain_access_blocked_error():
    """Provide detailed explanation of the 'Access blocked: Authorization Error'."""
    print("\n" + "="*80)
    print("ACCESS BLOCKED: AUTHORIZATION ERROR - EXPLANATION & FIXES")
    print("="*80)
    
    print("""
This error typically occurs for one of the following reasons:

1. OAuth Consent Screen Configuration Issues:
   - Your app is in "Testing" mode, but the test user email isn't added to the list
   - Required scopes are not properly configured
   - App verification status is pending or rejected

2. API Enablement Issues:
   - YouTube Data API v3 is not enabled for your Google Cloud Project

3. OAuth Client Type Issues:
   - You might be using 'web' application type instead of 'desktop'/'installed'
   - Redirect URIs are not properly configured

4. Account Restrictions:
   - Your Google account has security settings that block third-party access
   - Your account is a managed account (e.g., corporate Google Workspace) with restrictions
""")

def provide_fix_instructions(client_info):
    """Provide step-by-step instructions to fix the authorization error."""
    print("\n" + "="*80)
    print("STEP-BY-STEP FIX INSTRUCTIONS")
    print("="*80)
    
    # Get project ID for instructions
    project_id = client_info.get('project_id', '[YOUR_PROJECT_ID]') if client_info else '[YOUR_PROJECT_ID]'
    
    print("""
Follow these steps to fix the "Access blocked: Authorization Error":

1. Verify API Enablement:
   - Go to: https://console.cloud.google.com/apis/library/youtube.googleapis.com
   - Make sure YouTube Data API v3 is ENABLED for your project

2. Fix OAuth Consent Screen:
   - Go to: https://console.cloud.google.com/apis/credentials/consent
   - Ensure your app is properly configured:
     a. If in "Testing" mode, add your email to the list of test users
     b. Make sure required scopes are added (https://www.googleapis.com/auth/youtube.upload)
     c. Fill out all required fields in the OAuth consent screen

3. Check Credentials Configuration:
   - Go to: https://console.cloud.google.com/apis/credentials
   - For a desktop application, use "Desktop app" type (not "Web application")
   - If your app type is wrong, create a new OAuth client ID with the correct type
   
4. Account Settings:
   - Try with a personal Google account that has no organization restrictions
   - Check if you need to allow less secure apps in your Google account settings
""")

    # Give specific project link
    if project_id and project_id != '[YOUR_PROJECT_ID]':
        print(f"\nDirect link to your project's API credentials:")
        print(f"https://console.cloud.google.com/apis/credentials?project={project_id}")
        
        print(f"\nDirect link to your project's OAuth consent screen:")
        print(f"https://console.cloud.google.com/apis/credentials/consent?project={project_id}")

def verify_with_minimal_scope():
    """Attempt authentication with minimal scope to isolate the issue."""
    print("\n" + "="*80)
    print("TESTING AUTHENTICATION WITH MINIMAL SCOPE")
    print("="*80)
    
    # Use a minimal scope for testing
    test_scope = ["https://www.googleapis.com/auth/youtube.readonly"]
    
    try:
        print("Attempting authentication with minimal 'youtube.readonly' scope...")
        # Remove existing token if present
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
            
        # Create flow with minimal scope
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, test_scope
        )
        
        # Generate auth URL
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        print("\nPlease open this URL in your browser:")
        print(f"\n{auth_url}\n")
        
        # Open URL automatically if possible
        try:
            webbrowser.open(auth_url)
            print("The URL should have opened automatically in your browser.")
        except Exception:
            print("Couldn't open the browser automatically. Please copy and paste the URL manually.")
        
        print("\nIf you still see the 'Access blocked: Authorization Error' with this minimal scope,")
        print("the issue is definitely with your OAuth consent screen configuration, not the scopes.")
        
        print("\nAfter completing the flow (or if you encounter an error), press Enter to continue...")
        input()
        
    except Exception as e:
        print(f"Error during minimal scope test: {str(e)}")

def check_installed_packages():
    """Check if all required packages are installed."""
    print("\n" + "="*80)
    print("CHECKING INSTALLED PACKAGES")
    print("="*80)
    
    required_packages = [
        "google-auth", 
        "google-auth-oauthlib", 
        "google-auth-httplib2",
        "google-api-python-client"
    ]
    
    print("Checking for required packages:")
    for package in required_packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "show", package], 
                                 stdout=subprocess.DEVNULL, 
                                 stderr=subprocess.DEVNULL)
            print(f"  ✓ {package} is installed")
        except subprocess.CalledProcessError:
            print(f"  ✗ {package} is NOT installed")
            print(f"    Run: pip install {package}")
    
    # Check Python version
    print(f"\nPython version: {sys.version}")

def run_auth_test():
    """Run a simple authentication test with the new credentials."""
    print("\n" + "="*80)
    print("TESTING AUTHENTICATION WITH NEW CREDENTIALS")
    print("="*80)
    
    # Remove existing token if present
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
        print(f"Removed existing {TOKEN_FILE}")
    
    try:
        # Enable insecure transport for local testing
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        
        # Create flow
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
        
        # Test API connection
        print("Testing YouTube API connection...")
        youtube = googleapiclient.discovery.build(
            API_SERVICE_NAME, API_VERSION, credentials=credentials
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
            print("No channel found for authenticated user.")
            return False
            
    except Exception as e:
        print(f"Authentication failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to diagnose and fix the 'Access blocked: Authorization Error'."""
    print("\n" + "="*80)
    print("YOUTUBE API 'ACCESS BLOCKED: AUTHORIZATION ERROR' TROUBLESHOOTER")
    print("="*80)
    
    # Enable insecure transport for local testing
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    
    # Check installed packages
    check_installed_packages()
    
    # Setup credentials from JSON folder
    if not setup_credentials():
        print("Failed to set up credentials. Please check the JSON folder.")
        return
    
    # Check client secrets file
    client_info = check_client_secrets()
    
    # Print configuration info
    print_auth_info(client_info)
    
    if client_info and client_info['client_type'] == 'web':
        print("\nWARNING: You are using a 'web' application type. For desktop applications,")
        print("it's recommended to use the 'Desktop application' type when creating OAuth credentials.")
        
    # Explain the error
    explain_access_blocked_error()
    
    # Provide fix instructions
    provide_fix_instructions(client_info)
    
    # Ask if user wants to test authentication
    print("\nWould you like to test authentication with the new credentials?")
    choice = input("This will attempt to authenticate with YouTube API (y/n): ")
    
    if choice.lower() == 'y':
        run_auth_test()
    
    print("\n" + "="*80)
    print("TROUBLESHOOTING COMPLETED")
    print("="*80)
    print("\nPlease follow the instructions above if you encountered any issues.")
    print("After making changes in the Google Cloud Console, run this script again.")

if __name__ == "__main__":
    main() 