import os
import json
import logging
import keyring
import getpass
from pathlib import Path
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

class KeychainHelper:
    """
    Helper class for securely storing credentials using the system's keychain/keyring.
    Uses the keyring library for cross-platform credential storage.
    Falls back to file-based storage if keyring fails.
    """
    
    # Service name used for keyring entries
    SERVICE_NAME = "YoutubeShortUploader"
    
    def __init__(self, service_name=None):
        """
        Initialize KeychainHelper.
        
        Args:
            service_name (str, optional): Custom service name for keyring entries.
                Defaults to YoutubeShortUploader.
        """
        self.service_name = service_name or self.SERVICE_NAME
        self.use_file_fallback = False
        self.file_storage_path = os.path.expanduser("~/.youtube_shorts_uploader/credentials")
        
        # Ensure storage directory exists
        os.makedirs(os.path.dirname(self.file_storage_path), exist_ok=True)
        
        # Test keyring, use file fallback if it fails
        try:
            test_result = self._test_keyring()
            if not test_result:
                logger.warning("Keyring test failed, using file-based credential storage")
                self.use_file_fallback = True
        except Exception as e:
            logger.warning(f"Keyring unavailable, using file-based credential storage: {str(e)}")
            self.use_file_fallback = True
            
        # Generate encryption key for file storage
        self._setup_encryption()
            
        logger.debug(f"Initialized KeychainHelper with service name: {self.service_name}")
        
    def _test_keyring(self):
        """Test if keyring is working properly"""
        try:
            # Try setting and retrieving a test value
            test_key = "_test_keyring_functionality"
            test_value = "test_value"
            keyring.set_password(self.service_name, test_key, test_value)
            retrieved = keyring.get_password(self.service_name, test_key)
            keyring.delete_password(self.service_name, test_key)
            return retrieved == test_value
        except Exception:
            return False
            
    def _setup_encryption(self):
        """Setup encryption for file-based storage"""
        # Generate a key from a password (use machine-specific value)
        password = getpass.getuser() + "youtube_shorts_uploader_salt"
        password_bytes = password.encode()
        salt = b'youtube_shorts_salt'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
        self.cipher_suite = Fernet(key)
        
    def _read_file_storage(self):
        """Read credentials from file storage"""
        try:
            if not os.path.exists(self.file_storage_path):
                return {}
                
            with open(self.file_storage_path, 'rb') as f:
                encrypted_data = f.read()
                
            if not encrypted_data:
                return {}
                
            decrypted_data = self.cipher_suite.decrypt(encrypted_data)
            return json.loads(decrypted_data)
        except Exception as e:
            logger.error(f"Error reading from file storage: {str(e)}")
            return {}
            
    def _write_file_storage(self, data):
        """Write credentials to file storage"""
        try:
            encrypted_data = self.cipher_suite.encrypt(json.dumps(data).encode())
            with open(self.file_storage_path, 'wb') as f:
                f.write(encrypted_data)
            return True
        except Exception as e:
            logger.error(f"Error writing to file storage: {str(e)}")
            return False
    
    def set_password(self, key, password):
        """
        Store a password securely in the system's keychain or file fallback.
        
        Args:
            key (str): Key identifier for the password.
            password (str): The password to store.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        # If using file fallback
        if self.use_file_fallback:
            try:
                data = self._read_file_storage()
                data[key] = password
                success = self._write_file_storage(data)
                if success:
                    logger.info(f"Successfully stored password for key {key} in file storage")
                return success
            except Exception as e:
                logger.error(f"Failed to store password for key {key} in file storage: {str(e)}")
                return False
        
        # Otherwise use keyring
        try:
            # Get the current username for the keyring
            username = getpass.getuser()
            
            # Store the password with a unique identifier
            keyring.set_password(self.service_name, f"{username}_{key}", password)
            logger.info(f"Successfully stored password for key: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to store password for key {key} in keyring: {str(e)}")
            # Try file fallback if keyring fails
            self.use_file_fallback = True
            return self.set_password(key, password)
    
    def get_password(self, key):
        """
        Retrieve a password from the system's keychain or file fallback.
        
        Args:
            key (str): Key identifier for the password.
        
        Returns:
            str: The stored password, or None if not found.
        """
        # If using file fallback
        if self.use_file_fallback:
            try:
                data = self._read_file_storage()
                password = data.get(key)
                if password:
                    logger.debug(f"Successfully retrieved password for key {key} from file storage")
                else:
                    logger.debug(f"No password found for key {key} in file storage")
                return password
            except Exception as e:
                logger.error(f"Failed to retrieve password for key {key} from file storage: {str(e)}")
                return None
        
        # Otherwise use keyring
        try:
            # Get the current username for the keyring
            username = getpass.getuser()
            
            # Retrieve the password
            password = keyring.get_password(self.service_name, f"{username}_{key}")
            if password:
                logger.debug(f"Successfully retrieved password for key: {key}")
            else:
                logger.debug(f"No password found for key: {key}")
                # Try file fallback
                self.use_file_fallback = True
                return self.get_password(key)
            return password
        except Exception as e:
            logger.error(f"Failed to retrieve password for key {key} from keyring: {str(e)}")
            # Try file fallback if keyring fails
            self.use_file_fallback = True
            return self.get_password(key)
    
    def delete_password(self, key):
        """
        Delete a password from the system's keychain or file fallback.
        
        Args:
            key (str): Key identifier for the password.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        # If using file fallback
        if self.use_file_fallback:
            try:
                data = self._read_file_storage()
                if key in data:
                    del data[key]
                    success = self._write_file_storage(data)
                    if success:
                        logger.info(f"Successfully deleted password for key {key} from file storage")
                    return success
                return True  # Key wasn't there, so "deletion" succeeded
            except Exception as e:
                logger.error(f"Failed to delete password for key {key} from file storage: {str(e)}")
                return False
        
        # Otherwise use keyring
        try:
            # Get the current username for the keyring
            username = getpass.getuser()
            
            # Try to delete from keyring
            try:
                keyring.delete_password(self.service_name, f"{username}_{key}")
                logger.info(f"Successfully deleted password for key: {key}")
                return True
            except keyring.errors.PasswordDeleteError:
                # Password didn't exist, but that's fine for deletion
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete password for key {key} from keyring: {str(e)}")
            # Try file fallback if keyring fails
            self.use_file_fallback = True
            return self.delete_password(key)
    
    def store_oauth_token(self, token_data, account_id=None):
        """
        Store OAuth token data securely.
        
        Args:
            token_data (dict): OAuth token data to store.
            account_id (str): Optional account ID to associate with token
        
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # Convert token data to JSON string
            token_json = json.dumps(token_data)
            key = f'youtube_token_{account_id}' if account_id else 'oauth_token'
            return self.set_password(key, token_json)
        except Exception as e:
            logger.error(f"Failed to store OAuth token: {str(e)}")
            return False
    
    def get_oauth_token(self, account_id=None):
        """
        Retrieve OAuth token data.
        
        Args:
            account_id (str): Optional account ID to retrieve token for
            
        Returns:
            dict: The stored OAuth token data, or None if not found.
        """
        try:
            key = f'youtube_token_{account_id}' if account_id else 'oauth_token'
            token_json = self.get_password(key)
            if token_json:
                return json.loads(token_json)
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve OAuth token: {str(e)}")
            return None
    
    def delete_oauth_token(self, account_id=None):
        """
        Delete stored OAuth token data.
        
        Args:
            account_id (str): Optional account ID to delete token for
            
        Returns:
            bool: True if successful, False otherwise.
        """
        key = f'youtube_token_{account_id}' if account_id else 'oauth_token'
        return self.delete_password(key)
    
    @staticmethod
    def is_available():
        """
        Check if the keyring service is available on this system.
        
        Returns:
            bool: True if available, False otherwise.
        """
        try:
            # Try to use the keyring
            keyring.get_keyring()
            return True
        except Exception:
            return False 