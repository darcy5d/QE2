"""
In The Money View - Value betting recommendations using Kelly Criterion
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                                QLineEdit, QComboBox, QCheckBox, QGroupBox, QScrollArea,
                                QFrame, QMessageBox, QFileDialog, QTreeWidget, QTreeWidgetItem)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont, QColor, QDoubleValidator
from pathlib import Path
import sqlite3
from datetime import datetime
from collections import defaultdict
import csv

from .betting_calculator import BettingCalculator
from .styles import COLORS


class InTheMoneyView(QWidget):
    """View for displaying value betting recommendations"""
    
    def __init__(self, db_helper, parent=None):
        super().__init__(parent)
        self.db = db_helper
        self.upcoming_db_path = Path(__file__).parent.parent / "upcoming_races.db"
        
        # Default settings
        self.bankroll = 1000.0
        self.kelly_fraction = 0.5
        self.min_edge = 0.05
        self.market_confidence = 0.65  # Default to 65% market blend (conservative)
        self.selected_date = None  # None = All Dates
        
        # Bet type filters
        self.show_win = True
        self.show_place = True
        self.show_exacta = True
        self.show_trifecta = True
        self.show_first_four = True
        
        # Calculator instance
        self.calculator = BettingCalculator(
            self.bankroll, 
            self.kelly_fraction, 
            self.min_edge,
            self.market_confidence
        )
        
        # Store current recommendations
        self.all_recommendations = []
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the In The Money view UI"""
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
        
        title = QLabel("💰 IN THE MONEY - Value Betting Recommendations")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(18)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {COLORS['accent_green']}; padding: 10px;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Export button
        self.export_btn = QPushButton("📊 Export Bets")
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
        self.export_btn.clicked.connect(self.export_recommendations)
        self.export_btn.setEnabled(False)
        header_layout.addWidget(self.export_btn)
        
        # Generate button
        self.generate_btn = QPushButton("🚀 Find Value Bets")
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
        """)
        self.generate_btn.clicked.connect(self.generate_recommendations)
        header_layout.addWidget(self.generate_btn)
        
        main_layout.addLayout(header_layout)
        
        # Settings panel
        settings_panel = self.create_settings_panel()
        main_layout.addWidget(settings_panel)
        
        # Recommendations tree
        self.recommendations_tree = self.create_recommendations_tree()
        main_layout.addWidget(self.recommendations_tree, 1)
        
        # Summary panel
        self.summary_panel = self.create_summary_panel()
        main_layout.addWidget(self.summary_panel)
        
        self.setLayout(main_layout)
        
        # Show initial message
        self.show_empty_state()
    
    def create_settings_panel(self):
        """Create settings control panel"""
        panel = QGroupBox("⚙️ Settings")
        panel.setStyleSheet(f"""
            QGroupBox {{
                font-size: 14px;
                font-weight: bold;
                color: {COLORS['text_primary']};
                border: 2px solid {COLORS['border_medium']};
                border-radius: 6px;
                margin-top: 10px;
                padding: 15px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Row 1: Bankroll and Kelly Fraction
        row1 = QHBoxLayout()
        
        # Bankroll input
        bankroll_label = QLabel("Bankroll ($):")
        bankroll_label.setStyleSheet(f"font-weight: normal; color: {COLORS['text_primary']};")
        row1.addWidget(bankroll_label)
        
        self.bankroll_input = QLineEdit()
        self.bankroll_input.setText(f"{self.bankroll:.0f}")
        self.bankroll_input.setValidator(QDoubleValidator(1.0, 1000000.0, 2))
        self.bankroll_input.setMaximumWidth(150)
        self.bankroll_input.textChanged.connect(self.on_settings_changed)
        self.bankroll_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border_medium']};
                border-radius: 4px;
                padding: 5px;
                color: {COLORS['text_primary']};
            }}
        """)
        row1.addWidget(self.bankroll_input)
        
        row1.addSpacing(20)
        
        # Kelly fraction selector
        kelly_label = QLabel("Kelly Fraction:")
        kelly_label.setStyleSheet(f"font-weight: normal; color: {COLORS['text_primary']};")
        row1.addWidget(kelly_label)
        
        self.kelly_combo = QComboBox()
        self.kelly_combo.addItems([
            "1/8 Kelly (Very Conservative)",
            "1/4 Kelly (Conservative)",
            "1/3 Kelly (Cautious)",
            "1/2 Kelly (Balanced) ✓",
            "2/3 Kelly (Bold)",
            "Full Kelly (Aggressive)"
        ])
        self.kelly_combo.setCurrentIndex(3)  # Default to Half Kelly
        self.kelly_combo.currentIndexChanged.connect(self.on_settings_changed)
        self.kelly_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border_medium']};
                border-radius: 4px;
                padding: 5px;
                color: {COLORS['text_primary']};
            }}
        """)
        row1.addWidget(self.kelly_combo)
        
        row1.addStretch()
        layout.addLayout(row1)
        
        # Kelly warning label
        self.kelly_warning = QLabel()
        self.kelly_warning.setWordWrap(True)
        self.kelly_warning.setStyleSheet(f"""
            font-weight: normal;
            font-size: 11px;
            color: {COLORS['text_secondary']};
            padding: 5px;
            background-color: {COLORS['bg_tertiary']};
            border-radius: 4px;
        """)
        self.update_kelly_warning()
        layout.addWidget(self.kelly_warning)
        
        # Row 2: Min Edge and Bet Type Filters
        row2 = QHBoxLayout()
        
        # Min edge filter
        edge_label = QLabel("Min Edge:")
        edge_label.setStyleSheet(f"font-weight: normal; color: {COLORS['text_primary']};")
        row2.addWidget(edge_label)
        
        self.edge_combo = QComboBox()
        self.edge_combo.addItems(["5%", "10%", "15%", "20%"])
        self.edge_combo.setCurrentIndex(0)  # Default to 5%
        self.edge_combo.currentIndexChanged.connect(self.on_settings_changed)
        self.edge_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border_medium']};
                border-radius: 4px;
                padding: 5px;
                color: {COLORS['text_primary']};
            }}
        """)
        row2.addWidget(self.edge_combo)
        
        row2.addSpacing(20)
        
        # Market confidence (blending)
        conf_label = QLabel("Market Blend:")
        conf_label.setStyleSheet(f"font-weight: normal; color: {COLORS['text_primary']};")
        conf_label.setToolTip("How much to blend market probability with our model\n0% = Pure model (traditional Kelly)\n65% = Conservative (65% market + 35% model)")
        row2.addWidget(conf_label)
        
        self.market_confidence_combo = QComboBox()
        self.market_confidence_combo.addItems(["0% (Pure Model)", "30% (Slight Blend)", "50% (Balanced)", "65% (Conservative)"])
        self.market_confidence_combo.setCurrentIndex(3)  # Default to 65% (conservative)
        self.market_confidence_combo.currentIndexChanged.connect(self.on_settings_changed)
        self.market_confidence_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border_medium']};
                border-radius: 4px;
                padding: 5px;
                color: {COLORS['text_primary']};
            }}
        """)
        row2.addWidget(self.market_confidence_combo)
        
        row2.addSpacing(20)
        
        # Date Filter
        date_label = QLabel("Date:")
        date_label.setStyleSheet(f"font-weight: normal; color: {COLORS['text_primary']};")
        date_label.setToolTip("Filter races by date\nSelect a specific date for focused betting\nStakes will be calculated for that date only")
        row2.addWidget(date_label)
        
        self.date_combo = QComboBox()
        self.date_combo.addItem("All Dates")
        self.date_combo.currentIndexChanged.connect(self.on_date_changed)
        self.date_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border_medium']};
                border-radius: 4px;
                padding: 5px;
                color: {COLORS['text_primary']};
            }}
        """)
        row2.addWidget(self.date_combo)
        
        row2.addSpacing(20)
        
        # Race Type Filter
        race_type_label = QLabel("Race Type:")
        race_type_label.setStyleSheet(f"font-weight: normal; color: {COLORS['text_primary']};")
        race_type_label.setToolTip("Select which race types to bet on\nFlat: Fastest, shortest races with draw importance\nHurdle/Chase: Jump racing (models not available yet)")
        row2.addWidget(race_type_label)
        
        self.race_type_combo = QComboBox()
        self.race_type_combo.addItems([
            "🏇 Flat Only (Recommended)",
            "🐴 Hurdle Only (Not Available)",
            "🐴 Chase Only (Not Available)",
            "⚠️ All Types (Not Recommended)"
        ])
        
        # Disable non-Flat options for now (no models trained yet)
        for i in range(1, self.race_type_combo.count()):
            model_item = self.race_type_combo.model().item(i)
            model_item.setEnabled(False)
            model_item.setToolTip("Model not available yet - train Hurdle/Chase model first")
        
        self.race_type_combo.setCurrentIndex(0)  # Default to Flat Only
        self.race_type_combo.currentTextChanged.connect(self.on_settings_changed)
        self.race_type_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border_medium']};
                border-radius: 4px;
                padding: 5px;
                color: {COLORS['text_primary']};
            }}
        """)
        row2.addWidget(self.race_type_combo)
        
        row2.addSpacing(20)
        
        # Bet type filters
        filters_label = QLabel("Show:")
        filters_label.setStyleSheet(f"font-weight: normal; color: {COLORS['text_primary']};")
        row2.addWidget(filters_label)
        
        self.win_check = QCheckBox("Win")
        self.win_check.setChecked(True)
        self.win_check.stateChanged.connect(self.on_filter_changed)
        row2.addWidget(self.win_check)
        
        self.place_check = QCheckBox("Place")
        self.place_check.setChecked(True)
        self.place_check.stateChanged.connect(self.on_filter_changed)
        row2.addWidget(self.place_check)
        
        self.exacta_check = QCheckBox("Exacta")
        self.exacta_check.setChecked(True)
        self.exacta_check.stateChanged.connect(self.on_filter_changed)
        row2.addWidget(self.exacta_check)
        
        self.trifecta_check = QCheckBox("Trifecta")
        self.trifecta_check.setChecked(True)
        self.trifecta_check.stateChanged.connect(self.on_filter_changed)
        row2.addWidget(self.trifecta_check)
        
        self.first_four_check = QCheckBox("First 4")
        self.first_four_check.setChecked(True)
        self.first_four_check.stateChanged.connect(self.on_filter_changed)
        row2.addWidget(self.first_four_check)
        
        row2.addStretch()
        layout.addLayout(row2)
        
        panel.setLayout(layout)
        return panel
    
    def create_recommendations_tree(self):
        """Create tree widget for displaying recommendations hierarchically"""
        tree = QTreeWidget()
        tree.setHeaderLabels(["Bet Details", "Stake", "Odds", "EV %", "Potential Profit"])
        tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {COLORS['bg_secondary']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border_medium']};
                border-radius: 6px;
            }}
            QTreeWidget::item {{
                padding: 5px;
            }}
            QTreeWidget::item:hover {{
                background-color: {COLORS['bg_hover']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_tertiary']};
                color: {COLORS['text_primary']};
                padding: 8px;
                border: 1px solid {COLORS['border_medium']};
                font-weight: bold;
            }}
        """)
        tree.setColumnWidth(0, 400)
        tree.setColumnWidth(1, 100)
        tree.setColumnWidth(2, 100)
        tree.setColumnWidth(3, 80)
        tree.setColumnWidth(4, 120)
        
        return tree
    
    def create_summary_panel(self):
        """Create summary panel showing totals"""
        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_tertiary']};
                border: 2px solid {COLORS['accent_green']};
                border-radius: 6px;
                padding: 15px;
            }}
        """)
        
        layout = QHBoxLayout()
        
        self.summary_label = QLabel("No bets to display")
        self.summary_label.setStyleSheet(f"""
            font-size: 13px;
            font-weight: bold;
            color: {COLORS['text_primary']};
        """)
        layout.addWidget(self.summary_label)
        
        layout.addStretch()
        
        panel.setLayout(layout)
        return panel
    
    def show_empty_state(self):
        """Show empty state message"""
        self.recommendations_tree.clear()
        empty_item = QTreeWidgetItem(["Click 'Find Value Bets' to analyze predictions and find value opportunities", "", "", "", ""])
        empty_item.setForeground(0, QColor(COLORS['text_secondary']))
        self.recommendations_tree.addTopLevelItem(empty_item)
        self.summary_label.setText("No bets to display")
        self.export_btn.setEnabled(False)
    
    @Slot()
    def on_settings_changed(self):
        """Handle settings changes"""
        # Update bankroll
        try:
            self.bankroll = float(self.bankroll_input.text())
        except ValueError:
            self.bankroll = 1000.0
        
        # Update Kelly fraction
        kelly_index = self.kelly_combo.currentIndex()
        kelly_values = [0.125, 0.25, 0.33, 0.5, 0.67, 1.0]
        self.kelly_fraction = kelly_values[kelly_index]
        
        # Update min edge
        edge_text = self.edge_combo.currentText().replace('%', '')
        self.min_edge = float(edge_text) / 100.0
        
        # Update market confidence
        conf_index = self.market_confidence_combo.currentIndex()
        conf_values = [0.0, 0.30, 0.50, 0.65]
        self.market_confidence = conf_values[conf_index]
        
        # Update calculator
        self.calculator = BettingCalculator(
            self.bankroll, 
            self.kelly_fraction, 
            self.min_edge,
            self.market_confidence
        )
        
        # Update warning
        self.update_kelly_warning()
        
        # ✅ IMPROVEMENT: Don't auto-regenerate - let user click "Find Value Bets"
        # Show hint that settings have changed if recommendations exist
        if self.all_recommendations:
            self.summary_label.setText("⚠️ Settings changed - click 'Find Value Bets' to recalculate with new parameters")
    
    @Slot()
    def on_filter_changed(self):
        """Handle bet type filter changes"""
        self.show_win = self.win_check.isChecked()
        self.show_place = self.place_check.isChecked()
        self.show_exacta = self.exacta_check.isChecked()
        self.show_trifecta = self.trifecta_check.isChecked()
        self.show_first_four = self.first_four_check.isChecked()
        
        # Redisplay with filters
        if self.all_recommendations:
            self.display_filtered_recommendations()
    
    @Slot()
    def on_date_changed(self):
        """Handle date filter change"""
        date_text = self.date_combo.currentText()
        if date_text == "All Dates":
            self.selected_date = None
        else:
            # Extract date from "2025-10-24 (12 races)" format
            self.selected_date = date_text.split(' ')[0]
        
        # Show hint to regenerate if recommendations exist
        if self.all_recommendations:
            self.summary_label.setText("⚠️ Date filter changed - click 'Find Value Bets' to recalculate")
    
    def update_kelly_warning(self):
        """Update Kelly fraction warning message"""
        description = BettingCalculator.get_kelly_description(self.kelly_fraction)
        self.kelly_warning.setText(description)
    
    def load_available_dates(self):
        """Load available dates from upcoming_races.db into date dropdown"""
        if not self.upcoming_db_path.exists():
            return
        
        try:
            conn = sqlite3.connect(str(self.upcoming_db_path))
            cursor = conn.cursor()
            
            # Get dates with race counts
            cursor.execute("""
                SELECT date, COUNT(*) as race_count
                FROM races
                GROUP BY date
                ORDER BY date
            """)
            dates = cursor.fetchall()
            conn.close()
            
            # Clear existing items (except "All Dates")
            self.date_combo.blockSignals(True)  # Prevent triggering on_date_changed
            self.date_combo.clear()
            
            # Add "All Dates" with total count
            total_races = sum(count for _, count in dates)
            self.date_combo.addItem(f"All Dates ({total_races} races)")
            
            # Add individual dates
            for date, count in dates:
                self.date_combo.addItem(f"{date} ({count} races)")
            
            self.date_combo.blockSignals(False)
            
            # Reset to "All Dates" if current selection is invalid
            if self.selected_date:
                # Try to find and select the current date
                for i in range(self.date_combo.count()):
                    if self.selected_date in self.date_combo.itemText(i):
                        self.date_combo.setCurrentIndex(i)
                        break
                else:
                    # Date not found, reset to All Dates
                    self.date_combo.setCurrentIndex(0)
                    self.selected_date = None
            
        except Exception as e:
            print(f"Error loading dates: {e}")
    
    @Slot()
    def generate_recommendations(self):
        """Generate value betting recommendations from predictions"""
        # Check if predictions exist
        if not self.upcoming_db_path.exists():
            QMessageBox.warning(
                self,
                "No Predictions",
                "Please generate predictions first using the 'Predictions' tab."
            )
            return
        
        try:
            # Load available dates into dropdown
            self.load_available_dates()
            
            # Get all predictions from upcoming_races.db
            conn = sqlite3.connect(str(self.upcoming_db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Check if predictions have been generated (check for any races)
            cursor.execute("SELECT COUNT(*) FROM races")
            race_count = cursor.fetchone()[0]
            
            if race_count == 0:
                QMessageBox.warning(
                    self,
                    "No Races",
                    "No upcoming races found. Please fetch upcoming races first."
                )
                conn.close()
                return
            
            # Get all race IDs
            cursor.execute("SELECT race_id, course, date, off_time FROM races ORDER BY off_time")
            races = cursor.fetchall()
            
            conn.close()
            
            # Load predictions for each race
            all_race_predictions = self.load_all_predictions()
            
            if not all_race_predictions:
                QMessageBox.warning(
                    self,
                    "No Predictions",
                    "No predictions found. Please generate predictions first using the 'Predictions' tab."
                )
                return
            
            # Generate recommendations
            self.all_recommendations = self.analyze_predictions(all_race_predictions)
            
            # Display recommendations
            self.display_filtered_recommendations()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to generate recommendations:\n{str(e)}"
            )
    
    def load_all_predictions(self):
        """
        Load all predictions by generating them from upcoming races
        
        This generates predictions on-the-fly from the upcoming_races.db
        """
        # Import here to avoid circular dependency
        import sys
        from pathlib import Path
        
        # Add parent directory to path for imports
        ml_dir = Path(__file__).parent.parent / "ml"
        if str(ml_dir.parent) not in sys.path:
            sys.path.insert(0, str(ml_dir.parent))
        
        try:
            # Now import with absolute path
            from ml.predictor import ModelPredictor
        except ImportError:
            # Fallback to relative import
            try:
                from ..ml.predictor import ModelPredictor
            except ImportError:
                QMessageBox.critical(
                    self,
                    "Import Error",
                    "Could not import ModelPredictor. Please ensure the ML module is properly installed."
                )
                return []
        
        # Determine race type filter from UI
        race_type_text = self.race_type_combo.currentText()
        if "Flat Only" in race_type_text:
            race_type = 'Flat'
        elif "Hurdle Only" in race_type_text:
            race_type = 'Hurdle'
        elif "Chase Only" in race_type_text:
            race_type = 'Chase'
        else:
            race_type = None  # All types (not recommended)
        
        # Get race IDs with type filtering
        try:
            conn = sqlite3.connect(str(self.upcoming_db_path))
            cursor = conn.cursor()
            
            # Show race type breakdown
            cursor.execute("SELECT type, COUNT(*) FROM races GROUP BY type")
            type_counts = cursor.fetchall()
            print(f"\n📊 Upcoming races by type:")
            for row in type_counts:
                print(f"   {row[0]}: {row[1]} races")
            
            # Apply filters (race type AND date)
            if race_type and self.selected_date:
                cursor.execute("""
                    SELECT race_id, course, date, off_time, type 
                    FROM races 
                    WHERE type = ? AND date = ?
                    ORDER BY off_time
                """, (race_type, self.selected_date))
                print(f"✅ Filtering to {race_type} races on {self.selected_date}")
            elif race_type:
                cursor.execute("""
                    SELECT race_id, course, date, off_time, type 
                    FROM races 
                    WHERE type = ?
                    ORDER BY off_time
                """, (race_type,))
                print(f"✅ Filtering to {race_type} races only (all dates)")
            elif self.selected_date:
                cursor.execute("""
                    SELECT race_id, course, date, off_time, type 
                    FROM races 
                    WHERE date = ?
                    ORDER BY off_time
                """, (self.selected_date,))
                print(f"✅ Filtering to races on {self.selected_date} (all types)")
            else:
                cursor.execute("""
                    SELECT race_id, course, date, off_time, type 
                    FROM races 
                    ORDER BY off_time
                """)
                print(f"⚠️  Loading ALL race types and dates (may have unreliable predictions)")
            
            races = cursor.fetchall()
            conn.close()
            
            print(f"   Analyzing {len(races)} races for value bets...\n")
            
            if not races:
                return []
            
            # Initialize predictor with matching race type
            racing_db_path = Path(__file__).parent.parent / "racing_pro.db"
            predictor = ModelPredictor(
                racing_db_path=str(racing_db_path),
                race_type=race_type or 'Flat'
            )
            
            # Generate predictions for each race
            all_predictions = []
            for race_row in races:
                race_id = race_row[0]
                try:
                    race_predictions = predictor.predict_race(race_id, str(self.upcoming_db_path))
                    if race_predictions:
                        all_predictions.append(race_predictions)
                except Exception as e:
                    print(f"Error predicting race {race_id}: {e}")
                    continue
            
            predictor.close()
            return all_predictions
            
        except Exception as e:
            print(f"Error loading predictions: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def analyze_predictions(self, all_race_predictions):
        """Analyze predictions and generate betting recommendations"""
        recommendations = []
        
        for race_pred in all_race_predictions:
            race_info = race_pred['race_info']
            predictions = race_pred['predictions']
            field_size = len(predictions)
            
            # Collect all potential win and place bets for this race
            win_candidates = []
            place_candidates = []
            
            # Determine how many places are paid
            num_places = 2 if field_size <= 7 else 3
            
            for pred in predictions:
                predicted_rank = pred.get('predicted_rank', 999)
                
                # DEBUG: Log what we're evaluating
                horse_name = pred.get('horse_name', 'Unknown')
                win_prob = pred.get('win_probability', 0)
                market_odds = pred.get('market_odds', 0)
                print(f"  🔍 Evaluating {horse_name}: rank={predicted_rank}, win_prob={win_prob:.1%}, mkt_odds={market_odds}")
                
                if pred.get('market_odds'):
                    # ✅ CRITICAL FIX: Only check WIN bets for horses WE RANK as top contenders
                    # Don't chase longshot EV% - bet on horses we think can actually WIN!
                    # Only consider top 2 horses for win bets (only 1 can win - be VERY selective!)
                    if predicted_rank <= 2:
                        win_rec = self.calculator.recommend_win_bet(pred, pred['market_odds'])
                        if win_rec:
                            print(f"    ✅ Added WIN candidate: {horse_name} (rank {predicted_rank}, EV {win_rec['ev_percentage']:.1f}%)")
                            win_rec['race_info'] = race_info
                            win_candidates.append(win_rec)
                    
                    # ✅ Only check place bets for horses WE RANK highly
                    # Only consider place bets for top N+1 horses (slight buffer)
                    # E.g., if 3 places paid, only look at our top 4 ranked horses
                    if predicted_rank <= (num_places + 1):
                        place_rec = self.calculator.recommend_place_bet(pred, None, field_size)
                        if place_rec:
                            print(f"    ✅ Added PLACE candidate: {horse_name} (rank {predicted_rank}, EV {place_rec['ev_percentage']:.1f}%)")
                            place_rec['race_info'] = race_info
                            place_candidates.append(place_rec)
            
            # DEBUG: Show what we collected for this race
            print(f"  📊 Race summary: {len(win_candidates)} win candidates, {len(place_candidates)} place candidates")
            if win_candidates:
                win_names = [f"{w['horse_name']}" for w in win_candidates]
                print(f"     Win candidates: {win_names}")
            if place_candidates:
                place_names = [f"{p['horse_name']}" for p in place_candidates]
                print(f"     Place candidates: {place_names}")
            
            # Only keep the BEST win bets per race
            # ✅ Sort by our win probability (highest first), not EV%
            # We want to bet on horses WE THINK will win, not longshots with high EV%
            win_candidates.sort(key=lambda x: x['our_probability'], reverse=True)
            
            # Add only the best win bet(s) from our top 2 ranked horses
            # Usually only bet rank 1, maybe rank 2 if it has strong probability (>12%)
            max_win_bets = 2 if len(win_candidates) > 1 and win_candidates[1]['our_probability'] > 0.12 else 1
            for win_rec in win_candidates[:max_win_bets]:
                # Only add if EV is significant (but lower threshold since we filtered by rank)
                if win_rec['ev_percentage'] >= 5:  # At least 5% edge for win bets
                    recommendations.append(win_rec)
            
            # Only keep the BEST place bets per race
            # ✅ Sort by our probability (highest first), not EV%
            # We want to bet on horses WE THINK will place, not longshots with high EV%
            place_candidates.sort(key=lambda x: x['our_probability'], reverse=True)
            
            # Add top 2-3 place bets depending on field size
            # Smaller fields = fewer place bets make sense
            if field_size <= 7:
                max_place_bets = 2  # Only 2 places paid
            else:
                max_place_bets = 3  # 3 places paid
            
            for place_rec in place_candidates[:max_place_bets]:
                # Only add if EV is significant (but lower threshold since we filtered by rank)
                if place_rec['ev_percentage'] >= 5:  # At least 5% edge for place bets
                    recommendations.append(place_rec)
            
            # Analyze exotic bets - only if we have strong top picks
            if len(predictions) >= 2 and predictions[0].get('win_probability', 0) > 0.15:
                exacta_rec = self.calculator.recommend_exacta(predictions[:2])
                if exacta_rec:
                    exacta_rec['race_info'] = race_info
                    recommendations.append(exacta_rec)
            
            if len(predictions) >= 3 and predictions[0].get('win_probability', 0) > 0.20:
                trifecta_rec = self.calculator.recommend_trifecta(predictions[:3])
                if trifecta_rec:
                    trifecta_rec['race_info'] = race_info
                    recommendations.append(trifecta_rec)
            
            if len(predictions) >= 4 and predictions[0].get('win_probability', 0) > 0.25:
                first_four_rec = self.calculator.recommend_first_four(predictions[:4])
                if first_four_rec:
                    first_four_rec['race_info'] = race_info
                    recommendations.append(first_four_rec)
        
        # Apply portfolio scaling before returning
        recommendations = self.calculator.scale_recommendations_to_bankroll(
            recommendations,
            max_allocation=0.6  # Use max 60% of bankroll across all bets
        )
        
        return recommendations
    
    def display_filtered_recommendations(self):
        """Display recommendations filtered by bet type"""
        self.recommendations_tree.clear()
        
        # Filter recommendations
        filtered = []
        for rec in self.all_recommendations:
            bet_type = rec['bet_type']
            if bet_type == 'WIN' and self.show_win:
                filtered.append(rec)
            elif bet_type == 'PLACE' and self.show_place:
                filtered.append(rec)
            elif bet_type == 'EXACTA' and self.show_exacta:
                filtered.append(rec)
            elif bet_type == 'TRIFECTA' and self.show_trifecta:
                filtered.append(rec)
            elif bet_type == 'FIRST FOUR' and self.show_first_four:
                filtered.append(rec)
        
        if not filtered:
            self.show_empty_state()
            return
        
        # Organize by date -> course -> race
        organized = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        
        for rec in filtered:
            race_info = rec['race_info']
            date_str = race_info.get('date', 'Unknown')
            course = race_info.get('course', 'Unknown')
            time = race_info.get('time', '').split()[-1] if race_info.get('time') else 'TBA'
            
            # Build race key with name if available
            race_name = race_info.get('race_name', '')
            distance = race_info.get('distance', '')
            race_class = race_info.get('race_class', '')
            race_type = race_info.get('type', 'Unknown')
            
            # Add emoji for race type
            type_emoji = '🏇' if race_type == 'Flat' else '🐴'
            
            if race_name:
                # If race name exists, show it with time, type, and class
                race_key = f"{time} - {race_name} {type_emoji} ({race_type}, {distance}, {race_class})" if race_class else f"{time} - {race_name} {type_emoji} ({race_type}, {distance})"
            else:
                # Fallback to original format with type
                race_key = f"{time} - {distance} - {race_type} {type_emoji} - {race_class}"
            
            organized[date_str][course][race_key].append(rec)
        
        # Build tree
        for date in sorted(organized.keys()):
            date_item = QTreeWidgetItem([f"📅 {date}", "", "", "", ""])
            date_font = QFont()
            date_font.setBold(True)
            date_font.setPointSize(12)
            date_item.setFont(0, date_font)
            date_item.setForeground(0, QColor(COLORS['accent_blue']))
            self.recommendations_tree.addTopLevelItem(date_item)
            date_item.setExpanded(True)
            
            for course in sorted(organized[date].keys()):
                course_bets = sum(len(bets) for bets in organized[date][course].values())
                course_item = QTreeWidgetItem([f"🏇 {course} ({course_bets} bets)", "", "", "", ""])
                course_font = QFont()
                course_font.setBold(True)
                course_item.setFont(0, course_font)
                course_item.setForeground(0, QColor(COLORS['accent_green']))
                date_item.addChild(course_item)
                course_item.setExpanded(True)
                
                for race in sorted(organized[date][course].keys()):
                    race_item = QTreeWidgetItem([f"   {race}", "", "", "", ""])
                    race_item.setForeground(0, QColor(COLORS['text_secondary']))
                    course_item.addChild(race_item)
                    race_item.setExpanded(True)
                    
                    for rec in organized[date][course][race]:
                        self.add_bet_item(race_item, rec)
        
        # Update summary
        self.update_summary(filtered)
        self.export_btn.setEnabled(True)
    
    def add_bet_item(self, parent_item, rec):
        """Add a bet recommendation to the tree"""
        bet_type = rec['bet_type']
        
        # Format bet details
        if bet_type in ['WIN', 'PLACE']:
            details = f"      {bet_type}: {rec['horse_name']} (#{rec.get('runner_number', '?')})"
        else:
            details = f"      {bet_type}: {rec['combination']}"
        
        stake_text = f"${rec['stake']:.2f}"
        
        # Format odds with label to show what type they are
        if bet_type == 'WIN':
            odds_text = f"Win: {rec['market_odds']:.2f}"
        elif bet_type == 'PLACE':
            odds_text = f"Place: {rec['market_odds']:.2f}"
        else:
            odds_text = f"{rec['market_odds']:.2f}"
        
        ev_text = f"{rec['ev_percentage']:.1f}%"
        profit_text = f"${rec['potential_profit']:.2f}"
        
        bet_item = QTreeWidgetItem([details, stake_text, odds_text, ev_text, profit_text])
        
        # Color code by bet type
        if bet_type == 'WIN':
            bet_item.setForeground(0, QColor('#5CB85C'))
        elif bet_type == 'PLACE':
            bet_item.setForeground(0, QColor('#5DADE2'))
        else:
            bet_item.setForeground(0, QColor('#F0AD4E'))
        
        parent_item.addChild(bet_item)
    
    def update_summary(self, recommendations):
        """Update summary panel with totals"""
        total_bets = len(recommendations)
        total_stake = sum(rec['stake'] for rec in recommendations)
        total_expected_profit = sum(rec['potential_profit'] * rec['our_probability'] for rec in recommendations)
        roi = (total_expected_profit / total_stake * 100) if total_stake > 0 else 0
        
        summary_text = (
            f"📊 Total Bets: {total_bets} | "
            f"💰 Total Stake: ${total_stake:.2f} | "
            f"📈 Expected Profit: ${total_expected_profit:.2f} ({roi:.1f}% ROI)"
        )
        self.summary_label.setText(summary_text)
    
    @Slot()
    def export_recommendations(self):
        """Export recommendations to CSV"""
        if not self.all_recommendations:
            return
        
        # Get save file path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Betting Recommendations",
            f"betting_recommendations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow([
                    'Date', 'Course', 'Time', 'Race Type', 'Race Details', 'Bet Type', 'Selection',
                    'Our Odds', 'Market Odds', 'Stake', 'EV %', 'Potential Profit'
                ])
                
                # Write recommendations
                for rec in self.all_recommendations:
                    race_info = rec['race_info']
                    
                    if rec['bet_type'] in ['WIN', 'PLACE']:
                        selection = f"{rec['horse_name']} (#{rec.get('runner_number', '?')})"
                    else:
                        selection = rec['combination']
                    
                    # Format race details with name and type
                    race_name = race_info.get('race_name', '')
                    distance = race_info.get('distance', '')
                    race_class = race_info.get('race_class', '')
                    race_type = race_info.get('type', 'Unknown')
                    
                    if race_name:
                        race_details = f"{race_name} ({distance}, {race_class})" if race_class else f"{race_name} ({distance})"
                    else:
                        race_details = f"{distance} - {race_class}"
                    
                    # Format market odds with label for clarity
                    bet_type = rec['bet_type']
                    if bet_type == 'WIN':
                        market_odds_display = f"Win: {rec['market_odds']:.2f}"
                    elif bet_type == 'PLACE':
                        market_odds_display = f"Place: {rec['market_odds']:.2f}"
                    else:
                        market_odds_display = f"{rec['market_odds']:.2f}"
                    
                    row = [
                        race_info.get('date', ''),
                        race_info.get('course', ''),
                        race_info.get('time', '').split()[-1] if race_info.get('time') else '',
                        race_type,  # Add race type column
                        race_details,
                        bet_type,
                        selection,
                        f"{rec['our_odds']:.2f}",
                        market_odds_display,
                        f"{rec['stake']:.2f}",
                        f"{rec['ev_percentage']:.1f}",
                        f"{rec['potential_profit']:.2f}"
                    ]
                    writer.writerow(row)
            
            QMessageBox.information(
                self,
                "Export Successful",
                f"Betting recommendations exported to:\n{file_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export recommendations:\n{str(e)}"
            )

