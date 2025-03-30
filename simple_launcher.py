#!/usr/bin/env python3
"""
Simple minimal launcher for YouTube Shorts Uploader
This version creates just a basic window without multimedia dependencies
"""

import sys
import os
import logging
from pathlib import Path

try:
    from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget, QMessageBox
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon, QFont
except ImportError as e:
    print(f"Failed to import PyQt6: {e}")
    print("Please make sure PyQt6 is installed: pip install PyQt6")
    sys.exit(1)

class SimpleMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Shorts Uploader (Simple Mode)")
        self.setMinimumSize(800, 600)
        
        # Create central widget with layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Add title
        title_label = QLabel("YouTube Shorts Uploader")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Add description
        desc_label = QLabel("This is a limited functionality version due to Qt multimedia compatibility issues.")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_label)
        
        # Add status message
        status_label = QLabel("Status: Running in limited mode without video preview capability")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(status_label)
        
        # Add some buttons
        auth_button = QPushButton("Test Authentication")
        auth_button.clicked.connect(self.test_auth)
        layout.addWidget(auth_button)
        
        upload_button = QPushButton("Check Uploads")
        upload_button.clicked.connect(self.check_uploads)
        layout.addWidget(upload_button)
        
        # Set up app icon if available
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                "youtube_shorts_uploader", "resources", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
    
    def test_auth(self):
        """Test authentication flow by running test_auth.py"""
        try:
            QMessageBox.information(self, "Authentication", 
                                   "Starting authentication test...\n\n"
                                   "This will open a browser window for Google authentication.")
            
            # Run the auth test process
            import subprocess
            subprocess.Popen([sys.executable, "test_auth.py"])
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start authentication test: {str(e)}")
    
    def check_uploads(self):
        """Check uploads by running check_uploads.py"""
        try:
            QMessageBox.information(self, "Check Uploads", 
                                   "Starting upload check...\n\n"
                                   "This will open a terminal window to display your YouTube uploads.")
            
            # Run the upload check process
            import subprocess
            subprocess.Popen([sys.executable, "check_uploads.py"])
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to check uploads: {str(e)}")

def main():
    # Enable insecure transport for local OAuth testing
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("YouTube Shorts Uploader")
    app.setOrganizationName("ClipModeGo")
    app.setOrganizationDomain("clipmodego.com")
    
    # Create and show main window
    window = SimpleMainWindow()
    window.show()
    
    # Start the event loop
    return app.exec()

if __name__ == "__main__":
    sys.exit(main()) 