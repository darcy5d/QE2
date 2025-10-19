"""
Upcoming Races View - Display upcoming races grouped by date, course, time
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                QPushButton, QProgressBar, QScrollArea,
                                QFrame, QTableWidget, QTableWidgetItem,
                                QHeaderView, QMessageBox)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont, QColor
from pathlib import Path
import sqlite3
from itertools import groupby


class UpcomingRacesView(QWidget):
    """Display upcoming races grouped by date, course, time"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_path = Path(__file__).parent.parent / "upcoming_races.db"
        self.db = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup UI with fetch button and display area"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header with fetch button
        header_layout = QHBoxLayout()
        
        title = QLabel("UPCOMING RACES")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(18)
        title.setFont(title_font)
        title.setStyleSheet("color: white; padding: 10px;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Fetch button
        self.fetch_btn = QPushButton("🔄 Fetch Upcoming Races")
        self.fetch_btn.setStyleSheet("""
            QPushButton {
                background-color: #5CB85C;
                color: white;
                font-size: 13px;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background-color: #4A9D4A;
            }
            QPushButton:pressed {
                background-color: #3E8A3E;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        self.fetch_btn.clicked.connect(self.fetch_upcoming)
        header_layout.addWidget(self.fetch_btn)
        
        layout.addLayout(header_layout)
        
        # Separator
        separator = QLabel("═" * 100)
        separator.setStyleSheet("color: #555;")
        layout.addWidget(separator)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                border-radius: 4px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #5CB85C;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: gray; padding: 5px;")
        layout.addWidget(self.status_label)
        
        # Scroll area for races
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #1E1E1E;
            }
        """)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(10)
        self.content_widget.setLayout(self.content_layout)
        scroll.setWidget(self.content_widget)
        
        layout.addWidget(scroll)
        self.setLayout(layout)
        
        # Show initial message
        self.show_initial_message()
    
    def show_initial_message(self):
        """Show message prompting user to fetch"""
        msg = QLabel("Click 'Fetch Upcoming Races' to load races for yesterday, today, and tomorrow")
        msg.setStyleSheet("color: #888; font-size: 14px; padding: 40px;")
        msg.setAlignment(Qt.AlignCenter)
        self.content_layout.addWidget(msg)
    
    @Slot()
    def fetch_upcoming(self):
        """Start fetching upcoming races"""
        self.fetch_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Clear content
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Start fetcher
        from .upcoming_fetcher import UpcomingRacesFetcher
        self.fetcher = UpcomingRacesFetcher(str(self.db_path))
        self.fetcher.progress.connect(self.on_progress)
        self.fetcher.status.connect(self.on_status)
        self.fetcher.finished.connect(self.on_finished)
        self.fetcher.error.connect(self.on_error)
        self.fetcher.start()
    
    @Slot(int, int)
    def on_progress(self, current: int, total: int):
        """Update progress"""
        percentage = int((current / total) * 100)
        self.progress_bar.setValue(percentage)
        self.progress_bar.setFormat(f"{current}/{total} dates ({percentage}%)")
    
    @Slot(str)
    def on_status(self, message: str):
        """Update status"""
        self.status_label.setText(message)
    
    @Slot(int)
    def on_finished(self, total_races: int):
        """Display fetched races"""
        self.fetch_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Loaded {total_races} upcoming races")
        
        # Load and display races
        self.load_and_display_races()
    
    @Slot(str)
    def on_error(self, error_msg: str):
        """Handle error"""
        self.fetch_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("")
        QMessageBox.critical(self, "Fetch Error", f"Error fetching races:\n\n{error_msg}")
    
    def load_and_display_races(self):
        """Load races from database and display grouped"""
        # Connect to upcoming_races.db
        if self.db:
            self.db.close()
        
        if not self.db_path.exists():
            self.show_initial_message()
            return
        
        self.db = sqlite3.connect(str(self.db_path))
        self.db.row_factory = sqlite3.Row
        
        cursor = self.db.cursor()
        
        # Get all races ordered by date, course, time
        cursor.execute("""
            SELECT race_id, date, course, off_time, race_name, distance, type, prize
            FROM races
            ORDER BY date, course, off_time
        """)
        races = cursor.fetchall()
        
        if not races:
            no_data = QLabel("No upcoming races found")
            no_data.setStyleSheet("color: #888; font-size: 14px; padding: 40px;")
            no_data.setAlignment(Qt.AlignCenter)
            self.content_layout.addWidget(no_data)
            return
        
        # Convert to list first (groupby consumes iterator)
        races_list = list(races)
        
        # Group by date
        for date, date_races in groupby(races_list, key=lambda r: r['date']):
            # Date header
            date_header = QLabel(f"📅 {date}")
            date_header.setStyleSheet("""
                font-size: 16px;
                font-weight: bold;
                color: #4A90E2;
                padding: 15px 10px 5px 10px;
                background-color: #2A2A2A;
                border-radius: 4px;
            """)
            self.content_layout.addWidget(date_header)
            
            # Group by course
            date_races_list = list(date_races)
            for course, course_races in groupby(date_races_list, key=lambda r: r['course']):
                # Course section
                course_widget = self.create_course_widget(course, list(course_races))
                self.content_layout.addWidget(course_widget)
        
        self.content_layout.addStretch()
    
    def create_course_widget(self, course: str, races: list) -> QWidget:
        """Create widget for a course's races"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #333;
                border: 1px solid #555;
                border-radius: 4px;
                margin: 5px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(5)
        
        # Course name
        course_label = QLabel(f"🏇 {course}")
        course_label.setStyleSheet("font-size: 14px; font-weight: bold; color: white; padding: 5px;")
        layout.addWidget(course_label)
        
        # Race table
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Time", "Race Name", "Distance", "Type", "Prize"])
        table.setRowCount(len(races))
        table.verticalHeader().setVisible(False)
        table.setStyleSheet("""
            QTableWidget {
                background-color: #2A2A2A;
                color: white;
                gridline-color: #444;
                border: none;
            }
            QHeaderView::section {
                background-color: #3A3A3A;
                color: white;
                padding: 5px;
                border: none;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)
        
        for i, race in enumerate(races):
            # Time
            time_item = QTableWidgetItem(race['off_time'] or '')
            time_item.setForeground(QColor('white'))
            table.setItem(i, 0, time_item)
            
            # Race name
            name_item = QTableWidgetItem(race['race_name'] or '')
            name_item.setForeground(QColor('white'))
            table.setItem(i, 1, name_item)
            
            # Distance
            dist_item = QTableWidgetItem(race['distance'] or '')
            dist_item.setForeground(QColor('white'))
            table.setItem(i, 2, dist_item)
            
            # Type
            type_item = QTableWidgetItem(race['type'] or '')
            type_item.setForeground(QColor('white'))
            table.setItem(i, 3, type_item)
            
            # Prize
            prize_item = QTableWidgetItem(race['prize'] or '')
            prize_item.setForeground(QColor('white'))
            table.setItem(i, 4, prize_item)
        
        table.resizeColumnsToContents()
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        
        # Calculate height needed for all rows
        row_height = table.rowHeight(0) if len(races) > 0 else 30
        header_height = table.horizontalHeader().height()
        total_height = header_height + (row_height * len(races)) + 10  # +10 for padding
        table.setMinimumHeight(total_height)
        table.setMaximumHeight(total_height)
        
        # Disable vertical scrollbar since table shows all rows
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        layout.addWidget(table)
        
        frame.setLayout(layout)
        return frame

