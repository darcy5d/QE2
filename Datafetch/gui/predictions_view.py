"""
Predictions View - Display ML predictions for upcoming races with hierarchical navigation
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QTextEdit, QTableWidget, QTableWidgetItem,
                                QHeaderView, QGroupBox, QScrollArea, QProgressBar,
                                QMessageBox, QFileDialog, QFrame, QLayout)
from PySide6.QtCore import Qt, Slot, QRect, QSize
from PySide6.QtGui import QFont, QColor
from pathlib import Path
import sqlite3
import csv
from datetime import datetime
from collections import defaultdict

from .prediction_worker import PredictionWorker
from .styles import COLORS


class FlowLayout(QLayout):
    """Custom layout that wraps widgets to next line like word-wrap"""
    
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        self.itemList = []
        self.m_hSpace = spacing
        self.m_vSpace = spacing
        self.setContentsMargins(margin, margin, margin, margin)
        
    def addItem(self, item):
        self.itemList.append(item)
        
    def count(self):
        return len(self.itemList)
        
    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None
        
    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None
        
    def expandingDirections(self):
        return Qt.Orientations(0)
        
    def hasHeightForWidth(self):
        return True
        
    def heightForWidth(self, width):
        return self.doLayout(QRect(0, 0, width, 0), True)
        
    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)
        
    def sizeHint(self):
        return self.minimumSize()
        
    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        margin = self.contentsMargins().left()
        size += QSize(2 * margin, 2 * margin)
        return size
        
    def doLayout(self, rect, testOnly):
        left, top, right, bottom = self.getContentsMargins()
        effectiveRect = rect.adjusted(left, top, -right, -bottom)
        x = effectiveRect.x()
        y = effectiveRect.y()
        lineHeight = 0
        
        for item in self.itemList:
            widget = item.widget()
            spaceX = self.m_hSpace
            spaceY = self.m_vSpace
            
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > effectiveRect.right() and lineHeight > 0:
                x = effectiveRect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0
                
            if not testOnly:
                item.setGeometry(QRect(x, y, item.sizeHint().width(), item.sizeHint().height()))
                
            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())
            
        return y + lineHeight - rect.y() + bottom


class PredictionsView(QWidget):
    """View for generating and displaying ML predictions for upcoming races"""
    
    def __init__(self, db_helper, parent=None):
        super().__init__(parent)
        self.db = db_helper
        self.upcoming_db_path = Path(__file__).parent.parent / "upcoming_races.db"
        self.racing_db_path = self.db.db_path
        
        self.prediction_worker = None
        self.current_predictions = []
        
        # State management for hierarchical navigation
        self.organized_predictions = {}  # {date_str: {course: [races]}}
        self.date_objects = {}  # {date_str: date_obj} for proper sorting
        self.selected_date = None
        self.selected_course = None
        self.current_race = None
        self.current_race_index = 0  # Track position in current course's race list
        self.current_view = 'hierarchy'  # or 'detail'
        
        # Store UI elements for easy access
        self.date_buttons = {}
        self.course_buttons = {}
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the predictions view UI"""
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['bg_primary']};
                color: {COLORS['text_primary']};
            }}
        """)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("🎯 RACE PREDICTIONS")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(18)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {COLORS['text_primary']}; padding: 10px;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Export button
        self.export_btn = QPushButton("📊 Export to CSV")
        self.export_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent_blue']};
                color: white;
                font-size: 12px;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background-color: #357ABD;
            }}
            QPushButton:disabled {{
                background-color: #555;
                color: #999;
            }}
        """)
        self.export_btn.clicked.connect(self.export_predictions)
        self.export_btn.setEnabled(False)
        header_layout.addWidget(self.export_btn)
        
        # Generate predictions button
        self.generate_btn = QPushButton("🚀 Generate Predictions")
        self.generate_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent_green']};
                color: white;
                font-size: 13px;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 12px 24px;
            }}
            QPushButton:hover {{
                background-color: #4A9D4A;
            }}
            QPushButton:pressed {{
                background-color: #3E8A3E;
            }}
            QPushButton:disabled {{
                background-color: #555;
                color: #999;
            }}
        """)
        self.generate_btn.clicked.connect(self.generate_predictions)
        header_layout.addWidget(self.generate_btn)
        
        main_layout.addLayout(header_layout)
        
        # Info text
        info_label = QLabel(
            "Generate ML predictions for upcoming races. "
            "The model will analyze each runner and predict win probabilities based on historical data."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(f"color: {COLORS['text_secondary']}; padding: 5px; font-size: 12px;")
        main_layout.addWidget(info_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #555;
                border-radius: 4px;
                text-align: center;
                background-color: {COLORS['bg_secondary']};
                color: white;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['accent_green']};
            }}
        """)
        main_layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {COLORS['text_secondary']}; padding: 5px;")
        main_layout.addWidget(self.status_label)
        
        # Create stacked container for switching between hierarchy and detail views
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_container.setLayout(self.content_layout)
        
        # Create hierarchy view
        self.hierarchy_widget = self.create_hierarchy_widget()
        
        # Create detail view
        self.detail_widget = self.create_detail_widget()
        
        # Add both to content layout
        self.content_layout.addWidget(self.hierarchy_widget)
        self.content_layout.addWidget(self.detail_widget)
        
        # Initially hide detail view
        self.detail_widget.hide()
        
        main_layout.addWidget(self.content_container, 1)
        
        self.setLayout(main_layout)
        
        # Show initial empty state
        self.show_empty_state()
    
    def create_hierarchy_widget(self):
        """Create the hierarchical navigation widget (dates -> courses -> races)"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # Date tabs container
        self.date_tabs_container = QWidget()
        self.date_tabs_layout = QHBoxLayout()
        self.date_tabs_layout.setContentsMargins(0, 0, 0, 0)
        self.date_tabs_layout.setSpacing(10)
        self.date_tabs_container.setLayout(self.date_tabs_layout)
        self.date_tabs_container.setVisible(False)
        layout.addWidget(self.date_tabs_container)
        
        # Course chips container with FlowLayout for wrapping
        self.course_chips_container = QWidget()
        self.course_chips_layout = FlowLayout(spacing=10)
        self.course_chips_container.setLayout(self.course_chips_layout)
        self.course_chips_container.setVisible(False)
        layout.addWidget(self.course_chips_container)
        
        # Race cards scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {COLORS['bg_primary']};
                border: none;
            }}
        """)
        
        self.race_cards_container = QWidget()
        self.race_cards_layout = QVBoxLayout()
        self.race_cards_layout.setSpacing(10)
        self.race_cards_container.setLayout(self.race_cards_layout)
        
        scroll.setWidget(self.race_cards_container)
        layout.addWidget(scroll, 1)
        
        widget.setLayout(layout)
        return widget
    
    def create_detail_widget(self):
        """Create the race detail view widget"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Back button
        back_btn = QPushButton("← Back to Races")
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent_blue']};
                color: white;
                font-size: 12px;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: #357ABD;
            }}
        """)
        back_btn.clicked.connect(self.go_back_to_hierarchy)
        layout.addWidget(back_btn)
        
        # Navigation bar for previous/next race
        nav_bar = QWidget()
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(10)
        
        # Previous race button
        self.prev_race_btn = QPushButton("← Previous Race")
        self.prev_race_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['bg_tertiary']};
                color: {COLORS['text_primary']};
                font-size: 11px;
                font-weight: bold;
                border: 1px solid {COLORS['border_medium']};
                border-radius: 4px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['bg_hover']};
                border-color: {COLORS['accent_blue']};
            }}
            QPushButton:disabled {{
                background-color: {COLORS['bg_secondary']};
                color: {COLORS['text_muted']};
                border-color: {COLORS['border_light']};
            }}
        """)
        self.prev_race_btn.clicked.connect(self.show_previous_race)
        nav_layout.addWidget(self.prev_race_btn)
        
        # Race counter label
        self.race_counter_label = QLabel()
        self.race_counter_label.setAlignment(Qt.AlignCenter)
        self.race_counter_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: 11px;
            padding: 5px 10px;
        """)
        nav_layout.addWidget(self.race_counter_label, 1)
        
        # Next race button
        self.next_race_btn = QPushButton("Next Race →")
        self.next_race_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['bg_tertiary']};
                color: {COLORS['text_primary']};
                font-size: 11px;
                font-weight: bold;
                border: 1px solid {COLORS['border_medium']};
                border-radius: 4px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['bg_hover']};
                border-color: {COLORS['accent_blue']};
            }}
            QPushButton:disabled {{
                background-color: {COLORS['bg_secondary']};
                color: {COLORS['text_muted']};
                border-color: {COLORS['border_light']};
            }}
        """)
        self.next_race_btn.clicked.connect(self.show_next_race)
        nav_layout.addWidget(self.next_race_btn)
        
        nav_bar.setLayout(nav_layout)
        layout.addWidget(nav_bar)
        
        # Race header
        self.detail_header = QLabel()
        self.detail_header.setWordWrap(True)
        self.detail_header.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {COLORS['accent_blue']};
            padding: 10px;
            background-color: {COLORS['bg_secondary']};
            border-radius: 6px;
        """)
        layout.addWidget(self.detail_header)
        
        # Predictions table scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {COLORS['bg_primary']};
                border: none;
            }}
        """)
        
        self.detail_table_container = QWidget()
        self.detail_table_layout = QVBoxLayout()
        self.detail_table_layout.setContentsMargins(0, 0, 0, 0)
        self.detail_table_container.setLayout(self.detail_table_layout)
        
        scroll.setWidget(self.detail_table_container)
        layout.addWidget(scroll, 1)
        
        widget.setLayout(layout)
        return widget
    
    def show_empty_state(self):
        """Show message when no predictions have been generated"""
        self.clear_hierarchy()
        
        empty_label = QLabel(
            "No predictions yet.\n\n"
            "Click 'Generate Predictions' to analyze upcoming races."
        )
        empty_label.setAlignment(Qt.AlignCenter)
        empty_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: 14px;
            padding: 60px;
        """)
        self.race_cards_layout.addWidget(empty_label)
        self.race_cards_layout.addStretch()
    
    def clear_hierarchy(self):
        """Clear all hierarchy display elements"""
        # Clear date tabs
        while self.date_tabs_layout.count():
            item = self.date_tabs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Clear course chips
        while self.course_chips_layout.count():
            item = self.course_chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Clear race cards
        while self.race_cards_layout.count():
            item = self.race_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.date_buttons = {}
        self.course_buttons = {}
    
    @Slot()
    def generate_predictions(self):
        """Start prediction generation process"""
        # Check if upcoming races exist
        if not self.upcoming_db_path.exists():
            QMessageBox.warning(
                self,
                "No Upcoming Races",
                "Please fetch upcoming races first using the 'Upcoming Races' tab."
            )
            return
        
        # Get race IDs
        race_ids = self.get_upcoming_race_ids()
        if not race_ids:
            QMessageBox.warning(
                self,
                "No Races Found",
                "No upcoming races found in database. Please fetch races first."
            )
            return
        
        # Disable button and show progress
        self.generate_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Initializing prediction engine...")
        self.clear_hierarchy()
        
        # Start worker
        self.prediction_worker = PredictionWorker(
            race_ids,
            str(self.upcoming_db_path),
            str(self.racing_db_path)
        )
        self.prediction_worker.progress.connect(self.on_progress)
        self.prediction_worker.predictions_ready.connect(self.on_predictions_ready)
        self.prediction_worker.error_occurred.connect(self.on_error)
        self.prediction_worker.finished.connect(self.on_worker_finished)
        self.prediction_worker.start()
    
    def get_upcoming_race_ids(self):
        """Get list of race IDs from upcoming_races.db"""
        try:
            conn = sqlite3.connect(str(self.upcoming_db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT race_id FROM races ORDER BY off_time")
            race_ids = [row[0] for row in cursor.fetchall()]
            conn.close()
            print(f"📊 Found {len(race_ids)} upcoming races to predict")
            return race_ids
        except Exception as e:
            print(f"Error getting race IDs: {e}")
            return []
    
    @Slot(int, int, str)
    def on_progress(self, current, total, message):
        """Update progress bar"""
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)
    
    @Slot(list)
    def on_predictions_ready(self, predictions):
        """Display predictions when ready"""
        self.current_predictions = predictions
        self.clear_hierarchy()
        
        if not predictions:
            self.show_empty_state()
            return
        
        # Organize predictions by date -> course -> race
        self.organized_predictions = self.organize_predictions_by_hierarchy(predictions)
        
        # Create date tabs
        self.create_date_tabs()
        
        # Select first date by default (chronologically)
        if self.organized_predictions:
            first_date = sorted(
                self.organized_predictions.keys(),
                key=lambda d: self.date_objects.get(d, datetime.min)
            )[0]
            self.on_date_selected(first_date)
        
        self.status_label.setText(f"✓ Generated predictions for {len(predictions)} races")
        self.export_btn.setEnabled(True)
    
    def organize_predictions_by_hierarchy(self, predictions):
        """
        Organize predictions: dates -> courses -> races
        Returns: {date_str: {course: [race_pred, ...]}}
        """
        organized = defaultdict(lambda: defaultdict(list))
        self.date_objects = {}  # Clear and rebuild date object mapping
        
        for race_pred in predictions:
            race_info = race_pred['race_info']
            
            # Get date field from race_info (format: "2025-10-18")
            date_str_raw = race_info.get('date', '')
            
            if date_str_raw:
                try:
                    # Parse the date (format: "2025-10-18")
                    date_obj = datetime.strptime(date_str_raw, '%Y-%m-%d')
                    date_str = date_obj.strftime('%a %d %b')  # e.g., "Fri 18 Oct"
                    # Store the date object for proper sorting
                    self.date_objects[date_str] = date_obj
                except Exception as e:
                    print(f"Date parse error for {date_str_raw}: {e}")
                    date_str = "Unknown Date"
                    date_obj = None
            else:
                date_str = "Unknown Date"
                date_obj = None
            
            course = race_info.get('course', 'Unknown')
            
            organized[date_str][course].append(race_pred)
        
        # Sort races within each course by time
        for date in organized:
            for course in organized[date]:
                organized[date][course].sort(key=lambda x: x['race_info'].get('time', ''))
        
        return dict(organized)
    
    def create_date_tabs(self):
        """Create date tab buttons"""
        # Sort dates chronologically by date object, not alphabetically by string
        dates = sorted(
            self.organized_predictions.keys(),
            key=lambda d: self.date_objects.get(d, datetime.min)
        )
        
        for date in dates:
            btn = QPushButton(date)
            btn.setStyleSheet(self.get_tab_style(selected=False))
            btn.clicked.connect(lambda checked, d=date: self.on_date_selected(d))
            btn.setCursor(Qt.PointingHandCursor)
            
            self.date_tabs_layout.addWidget(btn)
            self.date_buttons[date] = btn
        
        self.date_tabs_layout.addStretch()
        self.date_tabs_container.setVisible(True)
    
    def get_tab_style(self, selected=False):
        """Get style for date tab button"""
        bg_color = COLORS['accent_blue'] if selected else COLORS['bg_tertiary']
        hover_color = COLORS['accent_blue_hover'] if selected else COLORS['bg_hover']
        
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: {COLORS['text_primary']};
                font-size: 13px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
        """
    
    def get_chip_style(self, selected=False):
        """Get style for course chip button"""
        bg_color = COLORS['accent_blue'] if selected else COLORS['bg_tertiary']
        hover_color = COLORS['accent_blue_hover'] if selected else COLORS['bg_hover']
        
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: {COLORS['text_primary']};
                font-size: 12px;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
        """
    
    @Slot(str)
    def on_date_selected(self, date):
        """Handle date tab selection"""
        self.selected_date = date
        
        # Update tab styles
        for d, btn in self.date_buttons.items():
            btn.setStyleSheet(self.get_tab_style(selected=(d == date)))
        
        # Create course chips for this date
        self.create_course_chips()
        
        # Select first course by default
        if self.organized_predictions[date]:
            first_course = sorted(self.organized_predictions[date].keys())[0]
            self.on_course_selected(first_course)
    
    def create_course_chips(self):
        """Create course chip buttons for selected date"""
        # Clear existing chips
        while self.course_chips_layout.count():
            item = self.course_chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.course_buttons = {}
        
        if not self.selected_date:
            return
        
        courses = sorted(self.organized_predictions[self.selected_date].keys())
        
        for course in courses:
            race_count = len(self.organized_predictions[self.selected_date][course])
            btn = QPushButton(f"{course} ({race_count})")
            btn.setStyleSheet(self.get_chip_style(selected=False))
            btn.clicked.connect(lambda checked, c=course: self.on_course_selected(c))
            btn.setCursor(Qt.PointingHandCursor)
            
            self.course_chips_layout.addWidget(btn)
            self.course_buttons[course] = btn
        
        # FlowLayout doesn't have addStretch(), wrapping is automatic
        self.course_chips_container.setVisible(True)
    
    @Slot(str)
    def on_course_selected(self, course):
        """Handle course chip selection"""
        self.selected_course = course
        
        # Update chip styles
        for c, btn in self.course_buttons.items():
            btn.setStyleSheet(self.get_chip_style(selected=(c == course)))
        
        # Display race cards for this date + course
        self.display_race_cards()
    
    def display_race_cards(self):
        """Display race preview cards for selected date + course"""
        # Clear existing cards
        while self.race_cards_layout.count():
            item = self.race_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self.selected_date or not self.selected_course:
            return
        
        races = self.organized_predictions[self.selected_date][self.selected_course]
        
        for race_pred in races:
            card = self.create_race_card_preview(race_pred)
            self.race_cards_layout.addWidget(card)
        
        self.race_cards_layout.addStretch()
    
    def create_race_card_preview(self, race_pred):
        """Create a clickable preview card for a race"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border_medium']};
                border-radius: 6px;
                padding: 15px;
            }}
            QFrame:hover {{
                background-color: {COLORS['bg_hover']};
                border-color: {COLORS['accent_blue']};
            }}
        """)
        card.setCursor(Qt.PointingHandCursor)
        
        # Find race index in current date+course races list
        race_index = 0
        if self.selected_date and self.selected_course:
            races = self.organized_predictions[self.selected_date][self.selected_course]
            try:
                race_index = races.index(race_pred)
            except ValueError:
                race_index = 0
        
        # Make card clickable with index
        card.mousePressEvent = lambda event, idx=race_index: self.show_race_detail(race_pred, idx)
        
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        race_info = race_pred['race_info']
        predictions = race_pred['predictions']
        
        # Extract race details
        time = race_info.get('time', '').split()[-1] if race_info.get('time') else 'TBA'
        distance = race_info.get('distance', '')
        race_class = race_info.get('race_class', '')
        race_name = race_info.get('race_name', '')
        pattern = race_info.get('pattern', '')
        surface = race_info.get('surface', '')
        
        # Always show race name if available
        if race_name:
            race_title = f"🏇 {race_name}"
            subtitle_parts = [time, distance]
            if pattern:
                subtitle_parts.append(pattern)
            elif race_class:
                subtitle_parts.append(race_class)
            subtitle = " • ".join(subtitle_parts)
        else:
            # Fallback if no race name
            race_title = f"🏇 {time} - {distance}"
            subtitle = race_class if race_class else "Standard Race"
        
        header = QLabel(race_title)
        header.setStyleSheet(f"""
            font-size: 14px;
            font-weight: bold;
            color: {COLORS['accent_blue']};
        """)
        layout.addWidget(header)
        
        subheader = QLabel(subtitle)
        subheader.setStyleSheet(f"""
            font-size: 11px;
            color: {COLORS['text_secondary']};
        """)
        layout.addWidget(subheader)
        
        # Number of runners and data coverage
        runner_count = len(predictions)
        
        # Get RPR/TS coverage for this race
        coverage_info = self.get_data_coverage(race_info.get('race_id'))
        
        if coverage_info:
            rpr_pct = coverage_info['rpr_pct']
            ts_pct = coverage_info['ts_pct']
            
            # Create coverage indicator
            if rpr_pct < 30:
                coverage_icon = "🔴"
                coverage_text = f"{runner_count} runners | {coverage_icon} RPR: {rpr_pct:.0f}% (Limited data)"
                coverage_color = COLORS['accent_red']
            elif rpr_pct < 70:
                coverage_icon = "🟡"
                coverage_text = f"{runner_count} runners | {coverage_icon} RPR: {rpr_pct:.0f}% (Partial data)"
                coverage_color = COLORS['accent_yellow']
            else:
                coverage_icon = "🟢"
                coverage_text = f"{runner_count} runners | {coverage_icon} RPR: {rpr_pct:.0f}%"
                coverage_color = COLORS['text_secondary']
        else:
            coverage_text = f"{runner_count} runners"
            coverage_color = COLORS['text_secondary']
        
        runner_label = QLabel(coverage_text)
        runner_label.setStyleSheet(f"color: {coverage_color}; font-size: 11px;")
        layout.addWidget(runner_label)
        
        # Top pick preview
        if predictions:
            top_pick = predictions[0]
            horse = top_pick.get('horse_name', 'Unknown')
            prob = top_pick['win_probability'] * 100
            
            top_pick_label = QLabel(f"Top Pick: {horse} ({prob:.1f}%)")
            top_pick_label.setStyleSheet(f"""
                color: {COLORS['accent_green']};
                font-size: 12px;
                font-weight: bold;
            """)
            layout.addWidget(top_pick_label)
        
        card.setLayout(layout)
        return card
    
    def show_race_detail(self, race_pred, race_index=None):
        """Show detailed race view with all runners"""
        self.current_race = race_pred
        
        # Track race index if provided, otherwise find it
        if race_index is not None:
            self.current_race_index = race_index
        else:
            # Find index in current date+course races list
            if self.selected_date and self.selected_course:
                races = self.organized_predictions[self.selected_date][self.selected_course]
                try:
                    self.current_race_index = races.index(race_pred)
                except ValueError:
                    self.current_race_index = 0
        
        # Update navigation buttons
        self.update_race_navigation()
        
        # Update header with comprehensive race information
        race_info = race_pred['race_info']
        course = race_info.get('course', 'Unknown')
        time = race_info.get('time', '')
        distance = race_info.get('distance', '')
        race_class = race_info.get('race_class', '')
        
        # Build comprehensive race header
        race_name = race_info.get('race_name', '')
        pattern = race_info.get('pattern', '')
        race_type = race_info.get('type', '')
        surface = race_info.get('surface', '')
        going = race_info.get('going', '')
        prize = race_info.get('prize', '')
        
        # Format: COURSE (SURFACE) - TIME
        # Race Name - Distance - Class/Pattern - Going - Prize
        header_line1 = f"{course} ({surface if surface else 'Turf'}) - {time}"
        header_line2_parts = []
        
        if race_name:
            header_line2_parts.append(race_name)
        header_line2_parts.append(distance)
        
        if pattern:
            header_line2_parts.append(pattern)
        elif race_class:
            header_line2_parts.append(race_class)
        
        if going:
            header_line2_parts.append(f"Going: {going}")
        
        if prize:
            header_line2_parts.append(f"Prize: {prize}")
        
        header_text = f"{header_line1}\n{' • '.join([p for p in header_line2_parts if p])}"
        self.detail_header.setText(header_text)
        
        # Clear and populate content
        while self.detail_table_layout.count():
            item = self.detail_table_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add data coverage warning if needed
        coverage_info = self.get_data_coverage(race_info.get('race_id'))
        if coverage_info and coverage_info['rpr_pct'] < 50:
            coverage_warning = self.create_coverage_warning(coverage_info)
            self.detail_table_layout.addWidget(coverage_warning)
        
        # Sort predictions by win probability (highest first)
        sorted_predictions = sorted(race_pred['predictions'], key=lambda x: x['win_probability'], reverse=True)
        
        # Re-assign ranks based on win probability
        for rank, pred in enumerate(sorted_predictions, 1):
            pred['predicted_rank'] = rank
        
        # Add exotic bets info panel
        exotics_panel = self.create_exotics_panel(sorted_predictions)
        self.detail_table_layout.addWidget(exotics_panel)
        
        # Add predictions table
        table = self.create_predictions_table(sorted_predictions)
        self.detail_table_layout.addWidget(table)
        
        # Switch views
        self.hierarchy_widget.hide()
        self.detail_widget.show()
        self.current_view = 'detail'
    
    def go_back_to_hierarchy(self):
        """Return to hierarchy view"""
        self.detail_widget.hide()
        self.hierarchy_widget.show()
        self.current_view = 'hierarchy'
    
    def update_race_navigation(self):
        """Update Previous/Next race button states and counter label"""
        if not self.selected_date or not self.selected_course:
            self.prev_race_btn.setEnabled(False)
            self.next_race_btn.setEnabled(False)
            self.race_counter_label.setText("")
            return
        
        races = self.organized_predictions[self.selected_date][self.selected_course]
        total_races = len(races)
        current_num = self.current_race_index + 1  # 1-based for display
        
        # Update counter label
        self.race_counter_label.setText(f"Race {current_num} of {total_races}")
        
        # Enable/disable buttons based on position
        self.prev_race_btn.setEnabled(self.current_race_index > 0)
        self.next_race_btn.setEnabled(self.current_race_index < total_races - 1)
    
    @Slot()
    def show_previous_race(self):
        """Navigate to previous race at same course/date"""
        if not self.selected_date or not self.selected_course:
            return
        
        races = self.organized_predictions[self.selected_date][self.selected_course]
        if self.current_race_index > 0:
            self.current_race_index -= 1
            race_pred = races[self.current_race_index]
            self.show_race_detail(race_pred, self.current_race_index)
    
    @Slot()
    def show_next_race(self):
        """Navigate to next race at same course/date"""
        if not self.selected_date or not self.selected_course:
            return
        
        races = self.organized_predictions[self.selected_date][self.selected_course]
        if self.current_race_index < len(races) - 1:
            self.current_race_index += 1
            race_pred = races[self.current_race_index]
            self.show_race_detail(race_pred, self.current_race_index)
    
    @Slot(str)
    def on_error(self, error_message):
        """Handle prediction errors"""
        QMessageBox.critical(
            self,
            "Prediction Error",
            f"Failed to generate predictions:\n\n{error_message}"
        )
        self.status_label.setText(f"❌ Error: {error_message}")
        self.show_empty_state()
    
    @Slot()
    def on_worker_finished(self):
        """Re-enable button when worker finishes"""
        self.generate_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
    
    def create_predictions_table(self, predictions):
        """Create table displaying predictions for runners"""
        table = QTableWidget()
        table.setRowCount(len(predictions))
        table.setColumnCount(11)
        table.setHorizontalHeaderLabels([
            'Rank', 'No.', 'Horse', 'Jockey', 'Trainer',
            'Assessment', 'Our Win Odds', 'Mkt Win Odds', 'Our Place Odds', 'Mkt Place Odds', 'Top Features'
        ])
        
        # Style table with proper alternating row colors
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_secondary']};
                color: {COLORS['text_primary']};
                gridline-color: {COLORS['border_light']};
                border: none;
            }}
            QTableWidget::item {{
                padding: 8px;
                color: {COLORS['text_primary']};
                background-color: {COLORS['bg_secondary']};
            }}
            QTableWidget::item:alternate {{
                background-color: {COLORS['bg_primary']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_tertiary']};
                color: {COLORS['text_primary']};
                padding: 8px;
                border: 1px solid {COLORS['border_medium']};
                font-weight: bold;
            }}
        """)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Calculate and normalize place probabilities (must sum to 300%)
        raw_place_probs = []
        for pred in predictions:
            raw_prob = self.calculate_place_probability(
                pred['predicted_rank'], 
                len(predictions),
                win_prob=pred['win_probability']
            )
            raw_place_probs.append(raw_prob)
        
        # Normalize to sum to 300%
        total_raw = sum(raw_place_probs)
        if total_raw > 0:
            normalized_place_probs = [(p / total_raw) * 300 for p in raw_place_probs]
        else:
            normalized_place_probs = raw_place_probs
        
        # Populate table
        for i, pred in enumerate(predictions):
            # Rank
            rank_item = QTableWidgetItem(str(pred['predicted_rank']))
            rank_item.setTextAlignment(Qt.AlignCenter)
            if pred['predicted_rank'] == 1:
                rank_item.setBackground(QColor(COLORS['accent_green']))
                rank_item.setForeground(QColor('white'))
            table.setItem(i, 0, rank_item)
            
            # Number
            num_item = QTableWidgetItem(str(pred.get('runner_number', '-')))
            num_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(i, 1, num_item)
            
            # Horse
            horse_item = QTableWidgetItem(pred.get('horse_name', 'Unknown'))
            table.setItem(i, 2, horse_item)
            
            # Jockey
            jockey_item = QTableWidgetItem(pred.get('jockey', 'Unknown'))
            table.setItem(i, 3, jockey_item)
            
            # Trainer
            trainer_item = QTableWidgetItem(pred.get('trainer', 'Unknown'))
            table.setItem(i, 4, trainer_item)
            
            # Assessment (categorical label based on win probability)
            prob = pred['win_probability'] * 100
            assessment = self.get_assessment_label(prob)
            assessment_item = QTableWidgetItem(assessment)
            assessment_item.setTextAlignment(Qt.AlignCenter)
            
            # Color code by assessment
            if prob > 25:
                assessment_item.setForeground(QColor('#5CB85C'))
                assessment_item.setBackground(QColor('#1B4D1B'))
            elif prob > 15:
                assessment_item.setForeground(QColor('#F0AD4E'))
                assessment_item.setBackground(QColor('#4D3A1B'))
            elif prob > 10:
                assessment_item.setForeground(QColor('#5DADE2'))
            else:
                assessment_item.setForeground(QColor(COLORS['text_secondary']))
            
            table.setItem(i, 5, assessment_item)
            
            # Our Win Odds (converted from probability)
            our_win_odds = self.probability_to_odds(pred['win_probability'])
            our_odds_item = QTableWidgetItem(f"{our_win_odds:.2f}" if our_win_odds else "-")
            our_odds_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(i, 6, our_odds_item)
            
            # Market Win Odds
            market_odds = pred.get('market_odds')
            mkt_odds_item = QTableWidgetItem(f"{market_odds:.2f}" if market_odds else "-")
            mkt_odds_item.setTextAlignment(Qt.AlignCenter)
            # Highlight if we have better odds (value bet)
            if market_odds and our_win_odds and market_odds > our_win_odds:
                mkt_odds_item.setForeground(QColor(COLORS['accent_green']))
                mkt_odds_item.setBackground(QColor('#1B4D1B'))
            table.setItem(i, 7, mkt_odds_item)
            
            # Our Place Odds (calculated from place probability)
            place_prob = normalized_place_probs[i] / 100.0  # Convert back to decimal
            our_place_odds = self.probability_to_odds(place_prob)
            our_place_item = QTableWidgetItem(f"{our_place_odds:.2f}" if our_place_odds else "-")
            our_place_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(i, 8, our_place_item)
            
            # Market Place Odds (calculated from market win odds)
            field_size = len(predictions)
            mkt_place_odds = self.calculate_market_place_odds(market_odds, field_size) if market_odds else None
            mkt_place_item = QTableWidgetItem(f"{mkt_place_odds:.2f}" if mkt_place_odds else "-")
            mkt_place_item.setTextAlignment(Qt.AlignCenter)
            # Highlight if we have better place odds (value bet)
            if mkt_place_odds and our_place_odds and mkt_place_odds > our_place_odds:
                mkt_place_item.setForeground(QColor(COLORS['accent_green']))
                mkt_place_item.setBackground(QColor('#1B4D1B'))
            table.setItem(i, 9, mkt_place_item)
            
            # Top Features
            features_text = self.format_top_features(pred.get('top_features', []))
            features_item = QTableWidgetItem(features_text)
            features_item.setForeground(QColor(COLORS['text_secondary']))
            table.setItem(i, 10, features_item)
        
        # Resize columns
        table.resizeColumnsToContents()
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)  # Horse name
        table.horizontalHeader().setSectionResizeMode(10, QHeaderView.Stretch)  # Top Features
        
        return table
    
    def format_top_features(self, top_features):
        """Format top features for display"""
        if not top_features:
            return "N/A"
        
        parts = []
        for feat in top_features[:3]:
            name = feat['feature'].replace('_', ' ').title()
            value = feat['value']
            parts.append(f"{name}: {value:.2f}")
        
        return " | ".join(parts)
    
    def calculate_place_probability(self, rank, total_runners, win_prob=None):
        """
        Estimate place probability (finish in top 3) from win probability.
        
        More realistic formula: place_prob ≈ win_prob * scaling_factor
        The scaling factor accounts for the increased chances of finishing 2nd or 3rd.
        
        Typical relationship:
        - 25-35% win → 75-85% place
        - 15-25% win → 60-75% place
        - 10-15% win → 50-60% place
        - 5-10% win → 30-50% place
        - <5% win → 10-30% place
        """
        if win_prob is not None and win_prob > 0:
            # Use win probability for more accurate estimation
            # Place probability formula: accounts for finishing 1st, 2nd, OR 3rd
            # Roughly: place_prob = win_prob + (1 - win_prob) * (2 / (total_runners - 1))
            
            if win_prob >= 0.20:  # Strong favorites
                return min(95.0, win_prob * 100 * 3.5)
            elif win_prob >= 0.10:  # Good chances
                return min(85.0, win_prob * 100 * 4.5)
            elif win_prob >= 0.05:  # Outside chances
                return min(70.0, win_prob * 100 * 6.0)
            else:  # Longshots
                return min(50.0, win_prob * 100 * 8.0)
        else:
            # Fallback to rank-based heuristic if no win_prob
            if rank == 1:
                return 85.0
            elif rank == 2:
                return 70.0
            elif rank == 3:
                return 55.0
            elif rank <= 5:
                return 40.0 - (rank - 4) * 10
            else:
                return max(10.0, 30.0 - (rank - 6) * 5)
    
    def create_coverage_warning(self, coverage_info):
        """Create warning panel for low RPR/TS coverage"""
        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_secondary']};
                border-left: 4px solid {COLORS['accent_yellow']};
                border-radius: 4px;
                padding: 12px;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(5)
        
        # Warning title
        rpr_pct = coverage_info['rpr_pct']
        has_rpr = coverage_info['has_rpr']
        total = coverage_info['total']
        
        if rpr_pct == 0:
            title = QLabel("⚠️  No RPR/TS Data Available")
            message = (
                f"This race has <b>no RPR or TS ratings</b> for any runner ({total} runners). "
                f"Predictions are based on <b>smart defaults</b> using race class and field statistics. "
                f"<br/><br/>💡 <i>Expect less differentiation between horses - all probabilities will be similar.</i>"
            )
        else:
            title = QLabel(f"⚠️  Limited RPR/TS Data ({rpr_pct:.0f}% coverage)")
            message = (
                f"Only <b>{has_rpr} of {total} runners</b> have RPR ratings. "
                f"Predictions use smart defaults for missing values. "
                f"<br/>💡 <i>Lower data coverage may result in less accurate predictions.</i>"
            )
        
        title.setStyleSheet(f"""
            font-weight: bold;
            color: {COLORS['accent_yellow']};
            font-size: 13px;
        """)
        layout.addWidget(title)
        
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: 11px;
        """)
        layout.addWidget(msg_label)
        
        panel.setLayout(layout)
        return panel
    
    def create_exotics_panel(self, predictions):
        """Create panel showing exotic bet probabilities"""
        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border_medium']};
                border-radius: 6px;
                padding: 15px;
            }}
        """)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("📊 Exotic Bet Probabilities")
        title.setStyleSheet(f"font-weight: bold; color: {COLORS['accent_blue']}; font-size: 13px;")
        layout.addWidget(title)
        
        if len(predictions) < 2:
            no_data = QLabel("Insufficient runners for exotic bets")
            no_data.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
            layout.addWidget(no_data)
            panel.setLayout(layout)
            return panel
        
        # Calculate exotic probabilities
        top_3 = predictions[:3] if len(predictions) >= 3 else predictions
        
        # Exacta (1-2 in correct order)
        exacta_prob = self.calculate_exacta_probability(predictions)
        if len(predictions) >= 2:
            exacta_combo = f"{top_3[0].get('horse_name', '?')} → {top_3[1].get('horse_name', '?')}"
        else:
            exacta_combo = "N/A"
        
        # Trifecta (1-2-3 in correct order)
        trifecta_prob = self.calculate_trifecta_probability(predictions)
        if len(predictions) >= 3:
            trifecta_combo = f"{top_3[0].get('horse_name', '?')} → {top_3[1].get('horse_name', '?')} → {top_3[2].get('horse_name', '?')}"
        else:
            trifecta_combo = "N/A"
        
        # First 4
        first4_prob = self.calculate_first4_probability(predictions)
        
        # Display
        info_layout = QHBoxLayout()
        
        exacta_label = QLabel(
            f"<b>Exacta:</b> {exacta_combo}<br/>"
            f"<span style='color: {COLORS['text_secondary']}'>Probability: {exacta_prob:.2f}%</span>"
        )
        exacta_label.setWordWrap(True)
        info_layout.addWidget(exacta_label)
        
        if len(predictions) >= 3:
            trifecta_label = QLabel(
                f"<b>Trifecta:</b> {trifecta_combo}<br/>"
                f"<span style='color: {COLORS['text_secondary']}'>Probability: {trifecta_prob:.2f}%</span>"
            )
            trifecta_label.setWordWrap(True)
            info_layout.addWidget(trifecta_label)
        
        if len(predictions) >= 4:
            first4_label = QLabel(
                f"<b>First 4:</b> Top 4 in order<br/>"
                f"<span style='color: {COLORS['text_secondary']}'>Probability: {first4_prob:.2f}%</span>"
            )
            first4_label.setWordWrap(True)
            info_layout.addWidget(first4_label)
        
        layout.addLayout(info_layout)
        panel.setLayout(layout)
        return panel
    
    def calculate_exacta_probability(self, predictions):
        """Calculate probability of top 2 finishing 1-2 in order"""
        if len(predictions) < 2:
            return 0.0
        # Simplified: multiply win probs and account for uncertainty
        p1 = predictions[0]['win_probability']
        p2 = predictions[1]['win_probability']
        return p1 * p2 * 100  # Convert to percentage
    
    def calculate_trifecta_probability(self, predictions):
        """Calculate probability of top 3 finishing 1-2-3 in order"""
        if len(predictions) < 3:
            return 0.0
        p1 = predictions[0]['win_probability']
        p2 = predictions[1]['win_probability']
        p3 = predictions[2]['win_probability']
        return p1 * p2 * p3 * 100
    
    def calculate_first4_probability(self, predictions):
        """Calculate probability of top 4 finishing in order"""
        if len(predictions) < 4:
            return 0.0
        p1 = predictions[0]['win_probability']
        p2 = predictions[1]['win_probability']
        p3 = predictions[2]['win_probability']
        p4 = predictions[3]['win_probability']
        return p1 * p2 * p3 * p4 * 100
    
    @Slot()
    def export_predictions(self):
        """Export predictions to CSV file"""
        if not self.current_predictions:
            return
        
        # Get save file path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Predictions",
            f"predictions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow([
                    'Course', 'Time', 'Distance', 'Class', 'Race Name', 'Pattern',
                    'Rank', 'Number', 'Horse', 'Jockey', 'Trainer',
                    'Win Probability %', 'Place Probability %', 'Confidence', 'Value Indicator',
                    'Top Feature 1', 'Top Feature 2', 'Top Feature 3'
                ])
                
                # Write predictions
                for race_pred in self.current_predictions:
                    race_info = race_pred['race_info']
                    predictions = race_pred['predictions']
                    
                    # Sort by win probability (highest first) for correct ranking
                    sorted_preds = sorted(predictions, key=lambda x: x['win_probability'], reverse=True)
                    
                    # Re-assign ranks based on win probability
                    for rank, pred in enumerate(sorted_preds, 1):
                        pred['predicted_rank'] = rank
                    
                    # Calculate and normalize place probabilities (must sum to 300%)
                    raw_place_probs = []
                    for pred in sorted_preds:
                        raw_prob = self.calculate_place_probability(
                            pred['predicted_rank'], 
                            len(predictions),
                            win_prob=pred['win_probability']
                        )
                        raw_place_probs.append(raw_prob)
                    
                    # Normalize to sum to 300%
                    total_raw = sum(raw_place_probs)
                    if total_raw > 0:
                        normalized_place_probs = [(p / total_raw) * 300 for p in raw_place_probs]
                    else:
                        normalized_place_probs = raw_place_probs
                    
                    for i, pred in enumerate(sorted_preds):
                        top_feats = pred.get('top_features', [])
                        
                        # Use normalized place probability
                        place_prob = normalized_place_probs[i]
                        
                        row = [
                            race_info.get('course', ''),
                            race_info.get('time', ''),
                            race_info.get('distance', ''),
                            race_info.get('race_class', ''),
                            race_info.get('race_name', ''),
                            race_info.get('pattern', ''),
                            pred['predicted_rank'],
                            pred.get('runner_number', ''),
                            pred.get('horse_name', ''),
                            pred.get('jockey', ''),
                            pred.get('trainer', ''),
                            f"{pred['win_probability']*100:.2f}",
                            f"{place_prob:.2f}",
                            pred.get('confidence', ''),
                            pred.get('value_indicator', ''),
                            self.format_feature(top_feats[0]) if len(top_feats) > 0 else '',
                            self.format_feature(top_feats[1]) if len(top_feats) > 1 else '',
                            self.format_feature(top_feats[2]) if len(top_feats) > 2 else ''
                        ]
                        writer.writerow(row)
            
            QMessageBox.information(
                self,
                "Export Successful",
                f"Predictions exported to:\n{file_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export predictions:\n{str(e)}"
            )
    
    def format_feature(self, feature_dict):
        """Format single feature for CSV"""
        if not feature_dict:
            return ''
        name = feature_dict['feature'].replace('_', ' ').title()
        value = feature_dict['value']
        return f"{name}: {value:.2f}"
    
    def get_data_coverage(self, race_id):
        """Get RPR/TS data coverage for a race from upcoming_races.db"""
        if not race_id or not self.upcoming_db_path.exists():
            return None
        
        try:
            conn = sqlite3.connect(str(self.upcoming_db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN rpr IS NOT NULL AND rpr != '' AND rpr != '-' THEN 1 END) as has_rpr,
                    COUNT(CASE WHEN ts IS NOT NULL AND ts != '' AND ts != '-' THEN 1 END) as has_ts
                FROM runners
                WHERE race_id = ?
            """, (race_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0] > 0:
                total, has_rpr, has_ts = row
                return {
                    'total': total,
                    'has_rpr': has_rpr,
                    'has_ts': has_ts,
                    'rpr_pct': (has_rpr / total * 100) if total > 0 else 0,
                    'ts_pct': (has_ts / total * 100) if total > 0 else 0
                }
            
            return None
            
        except Exception as e:
            print(f"Error getting coverage for race {race_id}: {e}")
            return None
    
    def get_assessment_label(self, win_percentage: float) -> str:
        """
        Get categorical assessment label based on win percentage
        
        Args:
            win_percentage: Win probability as percentage (0-100)
            
        Returns:
            Assessment label string
        """
        if win_percentage > 25:
            return "Top Pick"
        elif win_percentage > 15:
            return "Strong Chance"
        elif win_percentage > 10:
            return "Good Chance"
        else:
            return "Outsider"
    
    def probability_to_odds(self, probability: float) -> float:
        """
        Convert probability to decimal odds
        
        Args:
            probability: Win probability (0.0 to 1.0)
            
        Returns:
            Decimal odds or None if invalid
        """
        if probability <= 0 or probability >= 1:
            return None
        return 1.0 / probability
    
    def calculate_market_place_odds(self, win_odds: float, field_size: int) -> float:
        """
        Calculate place odds from win odds based on field size
        
        UK convention:
        - 5-7 runners: 1/4 odds
        - 8+ runners: 1/5 odds
        
        Args:
            win_odds: Decimal win odds
            field_size: Number of runners
            
        Returns:
            Place decimal odds or None
        """
        if not win_odds or field_size <= 4:
            return None
        elif field_size <= 7:
            # 1/4 odds: payout = (win_odds - 1) / 4 + 1
            return (win_odds - 1) * 0.25 + 1
        else:
            # 1/5 odds: payout = (win_odds - 1) / 5 + 1
            return (win_odds - 1) * 0.20 + 1
