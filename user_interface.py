"""
User interface for Bengali-to-English medical transcription application.
This module implements the PyQt5-based GUI that integrates with the transcription pipeline.
"""

import os
import sys
import time
import threading
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QPushButton, QLabel, QTextEdit,
                            QSplitter, QFileDialog, QStatusBar, QAction,
                            QToolBar, QComboBox, QMessageBox, QProgressBar)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QIcon, QTextCursor, QFont

# Import the transcription pipeline
from transcription_pipeline import TranscriptionPipeline

class AudioLevelWidget(QWidget):
    """Widget for visualizing audio input levels."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(20)
        self.setMaximumHeight(20)
        self.level = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.decay)
        self.timer.start(100)  # Decay every 100ms

    def set_level(self, level):
        """Set the current audio level (0-100)."""
        self.level = min(100, max(0, level))
        self.update()

    def decay(self):
        """Gradually reduce the level for a smoother visualization."""
        if self.level > 0:
            self.level = max(0, self.level - 5)
            self.update()

    def paintEvent(self, event):
        """Draw the audio level visualization."""
        import random  # For the placeholder implementation
        from PyQt5.QtGui import QPainter, QColor, QBrush

        painter = QPainter(self)
        width = self.width()
        height = self.height()

        # Background
        painter.fillRect(0, 0, width, height, QColor(240, 240, 240))

        # For the placeholder implementation, simulate audio levels
        # In the real implementation, this would use the actual level
        if hasattr(self, 'recording') and self.recording:
            self.level = min(100, self.level + random.randint(-10, 15))

        # Level indicator
        level_width = int(width * (self.level / 100.0))
        if self.level < 30:
            color = QColor(0, 200, 0)  # Green for low levels
        elif self.level < 80:
            color = QColor(255, 165, 0)  # Orange for medium levels
        else:
            color = QColor(255, 0, 0)  # Red for high levels

        painter.fillRect(0, 0, level_width, height, color)


class TranscriptionWorker(QThread):
    """Worker thread for handling transcription without blocking the UI."""

    bengali_update = pyqtSignal(str)
    english_update = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(self, pipeline):
        super().__init__()
        self.pipeline = pipeline
        self.pipeline.on_bengali_update = self._on_bengali_update
        self.pipeline.on_english_update = self._on_english_update
        self.running = False

    def _on_bengali_update(self, text):
        """Handle Bengali text updates from the pipeline."""
        self.bengali_update.emit(text)

    def _on_english_update(self, text):
        """Handle English text updates from the pipeline."""
        self.english_update.emit(text)

    def run(self):
        """Run the transcription process."""
        self.running = True
        self.status_update.emit("Starting transcription...")
        self.pipeline.start()

        # Keep the thread running while transcription is active
        while self.running:
            time.sleep(0.1)

        # Stop transcription when the thread is stopped
        self.status_update.emit("Stopping transcription...")
        bengali, english = self.pipeline.stop()
        self.bengali_update.emit(bengali)
        self.english_update.emit(english)
        self.status_update.emit("Transcription stopped")

    def stop(self):
        """Stop the transcription process."""
        self.running = False
        self.wait()


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()

        # Set up the transcription pipeline
        self.pipeline = TranscriptionPipeline()
        self.worker = None

        # Set up the UI
        self.init_ui()

        # Session management
        self.current_session = {
            'bengali': '',
            'english': '',
            'timestamp': datetime.now(),
            'filename': None
        }

        # Set up audio level simulation timer
        # In the real implementation, this would use actual audio levels
        self.audio_timer = QTimer(self)
        self.audio_timer.timeout.connect(self.update_audio_level)

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Bengali-to-English Medical Transcription")
        self.setGeometry(100, 100, 1000, 700)

        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # Create toolbar with actions
        self.create_toolbar()

        # Audio controls section
        audio_controls = QWidget()
        audio_layout = QHBoxLayout(audio_controls)

        self.start_button = QPushButton("Start Recording")
        self.start_button.clicked.connect(self.start_recording)

        self.pause_button = QPushButton("Pause")
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.toggle_pause)

        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_recording)

        self.reset_button = QPushButton("Reset")
        self.reset_button.clicked.connect(self.reset_session)

        audio_layout.addWidget(self.start_button)
        audio_layout.addWidget(self.pause_button)
        audio_layout.addWidget(self.stop_button)
        audio_layout.addWidget(self.reset_button)

        # Audio level visualization
        self.audio_level = AudioLevelWidget()
        audio_layout.addWidget(self.audio_level)

        main_layout.addWidget(audio_controls)

        # Transcription display section
        splitter = QSplitter(Qt.Horizontal)

        # Bengali panel
        bengali_widget = QWidget()
        bengali_layout = QVBoxLayout(bengali_widget)
        bengali_label = QLabel("Bengali Transcription (Original)")
        bengali_label.setAlignment(Qt.AlignCenter)
        self.bengali_text = QTextEdit()
        self.bengali_text.setReadOnly(False)  # Allow editing
        self.bengali_text.textChanged.connect(self.on_bengali_edited)
        bengali_layout.addWidget(bengali_label)
        bengali_layout.addWidget(self.bengali_text)

        # English panel
        english_widget = QWidget()
        english_layout = QVBoxLayout(english_widget)
        english_label = QLabel("English Translation")
        english_label.setAlignment(Qt.AlignCenter)
        self.english_text = QTextEdit()
        self.english_text.setReadOnly(False)  # Allow editing
        self.english_text.textChanged.connect(self.on_english_edited)
        english_layout.addWidget(english_label)
        english_layout.addWidget(self.english_text)

        splitter.addWidget(bengali_widget)
        splitter.addWidget(english_widget)
        splitter.setSizes([500, 500])  # Equal initial sizes

        main_layout.addWidget(splitter, 1)  # Give the splitter a stretch factor

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Set the central widget
        self.setCentralWidget(central_widget)

    def create_toolbar(self):
        """Create the application toolbar."""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        # New session action
        new_action = QAction("New Session", self)
        new_action.triggered.connect(self.reset_session)
        toolbar.addAction(new_action)

        # Save action
        save_action = QAction("Save Session", self)
        save_action.triggered.connect(self.save_session)
        toolbar.addAction(save_action)

        # Load action
        load_action = QAction("Load Session", self)
        load_action.triggered.connect(self.load_session)
        toolbar.addAction(load_action)

        toolbar.addSeparator()

        # Export actions
        export_menu = QComboBox()
        export_menu.addItem("Export as...")
        export_menu.addItem("Export as TXT")
        export_menu.addItem("Export as PDF")
        export_menu.addItem("Export as DOCX")
        export_menu.currentIndexChanged.connect(self.handle_export)
        toolbar.addWidget(export_menu)

        toolbar.addSeparator()

        # Settings action
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.show_settings)
        toolbar.addAction(settings_action)

        # Help action
        help_action = QAction("Help", self)
        help_action.triggered.connect(self.show_help)
        toolbar.addAction(help_action)

    def start_recording(self):
        """Start the recording and transcription process."""
        if self.worker and self.worker.isRunning():
            return

        # Update UI state
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.status_bar.showMessage("Recording...")

        # Start the audio level visualization
        self.audio_level.recording = True
        self.audio_timer.start(100)  # Update every 100ms

        # Start the transcription worker
        self.worker = TranscriptionWorker(self.pipeline)
        self.worker.bengali_update.connect(self.update_bengali_text)
        self.worker.english_update.connect(self.update_english_text)
        self.worker.status_update.connect(self.update_status)
        self.worker.start()

    def toggle_pause(self):
        """Pause or resume recording."""
        if not self.worker or not self.worker.isRunning():
            return

        if self.pause_button.text() == "Pause":
            # Pause recording
            self.pipeline.pause()
            self.pause_button.setText("Resume")
            self.status_bar.showMessage("Paused")
            self.audio_level.recording = False
            self.audio_timer.stop()
        else:
            # Resume recording
            self.pipeline.resume()
            self.pause_button.setText("Pause")
            self.status_bar.showMessage("Recording...")
            self.audio_level.recording = True
            self.audio_timer.start(100)

    def stop_recording(self):
        """Stop the recording and transcription process."""
        if not self.worker or not self.worker.isRunning():
            return

        # Stop the worker
        self.worker.stop()

        # Update UI state
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.pause_button.setText("Pause")
        self.stop_button.setEnabled(False)

        # Stop the audio level visualization
        self.audio_level.recording = False
        self.audio_timer.stop()
        self.audio_level.set_level(0)

    def reset_session(self):
 
    # Stop any ongoing recording
        if self.worker and self.worker.isRunning():
            self.stop_recording()
        
        # Clear the text fields
        self.bengali_text.clear()
        self.english_text.clear()
        
        # Reset the current session dictionary
        self.current_session = {
            'bengali': '',
            'english': '',
            'timestamp': datetime.now(),
            'filename': None
        }
        
        # Reset the pipeline by creating a new instance
        self.pipeline = TranscriptionPipeline()
        
        # Create a new worker (or set to None until needed)
        self.worker = None
        
        # Reset audio level widget
        self.audio_level.set_level(0)
        self.audio_level.recording = False
        
        # Make sure audio timer is stopped
        if self.audio_timer.isActive():
            self.audio_timer.stop()
        
        # Update UI state
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.pause_button.setText("Pause")
        self.stop_button.setEnabled(False)
        
        # Force garbage collection to clean up any lingering objects
        import gc
        gc.collect()
        
        self.status_bar.showMessage("Session reset - all memory cleared")

    def update_bengali_text(self, text):
        """Update the Bengali text display."""
        # Disconnect the signal to prevent recursive calls
        self.bengali_text.textChanged.disconnect(self.on_bengali_edited)

        # Update the text
        self.bengali_text.setPlainText(text)
        self.current_session['bengali'] = text

        # Reconnect the signal
        self.bengali_text.textChanged.connect(self.on_bengali_edited)

    def update_english_text(self, text):
        """Update the English text display."""
        # Disconnect the signal to prevent recursive calls
        self.english_text.textChanged.disconnect(self.on_english_edited)

        # Update the text
        self.english_text.setPlainText(text)
        self.current_session['english'] = text

        # Reconnect the signal
        self.english_text.textChanged.connect(self.on_english_edited)

    def on_bengali_edited(self):
        """Handle manual edits to the Bengali text."""
        if self.worker and self.worker.isRunning():
            # Don't process edits during active recording
            return

        # Get the updated text
        text = self.bengali_text.toPlainText()
        self.current_session['bengali'] = text

        # Trigger re-translation
        if text:
            # In a real implementation, this would use the pipeline's translation
            # For now, we'll just simulate it
            self.status_bar.showMessage("Translating...")

            # Use a timer to simulate translation delay
            def delayed_translation():
                english = self.pipeline.update_bengali_text(text)
                self.update_english_text(english)
                self.status_bar.showMessage("Translation updated")

            QTimer.singleShot(500, delayed_translation)

    def on_english_edited(self):
        """Handle manual edits to the English text."""
        if self.worker and self.worker.isRunning():
            # Don't process edits during active recording
            return

        # Get the updated text
        text = self.english_text.toPlainText()
        self.current_session['english'] = text

        # No back-translation to Bengali

    def update_status(self, message):
        """Update the status bar message."""
        self.status_bar.showMessage(message)

    def update_audio_level(self):
        """Update the audio level visualization."""
        # In a real implementation, this would use actual audio levels
        # For now, we'll just simulate it with random values
        import random
        if hasattr(self.audio_level, 'recording') and self.audio_level.recording:
            level = random.randint(10, 80)
            self.audio_level.set_level(level)

    def save_session(self):
        """Save the current session to a file."""
        if not self.current_session['bengali'] and not self.current_session['english']:
            QMessageBox.warning(self, "Empty Session",
                               "There is no transcription data to save.")
            return

        # Get a filename from the user
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Session", "", "Transcription Files (*.transcript);;All Files (*)"
        )

        if not filename:
            return

        # Add extension if not present
        if not filename.endswith('.transcript'):
            filename += '.transcript'

        try:
            # In a real implementation, this would use a more structured format
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"BENGALI TRANSCRIPTION\n")
                f.write(f"====================\n\n")
                f.write(self.current_session['bengali'])
                f.write(f"\n\nENGLISH TRANSLATION\n")
                f.write(f"===================\n\n")
                f.write(self.current_session['english'])
                f.write(f"\n\nTimestamp: {self.current_session['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")

    
            # Update the current session
            self.current_session['filename'] = filename
            self.status_bar.showMessage(f"Session saved to {filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save session: {str(e)}")
            
    def load_session(self):
        """Load a session from a file."""
        # Get a filename from the user
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Session", "", "Transcription Files (*.transcript);;All Files (*)"
        )
        
        if not filename:
            return
            
        try:
            # In a real implementation, this would use a more structured format
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Simple parsing of the file format
            bengali_section = content.split("BENGALI TRANSCRIPTION\n====================\n\n")[1]
            bengali_text = bengali_section.split("\n\nENGLISH TRANSLATION")[0].strip()
            
            english_section = content.split("ENGLISH TRANSLATION\n===================\n\n")[1]
            english_text = english_section.split("\n\nTimestamp:")[0].strip()
            
            # Update the UI
            self.update_bengali_text(bengali_text)
            self.update_english_text(english_text)
            
            # Update the current session
            self.current_session['filename'] = filename
            self.current_session['timestamp'] = datetime.now()  # Use current time as load time
            
            self.status_bar.showMessage(f"Session loaded from {filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load session: {str(e)}")
            
    def handle_export(self, index):
        """Handle export menu selection."""
        if index == 0:  # "Export as..." (no action)
            return
            
        if not self.current_session['bengali'] and not self.current_session['english']:
            QMessageBox.warning(self, "Empty Session", 
                               "There is no transcription data to export.")
            return
            
        # Reset the combo box
        combo = self.sender()
        combo.setCurrentIndex(0)
        
        # Handle export based on selection
        if index == 1:  # TXT
            self.export_as_txt()
        elif index == 2:  # PDF
            self.export_as_pdf()
        elif index == 3:  # DOCX
            self.export_as_docx()
            
    def export_as_txt(self):
        """Export the session as a text file."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export as TXT", "", "Text Files (*.txt);;All Files (*)"
        )
        
        if not filename:
            return
            
        # Add extension if not present
        if not filename.endswith('.txt'):
            filename += '.txt'
            
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"BENGALI TRANSCRIPTION\n")
                f.write(f"====================\n\n")
                f.write(self.current_session['bengali'])
                f.write(f"\n\nENGLISH TRANSLATION\n")
                f.write(f"===================\n\n")
                f.write(self.current_session['english'])
                f.write(f"\n\nExported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
            self.status_bar.showMessage(f"Exported to {filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export as TXT: {str(e)}")
            
    def export_as_pdf(self):
        """Export the session as a PDF file."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export as PDF", "", "PDF Files (*.pdf);;All Files (*)"
        )
        
        if not filename:
            return
            
        # Add extension if not present
        if not filename.endswith('.pdf'):
            filename += '.pdf'
            
        try:
            # In a real implementation, this would use a PDF library
            # For now, we'll just simulate it
            self.status_bar.showMessage("Exporting to PDF...")
            
            # Simulate PDF creation delay
            def delayed_export():
                # This would be replaced with actual PDF creation code
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("PDF EXPORT PLACEHOLDER")
                    
                self.status_bar.showMessage(f"Exported to {filename}")
                QMessageBox.information(self, "Export Complete", 
                                      f"Session exported to {filename}")
                
            QTimer.singleShot(1000, delayed_export)
            
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export as PDF: {str(e)}")
            
    def export_as_docx(self):
        """Export the session as a Word document."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export as DOCX", "", "Word Files (*.docx);;All Files (*)"
        )
        
        if not filename:
            return
            
        # Add extension if not present
        if not filename.endswith('.docx'):
            filename += '.docx'
            
        try:
            # In a real implementation, this would use a DOCX library
            # For now, we'll just simulate it
            self.status_bar.showMessage("Exporting to DOCX...")
            
            # Simulate DOCX creation delay
            def delayed_export():
                # This would be replaced with actual DOCX creation code
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("DOCX EXPORT PLACEHOLDER")
                    
                self.status_bar.showMessage(f"Exported to {filename}")
                QMessageBox.information(self, "Export Complete", 
                                      f"Session exported to {filename}")
                
            QTimer.singleShot(1000, delayed_export)
            
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export as DOCX: {str(e)}")
            
    def show_settings(self):
        """Show the settings dialog."""
        QMessageBox.information(self, "Settings", 
                              "Settings dialog would be implemented here.")
        
    def show_help(self):
        """Show the help dialog."""
        QMessageBox.information(self, "Help", 
                              "Bengali-to-English Medical Transcription\n\n"
                              "This application allows you to transcribe Bengali speech to text "
                              "and translate it to English in real-time.\n\n"
                              "To get started:\n"
                              "1. Click 'Start Recording' to begin capturing audio\n"
                              "2. Speak in Bengali into your microphone\n"
                              "3. View the transcription and translation in the panels below\n"
                              "4. Edit the text manually if needed\n"
                              "5. Save or export your transcription when finished")
