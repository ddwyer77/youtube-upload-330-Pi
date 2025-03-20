import os
import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QProgressBar, QMenu,
    QFileDialog, QMessageBox, QSplitter, QFrame,
    QTextEdit, QLineEdit, QComboBox, QTabWidget, QGroupBox,
    QRadioButton, QButtonGroup, QScrollArea, QSizePolicy,
    QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QSize, QTimer
from PyQt6.QtGui import QIcon, QAction, QDrag, QPixmap, QFont, QImage
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget

from ..utils.config_manager import ConfigManager
from ..core.youtube_api import YouTubeAPI
from ..core.auth_manager import AuthManager
from ..core.video_processor import VideoProcessor
from .video_preview import VideoPreview

logger = logging.getLogger(__name__)

class UploadWorker(QThread):
    """Worker thread for uploading videos in the background."""
    
    # Signals
    progress_updated = pyqtSignal(int, int)  # (video_index, progress_percentage)
    upload_complete = pyqtSignal(int, bool, str)  # (video_index, success, video_id_or_error)
    metadata_generated = pyqtSignal(int, str, str, list)  # (video_index, title, description, labels)
    
    def __init__(self, video_paths, auth_manager, video_processor, config_manager):
        """
        Initialize the upload worker.
        
        Args:
            video_paths (list): List of video file paths to upload.
            auth_manager (AuthManager): Authentication manager instance.
            video_processor (VideoProcessor): Video processor instance.
            config_manager (ConfigManager): Configuration manager instance.
        """
        super().__init__()
        self.video_paths = video_paths
        self.auth_manager = auth_manager
        self.video_processor = video_processor
        self.config_manager = config_manager
        self.youtube_api = YouTubeAPI(self.auth_manager)
        self.should_stop = False
    
    def run(self):
        """Process and upload each video in the queue."""
        for i, video_path in enumerate(self.video_paths):
            if self.should_stop:
                break
            
            # Update progress
            self.progress_updated.emit(i, 10)  # Starting
            
            try:
                # Process video to generate metadata
                self.progress_updated.emit(i, 20)  # Processing
                
                sample_interval = self.config_manager.get("sample_interval", 5)
                max_title_length = self.config_manager.get("max_title_length", 100)
                
                result = self.video_processor.process_video(
                    video_path, 
                    sample_interval=sample_interval, 
                    max_title_length=max_title_length
                )
                
                title = result.get('title')
                description = result.get('description')
                labels = result.get('labels', [])
                
                # Emit metadata
                self.metadata_generated.emit(i, title, description, labels)
                
                # Update progress
                self.progress_updated.emit(i, 50)  # Uploading
                
                # Get privacy status from config
                privacy_status = self.config_manager.get("privacy_status", "public")
                
                # Upload video
                response = self.youtube_api.upload_video(
                    video_path,
                    title,
                    description,
                    tags=labels[:10],  # Use top 10 labels as tags
                    privacy_status=privacy_status
                )
                
                if response and 'id' in response:
                    video_id = response['id']
                    self.progress_updated.emit(i, 100)  # Complete
                    self.upload_complete.emit(i, True, video_id)
                    
                    # Delete after upload if configured
                    if self.config_manager.get("delete_after_upload", False):
                        try:
                            os.remove(video_path)
                            logger.info(f"Deleted video after upload: {video_path}")
                        except Exception as e:
                            logger.error(f"Error deleting video after upload: {str(e)}")
                else:
                    self.progress_updated.emit(i, 0)  # Error
                    self.upload_complete.emit(i, False, "Upload failed")
            
            except Exception as e:
                logger.error(f"Error processing/uploading video: {str(e)}")
                self.progress_updated.emit(i, 0)  # Error
                self.upload_complete.emit(i, False, str(e))
    
    def stop(self):
        """Stop the worker thread."""
        self.should_stop = True
        self.wait()


class MetadataGenerationWorker(QThread):
    """Worker thread for generating metadata in the background."""
    
    generation_completed = pyqtSignal(dict)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, video_path, video_processor, style_prompt=None):
        """
        Initialize the metadata generation worker.
        
        Args:
            video_path (str): Path to the video file.
            video_processor: Video processor instance.
            style_prompt (str, optional): Custom style instructions for text generation.
        """
        super().__init__()
        self.video_path = video_path
        self.video_processor = video_processor
        self.style_prompt = style_prompt
        
    def run(self):
        """Run the metadata generation task."""
        try:
            self.progress_updated.emit(10)
            
            # First detect objects (this is the time-consuming part)
            labels = self.video_processor.detect_objects_in_video(self.video_path)
            self.progress_updated.emit(70)
            
            # Generate metadata with style prompt
            title, description, hashtags = self.video_processor.generate_metadata(
                labels, self.video_path, style_prompt=self.style_prompt
            )
            self.progress_updated.emit(90)
            
            # Generate alternatives with the same style prompt
            alternatives = self.video_processor.generate_alternative_metadata(
                self.video_path, labels, style_prompt=self.style_prompt
            )
            
            # Gather results
            result = {
                'title': title,
                'description': description,
                'hashtags': hashtags,
                'labels': labels,
                'alternatives': alternatives,
                'thumbnail': self.video_processor.last_video_thumbnail
            }
            
            self.progress_updated.emit(100)
            self.generation_completed.emit(result)
            
        except Exception as e:
            logger.error(f"Error generating metadata: {str(e)}")
            self.generation_completed.emit({
                'error': str(e),
                'title': os.path.basename(self.video_path),
                'description': '',
                'hashtags': [],
                'labels': []
            })


class UploadPanel(QWidget):
    """Panel for managing video uploads."""
    
    # Signal to notify when configuration is updated
    config_updated = pyqtSignal(dict)
    
    def __init__(self, auth_manager=None, video_processor=None, config_manager=None, parent=None):
        """
        Initialize the upload panel.
        
        Args:
            auth_manager (AuthManager): Authentication manager for YouTube API.
            video_processor (VideoProcessor): Video processor for generating metadata.
            config_manager (ConfigManager): Application configuration manager.
            parent (QWidget): Parent widget.
        """
        super().__init__(parent)
        
        self.config_manager = config_manager or ConfigManager()
        self.auth_manager = auth_manager or AuthManager()
        
        # Try to initialize the video processor with the stored API key
        self.video_processor = video_processor
        if not self.video_processor:
            self._init_video_processor()
        
        # Video queue
        self.video_queue = []  # List of video paths
        
        # Upload worker
        self.upload_worker = None
        
        # Metadata worker
        self.metadata_worker = None
        
        # Current metadata
        self.current_metadata = {}
        
        # Selected metadata index
        self.selected_metadata_index = 0
        
        # Setup UI
        self._setup_ui()
        
        logger.info("Upload panel initialized")
    
    def _init_video_processor(self):
        """Initialize the video processor with the stored API key."""
        from ..utils.keychain_helper import KeychainHelper
        
        # Try to get API key from keychain
        api_key = KeychainHelper.get_openai_api_key()
        
        if api_key:
            try:
                # Directly initialize with the API key
                self.video_processor = VideoProcessor(openai_api_key=api_key)
                logger.info("Video processor initialized with API key from keychain")
                
                # Verify the key was properly set
                if not hasattr(self.video_processor, 'openai_api_key') or not self.video_processor.openai_api_key:
                    logger.warning("API key not properly set, trying with direct assignment")
                    self.video_processor = VideoProcessor()
                    self.video_processor.openai_api_key = api_key
                    logger.info("Set OpenAI API key directly on video processor")
            except Exception as e:
                logger.error(f"Error initializing video processor: {str(e)}")
                self.video_processor = None
        else:
            # Fall back to environment variable
            try:
                self.video_processor = VideoProcessor()
                logger.info("Video processor initialized with API key from environment")
                # Check if the API key from environment is actually valid
                if not self.video_processor.openai_api_key or self.video_processor.openai_api_key == "":
                    logger.warning("API key from environment is empty or invalid")
                    self.video_processor.openai_api_key = None
            except Exception as e:
                logger.error(f"Error initializing video processor: {str(e)}")
                self.video_processor = None
        
        # Update the generate button state based on API key availability
        if hasattr(self, 'generate_button') and hasattr(self, 'video_list'):
            has_api_key = self.video_processor is not None and hasattr(self.video_processor, 'openai_api_key') and self.video_processor.openai_api_key is not None
            has_video = self.video_list.currentItem() is not None
            if hasattr(self, 'generate_button'):
                self.generate_button.setEnabled(has_api_key and has_video)
    
    def _setup_ui(self):
        """Set up the UI components."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Splitter for video list and preview
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel (queue and controls)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Video selection section
        selection_group = QGroupBox("Video Selection")
        selection_layout = QVBoxLayout()
        
        # Add file button
        self.add_button = QPushButton("Select Video Files")
        self.add_button.setIcon(QIcon.fromTheme("document-open"))
        self.add_button.clicked.connect(self._on_add_videos)
        selection_layout.addWidget(self.add_button)
        
        # Video list
        self.video_list = QListWidget()
        self.video_list.setMinimumHeight(150)
        self.video_list.setDragDropMode(QListWidget.DragDropMode.DragDrop)
        self.video_list.setAcceptDrops(True)
        self.video_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.video_list.itemClicked.connect(self._on_video_selected)
        self.video_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.video_list.customContextMenuRequested.connect(self._show_context_menu)
        
        # Video list controls
        video_controls_layout = QHBoxLayout()
        video_controls_layout.addWidget(QLabel("Selected Videos:"))
        
        self.select_all_button = QPushButton("Select All")
        self.select_all_button.clicked.connect(self._select_all_videos)
        video_controls_layout.addWidget(self.select_all_button)
        
        selection_layout.addLayout(video_controls_layout)
        selection_layout.addWidget(self.video_list)
        
        selection_group.setLayout(selection_layout)
        left_layout.addWidget(selection_group)
        
        # Upload controls
        upload_group = QGroupBox("Upload Controls")
        upload_layout = QVBoxLayout()
        
        # Privacy options
        privacy_layout = QHBoxLayout()
        privacy_layout.addWidget(QLabel("Privacy:"))
        self.privacy_combo = QComboBox()
        self.privacy_combo.addItems(["Public", "Unlisted", "Private"])
        # Set default from config
        default_privacy = self.config_manager.get("privacy_status", "unlisted")
        self.privacy_combo.setCurrentText(default_privacy.capitalize())
        self.privacy_combo.currentTextChanged.connect(self._update_privacy_status)
        privacy_layout.addWidget(self.privacy_combo)
        upload_layout.addLayout(privacy_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        upload_layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready to upload")
        upload_layout.addWidget(self.status_label)
        
        # Upload button
        self.upload_button = QPushButton("Upload to YouTube")
        self.upload_button.setIcon(QIcon.fromTheme("network-transmit"))
        self.upload_button.clicked.connect(self._on_start_upload)
        self.upload_button.setEnabled(False)
        upload_layout.addWidget(self.upload_button)
        
        upload_group.setLayout(upload_layout)
        left_layout.addWidget(upload_group)
        
        # Add the left panel to the splitter
        splitter.addWidget(left_panel)
        
        # Right panel (video preview and metadata)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Create tabs for metadata and preview
        metadata_tabs = QTabWidget()
        
        # Metadata tab
        metadata_tab = QWidget()
        metadata_layout = QVBoxLayout(metadata_tab)
        
        # AI Generation controls
        ai_group = QGroupBox("AI Content Generation")
        ai_layout = QVBoxLayout()
        
        # Generate button with icon and style
        self.generate_button = QPushButton("Generate Title, Description & Tags")
        self.generate_button.setIcon(QIcon.fromTheme("view-refresh"))
        self.generate_button.setEnabled(False)
        self.generate_button.clicked.connect(self._generate_metadata)
        ai_layout.addWidget(self.generate_button)
        
        # Generation progress
        self.generation_progress = QProgressBar()
        self.generation_progress.setRange(0, 100)
        self.generation_progress.setValue(0)
        self.generation_progress.setVisible(False)
        ai_layout.addWidget(self.generation_progress)
        
        # Style prompt input
        style_prompt_layout = QVBoxLayout()
        style_prompt_layout.addWidget(QLabel("Style Prompt (optional):"))
        self.style_prompt_input = QTextEdit()
        self.style_prompt_input.setPlaceholderText("Add style instructions like 'use a non-chalant manner' or 'include slang terms like ts, pmo, sybau'")
        self.style_prompt_input.setMaximumHeight(60)
        style_prompt_layout.addWidget(self.style_prompt_input)
        ai_layout.addLayout(style_prompt_layout)
        
        # Load style prompt from settings if available
        default_style = self.config_manager.get("style_prompt", "")
        if default_style:
            self.style_prompt_input.setText(default_style)
            logger.info(f"Loaded style prompt from settings: {default_style}")
        
        # Variations selector
        variations_layout = QHBoxLayout()
        variations_layout.addWidget(QLabel("Variations:"))
        self.variations_combo = QComboBox()
        self.variations_combo.addItem("Original")
        self.variations_combo.setEnabled(False)
        self.variations_combo.currentIndexChanged.connect(self._variation_selected)
        variations_layout.addWidget(self.variations_combo)
        ai_layout.addLayout(variations_layout)
        
        # AI suggestions for detected objects
        self.objects_label = QLabel("Detected objects: None")
        ai_layout.addWidget(self.objects_label)
        
        ai_group.setLayout(ai_layout)
        metadata_layout.addWidget(ai_group)
        
        # Title
        metadata_layout.addWidget(QLabel("Title:"))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Video title")
        self.title_edit.textChanged.connect(self._update_upload_button_state)
        metadata_layout.addWidget(self.title_edit)
        
        # Description
        metadata_layout.addWidget(QLabel("Description:"))
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Video description")
        self.description_edit.setMaximumHeight(100)
        self.description_edit.textChanged.connect(self._update_upload_button_state)
        metadata_layout.addWidget(self.description_edit)
        
        # Tags/Hashtags
        metadata_layout.addWidget(QLabel("Tags/Hashtags:"))
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("tag1, tag2, tag3")
        self.tags_edit.textChanged.connect(self._update_upload_button_state)
        metadata_layout.addWidget(self.tags_edit)
        
        metadata_tabs.addTab(metadata_tab, "Metadata")
        
        # Video Preview tab
        preview_tab = QWidget()
        preview_layout = QVBoxLayout(preview_tab)
        
        # Video preview component
        from .video_preview import VideoPreview
        self.video_preview = VideoPreview()
        preview_layout.addWidget(self.video_preview)
        
        # Video thumbnail preview
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setMinimumHeight(240)
        self.thumbnail_label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ddd;")
        self.thumbnail_label.setText("Video preview will appear here")
        preview_layout.addWidget(self.thumbnail_label)
        
        # Video info
        self.video_info_label = QLabel("No video selected")
        preview_layout.addWidget(self.video_info_label)
        
        preview_tab.setLayout(preview_layout)
        metadata_tabs.addTab(preview_tab, "Preview")
        right_layout.addWidget(metadata_tabs)
        
        # Add the right panel to the splitter
        splitter.addWidget(right_panel)
        
        # Set initial splitter sizes (40% left, 60% right)
        splitter.setSizes([400, 600])
        
        # Add the splitter to the main layout
        main_layout.addWidget(splitter)
    
    def _on_add_videos(self):
        """Handle adding videos to the queue."""
        # Get videos directory from config
        videos_dir = self.config_manager.get("upload_folder", str(Path.home()))
        
        # Open file dialog
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Video Files",
            videos_dir,
            "Video Files (*.mp4 *.mov *.avi *.mkv *.flv);;All Files (*)"
        )
        
        if file_paths:
            for file_path in file_paths:
                self.add_video_to_queue(file_path)
    
    def add_video_to_queue(self, file_path):
        """
        Add a video to the upload queue.
        
        Args:
            file_path (str): Path to the video file.
        """
        if file_path in self.video_queue:
            logger.warning(f"Video already in queue: {file_path}")
            return
        
        # Add to queue
        self.video_queue.append(file_path)
        
        # Create list item
        item = QListWidgetItem(os.path.basename(file_path))
        item.setData(Qt.ItemDataRole.UserRole, file_path)
        self.video_list.addItem(item)
        
        logger.info(f"Added video to queue: {file_path}")
        self.status_label.setText(f"Added {os.path.basename(file_path)} to queue")
    
    def _on_video_selected(self, item):
        """
        Handle video selection in the list.
        
        Args:
            item (QListWidgetItem): The selected list item.
        """
        if self.video_list.selectedItems():
            selected_items = self.video_list.selectedItems()
            if len(selected_items) == 1:
                # Single selection - show preview
                file_path = selected_items[0].data(Qt.ItemDataRole.UserRole)
                self.video_preview.load_video(file_path)
                self.status_label.setText(f"Selected: {os.path.basename(file_path)}")
            else:
                # Multiple selection
                self.video_preview.clear()
                self.status_label.setText(f"Selected {len(selected_items)} videos")
            
            self._update_upload_button_state()
    
    def _show_context_menu(self, position):
        """
        Show context menu for video list items.
        
        Args:
            position: Position where the context menu should appear.
        """
        item = self.video_list.itemAt(position)
        if not item:
            return
        
        menu = QMenu(self)
        
        # Preview action
        preview_action = QAction("Preview", self)
        preview_action.triggered.connect(lambda: self._on_video_selected(item))
        menu.addAction(preview_action)
        
        # Remove action
        remove_action = QAction("Remove from Queue", self)
        remove_action.triggered.connect(lambda: self._remove_video_from_queue(item))
        menu.addAction(remove_action)
        
        menu.exec(self.video_list.mapToGlobal(position))
    
    def _remove_video_from_queue(self, item):
        """
        Remove a video from the upload queue.
        
        Args:
            item (QListWidgetItem): The list item to remove.
        """
        file_path = item.data(Qt.ItemDataRole.UserRole)
        row = self.video_list.row(item)
        
        # Remove from list widget
        self.video_list.takeItem(row)
        
        # Remove from queue
        if file_path in self.video_queue:
            self.video_queue.remove(file_path)
        
        logger.info(f"Removed video from queue: {file_path}")
        self.status_label.setText(f"Removed {os.path.basename(file_path)} from queue")
    
    def _on_start_upload(self):
        """Start the upload process."""
        if not self.video_queue:
            QMessageBox.warning(self, "No Videos", "Please add videos to the queue first.")
            return
        
        if self.upload_worker and self.upload_worker.isRunning():
            # Stop current upload
            self.upload_worker.stop()
            self.upload_button.setText("Start Upload")
            self.status_label.setText("Upload stopped")
            self.progress_bar.setValue(0)
            return
        
        # Check if we have the video processor
        if not self.video_processor:
            self._init_video_processor()
            if not self.video_processor:
                QMessageBox.critical(
                    self, 
                    "OpenAI API Key Missing", 
                    "Please set your OpenAI API key in the Settings tab."
                )
                return
        
        # Create upload worker
        self.upload_worker = UploadWorker(
            self.video_queue.copy(),
            self.auth_manager,
            self.video_processor,
            self.config_manager
        )
        
        # Connect signals
        self.upload_worker.progress_updated.connect(self._on_upload_progress)
        self.upload_worker.upload_complete.connect(self._on_upload_complete)
        self.upload_worker.metadata_generated.connect(self._on_metadata_generated)
        
        # Start worker
        self.upload_worker.start()
        
        # Update UI
        self.upload_button.setText("Stop Upload")
        self.status_label.setText("Upload started")
    
    @pyqtSlot(int, int)
    def _on_upload_progress(self, video_index, progress):
        """
        Handle upload progress updates.
        
        Args:
            video_index (int): Index of the video in the queue.
            progress (int): Progress percentage (0-100).
        """
        if 0 <= video_index < len(self.video_queue):
            file_path = self.video_queue[video_index]
            self.progress_bar.setValue(progress)
            
            if progress > 0 and progress < 100:
                self.status_label.setText(f"Uploading {os.path.basename(file_path)}: {progress}%")
            elif progress == 0:
                self.status_label.setText(f"Error uploading {os.path.basename(file_path)}")
    
    @pyqtSlot(int, bool, str)
    def _on_upload_complete(self, video_index, success, video_id_or_error):
        """
        Handle upload completion.
        
        Args:
            video_index (int): Index of the video in the queue.
            success (bool): Whether the upload was successful.
            video_id_or_error (str): Video ID if successful, error message otherwise.
        """
        if 0 <= video_index < len(self.video_queue):
            file_path = self.video_queue[video_index]
            
            if success:
                self.status_label.setText(f"Upload successful: {os.path.basename(file_path)}")
                logger.info(f"Video uploaded successfully: {file_path}, ID: {video_id_or_error}")
                
                # Remove from list widget if delete after upload is enabled
                if self.config_manager.get("delete_after_upload", False):
                    for i in range(self.video_list.count()):
                        item = self.video_list.item(i)
                        if item.data(Qt.ItemDataRole.UserRole) == file_path:
                            self.video_list.takeItem(i)
                            break
            else:
                self.status_label.setText(f"Upload failed: {os.path.basename(file_path)} - {video_id_or_error}")
                logger.error(f"Upload failed for {file_path}: {video_id_or_error}")
            
            # Update the button when all uploads are complete
            if video_index == len(self.video_queue) - 1:
                self.upload_button.setText("Start Upload")
    
    @pyqtSlot(int, str, str, list)
    def _on_metadata_generated(self, video_index, title, description, labels):
        """
        Handle metadata generation.
        
        Args:
            video_index (int): Index of the video in the queue.
            title (str): Generated title.
            description (str): Generated description.
            labels (list): Detected object labels.
        """
        if 0 <= video_index < len(self.video_queue):
            file_path = self.video_queue[video_index]
            logger.info(f"Metadata generated for {file_path}: {title}")
            self.status_label.setText(f"Metadata generated for {os.path.basename(file_path)}")

    def _update_privacy_status(self, privacy_text):
        """Update the privacy status in configuration."""
        privacy = privacy_text.lower()
        self.config_manager.set("privacy_status", privacy)
        self.config_manager.save()
        
        # Emit signal that config was updated
        self.config_updated.emit({"privacy_status": privacy})
    
    def _generate_metadata(self):
        """Generate metadata using AI for the selected video(s)."""
        selected_items = self.video_list.selectedItems()
        
        if not selected_items:
            QMessageBox.warning(self, "No Video Selected", "Please select video(s) first.")
            return
            
        style_prompt = self.style_prompt_input.toPlainText().strip()
        
        # Save style prompt to config
        if style_prompt:
            self.config_manager.set("style_prompt", style_prompt)
            self.config_manager.save()
            logger.info(f"Saved style prompt to settings: {style_prompt}")
        
        # Handle multiple selection
        if len(selected_items) > 1:
            self._generate_metadata_for_multiple(selected_items, style_prompt)
            return
            
        # Single video processing
        self.generate_button.setEnabled(False)
        self.generation_progress.setVisible(True)
        self.generation_progress.setValue(10)  # Show some initial progress
        
        video_path = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        # Create worker thread for metadata generation
        self.metadata_worker = MetadataGenerationWorker(
            video_path, 
            self.video_processor,
            style_prompt
        )
        self.metadata_worker.generation_completed.connect(self.metadata_generation_completed)
        self.metadata_worker.progress_updated.connect(self.generation_progress.setValue)
        self.metadata_worker.start()
        
        logger.info(f"Started metadata generation for {video_path}")
        self.status_label.setText(f"Generating metadata for {os.path.basename(video_path)}...")
    
    def _generate_metadata_for_multiple(self, items, style_prompt):
        """
        Generate metadata for multiple videos.
        
        Args:
            items (list): List of QListWidgetItems
            style_prompt (str): Style prompt for AI
        """
        # Confirm with the user
        result = QMessageBox.question(
            self,
            "Process Multiple Videos",
            f"Generate AI metadata for {len(items)} videos? This may take a while.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
            
        # Process videos one by one
        self.generate_button.setEnabled(False)
        self.generation_progress.setVisible(True)
        total_videos = len(items)
        
        for i, item in enumerate(items):
            video_path = item.data(Qt.ItemDataRole.UserRole)
            file_name = os.path.basename(video_path)
            
            # Update progress
            progress = int((i / total_videos) * 100)
            self.generation_progress.setValue(progress)
            self.status_label.setText(f"Processing {i+1}/{total_videos}: {file_name}")
            
            try:
                # Process the video
                metadata = self.video_processor.process_video(
                    video_path,
                    sample_interval=5,
                    max_title_length=100,
                    style_prompt=style_prompt
                )
                
                # Update the item with the new title
                if metadata and 'title' in metadata:
                    # Clean title (remove quotation marks)
                    new_title = self._clean_title(metadata['title'])
                    metadata['title'] = new_title
                    
                    # Display the title in the item
                    item.setText(f"{file_name} - {new_title}")
                    item.setToolTip(new_title)
                    
                    logger.info(f"Generated metadata for {file_name}: {new_title}")
                
                # Process events to keep UI responsive
                QApplication.processEvents()
                
            except Exception as e:
                logger.error(f"Error generating metadata for {file_name}: {str(e)}")
        
        # Final update
        self.generation_progress.setValue(100)
        self.status_label.setText(f"Completed metadata generation for {total_videos} videos")
        self.generate_button.setEnabled(True)
        
        # Show completion message
        QMessageBox.information(
            self,
            "Metadata Generation Complete",
            f"Generated metadata for {total_videos} videos."
        )
    
    def _clean_title(self, title):
        """Remove quotation marks from a title."""
        if not title:
            return title
        return title.replace('"', '').replace("'", "").strip()
    
    def metadata_generation_completed(self, metadata):
        """Handle completion of metadata generation."""
        self.generate_button.setEnabled(True)
        self.generation_progress.setVisible(False)
        
        if 'error' in metadata:
            self.status_label.setText(f"Generation error: {metadata['error']}")
            QMessageBox.warning(self, "Generation Error", 
                                f"Failed to generate metadata: {metadata['error']}")
            return
            
        # Store metadata
        self.current_metadata = metadata
        
        # Clean the title (remove quotation marks)
        if 'title' in metadata:
            metadata['title'] = self._clean_title(metadata['title'])
        
        # Update UI with generated metadata
        self.title_edit.setText(metadata.get('title', ''))
        self.description_edit.setText(metadata.get('description', ''))
        self.tags_edit.setText(', '.join(metadata.get('hashtags', [])))
        
        # Show detected objects
        labels = metadata.get('labels', [])
        if labels:
            # Count occurrences of each label
            from collections import Counter
            counter = Counter(labels)
            top_labels = counter.most_common(5)
            label_text = ", ".join(f"{label} ({count})" for label, count in top_labels)
            self.objects_label.setText(f"Detected objects: {label_text}")
        else:
            self.objects_label.setText("No objects detected")
        
        # Update thumbnail if available
        thumbnail = metadata.get('thumbnail')
        if thumbnail is not None:
            # Convert thumbnail to QImage and display
            thumbnail_rgb = cv2.cvtColor(thumbnail, cv2.COLOR_BGR2RGB)
            h, w, ch = thumbnail_rgb.shape
            bytes_per_line = ch * w
            qt_image = QImage(thumbnail_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            
            # Scale pixmap to fit label while maintaining aspect ratio
            self.thumbnail_label.setPixmap(pixmap.scaled(
                self.thumbnail_label.width(), 
                self.thumbnail_label.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        
        # Update variations dropdown
        self.variations_combo.clear()
        self.variations_combo.addItem("Original")
        
        alternatives = metadata.get('alternatives', [])
        if alternatives:
            for i, alt in enumerate(alternatives):
                # Clean titles in alternatives too
                if 'title' in alt:
                    alt['title'] = self._clean_title(alt['title'])
                self.variations_combo.addItem(f"Variation {i+1}")
            self.variations_combo.setEnabled(True)
        else:
            self.variations_combo.setEnabled(False)
        
        self.selected_metadata_index = 0
        self.status_label.setText("Metadata generation completed")
    
    def _variation_selected(self, index):
        """Handle selection of a metadata variation."""
        if not self.current_metadata:
            return
            
        self.selected_metadata_index = index
        
        if index == 0:
            # Original metadata
            self.title_edit.setText(self.current_metadata.get('title', ''))
            self.description_edit.setText(self.current_metadata.get('description', ''))
            self.tags_edit.setText(', '.join(self.current_metadata.get('hashtags', [])))
        else:
            # Alternative metadata
            alternatives = self.current_metadata.get('alternatives', [])
            if 0 <= (index - 1) < len(alternatives):
                alt = alternatives[index - 1]
                self.title_edit.setText(alt.get('title', ''))
                self.description_edit.setText(alt.get('description', ''))
                self.tags_edit.setText(', '.join(alt.get('hashtags', [])))
    
    def resizeEvent(self, event):
        """Handle resize events to adjust the thumbnail display."""
        super().resizeEvent(event)
        
        # If we have a pixmap, rescale it
        pixmap = self.thumbnail_label.pixmap()
        if pixmap and not pixmap.isNull():
            self.thumbnail_label.setPixmap(pixmap.scaled(
                self.thumbnail_label.width(), 
                self.thumbnail_label.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))

    def _update_upload_button_state(self):
        """Update the state of the upload button based on selection and metadata."""
        selected_items = self.video_list.selectedItems()
        if not selected_items:
            self.upload_button.setEnabled(False)
            return
            
        # For single selection, require title
        if len(selected_items) == 1:
            has_title = bool(self.title_edit.text().strip())
            self.upload_button.setEnabled(has_title)
        else:
            # Multiple selection is not supported for upload
            self.upload_button.setEnabled(False)
            
        # Update generate button state
        has_api_key = self.video_processor is not None and hasattr(self.video_processor, 'openai_api_key') and self.video_processor.openai_api_key is not None
        self.generate_button.setEnabled(bool(selected_items) and has_api_key)

    def _select_all_videos(self):
        """Select all videos in the list and enable the generate button."""
        self.video_list.selectAll()
        self.generate_button.setEnabled(True)
