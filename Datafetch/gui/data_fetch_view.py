"""
Data Fetch View - Interface for updating database
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                QPushButton, QProgressBar, QGroupBox, QDateEdit,
                                QMessageBox)
from PySide6.QtCore import Signal, Qt, QDate, Slot
from PySide6.QtGui import QFont
from datetime import datetime, timedelta

from .database import DatabaseHelper
from .combined_fetcher_worker import CombinedFetcherWorker


class DataFetchView(QWidget):
    """Data fetch interface with date picker and update options"""
    
    # Signals
    fetch_started = Signal()
    fetch_completed = Signal()
    refresh_all_requested = Signal()
    
    def __init__(self, db_helper: DatabaseHelper, parent=None):
        super().__init__(parent)
        self.db = db_helper
        self.is_fetching = False
        self.setup_ui()
        self.load_current_stats()
    
    def setup_ui(self):
        """Setup the data fetch view UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("DATABASE UPDATE")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Separator
        separator = QLabel("═" * 80)
        separator.setStyleSheet("color: #333;")
        layout.addWidget(separator)
        
        # Current stats
        stats_label = QLabel("Current Database Range:")
        stats_font = QFont()
        stats_font.setBold(True)
        stats_label.setFont(stats_font)
        layout.addWidget(stats_label)
        
        self.current_stats = QLabel()
        layout.addWidget(self.current_stats)
        
        layout.addSpacing(20)
        
        # Option 1: Update to specific date
        option1_group = QGroupBox("OPTION 1: Update to Specific Date")
        option1_layout = QVBoxLayout()
        option1_layout.setSpacing(15)
        
        # Date picker
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Fetch data up to:"))
        
        self.date_picker = QDateEdit()
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setDate(QDate(2023, 6, 30))  # Default to June 30, 2023
        self.date_picker.setDisplayFormat("yyyy-MM-dd")
        date_layout.addWidget(self.date_picker)
        date_layout.addStretch()
        
        option1_layout.addLayout(date_layout)
        
        # Description
        desc1 = QLabel("This will fetch all missing dates between\n"
                       "the start of the database and the selected date.")
        desc1.setStyleSheet("color: gray; font-style: italic;")
        option1_layout.addWidget(desc1)
        
        # Button
        self.update_to_date_btn = QPushButton("Update to Selected Date")
        self.update_to_date_btn.setMinimumHeight(40)
        self.update_to_date_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
            QPushButton:pressed {
                background-color: #2868A8;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        self.update_to_date_btn.clicked.connect(self.on_update_to_date)
        option1_layout.addWidget(self.update_to_date_btn)
        
        option1_group.setLayout(option1_layout)
        layout.addWidget(option1_group)
        
        # Option 2: Update to yesterday
        option2_group = QGroupBox("OPTION 2: Update to Yesterday")
        option2_layout = QVBoxLayout()
        option2_layout.setSpacing(15)
        
        # System date info
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        system_date_label = QLabel(f"System date: {today.strftime('%Y-%m-%d')}")
        option2_layout.addWidget(system_date_label)
        
        target_date_label = QLabel(f"Target date: {yesterday.strftime('%Y-%m-%d')} (yesterday)")
        target_date_label_font = QFont()
        target_date_label_font.setBold(True)
        target_date_label.setFont(target_date_label_font)
        option2_layout.addWidget(target_date_label)
        
        # Description
        desc2 = QLabel("This will fetch all missing dates up to yesterday.")
        desc2.setStyleSheet("color: gray; font-style: italic;")
        option2_layout.addWidget(desc2)
        
        # Button
        self.update_to_yesterday_btn = QPushButton("Update to Yesterday")
        self.update_to_yesterday_btn.setMinimumHeight(40)
        self.update_to_yesterday_btn.setStyleSheet("""
            QPushButton {
                background-color: #5CB85C;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 4px;
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
        self.update_to_yesterday_btn.clicked.connect(self.on_update_to_yesterday)
        option2_layout.addWidget(self.update_to_yesterday_btn)
        
        option2_group.setLayout(option2_layout)
        layout.addWidget(option2_group)
        
        # Option 3: Complete Rebuild (NEW)
        option3_group = QGroupBox("OPTION 3: Complete Database Rebuild ⚠️")
        option3_layout = QVBoxLayout()
        option3_layout.setSpacing(15)
        
        # Warning message
        warning = QLabel(
            "⚠️ WARNING: This will backup and rebuild the ENTIRE database from scratch.\n\n"
            "✓ Backs up current database first\n"
            "✓ Re-fetches ALL data from API with proper odds aggregation\n"
            "✓ Fetches results for completed races\n"
            "✓ Regenerates ML features with full odds coverage\n\n"
            "Time estimate: 8-10 hours\n"
            "Result: 80%+ of data will have odds features (vs current 2.2%)"
        )
        warning.setStyleSheet(
            "color: #856404; padding: 15px; background: #fff3cd; "
            "border: 2px solid #ffc107; border-radius: 4px; font-size: 11px;"
        )
        warning.setWordWrap(True)
        option3_layout.addWidget(warning)
        
        # Date range selection
        date_range_layout = QHBoxLayout()
        date_range_layout.addWidget(QLabel("Start Date:"))
        self.rebuild_start_date = QDateEdit()
        self.rebuild_start_date.setCalendarPopup(True)
        self.rebuild_start_date.setDate(QDate(2023, 1, 23))
        self.rebuild_start_date.setDisplayFormat("yyyy-MM-dd")
        date_range_layout.addWidget(self.rebuild_start_date)
        
        date_range_layout.addWidget(QLabel("End Date:"))
        self.rebuild_end_date = QDateEdit()
        self.rebuild_end_date.setCalendarPopup(True)
        self.rebuild_end_date.setDate(QDate.currentDate().addDays(-1))
        self.rebuild_end_date.setDisplayFormat("yyyy-MM-dd")
        date_range_layout.addWidget(self.rebuild_end_date)
        date_range_layout.addStretch()
        
        option3_layout.addLayout(date_range_layout)
        
        # Rebuild button
        self.rebuild_btn = QPushButton("🔄 REBUILD ENTIRE DATABASE")
        self.rebuild_btn.setMinimumHeight(50)
        self.rebuild_btn.setStyleSheet("""
            QPushButton {
                background-color: #d9534f;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c9302c;
            }
            QPushButton:pressed {
                background-color: #ac2925;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.rebuild_btn.clicked.connect(self.confirm_and_rebuild)
        option3_layout.addWidget(self.rebuild_btn)
        
        option3_group.setLayout(option3_layout)
        layout.addWidget(option3_group)
        
        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: gray; font-style: italic;")
        progress_layout.addWidget(self.status_label)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Refresh all tabs button
        self.refresh_all_btn = QPushButton("🔄 Refresh All Tabs")
        self.refresh_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #5CB85C;
                color: white;
                font-size: 13px;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #4A9D4A;
            }
            QPushButton:pressed {
                background-color: #3E8A3E;
            }
        """)
        self.refresh_all_btn.clicked.connect(self.refresh_all_tabs)
        layout.addWidget(self.refresh_all_btn)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def load_current_stats(self):
        """Load and display current database statistics"""
        cursor = self.db.conn.cursor()
        
        # Get date range
        cursor.execute("SELECT MIN(date), MAX(date) FROM races")
        result = cursor.fetchone()
        
        if result and result[0]:
            min_date, max_date = result
            
            # Get total races
            cursor.execute("SELECT COUNT(*) FROM races")
            total_races = cursor.fetchone()[0]
            
            # Get race type breakdown
            cursor.execute("SELECT type, COUNT(*) FROM races GROUP BY type ORDER BY COUNT(*) DESC")
            type_breakdown = cursor.fetchall()
            
            # Format race type breakdown
            type_text = ""
            if type_breakdown:
                type_text = "\n• Race Types:"
                for race_type, count in type_breakdown:
                    type_emoji = '🏇' if race_type == 'Flat' else '🐴'
                    percentage = (count / total_races * 100) if total_races > 0 else 0
                    type_text += f"\n  {type_emoji} {race_type}: {count:,} ({percentage:.1f}%)"
            
            stats_text = (
                f"• Start: {min_date}\n"
                f"• End: {max_date}\n"
                f"• Total Races: {total_races:,}"
                f"{type_text}"
            )
        else:
            stats_text = "No data in database"
        
        self.current_stats.setText(stats_text)
    
    def on_update_to_date(self):
        """Handle update to specific date button"""
        if self.is_fetching:
            QMessageBox.warning(self, "Fetch in Progress", 
                              "A data fetch is already in progress.")
            return
        
        # Get selected date
        selected_date = self.date_picker.date()
        end_date = selected_date.toString("yyyy-MM-dd")
        
        # Confirm with user
        reply = QMessageBox.question(
            self,
            "Confirm Update",
            f"Fetch all missing data up to {end_date}?\n\n"
            f"This may take several minutes depending on the date range.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.start_fetch(end_date)
    
    def on_update_to_yesterday(self):
        """Handle update to yesterday button"""
        if self.is_fetching:
            QMessageBox.warning(self, "Fetch in Progress", 
                              "A data fetch is already in progress.")
            return
        
        # Calculate yesterday
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Confirm with user
        reply = QMessageBox.question(
            self,
            "Confirm Update",
            f"Fetch all missing data up to {yesterday} (yesterday)?\n\n"
            f"This may take several minutes depending on the date range.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.start_fetch(yesterday)
    
    def confirm_and_rebuild(self):
        """Show confirmation dialog before rebuilding"""
        if self.is_fetching:
            QMessageBox.warning(self, "Operation in Progress", 
                              "A data operation is already in progress.")
            return
        
        # Get date range
        start_date = self.rebuild_start_date.date().toString("yyyy-MM-dd")
        end_date = self.rebuild_end_date.date().toString("yyyy-MM-dd")
        
        # Calculate estimated time
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        days = (end_dt - start_dt).days + 1
        
        backup_name = f"racing_pro_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        
        # Show detailed confirmation
        reply = QMessageBox.question(
            self,
            'Confirm Database Rebuild',
            f'⚠️ Are you sure you want to rebuild the ENTIRE database?\n\n'
            f'Date Range: {start_date} to {end_date} ({days:,} days)\n\n'
            f'This will:\n'
            f'  ✓ Backup your current database to:\n'
            f'     {backup_name}\n'
            f'  ✓ Delete and recreate the database\n'
            f'  ✓ Re-fetch ~{days * 40:,} races from the API\n'
            f'  ✓ Properly aggregate ALL odds data\n'
            f'  ✓ Fetch results for completed races\n'
            f'  ✓ Regenerate ML features\n\n'
            f'Estimated time: 8-10 hours\n\n'
            f'⚠️ Do NOT close the application during this process!',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.start_rebuild(start_date, end_date)
    
    def start_rebuild(self, start_date: str, end_date: str):
        """Start the database rebuild process"""
        print(f"\n[GUI] Starting rebuild: {start_date} to {end_date}")
        
        from .rebuild_database_worker import RebuildDatabaseWorker
        
        self.is_fetching = True
        self.update_to_date_btn.setEnabled(False)
        self.update_to_yesterday_btn.setEnabled(False)
        self.rebuild_btn.setEnabled(False)
        self.date_picker.setEnabled(False)
        self.rebuild_start_date.setEnabled(False)
        self.rebuild_end_date.setEnabled(False)
        
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Starting database rebuild...")
        
        self.fetch_started.emit()
        
        # Create rebuild worker
        db_path = str(self.db.db_path)
        print(f"[GUI] Database path: {db_path}")
        print(f"[GUI] Creating RebuildDatabaseWorker...")
        self.rebuild_worker = RebuildDatabaseWorker(start_date, end_date, db_path)
        print(f"[GUI] Worker created successfully")
        
        # Connect signals
        print(f"[GUI] Connecting signals...")
        self.rebuild_worker.progress_update.connect(self.on_rebuild_progress_text)
        self.rebuild_worker.phase_changed.connect(self.on_rebuild_phase_changed)
        self.rebuild_worker.item_processed.connect(self.on_rebuild_item_processed)
        self.rebuild_worker.rebuild_complete.connect(self.on_rebuild_complete)
        self.rebuild_worker.rebuild_error.connect(self.on_rebuild_error)
        print(f"[GUI] Signals connected")
        
        # Track phase for progress
        self.current_phase_total = 0
        
        # Start rebuild
        print(f"[GUI] Starting worker thread...")
        self.rebuild_worker.start()
        print(f"[GUI] Worker thread started, check terminal for progress updates\n")
    
    def on_rebuild_progress_text(self, message: str):
        """Handle rebuild progress text messages"""
        self.status_label.setText(message)
    
    def on_rebuild_phase_changed(self, phase_name: str, total_items: int):
        """Handle rebuild phase change"""
        self.current_phase_total = total_items
        self.progress_bar.setValue(0)
        self.status_label.setText(phase_name)
    
    def on_rebuild_item_processed(self, current_item: int):
        """Handle rebuild item processed"""
        if self.current_phase_total > 0:
            percentage = int((current_item / self.current_phase_total) * 100)
            self.progress_bar.setValue(percentage)
    
    def on_rebuild_complete(self, stats: dict):
        """Handle rebuild completion"""
        self.is_fetching = False
        self.update_to_date_btn.setEnabled(True)
        self.update_to_yesterday_btn.setEnabled(True)
        self.rebuild_btn.setEnabled(True)
        self.date_picker.setEnabled(True)
        self.rebuild_start_date.setEnabled(True)
        self.rebuild_end_date.setEnabled(True)
        
        self.progress_bar.setValue(100)
        self.status_label.setText("Rebuild complete!")
        
        # Reconnect to database
        self.db.conn.close()
        import sqlite3
        self.db.conn = sqlite3.connect(str(self.db.db_path))
        self.db.conn.row_factory = sqlite3.Row
        
        # Reload stats
        self.load_current_stats()
        
        # Show completion message
        QMessageBox.information(
            self,
            "Rebuild Complete",
            f"✓ Database rebuild completed successfully!\n\n"
            f"Statistics:\n"
            f"  • Races: {stats.get('races', 0):,}\n"
            f"  • Runners: {stats.get('runners', 0):,}\n"
            f"  • Results: {stats.get('results', 0):,}\n"
            f"  • Odds records: {stats.get('odds', 0):,}\n"
            f"  • ML features: {stats.get('features', 0):,}\n\n"
            f"Backup saved to:\n{stats.get('backup_path', 'N/A')}"
        )
        
        self.fetch_completed.emit()
        self.refresh_all_tabs()
    
    def on_rebuild_error(self, error_message: str):
        """Handle rebuild error"""
        self.is_fetching = False
        self.update_to_date_btn.setEnabled(True)
        self.update_to_yesterday_btn.setEnabled(True)
        self.rebuild_btn.setEnabled(True)
        self.date_picker.setEnabled(True)
        self.rebuild_start_date.setEnabled(True)
        self.rebuild_end_date.setEnabled(True)
        
        self.status_label.setText(f"Rebuild failed: {error_message}")
        
        QMessageBox.critical(
            self,
            "Rebuild Error",
            f"Database rebuild failed:\n\n{error_message}\n\n"
            f"Your original database backup should still be available.\n"
            f"Check the Datafetch folder for backup files."
        )
    
    def start_fetch(self, end_date: str):
        """Start the data fetch process"""
        self.is_fetching = True
        self.update_to_date_btn.setEnabled(False)
        self.update_to_yesterday_btn.setEnabled(False)
        self.date_picker.setEnabled(False)
        
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Preparing to fetch data up to {end_date}...")
        
        self.fetch_started.emit()
        
        # Import and run fetcher worker
        # This will be implemented in the next step
        self.worker = CombinedFetcherWorker(self.db, end_date)
        self.worker.progress.connect(self.on_progress)
        self.worker.status.connect(self.on_status)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()
    
    def on_progress(self, current: int, total: int, phase: str):
        """Update progress bar"""
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
            self.progress_bar.setFormat(f"{phase}: {current}/{total} ({percentage}%)")
    
    def on_status(self, message: str):
        """Update status label"""
        self.status_label.setText(message)
    
    def on_finished(self, races_added: int, runners_added: int):
        """Handle fetch completion"""
        self.is_fetching = False
        self.update_to_date_btn.setEnabled(True)
        self.update_to_yesterday_btn.setEnabled(True)
        self.date_picker.setEnabled(True)
        
        self.progress_bar.setValue(100)
        self.status_label.setText(
            f"Complete! Added {races_added:,} races and {runners_added:,} runners."
        )
        
        # Reconnect to database to see new data (needed after background thread insert)
        self.db.conn.close()
        import sqlite3
        self.db.conn = sqlite3.connect(str(self.db.db_path))
        self.db.conn.row_factory = sqlite3.Row
        
        # Reload stats
        self.load_current_stats()
        
        # Show completion message
        QMessageBox.information(
            self,
            "Update Complete",
            f"Database updated successfully!\n\n"
            f"Races added: {races_added:,}\n"
            f"Runners added: {runners_added:,}"
        )
        
        self.fetch_completed.emit()
        
        # Auto-trigger refresh all tabs
        self.refresh_all_tabs()
    
    def on_error(self, error_message: str):
        """Handle fetch error"""
        self.is_fetching = False
        self.update_to_date_btn.setEnabled(True)
        self.update_to_yesterday_btn.setEnabled(True)
        self.date_picker.setEnabled(True)
        
        self.status_label.setText(f"Error: {error_message}")
        
        QMessageBox.critical(
            self,
            "Fetch Error",
            f"An error occurred during data fetch:\n\n{error_message}"
        )
    
    @Slot()
    def refresh_all_tabs(self):
        """Request refresh of all tabs"""
        self.refresh_all_requested.emit()

