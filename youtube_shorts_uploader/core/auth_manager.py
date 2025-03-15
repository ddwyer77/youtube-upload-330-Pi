import os
import json
import logging
import pickle
import shutil
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from .keychain_helper import KeychainHelper

logger = logging.getLogger(__name__)

class AuthManager:
    """
    Manages authentication with the YouTube API.
    Handles credential storage, refresh, and authorization flow.
    Updated to support multiple accounts.
    """
    
    # OAuth scopes required for YouTube uploads
    SCOPES = [
        'https://www.googleapis.com/auth/youtube.upload',
        'https://www.googleapis.com/auth/youtube',
        'https://www.googleapis.com/auth/youtube.readonly'
    ]
    
    def __init__(self, account_id=None, config_dir=None):
        """
        Initialize the authentication manager.
        
        Args:
            account_id (str, optional): ID of the account to manage. If None, uses default.
            config_dir (str, optional): Directory for configuration files.
        """
        self.account_id = account_id or 'default'
        self.config_dir = config_dir or os.path.join(str(Path.home()), '.youtube_shorts_uploader')
        
        # Create config directory if it doesn't exist
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Initialize keychain helper for secure storage
        self.keychain = KeychainHelper()
        
        # Credentials object
        self.credentials = None
        
        logger.info(f"Auth manager initialized for account: {self.account_id}")
    
    def authorize(self, client_secrets_file=None):
        """
        Authorize the application with the YouTube API.
        
        Args:
            client_secrets_file (str, optional): Path to client secrets file.
                If None, use the stored file path.
        
        Returns:
            bool: True if authorization was successful, False otherwise.
        """
        try:
            # Try to load existing credentials first
            self.load_credentials()
            
            # If credentials don't exist or are invalid, start auth flow
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    # Refresh the credentials
                    self.credentials.refresh(Request())
                    logger.info("Credentials refreshed")
                    self.save_credentials()
                    return True
                else:
                    # We need new credentials - start OAuth flow
                    if not client_secrets_file:
                        # Try to get the client secrets file from keychain
                        client_secrets_file = self.get_client_secrets_file()
                    
                    if not client_secrets_file or not os.path.exists(client_secrets_file):
                        logger.error("Client secrets file not found")
                        return False
                    
                    # Save the client secrets file path for future reference
                    self.set_client_secrets_file(client_secrets_file)
                    
                    # Start auth flow
                    flow = InstalledAppFlow.from_client_secrets_file(
                        client_secrets_file, self.SCOPES)
                    self.credentials = flow.run_local_server(port=0)
                    
                    logger.info("New credentials obtained")
                    self.save_credentials()
                    return True
            
            return True
        
        except Exception as e:
            logger.error(f"Authorization failed: {str(e)}")
            return False
    
    def get_credentials(self):
        """
        Get the current credentials, refreshing them if necessary.
        
        Returns:
            Credentials: The OAuth credentials, or None if not available.
        """
        try:
            if not self.credentials:
                self.load_credentials()
            
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
                self.save_credentials()
            
            return self.credentials
        
        except Exception as e:
            logger.error(f"Failed to get credentials: {str(e)}")
            return None
    
    def credentials_exist(self):
        """
        Check if credentials exist for this account.
        
        Returns:
            bool: True if credentials exist, False otherwise.
        """
        # Try loading credentials
        self.load_credentials()
        return self.credentials is not None
    
    def is_authenticated(self):
        """
        Check if the user is authenticated.
        
        Returns:
            bool: True if authenticated, False otherwise.
        """
        try:
            credentials = self.get_credentials()
            return credentials is not None and credentials.valid
        except Exception as e:
            logger.error(f"Authentication check failed: {str(e)}")
            return False
    
    def load_credentials(self):
        """
        Load credentials from keychain.
        
        Returns:
            bool: True if credentials were loaded, False otherwise.
        """
        try:
            # Get token from keychain using the enhanced keychain helper
            token_json = self.keychain.get_oauth_token(self.account_id)
            
            if token_json:
                # Create credentials from the token JSON
                self.credentials = Credentials.from_authorized_user_info(token_json)
                logger.info(f"Credentials loaded for account {self.account_id}")
                return True
            
            logger.info(f"No credentials found for account {self.account_id}")
            return False
        
        except Exception as e:
            logger.error(f"Failed to load credentials: {str(e)}")
            return False
    
    def save_credentials(self):
        """
        Save credentials to keychain.
        
        Returns:
            bool: True if credentials were saved, False otherwise.
        """
        try:
            if self.credentials:
                # Convert credentials to token JSON
                token_json = {
                    'token': self.credentials.token,
                    'refresh_token': self.credentials.refresh_token,
                    'token_uri': self.credentials.token_uri,
                    'client_id': self.credentials.client_id,
                    'client_secret': self.credentials.client_secret,
                    'scopes': self.credentials.scopes
                }
                
                # Save to keychain using the enhanced method
                success = self.keychain.store_oauth_token(token_json, self.account_id)
                
                if success:
                    logger.info(f"Credentials saved for account {self.account_id}")
                    return True
                else:
                    logger.error(f"Failed to save credentials to keychain for account {self.account_id}")
                    return False
            
            logger.warning("No credentials to save")
            return False
        
        except Exception as e:
            logger.error(f"Failed to save credentials: {str(e)}")
            return False
    
    def revoke_credentials(self):
        """
        Revoke and clear the current credentials.
        
        Returns:
            bool: True if credentials were revoked, False otherwise.
        """
        try:
            # Try to revoke token if we have valid credentials
            if self.credentials and self.credentials.valid:
                # Implement token revocation if needed
                # This step is optional and may require additional API calls
                pass
            
            # Clear credentials from keychain using the enhanced method
            self.keychain.delete_oauth_token(self.account_id)
            
            # Clear in-memory credentials
            self.credentials = None
            
            logger.info(f"Credentials revoked for account {self.account_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to revoke credentials: {str(e)}")
            return False
    
    def get_client_secrets_file(self):
        """
        Get the path to the client secrets file.
        
        Returns:
            str: Path to the client secrets file, or None if not set.
        """
        try:
            # Construct the path for account-specific client secrets
            return os.path.join(self.config_dir, f'client_secrets_{self.account_id}.json')
        except Exception as e:
            logger.error(f"Failed to get client secrets file: {str(e)}")
            return None
    
    def set_client_secrets_file(self, client_secrets_file):
        """
        Set the path to the client secrets file.
        
        Args:
            client_secrets_file (str): Path to the client secrets file.
            
        Returns:
            bool: True if the path was set, False otherwise.
        """
        try:
            # Copy the client secrets file to an account-specific location
            account_client_secrets = os.path.join(
                self.config_dir, f'client_secrets_{self.account_id}.json')
            
            # Copy the file if it's not already in the right location
            if client_secrets_file != account_client_secrets:
                shutil.copy2(client_secrets_file, account_client_secrets)
            
            logger.info(f"Client secrets file set for account {self.account_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to set client secrets file: {str(e)}")
            return False
