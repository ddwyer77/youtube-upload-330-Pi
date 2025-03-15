#!/usr/bin/env python3
"""
YouTube Shorts Uploader

Main entry point for the YouTube Shorts Uploader application.
"""

import sys
import os
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from youtube_shorts_uploader.ui.main_window import MainWindow
from youtube_shorts_uploader.utils.config_manager import ConfigManager

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

if __name__ == "__main__":
    # Configure logging
    configure_logging()
    
    # Create logger
    logger = logging.getLogger(__name__)
    logger.info("Starting YouTube Shorts Uploader")
    
    # Create config manager
    config_manager = ConfigManager()
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("YouTube Shorts Uploader")
    app.setOrganizationName("ClipModeGo")
    app.setOrganizationDomain("clipmodego.com")
    
    # Set app icon if available
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # Create main window
    window = MainWindow(config_manager)
    window.show()
    
    # Start the event loop
    logger.info("Application started")
    sys.exit(app.exec()) 