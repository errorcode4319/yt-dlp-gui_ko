"""
Main GUI application class for YTD YouTube downloader.
"""

import os
import sys
import threading
from typing import Dict, List, Any, Optional

from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMessageBox
from PyQt6.QtCore import pyqtSignal, QTimer

from .updater import Updater
from .login_manager import LoginManager
from .ui_manager import UIManager
from .download_manager import DownloadManager


class YTDGUI(QMainWindow):
    """
    Main GUI application class for YTD YouTube downloader.

    This class implements the complete user interface and handles all user interactions,
    download management, and application state.
    """

    # Custom signals for thread-safe GUI updates
    updateStatusSignal = pyqtSignal(str)
    logMessageSignal = pyqtSignal(str)

    def __init__(self, base_dir: str):
        """
        Initialize the main application window and all components.

        Args:
            base_dir: The base directory of the application.
        """
        super().__init__()

        # Window configuration
        self.setWindowTitle("YTD")
        self.resize(400, 300)
        self.base_dir = base_dir

        # Initialize manager components
        self.updater = Updater(self.base_dir, parent=self)
        self.login_manager = LoginManager(self)
        self.ui_manager = UIManager(self)
        self.download_manager = DownloadManager(self)

        # Set application icon
        self.ui_manager._set_window_icon()

        # Initialize application state
        self._initialize_state()

        # Load UI icons
        self.ui_manager._load_icons()

        # Build user interface
        self.ui_manager._create_ui()

        # Connect signals for thread-safe updates
        self._connect_signals()

        # Initial status
        self.update_status("Ready")

        # Check for updates on startup (delayed to allow UI to render)
        QTimer.singleShot(100, self.check_for_updates)

    def _initialize_state(self) -> None:
        """Initialize application state variables."""
        # Download management
        self.download_queue: List[Dict[str, Any]] = []
        self.downloading = False

        # Audio settings
        self.audio_quality_default = "320"

        # Authentication settings
        self.use_cookies = False
        self.cookie_browser = "chrome"
        self.cookie_file: Optional[str] = None

    def _connect_signals(self) -> None:
        """Connect Qt signals for thread-safe GUI updates."""
        self.updateStatusSignal.connect(self._update_status)
        self.logMessageSignal.connect(self._log_message)

    def check_for_updates(self) -> None:
        """
        Prompt user to check for yt-dlp updates on application startup.

        This runs automatically when the application starts and gives the user
        the option to update yt-dlp to the latest version.
        """
        reply = QMessageBox.question(
            self, "Check for Updates",
            "Do you want to check for a new version of yt-dlp?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Switch to activity page to show update progress
            self.ui_manager.switch_page("Activity")
            # Run update in background thread
            threading.Thread(target=self.run_updates, daemon=True).start()

    def run_updates(self) -> None:
        """
        Execute yt-dlp update process in background thread.

        This method runs in a separate thread to avoid blocking the UI
        during the update process.
        """

        def progress_callback(msg: str) -> None:
            """Callback function to report update progress."""
            self.log_message(msg)

        self.log_message("Starting yt-dlp update...")

        try:
            self.updater.download_yt(progress_callback)
            self.log_message("yt-dlp update completed successfully.")
        except Exception as e:
            error_msg = f"Update error: {e}"
            self.log_message(error_msg)

            # Show error dialog in main thread
            QTimer.singleShot(0, lambda: QMessageBox.critical(
                self, "Updater", f"Error during yt-dlp update: {e}"
            ))

    def select_save_path(self) -> None:
        """Open folder selection dialog for download location."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Download Folder"
        )

        if directory:
            self.path_entry.setText(directory)
            self.update_status("Save path selected")

    def update_status(self, message: str) -> None:
        """
        Update status bar message (thread-safe).

        Args:
            message: Status message to display
        """
        self.updateStatusSignal.emit(message)

    def _update_status(self, message: str) -> None:
        """Internal method to update status bar in main thread."""
        self.status_bar.showMessage(message)

    def log_message(self, msg: str) -> None:
        """
        Log message to activity panel and console (thread-safe).

        Args:
            msg: Message to log
        """
        self.logMessageSignal.emit(msg)
        print(f"[YTD] {msg}")  # Also log to console

    def _log_message(self, msg: str) -> None:
        """Internal method to add message to log widget in main thread."""
        if hasattr(self, "log_text"):
            # Add timestamp for better logging
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_msg = f"[{timestamp}] {msg}"
            self.log_text.append(formatted_msg)
