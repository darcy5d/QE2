"""
Dashboard View - Home screen with clickable tiles
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                QPushButton, QFrame)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont, QCursor

from .database import DatabaseHelper


class DashboardTile(QPushButton):
    """Large clickable tile for dashboard"""
    
    def __init__(self, title: str, icon: str, description: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.icon = icon
        self.description = description
        self.setup_ui()
    
    def setup_ui(self):
        """Setup tile appearance"""
        self.setMinimumSize(300, 200)
        self.setMaximumSize(400, 250)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        
        # Style
        self.setStyleSheet("""
            QPushButton {
                background-color: #3A3A3A;
                border: 2px solid #555;
                border-radius: 8px;
                padding: 20px;
                text-align: center;
                color: white;
            }
            QPushButton:hover {
                background-color: #4A4A4A;
                border: 2px solid #4A90E2;
            }
            QPushButton:pressed {
                background-color: #505050;
            }
        """)
        
        # Create text content
        text = f"{self.icon}\n\n{self.title}\n\n{self.description}"
        self.setText(text)
        
        font = QFont()
        font.setPointSize(14)
        self.setFont(font)


class DashboardView(QWidget):
    """Dashboard home screen with tiles"""
    
    # Signals
    racecard_clicked = Signal()
    datafetch_clicked = Signal()
    
    def __init__(self, db_helper: DatabaseHelper, parent=None):
        super().__init__(parent)
        self.db = db_helper
        self.setup_ui()
        self.load_stats()
    
    def setup_ui(self):
        """Setup the dashboard view UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)
        
        # Title
        title = QLabel("RACING DATA DASHBOARD")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(20)
        
        # Tiles container
        tiles_layout = QHBoxLayout()
        tiles_layout.setSpacing(30)
        
        # Racecard Viewer tile
        self.racecard_tile = DashboardTile(
            "RACECARD VIEWER",
            "📊",
            "Browse races\nView entities\nExplore data"
        )
        self.racecard_tile.clicked.connect(self.racecard_clicked.emit)
        tiles_layout.addWidget(self.racecard_tile)
        
        # Database Update tile
        self.datafetch_tile = DashboardTile(
            "DATABASE UPDATE",
            "📥",
            "Update database\nFetch new data\nExpand coverage"
        )
        self.datafetch_tile.clicked.connect(self.datafetch_clicked.emit)
        tiles_layout.addWidget(self.datafetch_tile)
        
        tiles_layout.addStretch()
        layout.addLayout(tiles_layout)
        
        layout.addStretch()
        
        # Database stats section
        stats_frame = QFrame()
        stats_frame.setFrameShape(QFrame.StyledPanel)
        stats_frame.setStyleSheet("""
            QFrame {
                background-color: #2C2C2C;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 15px;
            }
        """)
        
        stats_layout = QVBoxLayout()
        
        self.stats_label = QLabel()
        stats_font = QFont()
        stats_font.setPointSize(11)
        self.stats_label.setFont(stats_font)
        self.stats_label.setStyleSheet("color: white;")
        stats_layout.addWidget(self.stats_label)
        
        stats_frame.setLayout(stats_layout)
        layout.addWidget(stats_frame)
        
        self.setLayout(layout)
    
    def load_stats(self):
        """Load and display database statistics"""
        cursor = self.db.conn.cursor()
        
        # Get date range
        cursor.execute("SELECT MIN(date), MAX(date) FROM races")
        min_date, max_date = cursor.fetchone()
        
        # Get total races
        cursor.execute("SELECT COUNT(*) FROM races")
        total_races = cursor.fetchone()[0]
        
        # Get total runners
        cursor.execute("SELECT COUNT(*) FROM runners")
        total_runners = cursor.fetchone()[0]
        
        # Format stats text
        stats_text = (
            f"Database: racing_pro.db\n"
            f"Current Data: {min_date} to {max_date}\n"
            f"Total Races: {total_races:,} | Total Runners: {total_runners:,}"
        )
        
        self.stats_label.setText(stats_text)
    
    def refresh_stats(self):
        """Refresh database statistics"""
        self.load_stats()

