"""
Dashboard Window - Main container for entire application
Coordinates navigation ribbon, dashboard view, racecard viewer, and data fetch
"""

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QStackedWidget,
                                QMessageBox, QApplication)
from PySide6.QtCore import Slot

from .database import DatabaseHelper
from .nav_ribbon import NavigationRibbon
from .dashboard_view import DashboardView
from .main_window import MainWindow as RacecardWindow
from .data_fetch_view import DataFetchView
from .data_exploration_view import DataExplorationView
from .upcoming_races_view import UpcomingRacesView
from .ml_features_view import MLFeaturesView
from .ml_training_view import MLTrainingView
from .predictions_view import PredictionsView


class DashboardWindow(QMainWindow):
    """Main dashboard window with navigation and multiple views"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Racing Data Dashboard")
        self.setGeometry(100, 100, 1600, 900)
        
        # Initialize database helper
        try:
            self.db = DatabaseHelper()
        except FileNotFoundError as e:
            QMessageBox.critical(self, "Database Error", str(e))
            QApplication.quit()
            return
        
        self.setup_ui()
        self.connect_signals()
        
        # Show dashboard initially
        self.show_dashboard()
    
    def setup_ui(self):
        """Setup the dashboard window UI"""
        # Central widget with vertical layout
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Navigation ribbon at top
        self.nav_ribbon = NavigationRibbon()
        main_layout.addWidget(self.nav_ribbon)
        
        # Stacked widget for different views
        self.view_stack = QStackedWidget()
        
        # Dashboard view (home)
        self.dashboard_view = DashboardView(self.db)
        self.view_stack.addWidget(self.dashboard_view)
        
        # Racecard viewer (existing implementation)
        self.racecard_window = RacecardWindow()
        # Remove the racecard window's own window frame - it's now embedded
        self.racecard_widget = self.racecard_window.centralWidget()
        self.view_stack.addWidget(self.racecard_widget)
        
        # Data fetch view
        self.data_fetch_view = DataFetchView(self.db)
        self.view_stack.addWidget(self.data_fetch_view)
        
        # Data exploration view
        self.data_exploration_view = DataExplorationView(self.db)
        self.view_stack.addWidget(self.data_exploration_view)
        
        # Upcoming races view
        self.upcoming_races_view = UpcomingRacesView()
        self.view_stack.addWidget(self.upcoming_races_view)
        
        # ML Features view
        self.ml_features_view = MLFeaturesView(self.db)
        self.view_stack.addWidget(self.ml_features_view)
        
        # ML Training view
        self.ml_training_view = MLTrainingView(self.db)
        self.view_stack.addWidget(self.ml_training_view)
        
        # Predictions view
        self.predictions_view = PredictionsView(self.db)
        self.view_stack.addWidget(self.predictions_view)
        
        main_layout.addWidget(self.view_stack)
        
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
    
    def connect_signals(self):
        """Connect signals between components"""
        # Navigation ribbon
        self.nav_ribbon.home_clicked.connect(self.show_dashboard)
        self.nav_ribbon.dbupdate_clicked.connect(self.show_dbupdate)
        self.nav_ribbon.upcoming_clicked.connect(self.show_upcoming)
        self.nav_ribbon.racecard_clicked.connect(self.show_racecard)
        self.nav_ribbon.exploration_clicked.connect(self.show_exploration)
        self.nav_ribbon.ml_features_clicked.connect(self.show_ml_features)
        self.nav_ribbon.ml_training_clicked.connect(self.show_ml_training)
        self.nav_ribbon.predictions_clicked.connect(self.show_predictions)
        
        # Dashboard tiles
        self.dashboard_view.racecard_clicked.connect(self.show_racecard)
        self.dashboard_view.datafetch_clicked.connect(self.show_dbupdate)
        
        # Data fetch completion
        self.data_fetch_view.fetch_completed.connect(self.on_fetch_completed)
        
        # Refresh all tabs request
        self.data_fetch_view.refresh_all_requested.connect(self.refresh_all_views)
    
    @Slot()
    def show_dashboard(self):
        """Show dashboard view"""
        self.nav_ribbon.set_active('home')
        self.view_stack.setCurrentWidget(self.dashboard_view)
        # Refresh stats in case data was updated
        self.dashboard_view.refresh_stats()
    
    @Slot()
    def show_dbupdate(self):
        """Show database update view"""
        self.nav_ribbon.set_active('dbupdate')
        self.view_stack.setCurrentWidget(self.data_fetch_view)
    
    @Slot()
    def show_upcoming(self):
        """Show upcoming races view"""
        self.nav_ribbon.set_active('upcoming')
        self.view_stack.setCurrentWidget(self.upcoming_races_view)
    
    @Slot()
    def show_racecard(self):
        """Show racecard viewer"""
        self.nav_ribbon.set_active('racecard')
        self.view_stack.setCurrentWidget(self.racecard_widget)
    
    @Slot()
    def show_exploration(self):
        """Show data exploration view"""
        self.nav_ribbon.set_active('exploration')
        self.view_stack.setCurrentWidget(self.data_exploration_view)
    
    @Slot()
    def show_ml_features(self):
        """Show ML features view"""
        self.nav_ribbon.set_active('ml_features')
        self.view_stack.setCurrentWidget(self.ml_features_view)
    
    @Slot()
    def show_ml_training(self):
        """Show ML training view"""
        self.nav_ribbon.set_active('ml_training')
        self.view_stack.setCurrentWidget(self.ml_training_view)
    
    @Slot()
    def show_predictions(self):
        """Show predictions view"""
        self.nav_ribbon.set_active('predictions')
        self.view_stack.setCurrentWidget(self.predictions_view)
    
    @Slot()
    def on_fetch_completed(self):
        """Handle data fetch completion"""
        # Refresh dashboard stats
        self.dashboard_view.refresh_stats()
    
    @Slot()
    def refresh_all_views(self):
        """Refresh database connections for all views"""
        # Reconnect main database
        self.db.conn.close()
        import sqlite3
        self.db.conn = sqlite3.connect(str(self.db.db_path))
        self.db.conn.row_factory = sqlite3.Row
        
        # Refresh dashboard
        self.dashboard_view.refresh_stats()
        
        # Refresh data exploration
        from .stats_calculator import StatsCalculator
        self.data_exploration_view.stats_calc = StatsCalculator(self.db)
        self.data_exploration_view.load_tables()
        
        # Refresh racecard viewer navigation
        self.racecard_window.navigation_panel.on_refresh_clicked()
        
        # Show success message
        QMessageBox.information(self, "Refresh Complete", 
                              "All tabs refreshed with latest data!")
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Close database connection
        self.db.close()
        # Close racecard window's database connection if it has one
        if hasattr(self.racecard_window, 'db'):
            self.racecard_window.db.close()
        event.accept()

