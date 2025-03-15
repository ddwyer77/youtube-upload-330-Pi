import os
import logging
import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QComboBox, QSpinBox, QDateTimeEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt, QDateTime

logger = logging.getLogger(__name__)

class SchedulePanel(QWidget):
    """
    Panel for managing scheduled video uploads.
    Supports importing folders of videos and setting scheduled times.
    """
    
    def __init__(self, account_manager, scheduler):
        """
        Initialize the schedule panel.
        
        Args:
            account_manager: Account manager for handling YouTube accounts
            scheduler: Upload scheduler for managing scheduled uploads
        """
        super().__init__()
        
        self.account_manager = account_manager
        self.scheduler = scheduler
        
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
        
        # Interval options
        schedule_layout.addWidget(QLabel("Upload every:"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setMinimum(1)
        self.interval_spin.setMaximum(24)
        self.interval_spin.setValue(1)
        schedule_layout.addWidget(self.interval_spin)
        schedule_layout.addWidget(QLabel("hours"))
        
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
        
        self.videos_table = QTableWidget(0, 6)
        self.videos_table.setHorizontalHeaderLabels([
            "Title", "Account", "Scheduled Time", "Status", "Video ID", "Actions"
        ])
        self.videos_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.videos_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.videos_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.videos_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.videos_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.videos_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        main_layout.addWidget(self.videos_table)
        
        # Refresh button
        self.refresh_button = QPushButton("Refresh Schedule")
        self.refresh_button.clicked.connect(self.refresh_schedule)
        main_layout.addWidget(self.refresh_button)
        
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
        interval_hours = self.interval_spin.value()
        
        # Get start time
        start_time = self.start_time_edit.dateTime().toPython()
        
        # Schedule the videos
        count = self.scheduler.import_folder(
            folder_path, account_id, interval_hours, start_time
        )
        
        if count > 0:
            QMessageBox.information(
                self, "Videos Scheduled", 
                f"{count} videos have been scheduled for upload.\n\n"
                f"First upload will start at {start_time.strftime('%Y-%m-%d %H:%M')}, "
                f"then every {interval_hours} hour(s)."
            )
            # Refresh the schedule display
            self.refresh_schedule()
        else:
            QMessageBox.warning(
                self, "No Videos Found", 
                "No videos were found in the selected folder."
            )
    
    def refresh_schedule(self):
        """Refresh the scheduled videos table"""
        self.videos_table.setRowCount(0)
        
        videos = self.scheduler.get_scheduled_videos()
        
        for i, video in enumerate(videos):
            # Add a new row
            self.videos_table.insertRow(i)
            
            # Title
            title_item = QTableWidgetItem(video.get('title', 'Untitled'))
            self.videos_table.setItem(i, 0, title_item)
            
            # Account
            account_id = video.get('account_id', '')
            account_name = "Unknown"
            for account in self.account_manager.get_accounts():
                if account['id'] == account_id:
                    account_name = account['name']
                    break
            
            account_item = QTableWidgetItem(account_name)
            self.videos_table.setItem(i, 1, account_item)
            
            # Scheduled time
            scheduled_time = datetime.datetime.fromisoformat(video.get('scheduled_time', ''))
            time_item = QTableWidgetItem(scheduled_time.strftime('%Y-%m-%d %H:%M'))
            self.videos_table.setItem(i, 2, time_item)
            
            # Status
            status = "Pending"
            if video.get('uploaded', False):
                status = "Uploaded"
            elif video.get('cancelled', False):
                status = "Cancelled"
            elif 'error' in video:
                status = f"Error: {video['error']}"
            
            status_item = QTableWidgetItem(status)
            self.videos_table.setItem(i, 3, status_item)
            
            # Video ID
            video_id = video.get('video_id', '')
            id_item = QTableWidgetItem(video_id)
            self.videos_table.setItem(i, 4, id_item)
            
            # Actions
            if not video.get('uploaded', False) and not video.get('cancelled', False):
                cancel_button = QPushButton("Cancel")
                cancel_button.setProperty("video_id", video['id'])
                cancel_button.clicked.connect(self.cancel_upload)
                self.videos_table.setCellWidget(i, 5, cancel_button)
    
    def cancel_upload(self):
        """Cancel a scheduled upload"""
        button = self.sender()
        if button:
            video_id = button.property("video_id")
            if self.scheduler.cancel_scheduled_video(video_id):
                QMessageBox.information(self, "Upload Cancelled", "The scheduled upload has been cancelled.")
                self.refresh_schedule()
            else:
                QMessageBox.warning(self, "Cancel Failed", "Failed to cancel the scheduled upload.")
    
    def showEvent(self, event):
        """Called when the panel is shown"""
        super().showEvent(event)
        self.update_account_list()
        self.refresh_schedule() 