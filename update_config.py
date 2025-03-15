#!/usr/bin/env python3
"""
Script to update the YouTube Shorts Uploader configuration.
"""

import os
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration paths
HOME_DIR = os.path.expanduser("~")
CONFIG_DIR = os.path.join(HOME_DIR, ".youtube_shorts_uploader")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

def load_config():
    """Load the current configuration."""
    if not os.path.exists(CONFIG_PATH):
        logger.error(f"Configuration file not found: {CONFIG_PATH}")
        return None
    
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
            return config
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        return None

def save_config(config):
    """Save the updated configuration."""
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"Configuration saved to {CONFIG_PATH}")
        return True
    except Exception as e:
        logger.error(f"Error saving configuration: {str(e)}")
        return False

def update_config():
    """Update the application configuration."""
    # Load the current config
    current_config = load_config()
    if not current_config:
        logger.error("Failed to load current configuration")
        return False
    
    # Print current settings
    print("Current configuration:")
    print(f"- Privacy Status: {current_config.get('privacy_status', 'public')}")
    print(f"- Category ID: {current_config.get('category_id', '22')}")
    print(f"- Delete After Upload: {current_config.get('delete_after_upload', False)}")
    
    # Update privacy status
    current_config['privacy_status'] = 'unlisted'
    
    # Save the updated config
    if save_config(current_config):
        print("\nConfiguration updated successfully!")
        print("- Privacy Status: unlisted")
        return True
    else:
        print("\nFailed to update configuration.")
        return False

def main():
    """Main function to update the configuration."""
    print("\n=== YouTube Shorts Uploader Configuration Update ===\n")
    return update_config()

if __name__ == "__main__":
    main() 