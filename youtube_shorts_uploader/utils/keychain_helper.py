import keyring
import logging

logger = logging.getLogger(__name__)

class KeychainHelper:
    """Helper class for storing and retrieving secrets in the system keychain."""
    
    # Service name for the application in the keychain
    SERVICE_NAME = "YouTubeShortsUploader"
    
    # Key names
    OPENAI_API_KEY = "openai_api_key"
    
    @staticmethod
    def set_openai_api_key(api_key):
        """
        Store the OpenAI API key in the system keychain.
        
        Args:
            api_key (str): The OpenAI API key to store.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        helper = KeychainHelper()
        return helper.set_password("openai_api_key", api_key)
    
    @staticmethod
    def get_openai_api_key():
        """
        Retrieve the OpenAI API key from the system keychain.
        
        Returns:
            str: The OpenAI API key, or None if not found or on error.
        """
        helper = KeychainHelper()
        return helper.get_password("openai_api_key")
    
    @staticmethod
    def delete_openai_api_key():
        """
        Delete the OpenAI API key from the system keychain.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            keyring.delete_password(KeychainHelper.SERVICE_NAME, KeychainHelper.OPENAI_API_KEY)
            logger.info("OpenAI API key deleted from keychain")
            return True
        except keyring.errors.PasswordDeleteError:
            logger.warning("OpenAI API key not found in keychain, nothing to delete")
            return False
        except Exception as e:
            logger.error(f"Error deleting OpenAI API key from keychain: {str(e)}")
            return False
    
    @staticmethod
    def set_custom_secret(key_name, secret):
        """
        Store a custom secret in the system keychain.
        
        Args:
            key_name (str): Name of the secret key.
            secret (str): The secret value.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            keyring.set_password(KeychainHelper.SERVICE_NAME, key_name, secret)
            logger.info(f"Secret '{key_name}' stored in keychain")
            return True
        except Exception as e:
            logger.error(f"Error storing secret '{key_name}' in keychain: {str(e)}")
            return False
    
    @staticmethod
    def get_custom_secret(key_name):
        """
        Retrieve a custom secret from the system keychain.
        
        Args:
            key_name (str): Name of the secret key.
            
        Returns:
            str: The secret value, or None if not found or on error.
        """
        try:
            secret = keyring.get_password(KeychainHelper.SERVICE_NAME, key_name)
            if secret:
                logger.info(f"Secret '{key_name}' retrieved from keychain")
            else:
                logger.warning(f"Secret '{key_name}' not found in keychain")
            return secret
        except Exception as e:
            logger.error(f"Error retrieving secret '{key_name}' from keychain: {str(e)}")
            return None
    
    @staticmethod
    def delete_custom_secret(key_name):
        """
        Delete a custom secret from the system keychain.
        
        Args:
            key_name (str): Name of the secret key.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            keyring.delete_password(KeychainHelper.SERVICE_NAME, key_name)
            logger.info(f"Secret '{key_name}' deleted from keychain")
            return True
        except keyring.errors.PasswordDeleteError:
            logger.warning(f"Secret '{key_name}' not found in keychain, nothing to delete")
            return False
        except Exception as e:
            logger.error(f"Error deleting secret '{key_name}' from keychain: {str(e)}")
            return False
            
    def set_password(self, key, password):
        """
        Store a password in the system keychain.
        
        Args:
            key (str): Key identifier for the password.
            password (str): The password to store.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            keyring.set_password(self.SERVICE_NAME, key, password)
            logger.info(f"Password stored for key: {key}")
            return True
        except Exception as e:
            logger.error(f"Error storing password for key {key}: {str(e)}")
            return False
    
    def get_password(self, key):
        """
        Retrieve a password from the system keychain.
        
        Args:
            key (str): Key identifier for the password.
            
        Returns:
            str: The password, or None if not found.
        """
        try:
            password = keyring.get_password(self.SERVICE_NAME, key)
            if password:
                logger.info(f"Password retrieved for key: {key}")
            else:
                logger.warning(f"No password found for key: {key}")
            return password
        except Exception as e:
            logger.error(f"Error retrieving password for key {key}: {str(e)}")
            return None
    
    def delete_password(self, key):
        """
        Delete a password from the system keychain.
        
        Args:
            key (str): Key identifier for the password.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            keyring.delete_password(self.SERVICE_NAME, key)
            logger.info(f"Password deleted for key: {key}")
            return True
        except keyring.errors.PasswordDeleteError:
            logger.warning(f"No password found for key: {key}, nothing to delete")
            return True  # Not finding a password is fine for deletion
        except Exception as e:
            logger.error(f"Error deleting password for key {key}: {str(e)}")
            return False
