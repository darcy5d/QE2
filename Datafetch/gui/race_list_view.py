"""
Race List View for displaying filtered races
Shows all races matching current filter criteria
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTableWidget,
                                QTableWidgetItem, QHeaderView, QScrollArea)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont, QColor
from typing import List, Dict, Any


class RaceListView(QWidget):
    """Widget to display filtered list of races"""
    
    # Signals
    race_selected = Signal(str)  # Emits race_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.races = []
        self.setup_ui()
        self.show_placeholder()
    
    def setup_ui(self):
        """Setup the race list view UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Header label
        self.header_label = QLabel()
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        self.header_label.setFont(header_font)
        layout.addWidget(self.header_label)
        
        # Separator
        self.separator = QLabel("═" * 80)
        self.separator.setStyleSheet("color: #333;")
        layout.addWidget(self.separator)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(['Date', 'Time', 'Course', 'Race Name', 'Class', 'Field'])
        
        # Set column widths
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Date
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Time
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Course
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)  # Race Name
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Class
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Field
        
        # Table settings
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        
        # Connect row click
        self.table.cellClicked.connect(self.on_row_clicked)
        
        layout.addWidget(self.table)
        
        self.setLayout(layout)
    
    def show_placeholder(self):
        """Show placeholder when no filters selected"""
        self.header_label.setText("RACES (Select at least 3 filters to view races)")
        self.separator.setVisible(True)
        self.table.setVisible(True)
        self.table.setRowCount(0)
    
    def display_races(self, races: List[Dict[str, Any]]):
        """Display list of races"""
        self.races = races
        
        # Update header
        race_count = len(races)
        self.header_label.setText(f"RACES (Filtered: {race_count:,} race{'s' if race_count != 1 else ''})")
        
        # Clear and populate table
        self.table.setRowCount(len(races))
        
        for row, race in enumerate(races):
            # Date
            date_item = QTableWidgetItem(race.get('date', ''))
            date_item.setForeground(QColor('white'))
            self.table.setItem(row, 0, date_item)
            
            # Time
            time_item = QTableWidgetItem(race.get('off_time', ''))
            time_item.setForeground(QColor('white'))
            time_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, time_item)
            
            # Course
            course_item = QTableWidgetItem(race.get('course', ''))
            course_item.setForeground(QColor('white'))
            self.table.setItem(row, 2, course_item)
            
            # Race Name
            race_name_item = QTableWidgetItem(race.get('race_name', ''))
            race_name_item.setForeground(QColor('white'))
            self.table.setItem(row, 3, race_name_item)
            
            # Class
            race_class = race.get('race_class', '')
            class_item = QTableWidgetItem(str(race_class) if race_class else '')
            class_item.setForeground(QColor('white'))
            class_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, class_item)
            
            # Field Size
            field_size = race.get('field_size', '')
            field_item = QTableWidgetItem(str(field_size) if field_size else '')
            field_item.setForeground(QColor('white'))
            field_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 5, field_item)
            
            # Store race_id in first column
            date_item.setData(Qt.UserRole, race.get('race_id'))
            
            # Set row height
            self.table.setRowHeight(row, 30)
    
    def on_row_clicked(self, row: int, column: int):
        """Handle row click"""
        if row >= 0 and row < len(self.races):
            race_id = self.races[row].get('race_id')
            if race_id:
                self.race_selected.emit(race_id)

