import os
import logging
import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QComboBox, QSpinBox, QDateTimeEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt, QDateTime
from PyQt6.QtGui import QBrush, QColor

logger = logging.getLogger(__name__)

class SchedulePanel(QWidget):
    """
    Panel for managing scheduled video uploads.
    Supports importing folders of videos and setting scheduled times.
    """
    
    def __init__(self, account_manager, scheduler, video_processor=None):
        """
        Initialize the schedule panel.
        
        Args:
            account_manager: Account manager for handling YouTube accounts
            scheduler: Upload scheduler for managing scheduled uploads
            video_processor: Video processor for generating metadata
        """
        super().__init__()
        
        self.account_manager = account_manager
        self.scheduler = scheduler
        self.video_processor = video_processor
        
        # Initialize UI
        self.init_ui()
        
        logger.info("Schedule panel initialized")
    
    def init_ui(self):
        """Initialize the UI components"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Import section
        import_group_layout = QVBoxLayout()
        
        # Account selection
        account_layout = QHBoxLayout()
        account_layout.addWidget(QLabel("YouTube Account:"))
        
        self.account_combo = QComboBox()
        self.update_account_list()
        account_layout.addWidget(self.account_combo)
        import_group_layout.addLayout(account_layout)
        
        # Folder selection
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Video Folder:"))
        
        self.folder_path_label = QLabel("No folder selected")
        folder_layout.addWidget(self.folder_path_label, 1)
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_folder)
        folder_layout.addWidget(self.browse_button)
        
        import_group_layout.addLayout(folder_layout)
        
        # Scheduling options
        schedule_layout = QHBoxLayout()
        
        # Interval input
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Upload Interval:"))
        
        self.interval_options = QComboBox()
        self.interval_options.addItem("Every Hour", 1)
        self.interval_options.addItem("Every 2 Hours", 2)
        self.interval_options.addItem("Every 3 Hours", 3)
        self.interval_options.addItem("Every 4 Hours", 4)
        self.interval_options.addItem("Every 6 Hours", 6)
        self.interval_options.addItem("Every 12 Hours", 12)
        self.interval_options.addItem("Once a Day", 24)
        self.interval_options.addItem("Randomized Hourly", "random")
        interval_layout.addWidget(self.interval_options)
        
        self.interval_options.currentIndexChanged.connect(self._interval_option_changed)
        
        self.interval_info_label = QLabel("Videos will be uploaded exactly one hour apart")
        self.interval_info_label.setStyleSheet("color: gray; font-style: italic;")
        
        import_group_layout.addLayout(interval_layout)
        import_group_layout.addWidget(self.interval_info_label)
        
        # Privacy setting
        privacy_layout = QHBoxLayout()
        privacy_layout.addWidget(QLabel("Privacy Status:"))
        
        self.privacy_toggle = QComboBox()
        self.privacy_toggle.addItem("Unlisted", "unlisted")
        self.privacy_toggle.addItem("Public", "public")
        privacy_layout.addWidget(self.privacy_toggle)
        
        import_group_layout.addLayout(privacy_layout)
        
        # Start time
        schedule_layout.addWidget(QLabel("Starting at:"))
        self.start_time_edit = QDateTimeEdit(QDateTime.currentDateTime().addSecs(300))
        self.start_time_edit.setCalendarPopup(True)
        self.start_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        schedule_layout.addWidget(self.start_time_edit)
        
        import_group_layout.addLayout(schedule_layout)
        
        # Import button
        self.import_button = QPushButton("Import and Schedule")
        self.import_button.clicked.connect(self.import_and_schedule)
        import_group_layout.addWidget(self.import_button)
        
        main_layout.addLayout(import_group_layout)
        
        # Scheduled videos table
        main_layout.addWidget(QLabel("Scheduled Videos:"))
        
        self.schedule_table = QTableWidget(0, 6)
        self.schedule_table.setHorizontalHeaderLabels([
            "Title", "Account", "Scheduled Time", "Status", "Video ID", "Actions"
        ])
        self.schedule_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.schedule_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.schedule_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.schedule_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.schedule_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.schedule_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        main_layout.addWidget(self.schedule_table)
        
        # Buttons row
        buttons_layout = QHBoxLayout()
        
        # Refresh button
        self.refresh_button = QPushButton("Refresh Schedule")
        self.refresh_button.clicked.connect(self.refresh_schedule)
        buttons_layout.addWidget(self.refresh_button)
        
        # Auto apply AI titles button
        self.auto_titles_button = QPushButton("Auto Apply AI Title and Description")
        self.auto_titles_button.clicked.connect(self.auto_apply_ai_metadata)
        buttons_layout.addWidget(self.auto_titles_button)
        
        # Clear All button
        self.clear_all_button = QPushButton("Clear All Pending")
        self.clear_all_button.clicked.connect(self.clear_all_scheduled)
        self.clear_all_button.setStyleSheet("background-color: #ffdddd;")
        buttons_layout.addWidget(self.clear_all_button)
        
        main_layout.addLayout(buttons_layout)
        
        # Initial load
        self.refresh_schedule()
    
    def update_account_list(self):
        """Update the account dropdown with available accounts"""
        self.account_combo.clear()
        
        accounts = self.account_manager.get_accounts()
        for account in accounts:
            if account.get('authenticated', False):
                self.account_combo.addItem(account['name'], account['id'])
    
    def browse_folder(self):
        """Open a file dialog to select a folder with videos"""
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Video Folder", "", QFileDialog.Option.ShowDirsOnly
        )
        
        if folder_path:
            self.folder_path_label.setText(folder_path)
    
    def _interval_option_changed(self):
        """Update the info label based on the selected interval option"""
        interval = self.interval_options.currentData()
        
        if interval == "random":
            self.interval_info_label.setText("Videos will be uploaded with randomized intervals (60-70 minutes apart)")
        else:
            if interval == 1:
                self.interval_info_label.setText("Videos will be uploaded exactly one hour apart")
            else:
                self.interval_info_label.setText(f"Videos will be uploaded exactly {interval} hours apart")
    
    def import_and_schedule(self):
        """Import videos from the selected folder and schedule them"""
        folder_path = self.folder_path_label.text()
        
        if folder_path == "No folder selected":
            QMessageBox.warning(self, "No Folder Selected", "Please select a folder containing videos.")
            return
        
        # Get account ID
        if self.account_combo.count() == 0:
            QMessageBox.warning(self, "No Accounts", "Please add and authenticate a YouTube account first.")
            return
        
        account_id = self.account_combo.currentData()
        
        # Get interval
        interval_data = self.interval_options.currentData()
        
        # Handle randomized option
        is_randomized = False
        interval_hours = 1
        
        if interval_data == "random":
            is_randomized = True
            interval_hours = 1  # Base value, will be randomized in scheduler
        else:
            interval_hours = interval_data
        
        # Get privacy status
        privacy_status = self.privacy_toggle.currentData()
        
        # Get start time
        start_time = self.start_time_edit.dateTime().toPyDateTime()
        
        # Import and schedule
        try:
            count = self.scheduler.import_folder(
                folder_path=folder_path,
                account_id=account_id,
                interval_hours=interval_hours,
                start_time=start_time,
                randomized_hourly=is_randomized,
                privacy_status=privacy_status
            )
            
            if count > 0:
                QMessageBox.information(
                    self,
                    "Videos Scheduled",
                    f"{count} videos have been scheduled for upload starting at {start_time.strftime('%Y-%m-%d %H:%M')}."
                )
                self.refresh_schedule()
            else:
                QMessageBox.warning(
                    self,
                    "No Videos",
                    f"No suitable video files were found in the selected folder."
                )
        except Exception as e:
            logger.error(f"Error scheduling videos: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while scheduling videos: {str(e)}"
            )
    
    def auto_apply_ai_metadata(self):
        """Apply AI-generated title and description to all pending scheduled videos"""
        if not self.video_processor:
            QMessageBox.warning(
                self, 
                "Feature Unavailable", 
                "The video processor is not available. Cannot generate AI metadata."
            )
            return
            
        # Check if OpenAI API key is available
        if not self.video_processor.openai_api_key:
            QMessageBox.warning(
                self,
                "API Key Missing",
                "OpenAI API key is not set. Please configure it in the Settings panel."
            )
            return
            
        # Get all scheduled videos
        videos = self.scheduler.get_scheduled_videos()
        if not videos:
            QMessageBox.information(
                self,
                "No Videos",
                "There are no scheduled videos to process."
            )
            return
            
        # Count only pending videos
        pending_videos = [v for v in videos if not v.get('uploaded', False) and not v.get('cancelled', False)]
        if not pending_videos:
            QMessageBox.information(
                self,
                "No Pending Videos",
                "There are no pending videos to process."
            )
            return
            
        # Confirm with user
        result = QMessageBox.question(
            self,
            "Confirm AI Metadata Generation",
            f"Generate AI titles and descriptions for {len(pending_videos)} scheduled videos?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
            
        # Process each video
        processed_count = 0
        error_count = 0
        
        # Get style prompt from config
        from ..utils.config_manager import ConfigManager
        config_manager = ConfigManager()
        style_prompt = config_manager.get("style_prompt", "")
        
        for video in pending_videos:
            video_path = video.get('file_path')
            if not os.path.exists(video_path):
                logger.warning(f"Video file not found: {video_path}")
                error_count += 1
                continue
                
            try:
                # Generate metadata using process_video which includes object detection
                video_data = self.video_processor.process_video(
                    video_path,
                    sample_interval=5,
                    max_title_length=100,
                    style_prompt=style_prompt
                )
                
                if video_data and 'title' in video_data:
                    # Update the scheduled video with the new metadata
                    title = video_data.get('title')
                    description = video_data.get('description', '')
                    tags = video_data.get('hashtags', [])
                    
                    logger.info(f"Generated metadata for {video_path}: {title}")
                    
                    if self.scheduler.update_video_metadata(
                        video_id=video.get('id'),
                        title=title,
                        description=description,
                        tags=tags
                    ):
                        processed_count += 1
                    else:
                        logger.error(f"Failed to update metadata for video ID: {video.get('id')}")
                        error_count += 1
                else:
                    logger.error(f"Failed to generate metadata for {video_path}")
                    error_count += 1
                    
            except Exception as e:
                logger.error(f"Error generating metadata for {video_path}: {str(e)}")
                error_count += 1
                
        # Show result
        if processed_count > 0:
            QMessageBox.information(
                self,
                "AI Metadata Applied",
                f"Successfully applied AI-generated metadata to {processed_count} videos."
                + (f" Failed to process {error_count} videos." if error_count > 0 else "")
            )
        else:
            QMessageBox.warning(
                self,
                "AI Metadata Generation Failed",
                f"Failed to apply AI-generated metadata to any videos. Please check that your OpenAI API key is configured correctly."
            )
            
        # Refresh the schedule display
        self.refresh_schedule()
    
    def refresh_schedule(self):
        """Refresh the schedule display"""
        self.schedule_table.setRowCount(0)
        
        # Get scheduled videos
        videos = self.scheduler.get_scheduled_videos()
        
        if not videos:
            return
        
        # Sort by scheduled time
        videos.sort(key=lambda v: v.get('scheduled_time', ''))
        
        # Fill the table
        for i, video in enumerate(videos):
            self.schedule_table.insertRow(i)
            
            # Get video details
            title = video.get('title', 'Unknown')
            account_id = video.get('account_id', '')
            account_name = "Unknown"
            for acc in self.account_manager.get_accounts():
                if acc.get('id') == account_id:
                    account_name = acc.get('name', 'Unknown')
                    break
            
            scheduled_time = datetime.datetime.fromisoformat(video.get('scheduled_time', ''))
            is_randomized = video.get('randomized', False)
            
            # Status
            status = "Pending"
            if video.get('uploaded', False):
                status = "Uploaded"
            elif video.get('cancelled', False):
                status = "Cancelled"
            elif 'error' in video:
                status = f"Error: {video['error']}"
            
            video_id = video.get('video_id', '')
            
            # Set title
            title_item = QTableWidgetItem(title)
            title_item.setData(Qt.ItemDataRole.UserRole, video.get('id'))
            self.schedule_table.setItem(i, 0, title_item)
            
            # Set account
            self.schedule_table.setItem(i, 1, QTableWidgetItem(account_name))
            
            # Set scheduled time
            time_text = scheduled_time.strftime("%Y-%m-%d %H:%M")
            if is_randomized and i < len(videos) - 1:
                time_text += " (Randomized)"
            self.schedule_table.setItem(i, 2, QTableWidgetItem(time_text))
            
            # Set status
            status_item = QTableWidgetItem(status)
            if status == "Uploaded":
                status_item.setForeground(QBrush(QColor("green")))
            elif status == "Cancelled":
                status_item.setForeground(QBrush(QColor("gray")))
            elif status.startswith("Error"):
                status_item.setForeground(QBrush(QColor("red")))
            self.schedule_table.setItem(i, 3, status_item)
            
            # Set video ID
            self.schedule_table.setItem(i, 4, QTableWidgetItem(video_id))
            
            # Add cancel button for pending uploads
            if status == "Pending":
                cancel_button = QPushButton("Cancel")
                cancel_button.clicked.connect(lambda checked, vid=video.get('id'): self._cancel_upload(vid))
                self.schedule_table.setCellWidget(i, 5, cancel_button)
        
        # Resize columns to content
        self.schedule_table.resizeColumnsToContents()
    
    def _cancel_upload(self, video_id):
        """Cancel a scheduled upload"""
        if self.scheduler.cancel_scheduled_video(video_id):
            QMessageBox.information(self, "Upload Cancelled", "The scheduled upload has been cancelled.")
            self.refresh_schedule()
        else:
            QMessageBox.warning(self, "Cancel Failed", "Failed to cancel the scheduled upload.")
    
    def clear_all_scheduled(self):
        """Clear all pending scheduled uploads"""
        result = QMessageBox.question(
            self,
            "Confirm Clear All",
            "Are you sure you want to clear all pending scheduled uploads?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            self.scheduler.clear_all_scheduled_videos()
            QMessageBox.information(self, "All Videos Cancelled", "All pending scheduled uploads have been cancelled.")
            self.refresh_schedule()
    
    def showEvent(self, event):
        """Called when the panel is shown"""
        super().showEvent(event)
        self.update_account_list()
        self.refresh_schedule() 