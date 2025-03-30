#!/usr/bin/env python3
"""
Enhanced launcher for YouTube Shorts Uploader with patched upload functionality.
This launcher applies a patch to the YouTube API component for more reliable uploads.
"""

import os
import sys
import logging
import time
from pathlib import Path

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_paths():
    """
    Set up paths for the application.
    
    Ensures the token.pickle file is in the right location and
    adds the application directory to the Python path.
    """
    # Get the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Add project root to Python path
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # Ensure token.pickle is in the project root if not already
    token_path = os.path.join(project_root, "token.pickle")
    config_dir = os.path.join(str(Path.home()), '.youtube_shorts_uploader')
    config_token_path = os.path.join(config_dir, "token.pickle")
    
    if not os.path.exists(token_path) and os.path.exists(config_token_path):
        try:
            import shutil
            shutil.copy2(config_token_path, token_path)
            logger.info(f"Copied token.pickle from {config_token_path} to {token_path}")
        except Exception as e:
            logger.warning(f"Could not copy token.pickle: {e}")
    
    # Return the paths dictionary
    return {
        "project_root": project_root,
        "token_path": token_path,
        "config_dir": config_dir
    }

def apply_youtube_api_patch():
    """
    Apply the patch to the YouTube API module for more reliable uploads.
    """
    try:
        # Import the patch module
        from youtube_shorts_uploader.core.youtube_api_patch import patch_youtube_api
        
        # Apply the patch
        success = patch_youtube_api()
        
        if success:
            logger.info("Successfully applied YouTube API patch")
            return True
        else:
            logger.warning("Failed to apply YouTube API patch, will use original implementation")
            return False
    
    except Exception as e:
        logger.error(f"Error applying YouTube API patch: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def copy_youtube_api_patch():
    """
    Copy the YouTube API patch file to the correct location if needed.
    """
    try:
        # Define source and destination paths
        source_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                  "youtube_shorts_uploader/core/youtube_api_patch.py")
        dest_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                "youtube_shorts_uploader/core/youtube_api_patch.py")
        
        # Check if the patch file exists
        if not os.path.exists(source_path):
            source_path = "youtube_api_patch.py"
            if not os.path.exists(source_path):
                logger.error("YouTube API patch file not found")
                return False
        
        # Ensure the core directory exists
        core_dir = os.path.dirname(dest_path)
        os.makedirs(core_dir, exist_ok=True)
        
        # Copy the patch file if needed
        if source_path != dest_path and not os.path.exists(dest_path):
            import shutil
            shutil.copy2(source_path, dest_path)
            logger.info(f"Copied YouTube API patch to {dest_path}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error copying YouTube API patch: {str(e)}")
        return False

def launch_app():
    """
    Launch the YouTube Shorts Uploader application.
    """
    try:
        # Import the main application module
        from youtube_shorts_uploader import app
        
        # Run the application
        logger.info("Starting YouTube Shorts Uploader with patched YouTube API")
        app.main()
    
    except ImportError:
        # If the main app module import fails, try running run_fixed.py
        logger.warning("Could not import main application module, falling back to run_fixed.py")
        
        try:
            # Try to run the run_fixed.py script
            run_fixed_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_fixed.py")
            
            if os.path.exists(run_fixed_path):
                from run_fixed import main
                main()
            else:
                logger.error("run_fixed.py not found")
                return False
        
        except Exception as e:
            logger.error(f"Error running application: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    except Exception as e:
        logger.error(f"Error launching application: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def main():
    """
    Main entry point for the enhanced launcher.
    """
    logger.info("Starting enhanced YouTube Shorts Uploader launcher with patched uploads")
    
    # Set up paths
    paths = setup_paths()
    
    # Copy the patch file if needed
    copy_youtube_api_patch()
    
    # Apply the YouTube API patch
    apply_youtube_api_patch()
    
    # Launch the application
    launch_app()

if __name__ == "__main__":
    main() 