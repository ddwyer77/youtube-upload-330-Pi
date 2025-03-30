#!/usr/bin/env python3
"""
Enhanced YouTube Shorts Uploader launcher

This launcher handles Qt multimedia compatibility issues by using real multimedia
components when available and falling back to mocks when they're not.
"""

import sys
import os
import logging
import importlib
from pathlib import Path

# Configure logging
def configure_logging():
    """Set up application logging"""
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
    return logging.getLogger(__name__)

# Simple signal class for mocks
class Signal:
    """Simple signal implementation for mock objects"""
    def __init__(self):
        self.callbacks = []
    
    def connect(self, callback):
        if callback not in self.callbacks:
            self.callbacks.append(callback)
    
    def disconnect(self, callback=None):
        if callback:
            if callback in self.callbacks:
                self.callbacks.remove(callback)
        else:
            self.callbacks.clear()
    
    def emit(self, *args, **kwargs):
        for callback in self.callbacks:
            callback(*args, **kwargs)

# Handle Qt multimedia compatibility
def setup_multimedia():
    """
    Set up multimedia components, using real ones if available,
    or providing mock implementations if not
    """
    # Try importing real multimedia modules
    try:
        # Import both modules to test them
        from PyQt6 import QtMultimedia, QtMultimediaWidgets
        # Try creating a player to verify it works
        player = QtMultimedia.QMediaPlayer()
        # If we get here, both modules work fine
        print("Using real Qt multimedia components")
        return True
    except Exception as e:
        print(f"Qt multimedia not available: {e}")
        print("Using mock multimedia components instead")
        
        # Define mock multimedia modules
        class MockQtMultimedia:
            """Mock implementation of QtMultimedia module"""
            class QMediaPlayer:
                """Mock QMediaPlayer class with signal support"""
                def __init__(self, parent=None):
                    self.parent = parent
                    self._position = 0
                    self._duration = 0
                    self.video_output = None
                    self.audio_output = None
                    self._media_status = 0
                    self._playback_state = 0
                    
                    # Create signals
                    self.positionChanged = Signal()
                    self.durationChanged = Signal()
                    self.mediaStatusChanged = Signal()
                    self.playbackStateChanged = Signal()
                    self.errorOccurred = Signal()
                
                def setVideoOutput(self, output):
                    self.video_output = output
                
                def setAudioOutput(self, output):
                    self.audio_output = output
                
                def play(self): 
                    self._playback_state = MockQtMultimedia.PlaybackState.PlayingState
                    self.playbackStateChanged.emit(self._playback_state)
                
                def pause(self): 
                    self._playback_state = MockQtMultimedia.PlaybackState.PausedState
                    self.playbackStateChanged.emit(self._playback_state)
                
                def stop(self): 
                    self._playback_state = MockQtMultimedia.PlaybackState.StoppedState
                    self.playbackStateChanged.emit(self._playback_state)
                
                def setPosition(self, pos): 
                    self._position = pos
                    self.positionChanged.emit(pos)
                
                def position(self): 
                    return self._position
                
                def duration(self): 
                    return self._duration
                
                def setDuration(self, duration):
                    # Helper method to set duration (not in real API)
                    self._duration = duration
                    self.durationChanged.emit(duration)
                
                def mediaStatus(self): 
                    return self._media_status
                
                def setSource(self, source):
                    self._media_status = MockQtMultimedia.MediaStatus.LoadingMedia
                    self.mediaStatusChanged.emit(self._media_status)
                    
                    # Simulate successful loading after a moment
                    self._media_status = MockQtMultimedia.MediaStatus.LoadedMedia
                    self.mediaStatusChanged.emit(self._media_status)
                    
                    # Set a fake duration for the media
                    self.setDuration(60000)  # 1 minute in milliseconds
            
            class QAudioOutput:
                """Mock QAudioOutput class"""
                def __init__(self, parent=None):
                    self.parent = parent
                    self.volume = 1.0
                    self.muted = False
                
                def setVolume(self, volume):
                    self.volume = volume
                    
                def volume(self):
                    return self.volume
                    
                def setMuted(self, muted):
                    self.muted = muted
                    
                def isMuted(self):
                    return self.muted
            
            # Define required enums
            class PlaybackState:
                StoppedState = 0
                PlayingState = 1
                PausedState = 2
            
            class MediaStatus:
                NoMedia = 0
                LoadingMedia = 1
                LoadedMedia = 2
                StalledMedia = 3
                BufferingMedia = 4
                BufferedMedia = 5
                EndOfMedia = 6
                InvalidMedia = 7
            
            # Add all necessary classes and constants
            QMediaPlayer = QMediaPlayer
            QAudioOutput = QAudioOutput
            PlaybackState = PlaybackState
            MediaStatus = MediaStatus
            
        class MockQtMultimediaWidgets:
            """Mock implementation of QtMultimediaWidgets module"""
            class QVideoWidget:
                """Mock QVideoWidget class"""
                def __init__(self, parent=None):
                    self.parent = parent
                
                def show(self): pass
                def hide(self): pass
                def setGeometry(self, *args): pass
                def size(self): return (320, 240)
            
            # Add all required classes
            QVideoWidget = QVideoWidget
        
        # Register mock modules in sys.modules
        sys.modules['PyQt6.QtMultimedia'] = MockQtMultimedia
        sys.modules['PyQt6.QtMultimediaWidgets'] = MockQtMultimediaWidgets
        
        return True

def main():
    """Main application entry point"""
    # Configure logging
    logger = configure_logging()
    logger.info("Starting YouTube Shorts Uploader (enhanced launcher)")
    
    # Enable OAuth insecure for local testing
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    
    # Set up multimedia components
    if not setup_multimedia():
        logger.error("Failed to set up multimedia components")
        print("ERROR: Failed to set up multimedia components")
        return 1
    
    try:
        # Import Qt modules
        from PyQt6.QtWidgets import QApplication, QLabel, QMessageBox
        from PyQt6.QtCore import Qt, QTimer
        from PyQt6.QtGui import QFont
        
        # Create Qt application
        app = QApplication(sys.argv)
        app.setApplicationName("YouTube Shorts Uploader")
        app.setOrganizationName("ClipModeGo")
        app.setOrganizationDomain("clipmodego.com")
        
        # Show splash screen while loading
        splash_label = QLabel()
        splash_label.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint)
        splash_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Create styled splash text
        splash_text = "<html><body style='text-align: center;'>"
        splash_text += "<h1 style='color: #FF0000; font-size: 24px;'>YouTube Shorts Uploader</h1>"
        splash_text += "<p>Loading application...</p>"
        splash_text += "<p style='font-style: italic;'>Enhanced compatibility mode</p>"
        splash_text += "</body></html>"
        
        splash_label.setText(splash_text)
        splash_label.setMinimumWidth(400)
        splash_label.setStyleSheet("background-color: white; border: 1px solid #cccccc; border-radius: 10px; padding: 20px;")
        splash_label.show()
        
        # Process events to display splash
        app.processEvents()
        
        # Import config manager
        from youtube_shorts_uploader.utils.config_manager import ConfigManager
        config_manager = ConfigManager()
        
        # Function to initialize main window after splash screen
        def initialize_main():
            try:
                # Import main window class 
                from youtube_shorts_uploader.ui.main_window import MainWindow
                window = MainWindow(config_manager)
                window.show()
                splash_label.hide()
                logger.info("Application main window displayed")
            except Exception as e:
                logger.error(f"Error initializing main window: {str(e)}", exc_info=True)
                splash_label.hide()
                
                # Show error message to user
                QMessageBox.critical(
                    None, 
                    "Error Starting Application",
                    f"Failed to initialize application: {str(e)}\n\n"
                    "This may be due to compatibility issues with your system."
                )
                
                import traceback
                traceback.print_exc()
        
        # Use timer to show splash for a moment before initializing
        QTimer.singleShot(1000, initialize_main)
        
        return app.exec()
    
    except Exception as e:
        logger.error(f"Error starting application: {str(e)}", exc_info=True)
        print(f"ERROR: Failed to start application: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 