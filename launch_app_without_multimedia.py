#!/usr/bin/env python3
"""
Modified launcher for YouTube Shorts Uploader
This version bypasses the QtMultimedia dependency issues
"""

import sys
import os
import logging
from pathlib import Path
import importlib

# Configure logging
def configure_logging():
    """Configure logging for the application."""
    log_dir = os.path.join(str(Path.home()), '.youtube_shorts_uploader', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'app.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

# Apply monkey patches to bypass QtMultimedia
def apply_patches():
    """
    Apply monkey patches to bypass QtMultimedia dependencies
    This prevents the app from crashing on module import
    """
    # First check if we need to patch the UI files
    try:
        # Look for the upload_panel.py file
        upload_panel_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            'youtube_shorts_uploader', 'ui', 'upload_panel.py'
        )
        
        if os.path.exists(upload_panel_path):
            # Create a modified version that doesn't import multimedia modules
            with open(upload_panel_path, 'r') as f:
                content = f.read()
            
            # Create backup if it doesn't exist
            backup_path = upload_panel_path + '.backup'
            if not os.path.exists(backup_path):
                with open(backup_path, 'w') as f:
                    f.write(content)
                print(f"Created backup: {backup_path}")
            
            # Replace imports
            if 'from PyQt6.QtMultimedia import' in content or 'from PyQt6.QtMultimediaWidgets import' in content:
                modified_content = content.replace(
                    'from PyQt6.QtMultimedia import QMediaPlayer', 
                    '# PATCHED: from PyQt6.QtMultimedia import QMediaPlayer'
                )
                modified_content = modified_content.replace(
                    'from PyQt6.QtMultimediaWidgets import QVideoWidget', 
                    '# PATCHED: from PyQt6.QtMultimediaWidgets import QVideoWidget'
                )
                
                # Add mock classes
                mock_classes = """
# Mock classes to replace multimedia classes
class QMediaPlayer:
    def __init__(self, parent=None):
        self.parent = parent
    
    def setVideoOutput(self, *args, **kwargs):
        pass
    
    def play(self, *args, **kwargs):
        pass
    
    def pause(self, *args, **kwargs):
        pass
    
    def stop(self, *args, **kwargs):
        pass

class QVideoWidget:
    def __init__(self, parent=None):
        self.parent = parent
"""
                
                # Insert after imports
                import_end = modified_content.find('\n\n', modified_content.find('import'))
                if import_end > 0:
                    modified_content = modified_content[:import_end] + mock_classes + modified_content[import_end:]
                
                # Write modified file
                with open(upload_panel_path, 'w') as f:
                    f.write(modified_content)
                
                print(f"Modified {upload_panel_path} to bypass multimedia dependencies")
    
    except Exception as e:
        print(f"Warning: Failed to patch source files: {str(e)}")
    
    print("Applied patches to bypass QtMultimedia dependencies")

if __name__ == "__main__":
    # Configure logging
    configure_logging()
    
    # Create logger
    logger = logging.getLogger(__name__)
    logger.info("Starting modified YouTube Shorts Uploader launcher")
    
    # Apply patches
    apply_patches()
    
    try:
        # Import necessary modules
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QIcon
        
        # Create Qt application
        app = QApplication(sys.argv)
        app.setApplicationName("YouTube Shorts Uploader")
        app.setOrganizationName("ClipModeGo")
        app.setOrganizationDomain("clipmodego.com")
        
        # Set app icon if available
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                "youtube_shorts_uploader", "resources", "icon.png")
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
        
        # Import module with patches applied
        from youtube_shorts_uploader.utils.config_manager import ConfigManager
        
        # Dynamically import main window to avoid early import issues
        spec = importlib.util.find_spec('youtube_shorts_uploader.ui.main_window')
        if spec is not None:
            main_window_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(main_window_module)
            MainWindow = main_window_module.MainWindow
            
            # Create main window
            window = MainWindow(ConfigManager())
            window.show()
            
            # Start the event loop
            logger.info("Application started")
            sys.exit(app.exec())
        else:
            logger.error("Could not load MainWindow module")
            print("ERROR: Could not load the main application window")
    
    except Exception as e:
        logger.error(f"Error starting application: {str(e)}", exc_info=True)
        print(f"ERROR: Failed to start application: {str(e)}")
        import traceback
        traceback.print_exc() 