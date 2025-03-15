import os
import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QDialog, QFileDialog, QListWidget, QListWidgetItem, 
    QFrame, QMessageBox, QProgressBar, QToolButton, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap, QAction

from ..core.account_manager import AccountManager

logger = logging.getLogger(__name__)

class AddAccountDialog(QDialog):
    """Dialog for adding a new YouTube account."""
    
    def __init__(self, parent=None):
        """Initialize the add account dialog."""
        super().__init__(parent)
        self.setWindowTitle("Add YouTube Account")
        self.setMinimumWidth(450)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        
        # Account name
        name_layout = QHBoxLayout()
        name_label = QLabel("Account Name:")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Personal Channel")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # Client secrets file
        secrets_layout = QHBoxLayout()
        secrets_label = QLabel("Client Secrets:")
        self.secrets_input = QLineEdit()
        self.secrets_input.setPlaceholderText("Select client_secrets.json file")
        self.secrets_input.setReadOnly(True)
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._on_browse)
        secrets_layout.addWidget(secrets_label)
        secrets_layout.addWidget(self.secrets_input)
        secrets_layout.addWidget(browse_button)
        layout.addLayout(secrets_layout)
        
        # Instructions
        instructions = QLabel(
            "To add a YouTube account, you need a client secrets file from the "
            "Google API Console. This allows the application to access your YouTube channel."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #555; font-size: 11px;")
        layout.addWidget(instructions)
        
        # Get API keys link
        api_link = QLabel("<a href='https://console.developers.google.com/'>Get API Keys</a>")
        api_link.setOpenExternalLinks(True)
        api_link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(api_link)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        self.add_button = QPushButton("Add Account")
        self.add_button.clicked.connect(self.accept)
        self.add_button.setEnabled(False)  # Disabled until both fields are filled
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.add_button)
        layout.addLayout(button_layout)
        
        # Connect signals
        self.name_input.textChanged.connect(self._validate_inputs)
        self.secrets_input.textChanged.connect(self._validate_inputs)
    
    def _on_browse(self):
        """Handle browse button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Client Secrets File",
            str(Path.home()),
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            self.secrets_input.setText(file_path)
    
    def _validate_inputs(self):
        """Validate the input fields and enable/disable the add button."""
        name = self.name_input.text().strip()
        secrets_path = self.secrets_input.text().strip()
        
        self.add_button.setEnabled(bool(name) and bool(secrets_path))
    
    def get_values(self):
        """Get the values from the dialog."""
        return {
            "name": self.name_input.text().strip(),
            "client_secrets_file": self.secrets_input.text().strip()
        }


class AccountListItem(QWidget):
    """Custom widget for displaying account entries in the accounts list."""
    
    def __init__(self, account, parent=None):
        """Initialize the account list item."""
        super().__init__(parent)
        self.account = account
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Account icon
        icon_label = QLabel()
        icon_label.setFixedSize(32, 32)
        
        # Try to load a YouTube icon
        icon = QIcon.fromTheme("youtube")
        if not icon.isNull():
            pixmap = icon.pixmap(QSize(32, 32))
            icon_label.setPixmap(pixmap)
        else:
            # Use system icon as fallback
            icon = self.style().standardIcon(
                self.style().StandardPixmap.SP_DriveFDIcon)
            pixmap = icon.pixmap(QSize(32, 32))
            icon_label.setPixmap(pixmap)
        
        layout.addWidget(icon_label)
        
        # Account info (name and channel)
        info_layout = QVBoxLayout()
        
        # Account name
        name = self.account.get('name', 'Unknown Account')
        self.name_label = QLabel(f"<b>{name}</b>")
        info_layout.addWidget(self.name_label)
        
        # Channel info
        channel_title = self.account.get('channel_title')
        if channel_title:
            self.channel_label = QLabel(f"Channel: {channel_title}")
        else:
            self.channel_label = QLabel("No channel information available")
            self.channel_label.setStyleSheet("color: #888;")
        
        info_layout.addWidget(self.channel_label)
        layout.addLayout(info_layout)
        
        # Status indicator
        self.status_label = QLabel()
        if self.account.get('authenticated', False):
            self.status_label.setText("✓ Authenticated")
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText("✗ Not authenticated")
            self.status_label.setStyleSheet("color: red;")
        
        layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignRight)
        
        # Set fixed height for consistent sizing
        self.setFixedHeight(60)
        
        # Add a bottom border
        self.setStyleSheet("border-bottom: 1px solid #ddd;")


class AccountsPanel(QWidget):
    """Panel for managing YouTube accounts."""
    
    # Signals
    accounts_changed = pyqtSignal()
    account_selected = pyqtSignal(dict)
    
    def __init__(self, account_manager=None):
        """
        Initialize the accounts panel.
        
        Args:
            account_manager (AccountManager, optional): Account manager instance.
        """
        super().__init__()
        
        self.account_manager = account_manager or AccountManager()
        
        # Set up UI
        self.setup_ui()
        
        # Load accounts
        self._load_accounts()
        
        logger.info("Accounts panel initialized")
    
    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("YouTube Accounts")
        header_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(header_label)
        
        # Add account button
        self.add_button = QPushButton("Add Account")
        self.add_button.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_FileDialogNewFolder))
        self.add_button.clicked.connect(self._on_add_account)
        header_layout.addWidget(self.add_button, alignment=Qt.AlignmentFlag.AlignRight)
        
        layout.addLayout(header_layout)
        
        # Instructions
        instructions = QLabel(
            "Manage your YouTube accounts below. You can add multiple accounts and switch between them."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #555;")
        layout.addWidget(instructions)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # Accounts list
        self.accounts_list = QListWidget()
        self.accounts_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: white;
            }
            
            QListWidget::item {
                border-bottom: 1px solid #eee;
                padding: 5px;
            }
            
            QListWidget::item:selected {
                background-color: #e6f2ff;
                color: black;
            }
        """)
        self.accounts_list.setMinimumHeight(300)
        self.accounts_list.currentItemChanged.connect(self._on_account_selected)
        layout.addWidget(self.accounts_list)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        # Switch button
        self.switch_button = QPushButton("Switch To")
        self.switch_button.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ArrowRight))
        self.switch_button.clicked.connect(self._on_switch_account)
        self.switch_button.setEnabled(False)
        action_layout.addWidget(self.switch_button)
        
        # Authenticate button
        self.auth_button = QPushButton("Authenticate")
        self.auth_button.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_DialogApplyButton))
        self.auth_button.clicked.connect(self._on_authenticate_account)
        self.auth_button.setEnabled(False)
        action_layout.addWidget(self.auth_button)
        
        # Remove button
        self.remove_button = QPushButton("Remove")
        self.remove_button.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_TrashIcon))
        self.remove_button.clicked.connect(self._on_remove_account)
        self.remove_button.setEnabled(False)
        action_layout.addWidget(self.remove_button)
        
        layout.addLayout(action_layout)
        
        # Current account indicator
        current_layout = QHBoxLayout()
        current_label = QLabel("Current Account:")
        current_label.setStyleSheet("font-weight: bold;")
        current_layout.addWidget(current_label)
        
        self.current_account_label = QLabel("None")
        current_layout.addWidget(self.current_account_label)
        
        layout.addLayout(current_layout)
    
    def _load_accounts(self):
        """Load accounts from the account manager and update the UI."""
        self.accounts_list.clear()
        
        accounts = self.account_manager.get_accounts()
        current_account = self.account_manager.current_account
        
        if not accounts:
            # Add a placeholder item
            placeholder = QListWidgetItem("No accounts added yet")
            placeholder.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)  # Make it non-selectable
            self.accounts_list.addItem(placeholder)
            
            # Update current account label
            self.current_account_label.setText("None")
            return
        
        # Add accounts to the list
        for account in accounts:
            item = QListWidgetItem()
            
            # Create custom widget for the item
            widget = AccountListItem(account)
            
            # Set the size of the item to match the widget
            item.setSizeHint(widget.sizeHint())
            
            # Add the item to the list
            self.accounts_list.addItem(item)
            self.accounts_list.setItemWidget(item, widget)
            
            # Store the account ID in the item data
            item.setData(Qt.ItemDataRole.UserRole, account.get('id'))
            
            # Highlight current account
            if current_account and account.get('id') == current_account.get('id'):
                item.setSelected(True)
        
        # Update current account label
        if current_account:
            self.current_account_label.setText(current_account.get('name', 'Unknown'))
        else:
            self.current_account_label.setText("None")
    
    def _on_add_account(self):
        """Handle add account button click."""
        dialog = AddAccountDialog(self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.get_values()
            
            # Add the account
            account = self.account_manager.add_account(
                values["name"],
                values["client_secrets_file"]
            )
            
            if account:
                # Ask if the user wants to authenticate now
                reply = QMessageBox.question(
                    self,
                    "Authenticate Account",
                    f"Account '{values['name']}' has been added. Do you want to authenticate it now?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.account_manager.authenticate_account(
                        account["id"],
                        values["client_secrets_file"]
                    )
                
                # Reload accounts
                self._load_accounts()
                
                # Emit accounts changed signal
                self.accounts_changed.emit()
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Failed to add account '{values['name']}'."
                )
    
    def _on_switch_account(self):
        """Handle switch account button click."""
        selected_items = self.accounts_list.selectedItems()
        
        if not selected_items:
            return
        
        # Get the selected account ID
        account_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        # Switch to the account
        success = self.account_manager.set_current_account(account_id)
        
        if success:
            # Reload accounts
            self._load_accounts()
            
            # Emit accounts changed signal
            self.accounts_changed.emit()
            
            # Get account info
            account = self.account_manager.get_account(account_id)
            
            # Show message
            QMessageBox.information(
                self,
                "Account Switched",
                f"Switched to account: {account.get('name', 'Unknown')}"
            )
        else:
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to switch to the selected account."
            )
    
    def _on_authenticate_account(self):
        """Handle authenticate account button click."""
        selected_items = self.accounts_list.selectedItems()
        
        if not selected_items:
            return
        
        # Get the selected account ID
        account_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        # Get account info
        account = self.account_manager.get_account(account_id)
        
        if not account:
            return
        
        # Ask for client secrets file
        client_secrets_file, _ = QFileDialog.getOpenFileName(
            self,
            f"Select Client Secrets File for {account.get('name', 'Unknown')}",
            str(Path.home()),
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not client_secrets_file:
            return
        
        # Authenticate the account
        success = self.account_manager.authenticate_account(
            account_id,
            client_secrets_file
        )
        
        if success:
            # Reload accounts
            self._load_accounts()
            
            # Emit accounts changed signal
            self.accounts_changed.emit()
            
            # Show message
            QMessageBox.information(
                self,
                "Authentication Successful",
                f"Account '{account.get('name', 'Unknown')}' has been authenticated. "
                f"You can now upload videos with this account."
            )
        else:
            QMessageBox.warning(
                self,
                "Authentication Failed",
                f"Failed to authenticate account '{account.get('name', 'Unknown')}'. "
                f"Please make sure the client secrets file is valid and try again."
            )
    
    def _on_remove_account(self):
        """Handle remove account button click."""
        selected_items = self.accounts_list.selectedItems()
        
        if not selected_items:
            return
        
        # Get the selected account ID
        account_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        # Get account info
        account = self.account_manager.get_account(account_id)
        
        if not account:
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Remove Account",
            f"Are you sure you want to remove the account '{account.get('name', 'Unknown')}'?\n"
            f"This will delete all account information and require re-authentication if added again.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Remove the account
        success = self.account_manager.remove_account(account_id)
        
        if success:
            # Reload accounts
            self._load_accounts()
            
            # Emit accounts changed signal
            self.accounts_changed.emit()
            
            # Show message
            QMessageBox.information(
                self,
                "Account Removed",
                f"Account '{account.get('name', 'Unknown')}' has been removed."
            )
        else:
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to remove account '{account.get('name', 'Unknown')}'."
            )
    
    def _on_account_selected(self, current, previous):
        """Handle account selection."""
        if not current:
            self.switch_button.setEnabled(False)
            self.auth_button.setEnabled(False)
            self.remove_button.setEnabled(False)
            return
        
        # Get the selected account ID
        account_id = current.data(Qt.ItemDataRole.UserRole)
        
        # Get account info
        account = self.account_manager.get_account(account_id)
        
        if not account:
            return
        
        # Enable buttons
        is_current = (self.account_manager.current_account and 
                      account_id == self.account_manager.current_account.get('id'))
        
        self.switch_button.setEnabled(not is_current)
        self.auth_button.setEnabled(True)
        self.remove_button.setEnabled(True)
        
        # Emit account selected signal
        self.account_selected.emit(account) 