"""
Navigation Panel for Racecard GUI
Left sidebar with independent filters
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QComboBox, QGroupBox, QPushButton)
from PySide6.QtCore import Signal, Slot
from typing import Dict

from .database import DatabaseHelper


class NavigationPanel(QWidget):
    """Left navigation panel with independent filters"""
    
    # Signals
    filters_changed = Signal(dict)  # Emits dict of all current filter values
    refresh_requested = Signal()  # Emits when refresh button is clicked
    
    def __init__(self, db_helper: DatabaseHelper, parent=None):
        super().__init__(parent)
        self.db = db_helper
        self.setup_ui()
        self.load_filter_options()
        
        # Emit initial filter state (all "All")
        self.emit_filters()
    
    def setup_ui(self):
        """Setup the navigation panel UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Filters Group
        filters_group = QGroupBox("Filters")
        filters_layout = QVBoxLayout()
        filters_layout.setSpacing(10)
        
        # Year Filter
        filters_layout.addWidget(QLabel("Year:"))
        self.year_combo = QComboBox()
        self.year_combo.currentTextChanged.connect(self.on_filter_changed)
        filters_layout.addWidget(self.year_combo)
        
        # Month Filter
        filters_layout.addWidget(QLabel("Month:"))
        self.month_combo = QComboBox()
        self.month_combo.currentTextChanged.connect(self.on_filter_changed)
        filters_layout.addWidget(self.month_combo)
        
        # Day Filter
        filters_layout.addWidget(QLabel("Day:"))
        self.day_combo = QComboBox()
        self.day_combo.currentTextChanged.connect(self.on_filter_changed)
        filters_layout.addWidget(self.day_combo)
        
        # Region Filter
        filters_layout.addWidget(QLabel("Region:"))
        self.region_combo = QComboBox()
        self.region_combo.currentTextChanged.connect(self.on_filter_changed)
        filters_layout.addWidget(self.region_combo)
        
        # Course Filter
        filters_layout.addWidget(QLabel("Course:"))
        self.course_combo = QComboBox()
        self.course_combo.currentTextChanged.connect(self.on_filter_changed)
        filters_layout.addWidget(self.course_combo)
        
        filters_group.setLayout(filters_layout)
        layout.addWidget(filters_group)
        
        # Refresh button
        refresh_btn = QPushButton("↻ Refresh Data")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
        """)
        refresh_btn.clicked.connect(self.on_refresh_clicked)
        layout.addWidget(refresh_btn)
        
        layout.addStretch()
        self.setLayout(layout)
        self.setMinimumWidth(250)
        self.setMaximumWidth(300)
    
    def load_filter_options(self):
        """Load all filter options from database"""
        # Block signals while populating
        self.year_combo.blockSignals(True)
        self.month_combo.blockSignals(True)
        self.day_combo.blockSignals(True)
        self.region_combo.blockSignals(True)
        self.course_combo.blockSignals(True)
        
        # Year filter
        self.year_combo.addItem("All")
        years = self.db.get_years()
        self.year_combo.addItems(years)
        
        # Month filter
        self.month_combo.addItem("All")
        months = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]
        self.month_combo.addItems(months)
        
        # Day filter
        self.day_combo.addItem("All")
        for day in range(1, 32):
            self.day_combo.addItem(str(day))
        
        # Region filter
        self.region_combo.addItem("All")
        regions = self.db.get_regions()
        self.region_combo.addItems(regions)
        
        # Course filter
        self.course_combo.addItem("All")
        courses = self.db.get_courses()
        course_names = sorted(set(course[0] for course in courses))
        self.course_combo.addItems(course_names)
        
        # Unblock signals
        self.year_combo.blockSignals(False)
        self.month_combo.blockSignals(False)
        self.day_combo.blockSignals(False)
        self.region_combo.blockSignals(False)
        self.course_combo.blockSignals(False)
    
    def get_current_filters(self) -> Dict[str, str]:
        """Get current filter values as a dictionary"""
        return {
            'year': self.year_combo.currentText(),
            'month': self.month_combo.currentText(),
            'day': self.day_combo.currentText(),
            'region': self.region_combo.currentText(),
            'course': self.course_combo.currentText()
        }
    
    def emit_filters(self):
        """Emit current filter state"""
        filters = self.get_current_filters()
        self.filters_changed.emit(filters)
    
    def update_filter_options(self):
        """Update all filter options based on current selections"""
        # Get current filter values
        current_filters = self.get_current_filters()
        
        # Block signals to prevent cascading updates
        self.year_combo.blockSignals(True)
        self.month_combo.blockSignals(True)
        self.day_combo.blockSignals(True)
        self.region_combo.blockSignals(True)
        self.course_combo.blockSignals(True)
        
        # Store current selections
        current_year = current_filters['year']
        current_month = current_filters['month']
        current_day = current_filters['day']
        current_region = current_filters['region']
        current_course = current_filters['course']
        
        # Update Year options
        available_years = self.db.get_filtered_options(
            'year',
            month=current_month,
            day=current_day,
            region=current_region,
            course=current_course
        )
        self.year_combo.clear()
        self.year_combo.addItem("All")
        self.year_combo.addItems(available_years)
        # Restore selection if still available
        idx = self.year_combo.findText(current_year)
        if idx >= 0:
            self.year_combo.setCurrentIndex(idx)
        
        # Update Month options
        available_months_nums = self.db.get_filtered_options(
            'month',
            year=current_year,
            day=current_day,
            region=current_region,
            course=current_course
        )
        # Convert month numbers to names
        month_map = {
            "01": "January", "02": "February", "03": "March",
            "04": "April", "05": "May", "06": "June",
            "07": "July", "08": "August", "09": "September",
            "10": "October", "11": "November", "12": "December"
        }
        available_months = [month_map.get(m, m) for m in available_months_nums]
        self.month_combo.clear()
        self.month_combo.addItem("All")
        self.month_combo.addItems(available_months)
        idx = self.month_combo.findText(current_month)
        if idx >= 0:
            self.month_combo.setCurrentIndex(idx)
        
        # Update Day options
        available_days = self.db.get_filtered_options(
            'day',
            year=current_year,
            month=current_month,
            region=current_region,
            course=current_course
        )
        self.day_combo.clear()
        self.day_combo.addItem("All")
        self.day_combo.addItems(available_days)
        idx = self.day_combo.findText(current_day)
        if idx >= 0:
            self.day_combo.setCurrentIndex(idx)
        
        # Update Region options
        available_regions = self.db.get_filtered_options(
            'region',
            year=current_year,
            month=current_month,
            day=current_day,
            course=current_course
        )
        self.region_combo.clear()
        self.region_combo.addItem("All")
        self.region_combo.addItems(available_regions)
        idx = self.region_combo.findText(current_region)
        if idx >= 0:
            self.region_combo.setCurrentIndex(idx)
        
        # Update Course options
        available_courses = self.db.get_filtered_options(
            'course',
            year=current_year,
            month=current_month,
            day=current_day,
            region=current_region
        )
        self.course_combo.clear()
        self.course_combo.addItem("All")
        self.course_combo.addItems(available_courses)
        idx = self.course_combo.findText(current_course)
        if idx >= 0:
            self.course_combo.setCurrentIndex(idx)
        
        # Unblock signals
        self.year_combo.blockSignals(False)
        self.month_combo.blockSignals(False)
        self.day_combo.blockSignals(False)
        self.region_combo.blockSignals(False)
        self.course_combo.blockSignals(False)
    
    @Slot(str)
    def on_filter_changed(self, value: str):
        """Handle any filter change"""
        # Update filter options based on new selection
        self.update_filter_options()
        
        # Emit new filter state
        self.emit_filters()
    
    @Slot()
    def on_refresh_clicked(self):
        """Handle refresh button click"""
        # Reconnect to database
        import sqlite3
        self.db.conn.close()
        self.db.conn = sqlite3.connect(str(self.db.db_path))
        self.db.conn.row_factory = sqlite3.Row
        
        # Reload filter options
        self.load_filter_options()
        
        # Emit refresh signal
        self.refresh_requested.emit()
        
        # Re-emit current filters to refresh the race list
        self.emit_filters()
