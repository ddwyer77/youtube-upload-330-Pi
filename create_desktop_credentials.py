#!/usr/bin/env python3
"""
Create new OAuth credentials for YouTube Shorts Uploader
This script helps you create a proper desktop application client_secrets.json file
"""

import os
import json
import sys

def create_credentials_file():
    """Create a new client_secrets.json file with user-provided credentials for a desktop app"""
    print("\n=== Create New OAuth Desktop Application Credentials ===\n")
    print("You'll need to create a new OAuth client ID in the Google Cloud Console.")
    print("Follow these steps:")
    print("1. Go to https://console.cloud.google.com/apis/credentials")
    print("2. Create a new project or select an existing one")
    print("3. Click 'Create Credentials' > 'OAuth client ID'")
    print("4. Select 'Desktop app' as the application type (THIS IS CRITICAL)")
    print("5. Give it a name like 'YouTube Shorts Uploader Desktop'")
    print("6. Click 'Create'")
    print("7. Copy the Client ID and Client Secret\n")
    
    # Back up existing credentials if they exist
    if os.path.exists("client_secrets.json"):
        try:
            with open("client_secrets.json", "r") as f:
                existing_creds = f.read()
            
            with open("client_secrets.json.backup", "w") as f:
                f.write(existing_creds)
            
            print("Backed up existing credentials to client_secrets.json.backup")
        except Exception as e:
            print(f"Warning: Could not back up existing credentials: {e}")
    
    # Get credentials from user
    client_id = input("\nEnter Client ID: ").strip()
    client_secret = input("Enter Client Secret: ").strip()
    
    if not client_id or not client_secret:
        print("Error: Client ID and Client Secret are required")
        return False
    
    # Create credentials file with correct format for DESKTOP app
    credentials = {
        "installed": {  # This MUST be "installed" for desktop apps, not "web"
            "client_id": client_id,
            "project_id": "youtube-shorts-uploader",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret,
            "redirect_uris": [
                "http://localhost",
                "urn:ietf:wg:oauth:2.0:oob"  # Out-of-band for desktop apps
            ]
        }
    }
    
    try:
        with open("client_secrets.json", "w") as f:
            json.dump(credentials, f, indent=2)
        
        print("\nSuccessfully created client_secrets.json for a desktop application!")
        print("\nNow you need to:")
        print("1. Remove any existing token.pickle file: rm token.pickle")
        print("2. Run the authentication script: python desktop_auth.py")
        print("3. Launch the app: python run_fixed.py")
        
        return True
    
    except Exception as e:
        print(f"Error creating credentials file: {e}")
        return False

if __name__ == "__main__":
    create_credentials_file() 