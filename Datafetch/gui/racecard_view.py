"""
Racecard View for displaying race details and runners
Formatted like a traditional paper racecard
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTableWidget,
                                QTableWidgetItem, QHeaderView, QScrollArea)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont, QColor, QCursor
from typing import Dict, Any, Optional


class ClickableLabel(QLabel):
    """Label that emits a signal when clicked"""
    clicked = Signal(str, str, str)  # entity_type, entity_id, entity_name
    
    def __init__(self, text: str, entity_type: str, entity_id: str, entity_name: str, parent=None):
        super().__init__(text, parent)
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.entity_name = entity_name
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setStyleSheet("color: white; text-decoration: underline;")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.entity_type, self.entity_id, self.entity_name)


class RacecardView(QWidget):
    """Widget to display racecard details like a paper racecard"""
    
    # Signals
    entity_clicked = Signal(str, str, str)  # entity_type, entity_id, entity_name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the racecard view UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
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
        self.show_placeholder()
    
    def show_placeholder(self):
        """Show placeholder text when no race is selected"""
        self.clear()
        
        label = QLabel("Select a race from the navigation panel to view details")
        label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(12)
        label.setFont(font)
        label.setStyleSheet("color: gray;")
        
        self.content_layout.addStretch()
        self.content_layout.addWidget(label)
        self.content_layout.addStretch()
    
    def clear(self):
        """Clear all content"""
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def display_race(self, race_data: Dict[str, Any]):
        """Display race details"""
        self.clear()
        
        if not race_data:
            self.show_placeholder()
            return
        
        # ====================================================================
        # HEADER SECTION
        # ====================================================================
        
        # Course and Date line
        header_text = f"{race_data.get('course', 'Unknown Course')} - {race_data.get('date', '')}"
        if race_data.get('off_time'):
            header_text += f"          {race_data.get('off_time')}"
        
        header_label = QLabel(header_text)
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        self.content_layout.addWidget(header_label)
        
        # Race Name
        race_name = QLabel(race_data.get('race_name', 'Unknown Race'))
        race_name_font = QFont()
        race_name_font.setPointSize(12)
        race_name_font.setBold(True)
        race_name.setFont(race_name_font)
        self.content_layout.addWidget(race_name)
        
        # Separator line
        separator = QLabel("═" * 80)
        separator.setStyleSheet("color: #333;")
        self.content_layout.addWidget(separator)
        
        # ====================================================================
        # RACE DETAILS SECTION
        # ====================================================================
        
        details_parts = []
        
        if race_data.get('distance'):
            details_parts.append(f"Distance: {race_data['distance']}")
        
        if race_data.get('going'):
            details_parts.append(f"Going: {race_data['going']}")
        
        if race_data.get('race_class'):
            details_parts.append(f"Class: {race_data['race_class']}")
        
        if race_data.get('prize'):
            details_parts.append(f"Prize: {race_data['prize']}")
        
        if details_parts:
            details_line1 = QLabel("  |  ".join(details_parts[:2]))
            self.content_layout.addWidget(details_line1)
            
            if len(details_parts) > 2:
                details_line2 = QLabel("  |  ".join(details_parts[2:]))
                self.content_layout.addWidget(details_line2)
        
        # Surface and field size
        extra_parts = []
        
        if race_data.get('surface'):
            extra_parts.append(f"Surface: {race_data['surface']}")
        
        if race_data.get('field_size'):
            extra_parts.append(f"Field: {race_data['field_size']} runners")
        
        if extra_parts:
            extra_label = QLabel("  |  ".join(extra_parts))
            self.content_layout.addWidget(extra_label)
        
        self.content_layout.addSpacing(10)
        
        # ====================================================================
        # RUNNERS TABLE
        # ====================================================================
        
        runners = race_data.get('runners', [])
        
        if runners:
            table = QTableWidget()
            table.setColumnCount(6)
            table.setHorizontalHeaderLabels(['No.', 'Horse', 'Trainer', 'Jockey', 'Draw', 'Weight'])
            table.setRowCount(len(runners))
            
            # Set column widths
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)  # No.
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # Horse
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)  # Trainer
            table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)  # Jockey
            table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Draw
            table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Weight
            
            # Populate table
            for row, runner in enumerate(runners):
                # Number
                number_item = QTableWidgetItem(str(runner.get('number', '')))
                number_item.setTextAlignment(Qt.AlignCenter)
                number_item.setForeground(QColor('white'))
                table.setItem(row, 0, number_item)
                
                # Horse (clickable)
                horse_name = runner.get('horse_name', 'Unknown')
                horse_label = ClickableLabel(
                    horse_name,
                    'horse',
                    runner.get('horse_id', ''),
                    horse_name
                )
                horse_label.clicked.connect(self.entity_clicked.emit)
                table.setCellWidget(row, 1, horse_label)
                
                # Trainer (clickable)
                trainer_name = runner.get('trainer_name', 'Unknown')
                trainer_label = ClickableLabel(
                    trainer_name,
                    'trainer',
                    runner.get('trainer_id', ''),
                    trainer_name
                )
                trainer_label.clicked.connect(self.entity_clicked.emit)
                table.setCellWidget(row, 2, trainer_label)
                
                # Jockey (clickable)
                jockey_name = runner.get('jockey_name', 'Unknown')
                jockey_label = ClickableLabel(
                    jockey_name,
                    'jockey',
                    runner.get('jockey_id', ''),
                    jockey_name
                )
                jockey_label.clicked.connect(self.entity_clicked.emit)
                table.setCellWidget(row, 3, jockey_label)
                
                # Draw
                draw_item = QTableWidgetItem(str(runner.get('draw', '')))
                draw_item.setTextAlignment(Qt.AlignCenter)
                draw_item.setForeground(QColor('white'))
                table.setItem(row, 4, draw_item)
                
                # Weight
                weight_item = QTableWidgetItem(str(runner.get('lbs', '')))
                weight_item.setTextAlignment(Qt.AlignCenter)
                weight_item.setForeground(QColor('white'))
                table.setItem(row, 5, weight_item)
                
                # Set row height
                table.setRowHeight(row, 30)
            
            # Table styling
            table.setAlternatingRowColors(True)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setSelectionMode(QTableWidget.NoSelection)
            table.verticalHeader().setVisible(False)
            
            self.content_layout.addWidget(table)
        
        else:
            no_runners_label = QLabel("No runner information available")
            no_runners_label.setStyleSheet("color: gray; font-style: italic;")
            self.content_layout.addWidget(no_runners_label)
        
        # ====================================================================
        # ADDITIONAL INFO
        # ====================================================================
        
        if race_data.get('going_detailed'):
            self.content_layout.addSpacing(10)
            going_label = QLabel(f"Going Details: {race_data['going_detailed']}")
            going_label.setWordWrap(True)
            going_label.setStyleSheet("font-style: italic;")
            self.content_layout.addWidget(going_label)
        
        if race_data.get('verdict'):
            self.content_layout.addSpacing(5)
            verdict_label = QLabel(f"Verdict: {race_data['verdict']}")
            verdict_label.setWordWrap(True)
            verdict_label.setStyleSheet("font-style: italic;")
            self.content_layout.addWidget(verdict_label)
        
        self.content_layout.addStretch()

