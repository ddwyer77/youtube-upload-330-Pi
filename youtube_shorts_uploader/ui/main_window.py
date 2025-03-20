import sys
import os
import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QTabWidget, QMessageBox,
    QFileDialog, QSplitter, QApplication, QToolBar,
    QStatusBar, QStyle, QMenu, QToolButton, QFrame,
    QDockWidget, QStackedWidget
)
from PyQt6.QtCore import Qt, QSize, QUrl, QTimer, QSettings
from PyQt6.QtGui import QIcon, QAction, QDesktopServices, QPixmap, QColor, QPalette

from ..utils.config_manager import ConfigManager
from .upload_panel import UploadPanel
from .settings_panel import SettingsPanel
from .accounts_panel import AccountsPanel
from .schedule_panel import SchedulePanel
from .video_preview import VideoPreview

from ..core.auth_manager import AuthManager
from ..core.youtube_api import YouTubeAPI
from ..core.video_processor import VideoProcessor
from ..utils.keychain_helper import KeychainHelper
from ..core.account_manager import AccountManager
from ..core.scheduler import UploadScheduler

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self, config_manager=None):
        """Initialize the main window."""
        super().__init__()
        
        # Set window properties
        self.setWindowTitle("YouTube Shorts Uploader")
        self.setMinimumSize(1000, 700)
        
        # Initialize managers and helpers
        self._init_managers(config_manager)
        
        # Set up UI components
        self._setup_ui()
        
        # Create menus and toolbars
        self._create_menu()
        
        # Apply theme
        self._apply_theme()
        
        # Restore window geometry
        self._restore_geometry()
        
        # Set status message
        self.statusBar().showMessage("Ready")
        
        logger.info("Main window initialized")
    
    def _init_managers(self, config_manager=None):
        """Initialize core managers and helpers."""
        # Config manager for application settings
        self.config_manager = config_manager or ConfigManager()
        
        # Keychain helper for secure storage
        self.keychain = KeychainHelper()
        
        # Account manager for multiple YouTube accounts
        self.account_manager = AccountManager()
        
        # Get the current account from the account manager
        current_account = self.account_manager.current_account
        
        # Auth manager for authentication
        if current_account:
            self.auth_manager = AuthManager(current_account.get('id'))
        else:
            self.auth_manager = AuthManager()
        
        # Get the OpenAI API key from keychain
        openai_api_key = KeychainHelper.get_openai_api_key()
        
        # Video processor for video analysis and metadata
        self.video_processor = VideoProcessor(openai_api_key=openai_api_key)
        # Verify key was properly set
        if not self.video_processor.openai_api_key and openai_api_key:
            # Try setting it manually if the constructor didn't work
            self.video_processor.set_openai_api_key(openai_api_key)
            logger.info("Set OpenAI API key manually on video processor")
        
        # Upload scheduler for managing scheduled uploads
        self.scheduler = UploadScheduler(self.account_manager)
    
    def _setup_ui(self):
        """Set up the main UI components."""
        # Central widget and main layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)  # Modern UI has less margins
        
        # Create main splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Create a sidebar with options
        self.sidebar = QWidget()
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(10, 20, 10, 10)
        
        # Style for selected button
        self.selected_style = "QPushButton { background-color: #3498db; color: white; border-radius: 5px; padding: 10px; text-align: left; }"
        self.normal_style = "QPushButton { background-color: transparent; color: #555; border-radius: 5px; padding: 10px; text-align: left; }"
        
        # Sidebar buttons
        self.upload_btn = QPushButton("  Upload")
        self.upload_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp))
        self.upload_btn.setStyleSheet(self.selected_style)
        self.upload_btn.setMinimumHeight(40)
        self.upload_btn.clicked.connect(lambda: self._change_page(0))
        
        self.schedule_btn = QPushButton("  Schedule")
        self.schedule_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView))
        self.schedule_btn.setStyleSheet(self.normal_style)
        self.schedule_btn.setMinimumHeight(40)
        self.schedule_btn.clicked.connect(lambda: self._change_page(1))
        
        self.accounts_btn = QPushButton("  Accounts")
        self.accounts_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DriveHDIcon))
        self.accounts_btn.setStyleSheet(self.normal_style)
        self.accounts_btn.setMinimumHeight(40)
        self.accounts_btn.clicked.connect(lambda: self._change_page(2))
        
        self.settings_btn = QPushButton("  Settings")
        self.settings_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.settings_btn.setStyleSheet(self.normal_style)
        self.settings_btn.setMinimumHeight(40)
        self.settings_btn.clicked.connect(lambda: self._change_page(3))
        
        # Add buttons to sidebar
        sidebar_layout.addWidget(self.upload_btn)
        sidebar_layout.addWidget(self.schedule_btn)
        sidebar_layout.addWidget(self.accounts_btn)
        sidebar_layout.addWidget(self.settings_btn)
        sidebar_layout.addStretch()
        
        # Current account indicator
        self.account_indicator = QLabel("Current Account: None")
        self.account_indicator.setStyleSheet("color: #888; font-size: 11px; padding: 5px;")
        self.account_indicator.setWordWrap(True)
        self.account_indicator.setAlignment(Qt.AlignmentFlag.AlignLeft)
        sidebar_layout.addWidget(self.account_indicator)
        
        # App info at bottom of sidebar
        app_info = QLabel("YouTube Shorts Uploader v1.0")
        app_info.setStyleSheet("color: #888; font-size: 10px;")
        app_info.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(app_info)
        
        # Add sidebar to splitter
        self.main_splitter.addWidget(self.sidebar)
        
        # Create stacked widget for content
        self.content_stack = QStackedWidget()
        
        # Create content pages
        self.upload_panel = UploadPanel(
            self.auth_manager,
            self.video_processor,
            self.config_manager
        )
        
        self.schedule_panel = SchedulePanel(
            account_manager=self.account_manager,
            scheduler=self.scheduler,
            video_processor=self.video_processor
        )
        
        self.accounts_panel = AccountsPanel(
            self.account_manager
        )
        
        self.settings_panel = SettingsPanel(
            self.config_manager, 
            self.keychain
        )
        
        # Add pages to stack
        self.content_stack.addWidget(self.upload_panel)
        self.content_stack.addWidget(self.schedule_panel)
        self.content_stack.addWidget(self.accounts_panel)
        self.content_stack.addWidget(self.settings_panel)
        
        # Add content stack to splitter
        self.main_splitter.addWidget(self.content_stack)
        
        # Set splitter sizes - 1:4 ratio
        self.main_splitter.setSizes([200, 800])
        
        # Add splitter to main layout
        main_layout.addWidget(self.main_splitter)
        
        # Connect signals
        self.settings_panel.config_updated.connect(self._on_config_updated)
        self.accounts_panel.accounts_changed.connect(self._on_accounts_changed)
        self.accounts_panel.account_selected.connect(self._on_account_selected)
        
        # Update account indicator
        self._update_account_indicator()
    
    def _change_page(self, index):
        """Change the current page in the stack."""
        self.content_stack.setCurrentIndex(index)
        
        # Update button styles
        self.upload_btn.setStyleSheet(self.selected_style if index == 0 else self.normal_style)
        self.schedule_btn.setStyleSheet(self.selected_style if index == 1 else self.normal_style)
        self.accounts_btn.setStyleSheet(self.selected_style if index == 2 else self.normal_style)
        self.settings_btn.setStyleSheet(self.selected_style if index == 3 else self.normal_style)
    
    def _create_menu(self):
        """Create the application menu."""
        # File menu
        file_menu = self.menuBar().addMenu("&File")
        
        # File > Open Video
        open_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton), "&Open Video...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_video)
        file_menu.addAction(open_action)
        
        # File > Open Folder
        open_folder_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon), "Open &Folder...", self)
        open_folder_action.setShortcut("Ctrl+F")
        open_folder_action.triggered.connect(self._on_open_folder)
        file_menu.addAction(open_folder_action)
        
        file_menu.addSeparator()
        
        # File > Exit
        exit_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton), "E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Account menu
        account_menu = self.menuBar().addMenu("&Account")
        
        # Account > Add Account
        add_account_action = QAction("&Add Account...", self)
        add_account_action.triggered.connect(self._on_add_account)
        account_menu.addAction(add_account_action)
        
        # Account submenu (will be populated dynamically)
        self.accounts_submenu = QMenu("Switch &To", self)
        account_menu.addMenu(self.accounts_submenu)
        
        account_menu.addSeparator()
        
        # Account > Manage Accounts
        manage_accounts_action = QAction("&Manage Accounts", self)
        manage_accounts_action.triggered.connect(lambda: self._change_page(2))
        account_menu.addAction(manage_accounts_action)
        
        # View menu
        view_menu = self.menuBar().addMenu("&View")
        
        # View > Upload Panel
        upload_view_action = QAction("&Upload Panel", self)
        upload_view_action.triggered.connect(lambda: self._change_page(0))
        view_menu.addAction(upload_view_action)
        
        # View > Schedule Panel
        schedule_view_action = QAction("&Schedule Panel", self)
        schedule_view_action.triggered.connect(lambda: self._change_page(1))
        view_menu.addAction(schedule_view_action)
        
        # View > Accounts Panel
        accounts_view_action = QAction("&Accounts Panel", self)
        accounts_view_action.triggered.connect(lambda: self._change_page(2))
        view_menu.addAction(accounts_view_action)
        
        # View > Settings Panel
        settings_view_action = QAction("S&ettings Panel", self)
        settings_view_action.triggered.connect(lambda: self._change_page(3))
        view_menu.addAction(settings_view_action)
        
        view_menu.addSeparator()
        
        # View > Theme submenu
        theme_menu = QMenu("&Theme", self)
        
        system_theme_action = QAction("&System", self)
        system_theme_action.triggered.connect(lambda: self._set_theme("system"))
        theme_menu.addAction(system_theme_action)
        
        light_theme_action = QAction("&Light", self)
        light_theme_action.triggered.connect(lambda: self._set_theme("light"))
        theme_menu.addAction(light_theme_action)
        
        dark_theme_action = QAction("&Dark", self)
        dark_theme_action.triggered.connect(lambda: self._set_theme("dark"))
        theme_menu.addAction(dark_theme_action)
        
        view_menu.addMenu(theme_menu)
        
        # Schedule menu
        schedule_menu = self.menuBar().addMenu("Sche&dule")
        
        # Schedule > Import Folder
        import_folder_action = QAction("&Import Folder...", self)
        import_folder_action.triggered.connect(self._on_import_folder_for_schedule)
        schedule_menu.addAction(import_folder_action)
        
        # Schedule > View Schedule
        view_schedule_action = QAction("&View Schedule", self)
        view_schedule_action.triggered.connect(lambda: self._change_page(1))
        schedule_menu.addAction(view_schedule_action)
        
        # Help menu
        help_menu = self.menuBar().addMenu("&Help")
        
        # Help > About
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)
        
        # Populate the accounts submenu
        self._update_accounts_menu()
    
    def _on_import_folder_for_schedule(self):
        """Open the schedule panel and prompt for folder import"""
        self._change_page(1)  # Switch to schedule panel
        self.schedule_panel.browse_folder()  # Open folder browser
    
    def _on_open_video(self):
        """Handle opening a video file."""
        # Get videos directory from config
        videos_dir = self.config_manager.get("upload_folder", str(Path.home()))
        
        # Open file dialog
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Open Video Files",
            videos_dir,
            "Video Files (*.mp4 *.mov *.avi *.mkv *.flv);;All Files (*)"
        )
        
        if file_paths:
            # Add the videos to the upload queue
            for file_path in file_paths:
                self.upload_panel.add_video_to_queue(file_path)
            
            plural = "s" if len(file_paths) > 1 else ""
            self.statusBar().showMessage(f"Added {len(file_paths)} video{plural} to upload queue")
            
            # Switch to upload panel
            self._change_page(0)
    
    def _on_open_folder(self):
        """Handle opening a folder of videos."""
        # Get videos directory from config
        videos_dir = self.config_manager.get("upload_folder", str(Path.home()))
        
        # Open folder dialog
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder with Videos",
            videos_dir,
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder_path:
            # Get all video files in the folder
            video_extensions = [".mp4", ".mov", ".avi", ".mkv", ".flv"]
            video_files = []
            
            for root, _, files in os.walk(folder_path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in video_extensions):
                        video_files.append(os.path.join(root, file))
            
            # Add the videos to the upload queue
            if video_files:
                for file_path in video_files:
                    self.upload_panel.add_video_to_queue(file_path)
                
                plural = "s" if len(video_files) > 1 else ""
                self.statusBar().showMessage(f"Added {len(video_files)} video{plural} from folder")
                
                # Update config with this folder
                self.config_manager.set("upload_folder", folder_path)
                self.config_manager.save()
                
                # Switch to upload panel
                self._change_page(0)
            else:
                QMessageBox.information(
                    self,
                    "No Videos Found",
                    f"No video files were found in the selected folder:\n{folder_path}"
                )
    
    def _show_about_dialog(self):
        """Show the about dialog."""
        QMessageBox.about(
            self,
            "About YouTube Shorts Uploader",
            """<h2>YouTube Shorts Uploader</h2>
            <p style="font-size: 14px;">Version 1.0.0</p>
            <p>A desktop application for uploading shorts to YouTube with AI-generated metadata.</p>
            <p>Created for: Clipmode Go</p>
            <p>&copy; 2023-2025</p>
            <p><a href="https://youtube.com/@ClipModeGo">Visit Channel</a></p>"""
        )
    
    def _set_theme(self, theme):
        """Set the application theme."""
        # Update config
        self.config_manager.set("theme", theme)
        self.config_manager.save()
        
        # Apply the theme
        self._apply_theme()
        
        # Update status
        self.statusBar().showMessage(f"Theme changed to {theme}", 3000)
    
    def _apply_theme(self):
        """Apply the application theme from config."""
        theme = self.config_manager.get("theme", "system")
        
        if theme == "dark":
            # Apply dark theme styling
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #2c3e50; color: #ecf0f1; }
                QToolBar { background-color: #34495e; border: none; }
                QMenuBar { background-color: #34495e; color: #ecf0f1; }
                QMenuBar::item:selected { background-color: #3498db; }
                QMenu { background-color: #34495e; color: #ecf0f1; }
                QMenu::item:selected { background-color: #3498db; }
                QTabWidget::pane { border: 1px solid #3498db; }
                QTabBar::tab { background-color: #34495e; color: #ecf0f1; padding: 8px 16px; }
                QTabBar::tab:selected { background-color: #3498db; }
                QPushButton { background-color: #3498db; color: white; border: none; padding: 8px 16px; border-radius: 4px; }
                QPushButton:hover { background-color: #2980b9; }
                QLineEdit, QTextEdit { background-color: #34495e; color: #ecf0f1; border: 1px solid #7f8c8d; padding: 4px; }
                QListWidget { background-color: #34495e; color: #ecf0f1; border: 1px solid #7f8c8d; }
                QProgressBar { background-color: #34495e; color: #ecf0f1; border: 1px solid #7f8c8d; border-radius: 2px; }
                QProgressBar::chunk { background-color: #3498db; }
                QSplitter::handle { background-color: #7f8c8d; }
            """)
        elif theme == "light":
            # Apply light theme styling
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #f5f5f5; color: #333; }
                QToolBar { background-color: #e0e0e0; border: none; }
                QMenuBar { background-color: #e0e0e0; color: #333; }
                QMenuBar::item:selected { background-color: #3498db; color: white; }
                QMenu { background-color: #f5f5f5; color: #333; }
                QMenu::item:selected { background-color: #3498db; color: white; }
                QTabWidget::pane { border: 1px solid #3498db; }
                QTabBar::tab { background-color: #e0e0e0; color: #333; padding: 8px 16px; }
                QTabBar::tab:selected { background-color: #3498db; color: white; }
                QPushButton { background-color: #3498db; color: white; border: none; padding: 8px 16px; border-radius: 4px; }
                QPushButton:hover { background-color: #2980b9; }
                QLineEdit, QTextEdit { background-color: white; color: #333; border: 1px solid #ccc; padding: 4px; }
                QListWidget { background-color: white; color: #333; border: 1px solid #ccc; }
                QProgressBar { background-color: white; color: #333; border: 1px solid #ccc; border-radius: 2px; }
                QProgressBar::chunk { background-color: #3498db; }
                QSplitter::handle { background-color: #ccc; }
            """)
        else:
            # System theme - reset style sheet
            self.setStyleSheet("")
        
        logger.info(f"Applied theme: {theme}")
    
    def _restore_geometry(self):
        """Restore window geometry from settings."""
        settings = QSettings("YouTubeBuddy", "YouTube Shorts Uploader")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
    
    def _save_geometry(self):
        """Save window geometry to settings."""
        settings = QSettings("YouTubeBuddy", "YouTube Shorts Uploader")
        settings.setValue("geometry", self.saveGeometry())
    
    def _on_config_updated(self, config):
        """
        Handle configuration updates.
        
        Args:
            config (dict): Updated configuration values.
        """
        logger.debug(f"Config updated: {config}")
        
        # If OpenAI API key was updated, refresh the VideoProcessor
        if 'openai_api_key' in config:
            logger.info("OpenAI API key was updated, reinitializing video processor")
            # Reinitialize the video processor in the upload panel
            self.upload_panel._init_video_processor()
            # Update UI elements that depend on API key
            self.upload_panel._update_upload_button_state()
        
        # Update any components that need to reflect the new config
        self.statusBar().showMessage("Settings updated", 3000)  # Show for 3 seconds
    
    def _on_accounts_changed(self):
        """Handle account changes."""
        # Update auth status
        self._update_auth_status()
        
        # Update account indicator
        self._update_account_indicator()
        
        # Update account menus
        self._update_accounts_menu()
    
    def _on_account_selected(self, account):
        """Handle account selection."""
        # Just update the status bar with the selected account
        self.statusBar().showMessage(f"Selected account: {account.get('name', 'Unknown')}", 3000)
    
    def _update_account_indicator(self):
        """Update the account indicator in the sidebar."""
        current_account = self.account_manager.current_account
        
        if current_account:
            name = current_account.get('name', 'Unknown')
            self.account_indicator.setText(f"Current Account:\n{name}")
            
            # Add channel name if available
            channel_title = current_account.get('channel_title')
            if channel_title:
                self.account_indicator.setText(f"Current Account:\n{name}\nChannel: {channel_title}")
        else:
            self.account_indicator.setText("Current Account: None")
    
    def _update_accounts_menu(self):
        """Populate the accounts submenu in the main menu."""
        self.accounts_submenu.clear()
        
        accounts = self.account_manager.get_accounts()
        current_account = self.account_manager.current_account
        
        if not accounts:
            # Add "No accounts" item
            no_accounts_action = QAction("No accounts", self)
            no_accounts_action.setEnabled(False)
            self.accounts_submenu.addAction(no_accounts_action)
            return
        
        # Add accounts
        for account in accounts:
            account_id = account.get('id')
            name = account.get('name', 'Unknown')
            channel_title = account.get('channel_title')
            
            # Format text
            if channel_title and channel_title != name:
                text = f"{name} ({channel_title})"
            else:
                text = name
                
            # Create action
            action = QAction(text, self)
            action.setData(account_id)
            
            # Set checkable and check current account
            action.setCheckable(True)
            if current_account and account_id == current_account.get('id'):
                action.setChecked(True)
            
            # Connect action
            action.triggered.connect(lambda checked, id=account_id: self._switch_account(id))
            
            self.accounts_submenu.addAction(action)
        
        self.accounts_submenu.addSeparator()
        
        # Add Manage Accounts action
        manage_action = QAction("Manage Accounts...", self)
        manage_action.triggered.connect(lambda: self._change_page(2))
        self.accounts_submenu.addAction(manage_action)
    
    def _switch_account(self, account_id):
        """Switch to the selected account."""
        success = self.account_manager.set_current_account(account_id)
        
        if success:
            # Find account name
            account_name = "Unknown"
            for account in self.account_manager.get_accounts():
                if account.get('id') == account_id:
                    account_name = account.get('name', 'Unknown')
                    break
            
            # Update auth status
            self._update_auth_status()
            
            # Update account indicator
            self._update_account_indicator()
            
            # Update account menus
            self._update_accounts_menu()
            
            # Update upload panel with new auth manager
            self.auth_manager = self.account_manager.auth_manager
            self.upload_panel.auth_manager = self.auth_manager
            
            # Update accounts panel
            self.accounts_panel._load_accounts()
            
            # Show message
            self.statusBar().showMessage(f"Switched to account: {account_name}", 3000)
    
    def _on_add_account(self):
        """Open the add account dialog."""
        # Switch to accounts panel and trigger add account
        self._change_page(2)
        self.accounts_panel._on_add_account()
    
    def check_configurations(self):
        """Check if all required configurations are present."""
        # Check for accounts
        if not self.account_manager.get_accounts():
            self.statusBar().showMessage("No YouTube accounts configured. Please add an account in Settings.")
            
            reply = QMessageBox.question(
                self,
                "No Accounts Configured",
                "No YouTube accounts are configured yet. Would you like to add one now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Switch to accounts panel
                self._change_page(2)
                # Open add account dialog
                QTimer.singleShot(500, self.accounts_panel._on_add_account)
        
        # Check for OpenAI API key if AI features are enabled
        if self.config_manager.get('use_ai_features', True) and not self.keychain.get_password('openai'):
            self.statusBar().showMessage("OpenAI API key not found. AI features will be limited.")
            logger.warning("OpenAI API key not found. AI features will be limited.")
    
    def closeEvent(self, event):
        """Handle window close event."""
        try:
            # Save window geometry
            settings = QSettings("YouTubeBuddy", "YouTube Shorts Uploader")
            settings.setValue("geometry", self.saveGeometry())
            
            # Stop the scheduler
            if hasattr(self, 'scheduler'):
                self.scheduler.stop()
                
            # Accept the close event
            event.accept()
        except Exception as e:
            logger.error(f"Error during close: {str(e)}")
            event.accept()  # Still close even if there's an error

    def _on_upload(self):
        """Handle the upload action."""
        if self.upload_panel.upload_button.isEnabled():
            self.upload_panel._on_start_upload()
        else:
            QMessageBox.warning(
                self,
                "Cannot Upload",
                "Please select a video and provide a title before uploading."
            )
