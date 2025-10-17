"""
Main Window for Racecard GUI Application
Manages layout and coordinates between navigation, race list, racecard, and profile views
"""

from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QStackedWidget,
                                QMessageBox, QApplication)
from PySide6.QtCore import Slot
from PySide6.QtGui import QKeySequence, QShortcut

from .database import DatabaseHelper
from .navigation_panel import NavigationPanel
from .race_list_view import RaceListView
from .racecard_view import RacecardView
from .profile_view import ProfileView


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Racecard Viewer")
        self.setGeometry(100, 100, 1600, 900)
        
        # Initialize database helper
        try:
            self.db = DatabaseHelper()
        except FileNotFoundError as e:
            QMessageBox.critical(self, "Database Error", str(e))
            QApplication.quit()
            return
        
        # Navigation history for back button
        self.current_race_id = None
        self.view_history = []  # Stack of (view_type, data) tuples
        
        self.setup_ui()
        self.connect_signals()
        self.setup_shortcuts()
        
        # Show placeholder initially (require filters before loading)
        self.show_filter_prompt()
    
    def setup_ui(self):
        """Setup the main window UI"""
        # Central widget with horizontal layout
        central_widget = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Navigation panel (left side)
        self.navigation_panel = NavigationPanel(self.db)
        main_layout.addWidget(self.navigation_panel)
        
        # Stacked widget for content area (right side)
        # Three views: race list, racecard, profile
        self.content_stack = QStackedWidget()
        
        # Race list view (new default)
        self.race_list_view = RaceListView()
        self.content_stack.addWidget(self.race_list_view)
        
        # Racecard view
        self.racecard_view = RacecardView()
        self.content_stack.addWidget(self.racecard_view)
        
        # Profile view
        self.profile_view = ProfileView()
        self.content_stack.addWidget(self.profile_view)
        
        main_layout.addWidget(self.content_stack, 1)  # Stretch factor 1
        
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # Show race list view by default
        self.content_stack.setCurrentWidget(self.race_list_view)
    
    def connect_signals(self):
        """Connect signals between components"""
        # Navigation panel signals
        self.navigation_panel.filters_changed.connect(self.on_filters_changed)
        self.navigation_panel.refresh_requested.connect(self.on_refresh_requested)
        
        # Race list view signals
        self.race_list_view.race_selected.connect(self.on_race_selected)
        
        # Racecard view signals
        self.racecard_view.entity_clicked.connect(self.on_entity_clicked)
        
        # Profile view signals
        self.profile_view.back_clicked.connect(self.on_back_clicked)
        self.profile_view.entity_clicked.connect(self.on_entity_clicked)
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # ESC key for back
        back_shortcut = QShortcut(QKeySequence("Esc"), self)
        back_shortcut.activated.connect(self.on_back_clicked)
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def count_active_filters(self, filters: dict) -> int:
        """Count how many filters are set (not 'All')"""
        count = 0
        for key, value in filters.items():
            if value and value != "All":
                count += 1
        return count
    
    def show_filter_prompt(self):
        """Show prompt to select filters"""
        from PySide6.QtWidgets import QVBoxLayout, QLabel
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QFont
        
        # Create a simple widget with instruction text
        prompt_widget = QWidget()
        layout = QVBoxLayout()
        
        title = QLabel("Select Filters to View Races")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        
        instruction = QLabel("Please select at least 3 filters from the left panel\n"
                           "to display races.\n\n"
                           "Examples:\n"
                           "• Year + Month + Region\n"
                           "• Year + Month + Course\n"
                           "• Region + Course + Month")
        instruction.setAlignment(Qt.AlignCenter)
        instruction.setStyleSheet("color: gray; padding: 20px;")
        inst_font = QFont()
        inst_font.setPointSize(12)
        instruction.setFont(inst_font)
        
        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(instruction)
        layout.addStretch()
        
        prompt_widget.setLayout(layout)
        
        # Clear current race list view and show prompt
        self.race_list_view.table.setRowCount(0)
        self.race_list_view.header_label.setText("RACES")
        self.content_stack.setCurrentWidget(self.race_list_view)
    
    # ========================================================================
    # SLOTS (Event Handlers)
    # ========================================================================
    
    @Slot(dict)
    def on_filters_changed(self, filters: dict):
        """Handle filter changes from navigation panel"""
        # Require at least 3 filters to be set
        active_count = self.count_active_filters(filters)
        
        if active_count < 3:
            # Show prompt to select more filters
            self.race_list_view.table.setRowCount(0)
            self.race_list_view.header_label.setText(
                f"RACES (Select at least 3 filters - currently {active_count} selected)"
            )
            self.content_stack.setCurrentWidget(self.race_list_view)
        else:
            # Load and display races
            self.load_races(filters)
    
    def load_races(self, filters: dict):
        """Load and display races based on current filters"""
        # Get filtered races from database
        races = self.db.get_races_filtered(
            year=filters.get('year'),
            month=filters.get('month'),
            day=filters.get('day'),
            region=filters.get('region'),
            course=filters.get('course')
        )
        
        # Display in race list view
        self.race_list_view.display_races(races)
        
        # Show race list view
        self.content_stack.setCurrentWidget(self.race_list_view)
        
        # Clear navigation history when returning to race list
        self.view_history = []
    
    @Slot(str)
    def on_race_selected(self, race_id: str):
        """Handle race selection from race list"""
        self.current_race_id = race_id
        
        # Get race details
        race_data = self.db.get_race_details(race_id)
        
        if race_data:
            # Save current view to history
            self.view_history.append(('race_list', None))
            
            # Display in racecard view
            self.racecard_view.display_race(race_data)
            self.content_stack.setCurrentWidget(self.racecard_view)
        else:
            QMessageBox.warning(
                self,
                "Race Not Found",
                f"Could not load details for race {race_id}"
            )
    
    @Slot(str, str, str)
    def on_entity_clicked(self, entity_type: str, entity_id: str, entity_name: str):
        """Handle entity click from racecard or profile view"""
        if not entity_id:
            return
        
        # Save current view to history
        current_widget = self.content_stack.currentWidget()
        if current_widget == self.racecard_view:
            self.view_history.append(('racecard', self.current_race_id))
        elif current_widget == self.profile_view:
            # When clicking from profile to another profile, add to history
            self.view_history.append(('profile', (entity_type, entity_id)))
        
        # Get profile data
        profile_data = None
        
        if entity_type == 'horse':
            profile_data = self.db.get_horse_profile(entity_id)
        elif entity_type == 'trainer':
            profile_data = self.db.get_trainer_profile(entity_id)
        elif entity_type == 'jockey':
            profile_data = self.db.get_jockey_profile(entity_id)
        elif entity_type == 'owner':
            profile_data = self.db.get_owner_profile(entity_id)
        
        if profile_data:
            # Display profile
            self.profile_view.display_profile(entity_type, profile_data)
            self.content_stack.setCurrentWidget(self.profile_view)
        else:
            QMessageBox.warning(
                self,
                f"{entity_type.capitalize()} Not Found",
                f"Could not load profile for {entity_name}"
            )
    
    @Slot()
    def on_back_clicked(self):
        """Handle back button or ESC key"""
        if not self.view_history:
            # If no history, go back to race list
            self.load_races(self.navigation_panel.get_current_filters())
            return
        
        # Pop from history
        view_type, data = self.view_history.pop()
        
        if view_type == 'race_list':
            # Go back to race list
            self.load_races(self.navigation_panel.get_current_filters())
        
        elif view_type == 'racecard' and data:
            # Go back to racecard
            race_data = self.db.get_race_details(data)
            if race_data:
                self.racecard_view.display_race(race_data)
                self.content_stack.setCurrentWidget(self.racecard_view)
                self.current_race_id = data
        
        elif view_type == 'profile' and data:
            # Go back to previous profile
            entity_type, entity_id = data
            
            if entity_type == 'horse':
                profile_data = self.db.get_horse_profile(entity_id)
            elif entity_type == 'trainer':
                profile_data = self.db.get_trainer_profile(entity_id)
            elif entity_type == 'jockey':
                profile_data = self.db.get_jockey_profile(entity_id)
            elif entity_type == 'owner':
                profile_data = self.db.get_owner_profile(entity_id)
            else:
                profile_data = None
            
            if profile_data:
                self.profile_view.display_profile(entity_type, profile_data)
                self.content_stack.setCurrentWidget(self.profile_view)
    
    @Slot()
    def on_refresh_requested(self):
        """Handle refresh request from navigation panel"""
        # Show message
        QMessageBox.information(
            self,
            "Data Refreshed",
            "Database connection refreshed with latest data!"
        )
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Close database connection
        self.db.close()
        event.accept()
