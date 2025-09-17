#!/usr/bin/env python3
"""
Main entry point for the Bengali-to-English Medical Transcription Application.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import the user interface module
from user_interface import MainWindow

def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
