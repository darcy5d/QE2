"""
ML Features View - Explore engineered ML features
Shows statistics, sample data, and quality metrics
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                QPushButton, QTableWidget, QTableWidgetItem,
                                QTabWidget, QFrame, QLineEdit, QMessageBox,
                                QFileDialog, QHeaderView, QGroupBox, QGridLayout,
                                QProgressBar)
from PySide6.QtCore import Qt, Slot, QThread, Signal
from PySide6.QtGui import QFont
import pandas as pd
from pathlib import Path

from .database import DatabaseHelper
from .ml_database_helper import MLDatabaseHelper


class LoadStatsWorker(QThread):
    """Background worker for loading statistics"""
    stats_loaded = Signal(object)  # pd.DataFrame
    error_occurred = Signal(str)
    
    def __init__(self, ml_db: MLDatabaseHelper):
        super().__init__()
        self.ml_db = ml_db
    
    def run(self):
        print("LoadStatsWorker.run() started")
        try:
            print("Calling get_feature_statistics()...")
            stats_df = self.ml_db.get_feature_statistics()
            print(f"Statistics loaded: {len(stats_df)} rows")
            print("Emitting stats_loaded signal...")
            self.stats_loaded.emit(stats_df)
            print("Signal emitted")
        except Exception as e:
            print(f"Error in worker: {e}")
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(str(e))


class MLFeaturesView(QWidget):
    """ML Features exploration interface"""
    
    def __init__(self, db_helper: DatabaseHelper, parent=None):
        super().__init__(parent)
        self.db = db_helper
        self.ml_db = MLDatabaseHelper(db_helper.db_path)
        self.current_page = 0
        self.page_size = 50
        self.search_term = None
        self.stats_df = None
        
        self.setup_ui()
        self.check_features_exist()
    
    def check_features_exist(self):
        """Check if ML features exist in database"""
        try:
            count = self.ml_db.get_feature_count()
            if count == 0:
                self.show_no_features_message()
        except Exception as e:
            self.show_error_message(f"Error checking features: {e}")
    
    def show_no_features_message(self):
        """Show message when no features exist"""
        msg = QLabel(
            "No ML features found.\n\n"
            "Please run feature generation first:\n"
            "python ml/feature_engineer.py"
        )
        msg.setAlignment(Qt.AlignCenter)
        msg.setStyleSheet("color: white; font-size: 14px; padding: 50px;")
        
        # Clear and show message
        for i in reversed(range(self.layout().count())):
            self.layout().itemAt(i).widget().setVisible(False)
        self.layout().addWidget(msg)
    
    def show_error_message(self, error: str):
        """Show error message"""
        QMessageBox.warning(self, "Error", error)
    
    def setup_ui(self):
        """Setup the ML features UI"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("ML Features Explorer")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: white;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_all_tabs)
        header_layout.addWidget(refresh_btn)
        
        main_layout.addLayout(header_layout)
        
        # Tab widget for different views
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #2A2A2A;
            }
            QTabBar::tab {
                background-color: #3A3A3A;
                color: white;
                padding: 10px 20px;
                border: 1px solid #555;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #4A90E2;
            }
            QTabBar::tab:hover {
                background-color: #4A4A4A;
            }
        """)
        
        # Create tabs
        self.statistics_tab = self.create_statistics_tab()
        self.sample_data_tab = self.create_sample_data_tab()
        self.quality_tab = self.create_quality_metrics_tab()
        
        self.tab_widget.addTab(self.statistics_tab, "📊 Statistics")
        self.tab_widget.addTab(self.sample_data_tab, "🔍 Sample Data")
        self.tab_widget.addTab(self.quality_tab, "✓ Quality Metrics")
        
        # Load data when tab is selected
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)
        
        # Set dark theme
        self.setStyleSheet("background-color: #1E1E1E; color: white;")
    
    def create_statistics_tab(self) -> QWidget:
        """Create statistics tab showing feature statistics"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Export button
        export_btn = QPushButton("📥 Export to CSV")
        export_btn.setMaximumWidth(150)
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #5CB85C;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #4CAF50;
            }
        """)
        export_btn.clicked.connect(self.export_statistics)
        layout.addWidget(export_btn)
        
        # Loading indicator
        self.stats_loading_label = QLabel("Loading statistics...")
        self.stats_loading_label.setAlignment(Qt.AlignCenter)
        self.stats_loading_label.setStyleSheet("color: #888; font-size: 14px; padding: 20px;")
        layout.addWidget(self.stats_loading_label)
        
        # Statistics table
        self.stats_table = QTableWidget()
        self.stats_table.setStyleSheet("""
            QTableWidget {
                background-color: #2A2A2A;
                color: white;
                border: 1px solid #555;
                gridline-color: #555;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #4A90E2;
            }
            QHeaderView::section {
                background-color: #3A3A3A;
                color: white;
                padding: 8px;
                border: 1px solid #555;
                font-weight: bold;
            }
        """)
        self.stats_table.setAlternatingRowColors(True)
        self.stats_table.setVisible(False)
        layout.addWidget(self.stats_table)
        
        tab.setLayout(layout)
        return tab
    
    def create_sample_data_tab(self) -> QWidget:
        """Create sample data tab with pagination"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Search and controls
        controls_layout = QHBoxLayout()
        
        search_label = QLabel("Search:")
        search_label.setStyleSheet("color: white;")
        controls_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Horse name or race ID...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #2A2A2A;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        self.search_input.returnPressed.connect(self.search_features)
        controls_layout.addWidget(self.search_input)
        
        search_btn = QPushButton("🔍 Search")
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
        """)
        search_btn.clicked.connect(self.search_features)
        controls_layout.addWidget(search_btn)
        
        clear_btn = QPushButton("✕ Clear")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        clear_btn.clicked.connect(self.clear_search)
        controls_layout.addWidget(clear_btn)
        
        layout.addLayout(controls_layout)
        
        # Sample data table
        self.sample_table = QTableWidget()
        self.sample_table.setStyleSheet("""
            QTableWidget {
                background-color: #2A2A2A;
                color: white;
                border: 1px solid #555;
                gridline-color: #555;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #4A90E2;
            }
            QHeaderView::section {
                background-color: #3A3A3A;
                color: white;
                padding: 8px;
                border: 1px solid #555;
                font-weight: bold;
            }
        """)
        self.sample_table.setAlternatingRowColors(True)
        self.sample_table.doubleClicked.connect(self.show_full_features)
        layout.addWidget(self.sample_table)
        
        # Pagination controls
        pagination_layout = QHBoxLayout()
        
        self.prev_btn = QPushButton("← Previous")
        self.prev_btn.clicked.connect(self.previous_page)
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        pagination_layout.addWidget(self.prev_btn)
        
        self.page_label = QLabel("Page 1")
        self.page_label.setStyleSheet("color: white; padding: 0 20px;")
        self.page_label.setAlignment(Qt.AlignCenter)
        pagination_layout.addWidget(self.page_label)
        
        self.next_btn = QPushButton("Next →")
        self.next_btn.clicked.connect(self.next_page)
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        pagination_layout.addWidget(self.next_btn)
        
        layout.addLayout(pagination_layout)
        
        tab.setLayout(layout)
        return tab
    
    def create_quality_metrics_tab(self) -> QWidget:
        """Create quality metrics tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Summary cards grid
        cards_layout = QGridLayout()
        cards_layout.setSpacing(15)
        
        self.total_features_card = self.create_metric_card("Total Features", "Loading...")
        self.with_targets_card = self.create_metric_card("With Results", "Loading...")
        self.date_range_card = self.create_metric_card("Date Range", "Loading...")
        self.completeness_card = self.create_metric_card("Avg Completeness", "Loading...")
        
        cards_layout.addWidget(self.total_features_card, 0, 0)
        cards_layout.addWidget(self.with_targets_card, 0, 1)
        cards_layout.addWidget(self.date_range_card, 1, 0)
        cards_layout.addWidget(self.completeness_card, 1, 1)
        
        layout.addLayout(cards_layout)
        
        # Completeness by category
        category_group = QGroupBox("Feature Completeness by Category")
        category_group.setStyleSheet("""
            QGroupBox {
                color: white;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        category_layout = QVBoxLayout()
        
        self.category_bars_layout = QVBoxLayout()
        category_layout.addLayout(self.category_bars_layout)
        
        category_group.setLayout(category_layout)
        layout.addWidget(category_group)
        
        layout.addStretch()
        
        tab.setLayout(layout)
        return tab
    
    def create_metric_card(self, title: str, value: str) -> QFrame:
        """Create a metric display card"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #2A2A2A;
                border: 2px solid #4A90E2;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        
        layout = QVBoxLayout()
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #AAA; font-size: 12px;")
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        value_label.setObjectName(f"value_{title}")  # For easy reference
        layout.addWidget(value_label)
        
        card.setLayout(layout)
        return card
    
    @Slot(int)
    def on_tab_changed(self, index: int):
        """Load data when tab is opened"""
        print(f"Tab changed to index: {index}")
        print(f"stats_df is None: {self.stats_df is None}")
        if index == 0 and self.stats_df is None:
            print("Loading statistics...")
            self.load_statistics()
        elif index == 1:
            self.load_sample_data()
        elif index == 2:
            self.load_quality_metrics()
    
    def load_statistics(self):
        """Load feature statistics in background"""
        print("load_statistics() called")
        self.stats_loading_label.setVisible(True)
        self.stats_table.setVisible(False)
        
        # Start background worker
        print("Creating LoadStatsWorker...")
        self.stats_worker = LoadStatsWorker(self.ml_db)
        self.stats_worker.stats_loaded.connect(self.display_statistics)
        self.stats_worker.error_occurred.connect(self.show_error_message)
        print("Starting worker thread...")
        self.stats_worker.start()
        print("Worker thread started")
    
    @Slot(object)
    def display_statistics(self, stats_df: pd.DataFrame):
        """Display loaded statistics"""
        self.stats_df = stats_df
        self.stats_loading_label.setVisible(False)
        
        # Setup table
        self.stats_table.setRowCount(len(stats_df))
        self.stats_table.setColumnCount(len(stats_df.columns))
        self.stats_table.setHorizontalHeaderLabels(stats_df.columns.tolist())
        
        # Populate table
        for i, row in stats_df.iterrows():
            for j, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                self.stats_table.setItem(i, j, item)
        
        # Auto-resize columns
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.stats_table.horizontalHeader().setStretchLastSection(True)
        self.stats_table.setVisible(True)
    
    def load_sample_data(self):
        """Load sample feature data"""
        try:
            samples = self.ml_db.get_sample_features(
                offset=self.current_page * self.page_size,
                limit=self.page_size,
                search_term=self.search_term
            )
            
            if not samples:
                self.sample_table.setRowCount(1)
                self.sample_table.setColumnCount(1)
                self.sample_table.setItem(0, 0, QTableWidgetItem("No data found"))
                return
            
            # Setup table
            headers = list(samples[0].keys())
            self.sample_table.setRowCount(len(samples))
            self.sample_table.setColumnCount(len(headers))
            self.sample_table.setHorizontalHeaderLabels(headers)
            
            # Populate table
            for i, sample in enumerate(samples):
                for j, (key, value) in enumerate(sample.items()):
                    display_value = str(value) if value is not None else 'N/A'
                    if isinstance(value, float):
                        display_value = f"{value:.3f}"
                    
                    item = QTableWidgetItem(display_value)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.sample_table.setItem(i, j, item)
            
            # Auto-resize
            self.sample_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
            self.sample_table.horizontalHeader().setStretchLastSection(True)
            
            # Update pagination
            self.update_pagination_controls()
            
        except Exception as e:
            self.show_error_message(f"Error loading sample data: {e}")
    
    def load_quality_metrics(self):
        """Load quality metrics"""
        try:
            # Update metric cards
            total_features = self.ml_db.get_feature_count()
            self.update_card_value(self.total_features_card, f"{total_features:,}")
            
            targets = self.ml_db.get_target_count()
            self.update_card_value(self.with_targets_card, f"{targets:,}")
            
            min_date, max_date = self.ml_db.get_date_range()
            date_range = f"{min_date} to {max_date}" if min_date and max_date else "N/A"
            self.update_card_value(self.date_range_card, date_range)
            
            # Calculate completeness by category
            completeness = self.ml_db.get_feature_completeness()
            
            if completeness:
                avg_completeness = sum(completeness.values()) / len(completeness)
                self.update_card_value(self.completeness_card, f"{avg_completeness:.1f}%")
                
                # Clear and rebuild category bars
                while self.category_bars_layout.count():
                    child = self.category_bars_layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                
                # Add bars for each category
                for category, pct in sorted(completeness.items()):
                    self.add_completeness_bar(category, pct)
            else:
                self.update_card_value(self.completeness_card, "N/A")
            
        except Exception as e:
            self.show_error_message(f"Error loading quality metrics: {e}")
    
    def update_card_value(self, card: QFrame, value: str):
        """Update value label in a metric card"""
        # Find the value label (second QLabel in card)
        for child in card.children():
            if isinstance(child, QLabel) and "font-size: 24px" in child.styleSheet():
                child.setText(value)
                break
    
    def add_completeness_bar(self, category: str, percentage: float):
        """Add a completeness progress bar for a category"""
        layout = QHBoxLayout()
        
        label = QLabel(category)
        label.setStyleSheet("color: white; min-width: 150px;")
        layout.addWidget(label)
        
        progress = QProgressBar()
        progress.setValue(int(percentage))
        progress.setFormat(f"{percentage:.1f}%")
        progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                border-radius: 5px;
                text-align: center;
                color: white;
                background-color: #2A2A2A;
            }
            QProgressBar::chunk {
                background-color: #4A90E2;
                border-radius: 4px;
            }
        """)
        layout.addWidget(progress)
        
        self.category_bars_layout.addLayout(layout)
    
    @Slot()
    def search_features(self):
        """Search features by term"""
        self.search_term = self.search_input.text().strip() or None
        self.current_page = 0
        self.load_sample_data()
    
    @Slot()
    def clear_search(self):
        """Clear search and reload"""
        self.search_input.clear()
        self.search_term = None
        self.current_page = 0
        self.load_sample_data()
    
    @Slot()
    def previous_page(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.load_sample_data()
    
    @Slot()
    def next_page(self):
        """Go to next page"""
        self.current_page += 1
        self.load_sample_data()
    
    def update_pagination_controls(self):
        """Update pagination button states"""
        self.prev_btn.setEnabled(self.current_page > 0)
        self.page_label.setText(f"Page {self.current_page + 1}")
        # Could check if there are more pages, but for now just enable next
    
    @Slot()
    def show_full_features(self):
        """Show all features for selected runner"""
        current_row = self.sample_table.currentRow()
        if current_row < 0:
            return
        
        # Get runner_id from table
        runner_id_item = self.sample_table.item(current_row, 1)  # runner_id column
        if not runner_id_item:
            return
        
        try:
            runner_id = int(runner_id_item.text())
            features = self.ml_db.get_full_features_for_runner(runner_id)
            
            if features:
                # Show in dialog
                details_text = "All Features:\n\n"
                for key, value in features.items():
                    details_text += f"{key}: {value}\n"
                
                QMessageBox.information(self, f"Runner {runner_id} Features", details_text)
        except Exception as e:
            self.show_error_message(f"Error loading full features: {e}")
    
    @Slot()
    def export_statistics(self):
        """Export statistics to CSV"""
        if self.stats_df is None or self.stats_df.empty:
            QMessageBox.warning(self, "Export", "No statistics to export")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Statistics",
            "feature_statistics.csv",
            "CSV Files (*.csv)"
        )
        
        if filename:
            try:
                self.stats_df.to_csv(filename, index=False)
                QMessageBox.information(self, "Export", f"Statistics exported to {filename}")
            except Exception as e:
                self.show_error_message(f"Error exporting: {e}")
    
    @Slot()
    def refresh_all_tabs(self):
        """Refresh all tab data"""
        self.stats_df = None
        current_index = self.tab_widget.currentIndex()
        self.on_tab_changed(current_index)

