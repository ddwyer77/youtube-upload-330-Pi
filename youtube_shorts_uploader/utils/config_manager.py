import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages application configuration and settings."""
    
    DEFAULT_CONFIG = {
        "upload_folder": "",
        "delete_after_upload": True,
        "privacy_status": "public",
        "category_id": "22",
        "sample_interval": 5,
        "max_title_length": 100,
        "api_keys": {
            "openai": ""
        },
        "theme": "system",
        "auto_start": False
    }
    
    def __init__(self, config_file=None):
        """
        Initialize the ConfigManager.
        
        Args:
            config_file (str): Path to the config file. If None, it will use 
                              ~/.youtube_shorts_uploader/config.json
        """
        if config_file is None:
            home_dir = Path.home()
            config_dir = home_dir / ".youtube_shorts_uploader"
            if not config_dir.exists():
                config_dir.mkdir(parents=True, exist_ok=True)
            self.config_file = config_dir / "config.json"
        else:
            self.config_file = Path(config_file)
        
        self.config = self._load_config()
    
    def _load_config(self):
        """
        Load configuration from file or create default.
        
        Returns:
            dict: Configuration dictionary.
        """
        if not self.config_file.exists():
            logger.info(f"Config file not found, creating default at {self.config_file}")
            self._save_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG.copy()
        
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                logger.info(f"Config loaded from {self.config_file}")
                
                # Update with any missing default fields
                updated = False
                for key, value in self.DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                        updated = True
                
                if updated:
                    logger.info("Updated config with missing default fields")
                    self._save_config(config)
                
                return config
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            logger.info("Using default configuration")
            return self.DEFAULT_CONFIG.copy()
    
    def _save_config(self, config):
        """
        Save configuration to file.
        
        Args:
            config (dict): Configuration dictionary.
        """
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
                logger.info(f"Config saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving config: {str(e)}")
    
    def get_config(self):
        """
        Get the full configuration.
        
        Returns:
            dict: Configuration dictionary.
        """
        return self.config.copy()
    
    def get(self, key, default=None):
        """
        Get a configuration value.
        
        Args:
            key (str): Configuration key.
            default: Default value if key not found.
            
        Returns:
            Configuration value or default.
        """
        return self.config.get(key, default)
    
    def set(self, key, value):
        """
        Set a configuration value.
        
        Args:
            key (str): Configuration key.
            value: Configuration value.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            self.config[key] = value
            self._save_config(self.config)
            logger.info(f"Config updated: {key} = {value}")
            return True
        except Exception as e:
            logger.error(f"Error updating config: {str(e)}")
            return False
    
    def update(self, config_dict):
        """
        Update multiple configuration values.
        
        Args:
            config_dict (dict): Dictionary of configuration values to update.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            self.config.update(config_dict)
            self._save_config(self.config)
            logger.info(f"Config updated with {len(config_dict)} values")
            return True
        except Exception as e:
            logger.error(f"Error updating config: {str(e)}")
            return False
    
    def reset(self):
        """
        Reset configuration to default.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            self.config = self.DEFAULT_CONFIG.copy()
            self._save_config(self.config)
            logger.info("Config reset to default")
            return True
        except Exception as e:
            logger.error(f"Error resetting config: {str(e)}")
            return False
