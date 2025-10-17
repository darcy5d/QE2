#!/usr/bin/env python3
"""
Racecard Viewer GUI Application
Main entry point for the application
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from gui.dashboard_window import DashboardWindow


def main():
    """Main application entry point"""
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Racing Data Dashboard")
    app.setOrganizationName("Racing Data")
    
    # Set application style
    app.setStyle("Fusion")  # Clean, cross-platform style
    
    # Set default font with increased size (+2pt)
    default_font = app.font()
    default_font.setPointSize(default_font.pointSize() + 2)
    app.setFont(default_font)
    
    # Note: High DPI scaling is automatic in Qt 6.10+, no need to set attributes
    
    # Create and show dashboard window
    window = DashboardWindow()
    window.show()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

