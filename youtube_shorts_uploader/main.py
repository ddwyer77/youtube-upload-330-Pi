import sys
import os
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QDir
from PyQt6.QtGui import QIcon

from .ui.main_window import MainWindow
from .utils.logger import setup_logger
from .utils.config_manager import ConfigManager


def setup_app_resources():
    """Set up application resources."""
    # Set application name and organization for QSettings
    QApplication.setApplicationName("YouTube Shorts Uploader")
    QApplication.setOrganizationName("YouTubeBuddy")
    QApplication.setOrganizationDomain("example.com")
    
    # Set working directory to application directory
    app_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(app_dir)
    
    # High DPI scaling is enabled by default in PyQt6
    # These attributes were deprecated and are no longer needed


def main():
    """Main entry point for the application."""
    # Set up resources
    setup_app_resources()
    
    # Set up logging
    logger = setup_logger(logging.INFO)
    logger.info("Starting YouTube Shorts Uploader")
    
    try:
        # Create config manager
        config_manager = ConfigManager()
        
        # Create application
        app = QApplication(sys.argv)
        
        # Create main window
        main_window = MainWindow(config_manager)
        main_window.show()
        
        # Run application event loop
        sys.exit(app.exec())
    
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
