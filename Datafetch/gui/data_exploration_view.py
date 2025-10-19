"""
Data Exploration View - Comprehensive statistical analysis interface
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                QPushButton, QListWidget, QListWidgetItem,
                                QScrollArea, QFrame, QGroupBox, QFileDialog,
                                QMessageBox)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont

from .database import DatabaseHelper
from .stats_calculator import StatsCalculator


class DataExplorationView(QWidget):
    """Data exploration interface with table browser and statistics"""
    
    def __init__(self, db_helper: DatabaseHelper, parent=None):
        super().__init__(parent)
        self.db = db_helper
        self.stats_calc = StatsCalculator(db_helper)
        self.current_table = None
        self.setup_ui()
        self.load_tables()
    
    def setup_ui(self):
        """Setup the data exploration UI"""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Left panel - Table list
        left_panel = QFrame()
        left_panel.setMaximumWidth(250)
        left_panel.setStyleSheet("""
            QFrame {
                background-color: #2A2A2A;
                border-right: 1px solid #555;
            }
        """)
        
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        tables_label = QLabel("TABLES")
        tables_font = QFont()
        tables_font.setBold(True)
        tables_font.setPointSize(14)
        tables_label.setFont(tables_font)
        tables_label.setStyleSheet("color: white; padding: 10px;")
        left_layout.addWidget(tables_label)
        
        # Refresh button
        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_data)
        left_layout.addWidget(refresh_btn)
        
        # Table list
        self.table_list = QListWidget()
        self.table_list.setStyleSheet("""
            QListWidget {
                background-color: #333;
                color: white;
                border: none;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #444;
            }
            QListWidget::item:selected {
                background-color: #4A90E2;
            }
            QListWidget::item:hover {
                background-color: #3A3A3A;
            }
        """)
        self.table_list.itemClicked.connect(self.on_table_selected)
        left_layout.addWidget(self.table_list)
        
        left_panel.setLayout(left_layout)
        layout.addWidget(left_panel)
        
        # Right panel - Statistics display
        right_panel = QFrame()
        right_panel.setStyleSheet("background-color: #1E1E1E;")
        
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        self.title_label = QLabel("DATA EXPLORATION")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(20)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color: white; padding: 10px;")
        right_layout.addWidget(self.title_label)
        
        # Separator
        separator = QLabel("═" * 80)
        separator.setStyleSheet("color: #555;")
        right_layout.addWidget(separator)
        
        # Scroll area for content
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
        self.content_layout.setSpacing(15)
        self.content_widget.setLayout(self.content_layout)
        
        scroll.setWidget(self.content_widget)
        right_layout.addWidget(scroll)
        
        right_panel.setLayout(right_layout)
        layout.addWidget(right_panel)
        
        self.setLayout(layout)
    
    def load_tables(self):
        """Load list of tables"""
        self.table_list.clear()
        tables = self.stats_calc.get_table_list()
        
        for table_name, row_count in tables:
            item_text = f"{table_name} ({row_count:,} rows)"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, table_name)
            self.table_list.addItem(item)
    
    @Slot()
    def refresh_data(self):
        """Refresh data from database"""
        # Reconnect to database
        import sqlite3
        self.db.conn.close()
        self.db.conn = sqlite3.connect(str(self.db.db_path))
        self.db.conn.row_factory = sqlite3.Row
        
        # Recreate stats calculator
        from .stats_calculator import StatsCalculator
        self.stats_calc = StatsCalculator(self.db)
        
        # Reload tables
        self.load_tables()
        
        # Clear current display
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Show refresh message
        refresh_label = QLabel("Data refreshed! Select a table to view statistics.")
        refresh_label.setStyleSheet("color: #4A90E2; font-size: 16px; padding: 20px;")
        self.content_layout.addWidget(refresh_label)
        self.content_layout.addStretch()
    
    @Slot(QListWidgetItem)
    def on_table_selected(self, item):
        """Handle table selection"""
        table_name = item.data(Qt.UserRole)
        self.current_table = table_name
        self.display_table_stats(table_name)
    
    def display_table_stats(self, table_name: str):
        """Display comprehensive statistics for selected table"""
        # Clear existing content
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Get table info
        table_info = self.stats_calc.get_table_info(table_name)
        
        # Table overview
        overview_group = self.create_section("TABLE OVERVIEW")
        overview_layout = QVBoxLayout()
        
        overview_text = f"""
Table: {table_info['table_name']}
Total Rows: {table_info['row_count']:,}
Total Columns: {table_info['column_count']}
        """.strip()
        
        if table_info['date_range']:
            col_name, min_date, max_date = table_info['date_range']
            overview_text += f"\nDate Range: {min_date} to {max_date}"
        
        overview_label = QLabel(overview_text)
        overview_label.setStyleSheet("color: white; font-size: 14px; padding: 10px;")
        overview_layout.addWidget(overview_label)
        
        # Export button
        export_btn = QPushButton("Export Table Stats to CSV")
        export_btn.clicked.connect(lambda: self.export_table_stats(table_name))
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
        """)
        overview_layout.addWidget(export_btn)
        
        overview_group.setLayout(overview_layout)
        self.content_layout.addWidget(overview_group)
        
        # Column analysis
        columns_group = self.create_section("COLUMN ANALYSIS")
        columns_layout = QVBoxLayout()
        
        for col_name, col_type in table_info['columns']:
            col_widget = self.create_column_widget(table_name, col_name, col_type)
            columns_layout.addWidget(col_widget)
        
        columns_group.setLayout(columns_layout)
        self.content_layout.addWidget(columns_group)
        
        self.content_layout.addStretch()
    
    def create_section(self, title: str) -> QGroupBox:
        """Create a section group box"""
        group = QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #555;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        return group
    
    def create_column_widget(self, table_name: str, col_name: str, col_type: str) -> QFrame:
        """Create widget displaying column statistics"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #2A2A2A;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Column header
        header = QLabel(f"▸ {col_name}")
        header_font = QFont()
        header_font.setBold(True)
        header_font.setPointSize(13)
        header.setFont(header_font)
        header.setStyleSheet("color: #4A90E2; padding: 5px;")
        header.setCursor(Qt.PointingHandCursor)
        layout.addWidget(header)
        
        # Stats container (collapsible)
        stats_container = QFrame()
        stats_layout = QVBoxLayout()
        
        # Get statistics
        stats = self.stats_calc.analyze_column(table_name, col_name)
        
        # Display basic info
        basic_info = f"""
Type: {stats['data_type']}
Total: {stats['total_count']:,} | Non-null: {stats['non_null_count']:,} | Null: {stats['null_count']:,} ({stats['null_percentage']}%)
Unique Values: {stats['unique_count']:,}
        """.strip()
        
        basic_label = QLabel(basic_info)
        basic_label.setStyleSheet("color: #CCC; font-size: 12px; padding: 5px;")
        stats_layout.addWidget(basic_label)
        
        # Type-specific statistics
        if stats.get('analysis_type') == 'numeric':
            numeric_info = f"""
Mean: {stats['mean']} | Median: {stats['median']} | Mode: {stats.get('mode', 'N/A')}
Std Dev: {stats['std_dev']} | Skewness: {stats['skewness']}
Min: {stats['min']} | Q1: {stats['q1']} | Q3: {stats['q3']} | Max: {stats['max']}
Range: {stats['range']}
            """.strip()
            
            numeric_label = QLabel(numeric_info)
            numeric_label.setStyleSheet("color: #9EE09E; font-size: 12px; padding: 5px;")
            stats_layout.addWidget(numeric_label)
        
        elif stats.get('analysis_type') == 'text':
            text_info = "Most Common Values:\n"
            for val, freq in stats['most_common'][:10]:
                percentage = (freq / stats['non_null_count'] * 100) if stats['non_null_count'] > 0 else 0
                text_info += f"  • {val}: {freq:,} ({percentage:.1f}%)\n"
            
            text_info += f"\nLength: Min={stats['min_length']} | Avg={stats['avg_length']} | Max={stats['max_length']}"
            
            text_label = QLabel(text_info)
            text_label.setStyleSheet("color: #FFE4B5; font-size: 12px; padding: 5px;")
            stats_layout.addWidget(text_label)
        
        elif stats.get('analysis_type') == 'date':
            date_info = f"Date Range: {stats['min_date']} to {stats['max_date']}\n"
            
            if stats.get('monthly_distribution'):
                date_info += "\nMonthly Distribution:\n"
                for month, count in stats['monthly_distribution'][:6]:
                    date_info += f"  • {month}: {count:,}\n"
            
            date_label = QLabel(date_info)
            date_label.setStyleSheet("color: #ADD8E6; font-size: 12px; padding: 5px;")
            stats_layout.addWidget(date_label)
        
        # Export button for column
        export_col_btn = QPushButton("Export Column Stats (JSON)")
        export_col_btn.clicked.connect(lambda: self.export_column_stats(table_name, col_name))
        export_col_btn.setStyleSheet("""
            QPushButton {
                background-color: #555;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 5px 10px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #666;
            }
        """)
        stats_layout.addWidget(export_col_btn)
        
        stats_container.setLayout(stats_layout)
        layout.addWidget(stats_container)
        
        frame.setLayout(layout)
        return frame
    
    @Slot()
    def export_table_stats(self, table_name: str):
        """Export table statistics to CSV"""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Table Statistics",
            f"{table_name}_stats.csv",
            "CSV Files (*.csv)"
        )
        
        if filepath:
            try:
                self.stats_calc.export_table_stats_csv(table_name, filepath)
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Table statistics exported to:\n{filepath}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"Error exporting statistics:\n{str(e)}"
                )
    
    @Slot()
    def export_column_stats(self, table_name: str, column_name: str):
        """Export column statistics to JSON"""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Column Statistics",
            f"{table_name}_{column_name}_stats.json",
            "JSON Files (*.json)"
        )
        
        if filepath:
            try:
                self.stats_calc.export_column_stats_json(table_name, column_name, filepath)
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Column statistics exported to:\n{filepath}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"Error exporting statistics:\n{str(e)}"
                )

