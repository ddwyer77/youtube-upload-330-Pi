import os
import logging
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QCheckBox, QComboBox, QFormLayout, QGroupBox,
    QSpinBox, QFileDialog, QMessageBox, QTabWidget, QScrollArea,
    QPlainTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon

from ..utils.config_manager import ConfigManager
from ..utils.keychain_helper import KeychainHelper

logger = logging.getLogger(__name__)

class SettingsPanel(QWidget):
    """Panel for configuring application settings."""
    
    # Signal emitted when config is updated
    config_updated = pyqtSignal(dict)
    
    def __init__(self, config_manager=None, keychain_helper=None, parent=None):
        """
        Initialize the settings panel.
        
        Args:
            config_manager (ConfigManager): Application configuration manager.
            keychain_helper (KeychainHelper): Keychain helper for secure storage.
            parent (QWidget): Parent widget.
        """
        super().__init__(parent)
        
        self.config_manager = config_manager or ConfigManager()
        self.keychain_helper = keychain_helper or KeychainHelper()
        
        # Setup UI
        self._setup_ui()
        
        # Load saved settings
        self._load_settings()
        
        logger.info("Settings panel initialized")
    
    def _setup_ui(self):
        """Set up the UI components."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create a scroll area for settings
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Create a widget for the scroll area
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # Create settings tabs
        settings_tabs = QTabWidget()
        
        # YouTube Settings tab
        youtube_tab = QWidget()
        youtube_layout = QVBoxLayout(youtube_tab)
        
        # YouTube API Settings
        api_group = QGroupBox("YouTube API Configuration")
        api_layout = QFormLayout()
        
        # Client Secrets path
        self.client_secrets_path = QLineEdit()
        self.client_secrets_path.setReadOnly(True)
        self.client_secrets_path.setPlaceholderText("Path to client_secrets.json file")
        
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self._on_browse_client_secrets)
        
        # Horizontal layout for path and browse button
        client_secrets_layout = QHBoxLayout()
        client_secrets_layout.addWidget(self.client_secrets_path)
        client_secrets_layout.addWidget(browse_button)
        
        api_layout.addRow("Client Secrets:", client_secrets_layout)
        
        # Authentication status
        self.auth_status_label = QLabel("Not authenticated")
        api_layout.addRow("Auth Status:", self.auth_status_label)
        
        # Authentication buttons
        auth_buttons_layout = QHBoxLayout()
        
        self.auth_button = QPushButton("Authenticate")
        self.auth_button.clicked.connect(self._on_authenticate_youtube)
        auth_buttons_layout.addWidget(self.auth_button)
        
        self.auth_revoke_button = QPushButton("Revoke Access")
        self.auth_revoke_button.clicked.connect(self._on_revoke_youtube_auth)
        auth_buttons_layout.addWidget(self.auth_revoke_button)
        
        api_layout.addRow("", auth_buttons_layout)
        
        api_group.setLayout(api_layout)
        youtube_layout.addWidget(api_group)
        
        # Default Settings
        defaults_group = QGroupBox("Upload Defaults")
        defaults_layout = QFormLayout()
        
        # Default privacy
        self.privacy_combo = QComboBox()
        self.privacy_combo.addItems(["Public", "Unlisted", "Private"])
        defaults_layout.addRow("Default Privacy:", self.privacy_combo)
        
        # Default category
        self.category_combo = QComboBox()
        # YouTube video categories
        categories = {
            "1": "Film & Animation",
            "2": "Autos & Vehicles",
            "10": "Music",
            "15": "Pets & Animals",
            "17": "Sports",
            "18": "Short Movies",
            "19": "Travel & Events",
            "20": "Gaming",
            "21": "Videoblogging",
            "22": "People & Blogs",
            "23": "Comedy",
            "24": "Entertainment",
            "25": "News & Politics",
            "26": "Howto & Style",
            "27": "Education",
            "28": "Science & Technology",
            "29": "Nonprofits & Activism",
            "30": "Movies",
            "31": "Anime/Animation",
            "32": "Action/Adventure",
            "33": "Classics",
            "34": "Comedy",
            "35": "Documentary",
            "36": "Drama",
            "37": "Family",
            "38": "Foreign",
            "39": "Horror",
            "40": "Sci-Fi/Fantasy",
            "41": "Thriller",
            "42": "Shorts",
            "43": "Shows",
            "44": "Trailers"
        }
        for id, name in categories.items():
            self.category_combo.addItem(name, id)
        defaults_layout.addRow("Default Category:", self.category_combo)
        
        defaults_group.setLayout(defaults_layout)
        youtube_layout.addWidget(defaults_group)
        
        # Add stretch to push everything to the top
        youtube_layout.addStretch()
        
        settings_tabs.addTab(youtube_tab, "YouTube")
        
        # AI Settings tab
        ai_tab = QWidget()
        ai_layout = QVBoxLayout(ai_tab)
        
        # OpenAI API Settings
        openai_group = QGroupBox("OpenAI API Configuration")
        openai_layout = QFormLayout()
        
        # API Key input
        self.openai_api_key = QLineEdit()
        self.openai_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_api_key.setPlaceholderText("Enter your OpenAI API key")
        openai_layout.addRow("API Key:", self.openai_api_key)
        
        # API Key buttons
        api_key_buttons = QHBoxLayout()
        
        # Save API Key button
        save_api_key_button = QPushButton("Save API Key")
        save_api_key_button.clicked.connect(self._on_save_openai_api_key)
        api_key_buttons.addWidget(save_api_key_button)
        
        # Reset API Key button
        reset_api_key_button = QPushButton("Reset API Key")
        reset_api_key_button.clicked.connect(self._on_reset_api_key)
        api_key_buttons.addWidget(reset_api_key_button)
        
        openai_layout.addRow("", api_key_buttons)
        
        openai_group.setLayout(openai_layout)
        ai_layout.addWidget(openai_group)
        
        # AI Features Settings
        features_group = QGroupBox("AI Features Configuration")
        features_layout = QFormLayout()
        
        # Enable AI Features
        self.enable_ai_features = QCheckBox("Enable AI-powered title and description generation")
        features_layout.addRow("", self.enable_ai_features)
        
        # Model selection
        self.model_combo = QComboBox()
        self.model_combo.addItems(["gpt-3.5-turbo", "gpt-4"])
        features_layout.addRow("Model:", self.model_combo)
        
        # Number of variations
        self.variations_spin = QSpinBox()
        self.variations_spin.setRange(1, 5)
        self.variations_spin.setValue(3)
        features_layout.addRow("Number of variations:", self.variations_spin)
        
        # Style prompt
        self.style_prompt = QPlainTextEdit()
        self.style_prompt.setPlaceholderText("Add custom style instructions for title/description generation (e.g., 'use a non-chalant manner' or 'include slang terms like ts, pmo, sybau')")
        self.style_prompt.setMaximumHeight(100)
        features_layout.addRow("Style Prompt:", self.style_prompt)
        
        features_group.setLayout(features_layout)
        ai_layout.addWidget(features_group)
        
        # Add stretch to push everything to the top
        ai_layout.addStretch()
        
        settings_tabs.addTab(ai_tab, "AI Settings")
        
        # Application Settings tab
        app_tab = QWidget()
        app_layout = QVBoxLayout(app_tab)
        
        # General Settings
        general_group = QGroupBox("General Settings")
        general_layout = QFormLayout()
        
        # Auto-start upload
        self.auto_upload = QCheckBox("Automatically start upload when videos are added")
        general_layout.addRow("", self.auto_upload)
        
        # Remember last directory
        self.remember_dir = QCheckBox("Remember last used directory")
        general_layout.addRow("", self.remember_dir)
        
        general_group.setLayout(general_layout)
        app_layout.addWidget(general_group)
        
        # Appearance Settings
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QFormLayout()
        
        # Theme selection
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["System", "Light", "Dark"])
        appearance_layout.addRow("Theme:", self.theme_combo)
        
        appearance_group.setLayout(appearance_layout)
        app_layout.addWidget(appearance_group)
        
        # Add stretch to push everything to the top
        app_layout.addStretch()
        
        settings_tabs.addTab(app_tab, "Application")
        
        # Add settings tabs to the scroll layout
        scroll_layout.addWidget(settings_tabs)
        
        # Add save and reset buttons
        buttons_layout = QHBoxLayout()
        
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self._on_save_settings)
        buttons_layout.addWidget(save_button)
        
        reset_button = QPushButton("Reset to Defaults")
        reset_button.clicked.connect(self._on_reset_settings)
        buttons_layout.addWidget(reset_button)
        
        scroll_layout.addLayout(buttons_layout)
        
        # Set the scroll widget
        scroll_area.setWidget(scroll_content)
        
        # Add the scroll area to the main layout
        main_layout.addWidget(scroll_area)
    
    def _load_settings(self):
        """Load saved settings from config manager."""
        try:
            # Load general settings
            self.client_secrets_path.setText(self.config_manager.get("client_secrets_path", ""))
            self.privacy_combo.setCurrentText(self.config_manager.get("privacy_status", "unlisted"))
            self.category_combo.setCurrentText(self.config_manager.get("category_id", "22"))
            
            # Load video processing settings
            self.auto_upload.setChecked(self.config_manager.get("auto_upload", False))
            self.remember_dir.setChecked(self.config_manager.get("remember_last_dir", True))
            
            # Load theme settings
            self.theme_combo.setCurrentText(self.config_manager.get("theme", "System"))
            
            # Load client secrets file path (from env or config)
            client_secrets = os.getenv("YOUTUBE_CLIENT_SECRETS", "client_secrets.json")
            self.client_secrets_path.setText(client_secrets)
            
            # Load OpenAI API key from keychain
            api_key = KeychainHelper.get_openai_api_key()
            if api_key:
                # We don't actually show the api key, just indicate that it's set
                self.openai_api_key.setText("********")
                self.openai_api_key.setPlaceholderText("API key is stored securely")
            
            # Check authentication status
            if os.path.isfile(client_secrets):
                token_path = self.config_manager.get("token_file", "token.pickle")
                if os.path.isfile(token_path):
                    self.auth_status_label.setText("Authenticated")
                    self.auth_status_label.setStyleSheet("color: green;")
                else:
                    self.auth_status_label.setText("Not authenticated")
                    self.auth_status_label.setStyleSheet("color: red;")
            else:
                self.auth_status_label.setText("Client secrets file not found")
                self.auth_status_label.setStyleSheet("color: red;")
            
            # Load AI settings
            self.enable_ai_features.setChecked(self.config_manager.get("use_ai_features", True))
            self.model_combo.setCurrentText(self.config_manager.get("openai_model", "gpt-3.5-turbo"))
            self.variations_spin.setValue(self.config_manager.get("num_variations", 3))
            self.style_prompt.setPlainText(self.config_manager.get("style_prompt", ""))
            
            logger.info("Settings loaded successfully")
        except Exception as e:
            logger.error(f"Error loading settings: {str(e)}")
    
    def _on_save_settings(self):
        """Save settings."""
        try:
            # Parse settings
            settings = {
                "client_secrets_path": self.client_secrets_path.text(),
                "privacy_status": self.privacy_combo.currentText(),
                "category_id": self.category_combo.currentData(),
                "auto_upload": self.auto_upload.isChecked(),
                "remember_last_dir": self.remember_dir.isChecked(),
                "theme": self.theme_combo.currentText(),
                "use_ai_features": self.enable_ai_features.isChecked(),
                "openai_model": self.model_combo.currentText(),
                "num_variations": self.variations_spin.value(),
                "style_prompt": self.style_prompt.toPlainText()
            }
            
            # Save settings in config manager
            self.config_manager.update(settings)
            
            # Save OpenAI API key in keychain if provided and not placeholder
            api_key = self.openai_api_key.text()
            if api_key and api_key != "********":
                KeychainHelper.set_openai_api_key(api_key)
                self.openai_api_key.setText("********")
                self.openai_api_key.setPlaceholderText("API key is stored securely")
            
            logger.info("Settings saved successfully")
            
            # Show success message
            QMessageBox.information(self, "Settings Saved", "Your settings have been saved successfully.")
            
            # Emit signal
            self.config_updated.emit(settings)
            
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")
            QMessageBox.critical(self, "Error", f"An error occurred while saving settings: {str(e)}")
    
    def _on_reset_settings(self):
        """Reset settings to default."""
        reply = QMessageBox.question(
            self, 
            "Reset Settings", 
            "Are you sure you want to reset all settings to default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Reset config
                self.config_manager.reset()
                
                # Reload settings
                self._load_settings()
                
                logger.info("Settings reset to default")
                
                # Show success message
                QMessageBox.information(self, "Settings Reset", "Your settings have been reset to default values.")
                
                # Emit signal
                self.config_updated.emit({})
                
            except Exception as e:
                logger.error(f"Error resetting settings: {str(e)}")
                QMessageBox.critical(self, "Error", f"An error occurred while resetting settings: {str(e)}")
    
    def _on_browse_client_secrets(self):
        """Browse for client secrets file."""
        current_file = self.client_secrets_path.text() or os.getcwd()
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Client Secrets File", 
            os.path.dirname(current_file),
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            self.client_secrets_path.setText(file_path)
    
    def _on_authenticate_youtube(self):
        """Authenticate with YouTube API."""
        client_secrets_path = self.client_secrets_path.text()
        
        if not client_secrets_path or not os.path.isfile(client_secrets_path):
            QMessageBox.warning(
                self,
                "Authentication Error",
                "Client secrets file not found. Please select a valid file."
            )
            return
        
        # This should be implemented to open the OAuth flow
        # For now, we'll just show a message with instructions
        QMessageBox.information(
            self,
            "Authentication",
            "Authentication will open in your web browser. Please follow the instructions to authorize the application."
        )
        
        # TODO: Implement actual authentication flow with YouTube API
        logger.info("Starting YouTube authentication flow")
        
        # For demonstration purposes only
        # In a real implementation, this would handle the OAuth flow
        self.auth_status_label.setText("Authentication initiated...")
        
        # Here we would typically:
        # 1. Initialize the OAuth flow
        # 2. Open a browser for the user to authenticate
        # 3. Handle the callback and store the token
        # 4. Update the UI accordingly
    
    def _on_revoke_youtube_auth(self):
        """Revoke YouTube API authentication."""
        reply = QMessageBox.question(
            self,
            "Confirm Revocation",
            "Are you sure you want to revoke access to your YouTube account? You will need to re-authenticate to use the app.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # TODO: Implement actual revocation of YouTube API access
            logger.info("Revoking YouTube authentication")
            
            # For demonstration purposes only
            # In a real implementation, this would revoke the OAuth token
            token_path = self.config_manager.get("token_file", "token.pickle")
            if os.path.exists(token_path):
                try:
                    os.remove(token_path)
                    self.auth_status_label.setText("Not authenticated")
                    self.auth_status_label.setStyleSheet("color: red;")
                    QMessageBox.information(self, "Revocation Complete", "YouTube access has been revoked.")
                except Exception as e:
                    logger.error(f"Error revoking authentication: {str(e)}")
                    QMessageBox.critical(self, "Revocation Error", f"Error revoking access: {str(e)}")
            else:
                QMessageBox.information(self, "Not Authenticated", "You are not currently authenticated.")
    
    def _on_save_openai_api_key(self):
        """Save the OpenAI API key to keychain."""
        api_key = self.openai_api_key.text()
        if not api_key:
            QMessageBox.warning(self, "Empty API Key", "Please enter your OpenAI API key.")
            return
        
        from ..utils.keychain_helper import KeychainHelper
        
        success = KeychainHelper.set_openai_api_key(api_key)
        if success:
            logger.info("OpenAI API key saved to keychain")
            self.openai_api_key.setText("********")
            self.openai_api_key.setPlaceholderText("API key is stored securely")
            QMessageBox.information(self, "API Key Saved", "Your OpenAI API key has been saved securely.")
            
            # Reinitialize any existing video processor instances with the new key
            # This will update the main window's video processor
            if hasattr(self.parent(), "video_processor") and self.parent().video_processor:
                self.parent().video_processor.set_openai_api_key(api_key)
                logger.info("Updated existing video processor with new API key")
                
            # Also update the upload panel's video processor if it exists
            if hasattr(self.parent(), "upload_panel") and hasattr(self.parent().upload_panel, "video_processor"):
                if self.parent().upload_panel.video_processor:
                    self.parent().upload_panel.video_processor.set_openai_api_key(api_key)
                else:
                    # Initialize it if it doesn't exist
                    self.parent().upload_panel._init_video_processor()
                logger.info("Updated upload panel's video processor with new API key")
                
            # Emit signal that config has been updated
            self.config_updated.emit({"openai_api_key": "updated"})
        else:
            logger.error("Failed to save OpenAI API key to keychain")
            QMessageBox.critical(self, "Error", "Failed to save API key securely. Please try again.")
            
    def _on_reset_api_key(self):
        """Reset the OpenAI API key in keychain."""
        reply = QMessageBox.question(
            self, 
            "Reset API Key", 
            "Are you sure you want to remove the stored API key?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            from ..utils.keychain_helper import KeychainHelper
            
            success = KeychainHelper().delete_password("openai_api_key")
            if success:
                logger.info("OpenAI API key removed from keychain")
                self.openai_api_key.clear()
                self.openai_api_key.setPlaceholderText("Enter your OpenAI API key")
                QMessageBox.information(self, "API Key Reset", "Your API key has been removed.")
            else:
                logger.error("Failed to remove OpenAI API key from keychain")
                QMessageBox.critical(self, "Error", "Failed to remove API key. Please try again.")

    @staticmethod
    def get_openai_api_key():
        """
        Get the OpenAI API key from keychain.
        
        Returns:
            str: The API key, or None if not found.
        """
        key_helper = KeychainHelper()
        try:
            return key_helper.get_password("openai_api_key")
        except Exception as e:
            logger.error(f"Error retrieving OpenAI API key: {str(e)}")
            return None
    
    @staticmethod
    def set_openai_api_key(api_key):
        """
        Store the OpenAI API key in keychain.
        
        Args:
            api_key (str): The API key to store.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        key_helper = KeychainHelper()
        try:
            return key_helper.set_password("openai_api_key", api_key)
        except Exception as e:
            logger.error(f"Error storing OpenAI API key: {str(e)}")
            return False
