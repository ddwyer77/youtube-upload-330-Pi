import os
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QSlider, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QUrl, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QIcon
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

logger = logging.getLogger(__name__)

class VideoPreview(QWidget):
    """Widget for previewing videos."""
    
    def __init__(self, parent=None):
        """
        Initialize the video preview widget.
        
        Args:
            parent (QWidget): Parent widget.
        """
        super().__init__(parent)
        
        # Create media player and audio output
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        # Connect signals
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)
        self.media_player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.media_player.errorOccurred.connect(self._on_error)
        
        # Track current video path
        self.current_video_path = None
        
        # Setup UI
        self._setup_ui()
        
        logger.info("Video preview widget initialized")
    
    def _setup_ui(self):
        """Set up the UI components."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Video widget
        self.video_widget = QVideoWidget()
        self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.media_player.setVideoOutput(self.video_widget)
        main_layout.addWidget(self.video_widget)
        
        # Control area
        control_layout = QVBoxLayout()
        
        # Timeline slider
        self.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        self.timeline_slider.setRange(0, 0)
        self.timeline_slider.sliderMoved.connect(self._on_slider_moved)
        control_layout.addWidget(self.timeline_slider)
        
        # Player controls
        player_controls_layout = QHBoxLayout()
        
        # Play/pause button
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self._on_play_pause)
        player_controls_layout.addWidget(self.play_button)
        
        # Stop button
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self._on_stop)
        player_controls_layout.addWidget(self.stop_button)
        
        # Volume slider (0-100)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)  # Default volume: 70%
        self.volume_slider.setMaximumWidth(100)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        player_controls_layout.addWidget(self.volume_slider)
        
        # Time labels
        self.time_label = QLabel("00:00 / 00:00")
        player_controls_layout.addWidget(self.time_label)
        
        control_layout.addLayout(player_controls_layout)
        main_layout.addLayout(control_layout)
        
        # Set initial volume
        self._on_volume_changed(self.volume_slider.value())
    
    def load_video(self, file_path):
        """
        Load a video for playback.
        
        Args:
            file_path (str): Path to the video file.
        """
        if not os.path.exists(file_path):
            logger.error(f"Video file not found: {file_path}")
            return
        
        # Stop current playback
        self.media_player.stop()
        
        # Load new video
        video_url = QUrl.fromLocalFile(file_path)
        self.media_player.setSource(video_url)
        self.current_video_path = file_path
        
        # Update UI
        self.play_button.setText("Play")
        self.timeline_slider.setValue(0)
        self.time_label.setText("00:00 / 00:00")
        
        logger.info(f"Loaded video: {file_path}")
    
    def _on_play_pause(self):
        """Toggle video playback."""
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()
    
    def _on_stop(self):
        """Stop video playback."""
        self.media_player.stop()
        self.timeline_slider.setValue(0)
        self.play_button.setText("Play")
    
    def _on_slider_moved(self, position):
        """
        Handle timeline slider movement.
        
        Args:
            position (int): New position value.
        """
        self.media_player.setPosition(position)
    
    def _on_volume_changed(self, volume):
        """
        Handle volume slider movement.
        
        Args:
            volume (int): Volume value (0-100).
        """
        # Scale volume to 0.0 - 1.0
        self.audio_output.setVolume(volume / 100.0)
    
    def _on_position_changed(self, position):
        """
        Handle media player position change.
        
        Args:
            position (int): Current playback position in milliseconds.
        """
        # Update slider position
        self.timeline_slider.setValue(position)
        
        # Update time label
        current_time = self._format_time(position)
        total_time = self._format_time(self.media_player.duration())
        self.time_label.setText(f"{current_time} / {total_time}")
    
    def _on_duration_changed(self, duration):
        """
        Handle media player duration change.
        
        Args:
            duration (int): Media duration in milliseconds.
        """
        self.timeline_slider.setRange(0, duration)
        total_time = self._format_time(duration)
        current_time = self._format_time(0)
        self.time_label.setText(f"{current_time} / {total_time}")
    
    def _on_playback_state_changed(self, state):
        """
        Handle playback state changes.
        
        Args:
            state: Current playback state.
        """
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_button.setText("Pause")
        else:
            self.play_button.setText("Play")
    
    def _on_error(self, error, error_string):
        """
        Handle media player errors.
        
        Args:
            error: Error code.
            error_string (str): Error message.
        """
        logger.error(f"Media player error: {error} - {error_string}")
        self.time_label.setText("Error: Could not play video")
    
    def _format_time(self, milliseconds):
        """
        Format time in milliseconds to MM:SS.
        
        Args:
            milliseconds (int): Time in milliseconds.
            
        Returns:
            str: Formatted time string.
        """
        seconds = milliseconds // 1000
        minutes = seconds // 60
        seconds %= 60
        return f"{minutes:02}:{seconds:02}"
