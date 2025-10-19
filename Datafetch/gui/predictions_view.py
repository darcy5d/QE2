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
        
        # Make card clickable
        card.mousePressEvent = lambda event: self.show_race_detail(race_pred)
        
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        race_info = race_pred['race_info']
        predictions = race_pred['predictions']
        
        # Time and distance
        time = race_info.get('time', '').split()[-1] if race_info.get('time') else 'TBA'
        distance = race_info.get('distance', '')
        race_class = race_info.get('race_class', '')
        
        header = QLabel(f"🏇 {time} | {distance} | {race_class}")
        header.setStyleSheet(f"""
            font-size: 14px;
            font-weight: bold;
            color: {COLORS['accent_blue']};
        """)
        layout.addWidget(header)
        
        # Number of runners
        runner_count = len(predictions)
        runner_label = QLabel(f"{runner_count} runners")
        runner_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
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
    
    def show_race_detail(self, race_pred):
        """Show detailed race view with all runners"""
        self.current_race = race_pred
        
        # Update header
        race_info = race_pred['race_info']
        course = race_info.get('course', 'Unknown')
        time = race_info.get('time', '')
        distance = race_info.get('distance', '')
        race_class = race_info.get('race_class', '')
        
        header_text = f"{course} - {time} | {distance} | {race_class}"
        self.detail_header.setText(header_text)
        
        # Clear and populate table
        while self.detail_table_layout.count():
            item = self.detail_table_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        table = self.create_predictions_table(race_pred['predictions'])
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
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels([
            'Rank', 'No.', 'Horse', 'Jockey', 'Trainer',
            'Win Prob %', 'Top Features'
        ])
        
        # Style table
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_secondary']};
                color: {COLORS['text_primary']};
                gridline-color: #555;
                border: none;
            }}
            QTableWidget::item {{
                padding: 8px;
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_tertiary']};
                color: {COLORS['text_primary']};
                padding: 8px;
                border: 1px solid #555;
                font-weight: bold;
            }}
        """)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        
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
            
            # Win Probability
            prob = pred['win_probability'] * 100
            prob_item = QTableWidgetItem(f"{prob:.1f}%")
            prob_item.setTextAlignment(Qt.AlignCenter)
            
            # Color code by probability
            if prob > 25:
                prob_item.setForeground(QColor('#5CB85C'))
            elif prob > 15:
                prob_item.setForeground(QColor('#F0AD4E'))
            else:
                prob_item.setForeground(QColor(COLORS['text_secondary']))
            
            # Add value indicator
            if pred.get('value_indicator'):
                prob_item.setText(f"{prob:.1f}% {pred['value_indicator']}")
            
            table.setItem(i, 5, prob_item)
            
            # Top Features
            features_text = self.format_top_features(pred.get('top_features', []))
            features_item = QTableWidgetItem(features_text)
            features_item.setForeground(QColor(COLORS['text_secondary']))
            table.setItem(i, 6, features_item)
        
        # Resize columns
        table.resizeColumnsToContents()
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        
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
                    'Course', 'Time', 'Distance', 'Class',
                    'Rank', 'Number', 'Horse', 'Jockey', 'Trainer',
                    'Win Probability %', 'Confidence', 'Value Indicator',
                    'Top Feature 1', 'Top Feature 2', 'Top Feature 3'
                ])
                
                # Write predictions
                for race_pred in self.current_predictions:
                    race_info = race_pred['race_info']
                    for pred in race_pred['predictions']:
                        top_feats = pred.get('top_features', [])
                        
                        row = [
                            race_info.get('course', ''),
                            race_info.get('time', ''),
                            race_info.get('distance', ''),
                            race_info.get('race_class', ''),
                            pred['predicted_rank'],
                            pred.get('runner_number', ''),
                            pred.get('horse_name', ''),
                            pred.get('jockey', ''),
                            pred.get('trainer', ''),
                            f"{pred['win_probability']*100:.2f}",
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
