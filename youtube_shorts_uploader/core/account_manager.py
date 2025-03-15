import os
import json
import uuid
import logging
from pathlib import Path
import shutil

from .auth_manager import AuthManager
from .keychain_helper import KeychainHelper
from .youtube_api import YouTubeAPI

logger = logging.getLogger(__name__)

class AccountManager:
    """
    Manages multiple YouTube accounts and facilitates switching between them.
    Handles account profiles, OAuth credentials, and account-specific settings.
    """
    
    def __init__(self, config_dir=None):
        """
        Initialize the account manager.
        
        Args:
            config_dir (str, optional): Directory for configuration files.
        """
        self.keychain = KeychainHelper()
        
        self.config_dir = config_dir or os.path.join(str(Path.home()), '.youtube_shorts_uploader')
        
        # Create config directory if it doesn't exist
        os.makedirs(self.config_dir, exist_ok=True)
        
        # File to store account information
        self.accounts_file = os.path.join(self.config_dir, 'accounts.json')
        
        # Initialize accounts list and current account
        self.accounts = []
        self.current_account = None
        
        # Load accounts from file
        self._load_accounts()
        
        # Create an auth manager for the current account
        self.auth_manager = None
        self._init_auth_manager()
        
        logger.info("Account manager initialized")
    
    def _load_accounts(self):
        """
        Load accounts from the accounts file.
        
        Returns:
            bool: True if accounts were loaded, False otherwise.
        """
        try:
            if os.path.exists(self.accounts_file):
                with open(self.accounts_file, 'r') as f:
                    data = json.load(f)
                    self.accounts = data.get('accounts', [])
                    current_account_id = data.get('current_account')
                    
                    # Set current account if it exists
                    if current_account_id:
                        for account in self.accounts:
                            if account.get('id') == current_account_id:
                                self.current_account = account
                                break
                    
                    # If no current account is set but accounts exist, use the first one
                    if not self.current_account and self.accounts:
                        self.current_account = self.accounts[0]
                    
                    logger.info(f"Loaded {len(self.accounts)} accounts")
                    return True
            
            logger.info("No accounts file found, starting with empty accounts list")
            return False
            
        except Exception as e:
            logger.error(f"Failed to load accounts: {str(e)}")
            self.accounts = []
            self.current_account = None
            return False
    
    def _save_accounts(self):
        """
        Save accounts to the accounts file.
        
        Returns:
            bool: True if accounts were saved, False otherwise.
        """
        try:
            current_account_id = self.current_account.get('id') if self.current_account else None
            
            data = {
                'accounts': self.accounts,
                'current_account': current_account_id
            }
            
            with open(self.accounts_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved {len(self.accounts)} accounts")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save accounts: {str(e)}")
            return False
    
    def _init_auth_manager(self):
        """
        Initialize the auth manager for the current account.
        
        Returns:
            bool: True if the auth manager was initialized, False otherwise.
        """
        try:
            account_id = self.current_account.get('id') if self.current_account else None
            self.auth_manager = AuthManager(
                account_id=account_id,
                config_dir=self.config_dir
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize auth manager: {str(e)}")
            return False
    
    def get_accounts(self):
        """
        Get the list of all accounts.
        
        Returns:
            list: List of account dictionaries.
        """
        return self.accounts
    
    def get_account(self, account_id):
        """
        Get a specific account by ID.
        
        Args:
            account_id (str): The account ID.
            
        Returns:
            dict: The account dictionary, or None if not found.
        """
        for account in self.accounts:
            if account.get('id') == account_id:
                return account
        return None
    
    def add_account(self, name, client_secrets_file=None):
        """
        Add a new account.
        
        Args:
            name (str): Account name.
            client_secrets_file (str, optional): Path to client secrets file.
            
        Returns:
            dict: The new account dictionary, or None if the addition failed.
        """
        try:
            # Generate a unique ID for the account
            account_id = str(uuid.uuid4())
            
            # Create the account
            account = {
                'id': account_id,
                'name': name,
                'authenticated': False,
                'channel_id': None,
                'channel_title': None
            }
            
            # Add the account to the list
            self.accounts.append(account)
            
            # If this is the first account, set it as current
            if len(self.accounts) == 1:
                self.current_account = account
                self._init_auth_manager()
            
            # Save the accounts
            self._save_accounts()
            
            # If client secrets file was provided, try to authenticate
            if client_secrets_file and os.path.exists(client_secrets_file):
                # If this is the current account, use self.auth_manager
                if self.current_account and self.current_account.get('id') == account_id:
                    success = self.auth_manager.set_client_secrets_file(client_secrets_file)
                    if success:
                        self.authenticate_account(account_id, client_secrets_file)
                else:
                    # Create a temporary auth manager for this account
                    temp_auth_manager = AuthManager(
                        account_id=account_id,
                        config_dir=self.config_dir
                    )
                    temp_auth_manager.set_client_secrets_file(client_secrets_file)
            
            logger.info(f"Added account: {name} ({account_id})")
            return account
            
        except Exception as e:
            logger.error(f"Failed to add account: {str(e)}")
            return None
    
    def remove_account(self, account_id):
        """
        Remove an account.
        
        Args:
            account_id (str): The account ID.
            
        Returns:
            bool: True if the account was removed, False otherwise.
        """
        try:
            # Find the account
            for i, account in enumerate(self.accounts):
                if account.get('id') == account_id:
                    # If this is the current account, set a new current account
                    if self.current_account and self.current_account.get('id') == account_id:
                        if len(self.accounts) > 1:
                            # Set the next account as current, or the previous if this is the last one
                            new_index = 0 if i == len(self.accounts) - 1 else i + 1
                            self.current_account = self.accounts[new_index]
                            self._init_auth_manager()
                        else:
                            # No more accounts
                            self.current_account = None
                            self.auth_manager = None
                    
                    # Remove the account
                    self.accounts.pop(i)
                    
                    # Save the accounts
                    self._save_accounts()
                    
                    logger.info(f"Removed account: {account.get('name')} ({account_id})")
                    return True
            
            logger.warning(f"Account not found: {account_id}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to remove account: {str(e)}")
            return False
    
    def set_current_account(self, account_id):
        """
        Set the current account.
        
        Args:
            account_id (str): The account ID.
            
        Returns:
            bool: True if the account was set as current, False otherwise.
        """
        try:
            # If the account is already current, do nothing
            if self.current_account and self.current_account.get('id') == account_id:
                return True
            
            # Find the account
            for account in self.accounts:
                if account.get('id') == account_id:
                    # Set as current
                    self.current_account = account
                    
                    # Initialize auth manager for this account
                    self._init_auth_manager()
                    
                    # Save the accounts
                    self._save_accounts()
                    
                    logger.info(f"Set current account: {account.get('name')} ({account_id})")
                    return True
            
            logger.warning(f"Account not found: {account_id}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to set current account: {str(e)}")
            return False
    
    def authenticate_account(self, account_id, client_secrets_file=None):
        """
        Authenticate an account with the YouTube API.
        
        Args:
            account_id (str): The account ID.
            client_secrets_file (str, optional): Path to client secrets file.
            
        Returns:
            bool: True if authentication was successful, False otherwise.
        """
        try:
            # Find the account
            account = self.get_account(account_id)
            if not account:
                logger.warning(f"Account not found: {account_id}")
                return False
            
            # If this is the current account, use self.auth_manager
            if self.current_account and self.current_account.get('id') == account_id:
                auth_manager = self.auth_manager
            else:
                # Create a temporary auth manager for this account
                auth_manager = AuthManager(
                    account_id=account_id,
                    config_dir=self.config_dir
                )
            
            # Authenticate
            success = auth_manager.authorize(client_secrets_file)
            
            if success:
                # Update the account
                account['authenticated'] = True
                
                # Try to get channel info
                youtube_api = YouTubeAPI(auth_manager)
                channel_info = youtube_api.get_channel_info()
                
                if channel_info:
                    account['channel_id'] = channel_info.get('id')
                    account['channel_title'] = channel_info.get('title')
                
                # Save the accounts
                self._save_accounts()
                
                logger.info(f"Authenticated account: {account.get('name')} ({account_id})")
                return True
            
            logger.warning(f"Authentication failed for account: {account.get('name')} ({account_id})")
            return False
            
        except Exception as e:
            logger.error(f"Failed to authenticate account: {str(e)}")
            return False
    
    def revoke_authentication(self, account_id):
        """
        Revoke authentication for an account.
        
        Args:
            account_id (str): The account ID.
            
        Returns:
            bool: True if authentication was revoked, False otherwise.
        """
        try:
            # Find the account
            account = self.get_account(account_id)
            if not account:
                logger.warning(f"Account not found: {account_id}")
                return False
            
            # If this is the current account, use self.auth_manager
            if self.current_account and self.current_account.get('id') == account_id:
                auth_manager = self.auth_manager
            else:
                # Create a temporary auth manager for this account
                auth_manager = AuthManager(
                    account_id=account_id,
                    config_dir=self.config_dir
                )
            
            # Revoke authentication
            success = auth_manager.revoke_credentials()
            
            if success:
                # Update the account
                account['authenticated'] = False
                
                # Save the accounts
                self._save_accounts()
                
                logger.info(f"Revoked authentication for account: {account.get('name')} ({account_id})")
                return True
            
            logger.warning(f"Failed to revoke authentication for account: {account.get('name')} ({account_id})")
            return False
            
        except Exception as e:
            logger.error(f"Failed to revoke authentication: {str(e)}")
            return False
    
    def update_account_info(self, account_id, name=None):
        """
        Update account information.
        
        Args:
            account_id (str): The account ID.
            name (str, optional): New account name.
            
        Returns:
            bool: True if the account was updated, False otherwise.
        """
        try:
            # Find the account
            account = self.get_account(account_id)
            if not account:
                logger.warning(f"Account not found: {account_id}")
                return False
            
            # Update the account
            if name is not None:
                account['name'] = name
            
            # Save the accounts
            self._save_accounts()
            
            logger.info(f"Updated account: {account.get('name')} ({account_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update account: {str(e)}")
            return False
    
    def refresh_account_channel_info(self, account_id):
        """
        Refresh channel information for an account.
        
        Args:
            account_id (str): The account ID.
            
        Returns:
            dict: The updated channel info, or None if the refresh failed.
        """
        try:
            # Find the account
            account = self.get_account(account_id)
            if not account:
                logger.warning(f"Account not found: {account_id}")
                return None
            
            # If the account is not authenticated, return None
            if not account.get('authenticated', False):
                logger.warning(f"Account not authenticated: {account.get('name')} ({account_id})")
                return None
            
            # If this is the current account, use self.auth_manager
            if self.current_account and self.current_account.get('id') == account_id:
                auth_manager = self.auth_manager
            else:
                # Create a temporary auth manager for this account
                auth_manager = AuthManager(
                    account_id=account_id,
                    config_dir=self.config_dir
                )
            
            # Try to get channel info
            youtube_api = YouTubeAPI(auth_manager)
            channel_info = youtube_api.get_channel_info()
            
            if channel_info:
                # Update the account
                account['channel_id'] = channel_info.get('id')
                account['channel_title'] = channel_info.get('title')
                
                # Save the accounts
                self._save_accounts()
                
                logger.info(f"Refreshed channel info for account: {account.get('name')} ({account_id})")
                return channel_info
            
            logger.warning(f"Failed to refresh channel info for account: {account.get('name')} ({account_id})")
            return None
            
        except Exception as e:
            logger.error(f"Failed to refresh channel info: {str(e)}")
            return None

# Helper function to get current time
def import_time():
    from datetime import datetime
    return datetime.now().isoformat() 