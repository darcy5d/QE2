"""
Profile View for displaying entity details (Horse, Trainer, Jockey, Owner)
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton,
                                QTableWidget, QTableWidgetItem, QHeaderView,
                                QScrollArea, QHBoxLayout)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont
from typing import Dict, Any

from PySide6.QtGui import QColor, QCursor

from .racecard_view import ClickableLabel


class ProfileView(QWidget):
    """Widget to display entity profiles"""
    
    # Signals
    back_clicked = Signal()
    entity_clicked = Signal(str, str, str)  # entity_type, entity_id, entity_name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the profile view UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Back button
        button_layout = QHBoxLayout()
        self.back_button = QPushButton("← Back to Racecard")
        self.back_button.clicked.connect(self.back_clicked.emit)
        self.back_button.setMaximumWidth(200)
        button_layout.addWidget(self.back_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Create scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Content widget
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(15)
        self.content_widget.setLayout(self.content_layout)
        
        scroll.setWidget(self.content_widget)
        layout.addWidget(scroll)
        
        self.setLayout(layout)
    
    def clear(self):
        """Clear all content"""
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def display_profile(self, entity_type: str, profile_data: Dict[str, Any]):
        """Display profile based on entity type"""
        self.clear()
        
        if not profile_data:
            error_label = QLabel(f"{entity_type.capitalize()} not found")
            error_label.setAlignment(Qt.AlignCenter)
            self.content_layout.addWidget(error_label)
            return
        
        if entity_type == 'horse':
            self.display_horse_profile(profile_data)
        elif entity_type == 'trainer':
            self.display_trainer_profile(profile_data)
        elif entity_type == 'jockey':
            self.display_jockey_profile(profile_data)
        elif entity_type == 'owner':
            self.display_owner_profile(profile_data)
    
    def display_horse_profile(self, horse: Dict[str, Any]):
        """Display horse profile"""
        # Header
        header = QLabel(f"HORSE: {horse.get('name', 'Unknown')}")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        self.content_layout.addWidget(header)
        
        # Separator
        separator = QLabel("═" * 80)
        separator.setStyleSheet("color: #333;")
        self.content_layout.addWidget(separator)
        
        # Basic info
        info_parts = []
        if horse.get('age'):
            info_parts.append(f"Age: {horse['age']}yo")
        if horse.get('sex'):
            info_parts.append(f"Sex: {horse['sex']}")
        if horse.get('colour'):
            info_parts.append(f"Colour: {horse['colour']}")
        
        if info_parts:
            info_label = QLabel("  |  ".join(info_parts))
            self.content_layout.addWidget(info_label)
        
        if horse.get('region'):
            region_label = QLabel(f"Region: {horse['region']}")
            self.content_layout.addWidget(region_label)
        
        self.content_layout.addSpacing(10)
        
        # Pedigree section
        pedigree_header = QLabel("PEDIGREE:")
        pedigree_header_font = QFont()
        pedigree_header_font.setBold(True)
        pedigree_header.setFont(pedigree_header_font)
        self.content_layout.addWidget(pedigree_header)
        
        if horse.get('sire_name'):
            sire_label = QLabel(f"Sire (Father): {horse['sire_name']}")
            self.content_layout.addWidget(sire_label)
        
        if horse.get('dam_name'):
            dam_label = QLabel(f"Dam (Mother): {horse['dam_name']}")
            self.content_layout.addWidget(dam_label)
        
        if horse.get('damsire_name'):
            damsire_label = QLabel(f"Damsire (Maternal Grandsire): {horse['damsire_name']}")
            self.content_layout.addWidget(damsire_label)
        
        if horse.get('breeder'):
            breeder_label = QLabel(f"Breeder: {horse['breeder']}")
            self.content_layout.addWidget(breeder_label)
        
        self.content_layout.addSpacing(10)
        
        # Recent runs
        runs = horse.get('runs', [])
        if runs:
            runs_header = QLabel(f"RECENT RUNS IN DATASET ({len(runs)} runs):")
            runs_header_font = QFont()
            runs_header_font.setBold(True)
            runs_header.setFont(runs_header_font)
            self.content_layout.addWidget(runs_header)
            
            # Create table
            table = QTableWidget()
            table.setColumnCount(6)
            table.setHorizontalHeaderLabels(['Date', 'Course', 'Race', 'Trainer', 'Jockey', 'No.'])
            table.setRowCount(len(runs))
            
            # Set column widths
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
            table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
            
            for row, run in enumerate(runs):
                date_item = QTableWidgetItem(str(run.get('date', '')))
                date_item.setForeground(QColor('white'))
                table.setItem(row, 0, date_item)
                
                course_item = QTableWidgetItem(str(run.get('course', '')))
                course_item.setForeground(QColor('white'))
                table.setItem(row, 1, course_item)
                
                race_item = QTableWidgetItem(str(run.get('race_name', '')))
                race_item.setForeground(QColor('white'))
                table.setItem(row, 2, race_item)
                
                trainer_item = QTableWidgetItem(str(run.get('trainer_name', '')))
                trainer_item.setForeground(QColor('white'))
                table.setItem(row, 3, trainer_item)
                
                jockey_item = QTableWidgetItem(str(run.get('jockey_name', '')))
                jockey_item.setForeground(QColor('white'))
                table.setItem(row, 4, jockey_item)
                
                number_item = QTableWidgetItem(str(run.get('number', '')))
                number_item.setTextAlignment(Qt.AlignCenter)
                number_item.setForeground(QColor('white'))
                table.setItem(row, 5, number_item)
                
                table.setRowHeight(row, 25)
            
            table.setAlternatingRowColors(True)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setSelectionMode(QTableWidget.SingleSelection)
            table.verticalHeader().setVisible(False)
            
            self.content_layout.addWidget(table)
        
        self.content_layout.addStretch()
    
    def display_trainer_profile(self, trainer: Dict[str, Any]):
        """Display trainer profile"""
        # Header
        header = QLabel(f"TRAINER: {trainer.get('name', 'Unknown')}")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        self.content_layout.addWidget(header)
        
        # Separator
        separator = QLabel("═" * 80)
        separator.setStyleSheet("color: #333;")
        self.content_layout.addWidget(separator)
        
        # Basic info
        if trainer.get('location'):
            location_label = QLabel(f"Location: {trainer['location']}")
            self.content_layout.addWidget(location_label)
        
        if trainer.get('runner_count'):
            count_label = QLabel(f"Runners in dataset: {trainer['runner_count']}")
            self.content_layout.addWidget(count_label)
        
        self.content_layout.addSpacing(10)
        
        # 14-day stats if available
        stats_14 = trainer.get('stats_14_days', {})
        if stats_14:
            stats_header = QLabel("14-DAY STATISTICS:")
            stats_header_font = QFont()
            stats_header_font.setBold(True)
            stats_header.setFont(stats_header_font)
            self.content_layout.addWidget(stats_header)
            
            for key, value in stats_14.items():
                stat_label = QLabel(f"{key}: {value}")
                self.content_layout.addWidget(stat_label)
            
            self.content_layout.addSpacing(10)
        
        # Recent runners
        runners = trainer.get('recent_runners', [])
        if runners:
            runners_header = QLabel(f"RECENT RUNNERS ({len(runners)}):")
            runners_header_font = QFont()
            runners_header_font.setBold(True)
            runners_header.setFont(runners_header_font)
            self.content_layout.addWidget(runners_header)
            
            # Create table
            table = QTableWidget()
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels(['Date', 'Course', 'Horse', 'Jockey', 'No.'])
            table.setRowCount(len(runners))
            
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
            table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
            
            for row, runner in enumerate(runners):
                date_item = QTableWidgetItem(str(runner.get('date', '')))
                date_item.setForeground(QColor('white'))
                table.setItem(row, 0, date_item)
                
                course_item = QTableWidgetItem(str(runner.get('course', '')))
                course_item.setForeground(QColor('white'))
                table.setItem(row, 1, course_item)
                
                # Horse name - clickable
                horse_name = runner.get('horse_name', 'Unknown')
                horse_label = ClickableLabel(
                    horse_name,
                    'horse',
                    runner.get('horse_id', ''),
                    horse_name
                )
                horse_label.clicked.connect(self.entity_clicked.emit)
                table.setCellWidget(row, 2, horse_label)
                
                jockey_item = QTableWidgetItem(str(runner.get('jockey_name', '')))
                jockey_item.setForeground(QColor('white'))
                table.setItem(row, 3, jockey_item)
                
                number_item = QTableWidgetItem(str(runner.get('number', '')))
                number_item.setTextAlignment(Qt.AlignCenter)
                number_item.setForeground(QColor('white'))
                table.setItem(row, 4, number_item)
                
                table.setRowHeight(row, 25)
            
            table.setAlternatingRowColors(True)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setSelectionMode(QTableWidget.SingleSelection)
            table.verticalHeader().setVisible(False)
            
            self.content_layout.addWidget(table)
        
        self.content_layout.addStretch()
    
    def display_jockey_profile(self, jockey: Dict[str, Any]):
        """Display jockey profile"""
        # Header
        header = QLabel(f"JOCKEY: {jockey.get('name', 'Unknown')}")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        self.content_layout.addWidget(header)
        
        # Separator
        separator = QLabel("═" * 80)
        separator.setStyleSheet("color: #333;")
        self.content_layout.addWidget(separator)
        
        # Basic info
        if jockey.get('ride_count'):
            count_label = QLabel(f"Rides in dataset: {jockey['ride_count']}")
            self.content_layout.addWidget(count_label)
        
        self.content_layout.addSpacing(10)
        
        # Recent rides
        rides = jockey.get('recent_rides', [])
        if rides:
            rides_header = QLabel(f"RECENT RIDES ({len(rides)}):")
            rides_header_font = QFont()
            rides_header_font.setBold(True)
            rides_header.setFont(rides_header_font)
            self.content_layout.addWidget(rides_header)
            
            # Create table
            table = QTableWidget()
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels(['Date', 'Course', 'Horse', 'Trainer', 'No.'])
            table.setRowCount(len(rides))
            
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
            table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
            
            for row, ride in enumerate(rides):
                date_item = QTableWidgetItem(str(ride.get('date', '')))
                date_item.setForeground(QColor('white'))
                table.setItem(row, 0, date_item)
                
                course_item = QTableWidgetItem(str(ride.get('course', '')))
                course_item.setForeground(QColor('white'))
                table.setItem(row, 1, course_item)
                
                # Horse name - clickable
                horse_name = ride.get('horse_name', 'Unknown')
                horse_label = ClickableLabel(
                    horse_name,
                    'horse',
                    ride.get('horse_id', ''),
                    horse_name
                )
                horse_label.clicked.connect(self.entity_clicked.emit)
                table.setCellWidget(row, 2, horse_label)
                
                trainer_item = QTableWidgetItem(str(ride.get('trainer_name', '')))
                trainer_item.setForeground(QColor('white'))
                table.setItem(row, 3, trainer_item)
                
                number_item = QTableWidgetItem(str(ride.get('number', '')))
                number_item.setTextAlignment(Qt.AlignCenter)
                number_item.setForeground(QColor('white'))
                table.setItem(row, 4, number_item)
                
                table.setRowHeight(row, 25)
            
            table.setAlternatingRowColors(True)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setSelectionMode(QTableWidget.SingleSelection)
            table.verticalHeader().setVisible(False)
            
            self.content_layout.addWidget(table)
        
        self.content_layout.addStretch()
    
    def display_owner_profile(self, owner: Dict[str, Any]):
        """Display owner profile"""
        # Header
        header = QLabel(f"OWNER: {owner.get('name', 'Unknown')}")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        self.content_layout.addWidget(header)
        
        # Separator
        separator = QLabel("═" * 80)
        separator.setStyleSheet("color: #333;")
        self.content_layout.addWidget(separator)
        
        # Basic info
        if owner.get('horse_count'):
            count_label = QLabel(f"Horses in dataset: {owner['horse_count']}")
            self.content_layout.addWidget(count_label)
        
        self.content_layout.addSpacing(10)
        
        # Recent runners
        runners = owner.get('recent_runners', [])
        if runners:
            runners_header = QLabel(f"RECENT RUNNERS ({len(runners)}):")
            runners_header_font = QFont()
            runners_header_font.setBold(True)
            runners_header.setFont(runners_header_font)
            self.content_layout.addWidget(runners_header)
            
            # Create table
            table = QTableWidget()
            table.setColumnCount(6)
            table.setHorizontalHeaderLabels(['Date', 'Course', 'Horse', 'Trainer', 'Jockey', 'No.'])
            table.setRowCount(len(runners))
            
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
            table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
            
            for row, runner in enumerate(runners):
                date_item = QTableWidgetItem(str(runner.get('date', '')))
                date_item.setForeground(QColor('white'))
                table.setItem(row, 0, date_item)
                
                course_item = QTableWidgetItem(str(runner.get('course', '')))
                course_item.setForeground(QColor('white'))
                table.setItem(row, 1, course_item)
                
                # Horse name - clickable
                horse_name = runner.get('horse_name', 'Unknown')
                horse_label = ClickableLabel(
                    horse_name,
                    'horse',
                    runner.get('horse_id', ''),
                    horse_name
                )
                horse_label.clicked.connect(self.entity_clicked.emit)
                table.setCellWidget(row, 2, horse_label)
                
                trainer_item = QTableWidgetItem(str(runner.get('trainer_name', '')))
                trainer_item.setForeground(QColor('white'))
                table.setItem(row, 3, trainer_item)
                
                jockey_item = QTableWidgetItem(str(runner.get('jockey_name', '')))
                jockey_item.setForeground(QColor('white'))
                table.setItem(row, 4, jockey_item)
                
                number_item = QTableWidgetItem(str(runner.get('number', '')))
                number_item.setTextAlignment(Qt.AlignCenter)
                number_item.setForeground(QColor('white'))
                table.setItem(row, 5, number_item)
                
                table.setRowHeight(row, 25)
            
            table.setAlternatingRowColors(True)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setSelectionMode(QTableWidget.SingleSelection)
            table.verticalHeader().setVisible(False)
            
            self.content_layout.addWidget(table)
        
        self.content_layout.addStretch()

