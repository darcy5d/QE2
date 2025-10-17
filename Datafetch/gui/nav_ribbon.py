"""
Navigation Ribbon - Top navigation bar for dashboard
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont


class NavigationRibbon(QWidget):
    """Top navigation bar with Home, Racecard, Data Fetch buttons"""
    
    # Signals
    home_clicked = Signal()
    dbupdate_clicked = Signal()
    upcoming_clicked = Signal()
    racecard_clicked = Signal()
    exploration_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_view = 'home'
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the navigation ribbon UI"""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create buttons
        self.home_btn = QPushButton("🏠 Home")
        self.dbupdate_btn = QPushButton("Database Update")
        self.upcoming_btn = QPushButton("Upcoming Races")
        self.racecard_btn = QPushButton("Racecard Viewer")
        self.exploration_btn = QPushButton("Data Exploration")
        
        # Style buttons
        button_style = """
            QPushButton {
                background-color: #E0E0E0;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                margin: 5px;
                text-align: center;
                font-size: 14px;
                color: #333;
            }
            QPushButton:hover {
                background-color: #D0D0D0;
            }
            QPushButton:pressed {
                background-color: #C0C0C0;
            }
        """
        
        active_style = """
            QPushButton {
                background-color: #4A90E2;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                margin: 5px;
                text-align: center;
                font-size: 14px;
                color: white;
                font-weight: bold;
            }
        """
        
        self.button_style = button_style
        self.active_style = active_style
        
        for btn in [self.home_btn, self.dbupdate_btn, self.upcoming_btn, 
                    self.racecard_btn, self.exploration_btn]:
            btn.setStyleSheet(button_style)
            font = QFont()
            font.setPointSize(12)
            btn.setFont(font)
        
        # Connect signals
        self.home_btn.clicked.connect(self.on_home_clicked)
        self.dbupdate_btn.clicked.connect(self.on_dbupdate_clicked)
        self.upcoming_btn.clicked.connect(self.on_upcoming_clicked)
        self.racecard_btn.clicked.connect(self.on_racecard_clicked)
        self.exploration_btn.clicked.connect(self.on_exploration_clicked)
        
        # Add to layout
        layout.addWidget(self.home_btn)
        layout.addWidget(self.dbupdate_btn)
        layout.addWidget(self.upcoming_btn)
        layout.addWidget(self.racecard_btn)
        layout.addWidget(self.exploration_btn)
        layout.addStretch()
        
        self.setLayout(layout)
        self.setFixedHeight(50)
        self.setStyleSheet("background-color: #F5F5F5;")
        
        # Set home as active initially
        self.set_active('home')
    
    def set_active(self, view: str):
        """Set which view is currently active"""
        self.current_view = view
        
        # Reset all buttons to normal style
        self.home_btn.setStyleSheet(self.button_style)
        self.dbupdate_btn.setStyleSheet(self.button_style)
        self.upcoming_btn.setStyleSheet(self.button_style)
        self.racecard_btn.setStyleSheet(self.button_style)
        self.exploration_btn.setStyleSheet(self.button_style)
        
        # Set active button style
        if view == 'home':
            self.home_btn.setStyleSheet(self.active_style)
        elif view == 'dbupdate':
            self.dbupdate_btn.setStyleSheet(self.active_style)
        elif view == 'upcoming':
            self.upcoming_btn.setStyleSheet(self.active_style)
        elif view == 'racecard':
            self.racecard_btn.setStyleSheet(self.active_style)
        elif view == 'exploration':
            self.exploration_btn.setStyleSheet(self.active_style)
    
    def on_home_clicked(self):
        """Handle home button click"""
        self.set_active('home')
        self.home_clicked.emit()
    
    def on_dbupdate_clicked(self):
        """Handle database update button click"""
        self.set_active('dbupdate')
        self.dbupdate_clicked.emit()
    
    def on_upcoming_clicked(self):
        """Handle upcoming races button click"""
        self.set_active('upcoming')
        self.upcoming_clicked.emit()
    
    def on_racecard_clicked(self):
        """Handle racecard button click"""
        self.set_active('racecard')
        self.racecard_clicked.emit()
    
    def on_exploration_clicked(self):
        """Handle exploration button click"""
        self.set_active('exploration')
        self.exploration_clicked.emit()

