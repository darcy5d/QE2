"""
ML Training View - Train and evaluate ML models
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                QPushButton, QComboBox, QTextEdit, QFrame,
                                QSlider, QSpinBox, QGroupBox, QTableWidget,
                                QTableWidgetItem, QMessageBox, QScrollArea,
                                QHeaderView, QDialog, QDialogButtonBox, QCheckBox)
from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtGui import QFont
from pathlib import Path
import json

from .database import DatabaseHelper
from .ml_database_helper import MLDatabaseHelper
from .training_worker import TrainingWorker
from .feature_regen_worker import FeatureRegenWorker


class MLTrainingView(QWidget):
    """ML model training interface"""
    
    def __init__(self, db_helper: DatabaseHelper, parent=None):
        super().__init__(parent)
        self.db = db_helper
        self.ml_db = MLDatabaseHelper(db_helper.db_path)
        self.current_worker = None
        self.feature_regen_worker = None
        self.last_results = None
        self.pending_training_config = None  # Store config if regenerating features first
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the training view UI"""
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Left panel - Model selection and configuration
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)
        
        # Right panel - Training output and results
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 2)
        
        self.setLayout(main_layout)
        self.setStyleSheet("background-color: #1E1E1E; color: white;")
    
    def create_left_panel(self) -> QWidget:
        """Create left configuration panel"""
        panel = QFrame()
        panel.setMaximumWidth(400)
        panel.setStyleSheet("""
            QFrame {
                background-color: #2A2A2A;
                border-right: 1px solid #555;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Model Training")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        
        # Model selection
        model_label = QLabel("Select Model:")
        model_label.setStyleSheet("color: white; font-weight: bold;")
        layout.addWidget(model_label)
        
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "XGBoost Winner Classifier",
            "XGBoost Top 3 Classifier (Coming Soon)",
            "Neural Network (Coming Soon)"
        ])
        self.model_combo.setStyleSheet("""
            QComboBox {
                background-color: #3A3A3A;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #3A3A3A;
                color: white;
                selection-background-color: #4A90E2;
            }
        """)
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        layout.addWidget(self.model_combo)
        
        # Race Type Selector
        race_type_label = QLabel("Race Type:")
        race_type_label.setStyleSheet("color: white; font-weight: bold; margin-top: 15px;")
        layout.addWidget(race_type_label)
        
        self.race_type_combo = QComboBox()
        self.race_type_combo.addItems([
            "🏇 Flat (Recommended)",
            "🐴 Hurdle (Not Available)",
            "🐴 Chase (Not Available)"
        ])
        self.race_type_combo.setStyleSheet("""
            QComboBox {
                background-color: #3A3A3A;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #3A3A3A;
                color: white;
                selection-background-color: #4A90E2;
            }
        """)
        self.race_type_combo.setToolTip("Select which type of races to train on\nFlat: Shorter, faster races (draw important)\nHurdle/Chase: Jump racing (different dynamics)")
        
        # Disable non-Flat options for now
        for i in range(1, self.race_type_combo.count()):
            model_item = self.race_type_combo.model().item(i)
            model_item.setEnabled(False)
            model_item.setToolTip("Model not available - train Flat model first, then expand to Jump racing")
        
        self.race_type_combo.currentTextChanged.connect(self.update_model_output_name)
        layout.addWidget(self.race_type_combo)
        
        # Model output filename display
        output_name_label = QLabel("Model Output:")
        output_name_label.setStyleSheet("color: #888; font-size: 11px; margin-top: 5px;")
        layout.addWidget(output_name_label)
        
        self.model_output_label = QLabel("xgboost_flat.json")
        self.model_output_label.setStyleSheet("""
            color: #4A90E2;
            font-family: 'Courier New', monospace;
            font-size: 11px;
            padding: 5px;
            background-color: #1E1E1E;
            border: 1px solid #555;
            border-radius: 3px;
        """)
        layout.addWidget(self.model_output_label)
        
        # Model explanation
        explanation_label = QLabel("Model Details:")
        explanation_label.setStyleSheet("color: white; font-weight: bold; margin-top: 10px;")
        layout.addWidget(explanation_label)
        
        self.explanation_text = QTextEdit()
        self.explanation_text.setReadOnly(True)
        self.explanation_text.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        self.explanation_text.setMaximumHeight(300)
        layout.addWidget(self.explanation_text)
        
        # Configuration group
        config_group = QGroupBox("Configuration")
        config_group.setStyleSheet("""
            QGroupBox {
                color: white;
                border: 1px solid #555;
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
        config_layout = QVBoxLayout()
        
        # Test size slider
        test_size_layout = QHBoxLayout()
        test_size_label = QLabel("Test Size:")
        test_size_label.setStyleSheet("color: white;")
        test_size_layout.addWidget(test_size_label)
        
        self.test_size_slider = QSlider(Qt.Horizontal)
        self.test_size_slider.setMinimum(10)
        self.test_size_slider.setMaximum(30)
        self.test_size_slider.setValue(20)
        self.test_size_slider.setTickPosition(QSlider.TicksBelow)
        self.test_size_slider.setTickInterval(5)
        self.test_size_slider.valueChanged.connect(self.update_test_size_label)
        test_size_layout.addWidget(self.test_size_slider)
        
        self.test_size_value = QLabel("20%")
        self.test_size_value.setStyleSheet("color: white; min-width: 40px;")
        test_size_layout.addWidget(self.test_size_value)
        
        config_layout.addLayout(test_size_layout)
        
        # Random seed
        seed_layout = QHBoxLayout()
        seed_label = QLabel("Random Seed:")
        seed_label.setStyleSheet("color: white;")
        seed_layout.addWidget(seed_label)
        
        self.seed_input = QSpinBox()
        self.seed_input.setMinimum(0)
        self.seed_input.setMaximum(9999)
        self.seed_input.setValue(42)
        self.seed_input.setStyleSheet("""
            QSpinBox {
                background-color: #3A3A3A;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        seed_layout.addWidget(self.seed_input)
        seed_layout.addStretch()
        
        config_layout.addLayout(seed_layout)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Feature regeneration section
        features_group = QGroupBox("Features")
        features_group.setStyleSheet("""
            QGroupBox {
                color: white;
                border: 1px solid #555;
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
        features_layout = QVBoxLayout()
        
        # Auto-regenerate checkbox
        self.auto_regen_checkbox = QCheckBox("Regenerate features before training")
        self.auto_regen_checkbox.setStyleSheet("color: white;")
        self.auto_regen_checkbox.setToolTip("Automatically rebuild ML features with latest data before training")
        features_layout.addWidget(self.auto_regen_checkbox)
        
        # Manual regenerate button
        self.regen_button = QPushButton("🔄 Regenerate Features Now")
        self.regen_button.setStyleSheet("""
            QPushButton {
                background-color: #F39C12;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #E67E22;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        self.regen_button.clicked.connect(self.start_feature_regeneration)
        features_layout.addWidget(self.regen_button)
        
        # Info label
        info_label = QLabel("Regenerates all 83 features including\nfield strength, draw bias, and pace metrics")
        info_label.setStyleSheet("color: #999; font-size: 11px; margin-top: 5px;")
        info_label.setWordWrap(True)
        features_layout.addWidget(info_label)
        
        features_group.setLayout(features_layout)
        layout.addWidget(features_group)
        
        # Train button
        self.train_button = QPushButton("🚀 Train Model")
        self.train_button.setStyleSheet("""
            QPushButton {
                background-color: #5CB85C;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 15px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4CAF50;
            }
            QPushButton:pressed {
                background-color: #45A049;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        self.train_button.clicked.connect(self.start_training)
        layout.addWidget(self.train_button)
        
        # View saved models button
        self.view_models_button = QPushButton("📁 View Saved Models")
        self.view_models_button.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
        """)
        self.view_models_button.clicked.connect(self.show_saved_models)
        layout.addWidget(self.view_models_button)
        
        layout.addStretch()
        
        panel.setLayout(layout)
        
        # Load initial explanation
        self.on_model_changed(self.model_combo.currentText())
        
        return panel
    
    def create_right_panel(self) -> QWidget:
        """Create right results panel"""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("Training Output")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        
        # Training log
        self.training_log = QTextEdit()
        self.training_log.setReadOnly(True)
        self.training_log.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #00FF00;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 10px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
            }
        """)
        self.training_log.setPlaceholderText("Training output will appear here...")
        layout.addWidget(self.training_log, 2)
        
        # Results section
        results_label = QLabel("Results")
        results_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px; margin-top: 10px;")
        layout.addWidget(results_label)
        
        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout()
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_widget.setLayout(self.results_layout)
        
        # Wrap in scroll area
        scroll = QScrollArea()
        scroll.setWidget(self.results_widget)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #555;
                border-radius: 4px;
                background-color: #2A2A2A;
            }
        """)
        layout.addWidget(scroll, 1)
        
        panel.setLayout(layout)
        return panel
    
    def get_model_explanation(self, model_type: str) -> str:
        """Get detailed explanation for model type"""
        
        explanations = {
            "XGBoost Winner Classifier": """
<h3>XGBoost Ranking Model (NEW!)</h3>
<p><b>Algorithm:</b> Gradient Boosted Decision Trees with Pairwise Ranking<br>
<b>Task:</b> Rank horses within each race</p>

<h4>How it works:</h4>
<ul>
<li>Learns to compare pairs of horses in same race</li>
<li>Understands horses compete TOGETHER, not in isolation</li>
<li>Outputs ranking scores (higher = better chance)</li>
<li>Converts scores to probabilities using softmax</li>
<li>Probabilities naturally sum to 100% per race</li>
</ul>

<h4>Why Ranking > Binary Classification:</h4>
<ul>
<li>✓ Race-aware: Knows which horses compete together</li>
<li>✓ Field strength: Distinguishes weak vs competitive races</li>
<li>✓ Valid probabilities: Always sum to 100% (no manual fix needed)</li>
<li>✓ Better accuracy: Learns relative performance, not absolute</li>
<li>✓ Context-aware: Same horse rated differently vs weak/strong fields</li>
</ul>

<h4>Metrics:</h4>
<ul>
<li><b>NDCG@3:</b> Ranking quality for top 3 predictions</li>
<li><b>Top Pick Win Rate:</b> % of races where highest-scored horse wins</li>
<li><b>Top 3 Hit Rate:</b> % of races where winner is in predicted top 3</li>
<li><b>Mean Reciprocal Rank:</b> Average position of actual winner in predictions</li>
<li><b>Spearman Correlation:</b> Rank order accuracy</li>
</ul>

<h4>Features Used (83 total):</h4>
<ul>
<li><b>Horse (19):</b> career stats, form, performance, TSR, running style</li>
<li><b>Trainer (9):</b> recent form, specialization, rating vs field</li>
<li><b>Jockey (9):</b> win rates, expertise, rating vs field</li>
<li><b>Combo (3):</b> trainer-jockey partnership statistics</li>
<li><b>Race Context (7):</b> distance, going, class, prize money</li>
<li><b>Runner (7):</b> rating, draw, weight, headgear</li>
<li><b>Field Strength (13):</b> best/avg/worst RPR, rank vs field, quartile</li>
<li><b>Draw Bias (4):</b> historical draw performance, normalized position</li>
<li><b>Pace (4):</b> TSR trends, running style, pace pressure</li>
<li><b>Relative (8):</b> ranks for weight, age, rating vs averages</li>
</ul>

<p><b>New in this version:</b> 23 new race-context features including field strength,
draw bias analysis, pace dynamics, and speed ratings!</p>
            """,
            
            "XGBoost Top 3 Classifier (Coming Soon)": """
<h3>XGBoost Top 3 Classifier</h3>
<p><b>Status:</b> Coming Soon</p>

<p>This model will predict whether a horse finishes in the top 3 (placed)
rather than just winning. Higher success rate but lower odds.</p>

<h4>Planned Features:</h4>
<ul>
<li>Multi-class classification (1st, 2nd, 3rd, 4th+)</li>
<li>Place probability distribution</li>
<li>Each-way betting strategy optimization</li>
</ul>
            """,
            
            "Neural Network (Coming Soon)": """
<h3>Neural Network</h3>
<p><b>Status:</b> Coming Soon</p>

<p>Deep learning approach using PyTorch for more complex pattern recognition.</p>

<h4>Planned Architecture:</h4>
<ul>
<li>Feedforward neural network with 3-4 hidden layers</li>
<li>Batch normalization and dropout for regularization</li>
<li>Softmax output for position prediction</li>
<li>Custom loss function for ranking</li>
</ul>

<h4>Potential Advantages:</h4>
<ul>
<li>Can learn non-linear feature interactions</li>
<li>More flexible than tree-based models</li>
<li>Can incorporate race-level attention mechanisms</li>
</ul>
            """
        }
        
        return explanations.get(model_type, "<p>Model explanation not available</p>")
    
    @Slot(str)
    def on_model_changed(self, model_type: str):
        """Update explanation when model selection changes"""
        explanation = self.get_model_explanation(model_type)
        self.explanation_text.setHtml(explanation)
        
        # Disable training for non-implemented models
        is_available = "Coming Soon" not in model_type
        self.train_button.setEnabled(is_available)
    
    @Slot(int)
    def update_test_size_label(self, value: int):
        """Update test size label"""
        self.test_size_value.setText(f"{value}%")
    
    @Slot()
    def update_model_output_name(self):
        """Update model output filename based on race type"""
        race_type_text = self.race_type_combo.currentText()
        race_type = race_type_text.split()[1] if len(race_type_text.split()) > 1 else "Flat"  # Extract "Flat" from emoji text
        race_type_lower = race_type.lower()
        self.model_output_label.setText(f"xgboost_{race_type_lower}.json")
    
    @Slot()
    def start_training(self):
        """Start model training in background"""
        model_type = self.model_combo.currentText()
        
        # Clear previous results
        self.training_log.clear()
        self.clear_results()
        
        # Get configuration
        config = {
            'test_size': self.test_size_slider.value() / 100.0,
            'random_seed': self.seed_input.value()
        }
        
        # Check if we should regenerate features first
        if self.auto_regen_checkbox.isChecked():
            self.append_log("Auto-regenerate enabled: Rebuilding features first...\n")
            # Extract race type from combo box
            race_type_text = self.race_type_combo.currentText()
            race_type = race_type_text.split()[1] if len(race_type_text.split()) > 1 else "Flat"
            self.pending_training_config = {'model_type': model_type, 'config': config, 'race_type': race_type}
            self.start_feature_regeneration()
            return
        
        # Disable buttons
        self.train_button.setEnabled(False)
        self.regen_button.setEnabled(False)
        self.train_button.setText("Training...")
        
        # Start worker thread
        # Extract race type from combo box
        race_type_text = self.race_type_combo.currentText()
        race_type = race_type_text.split()[1] if len(race_type_text.split()) > 1 else "Flat"
        
        self.current_worker = TrainingWorker(
            model_type=model_type,
            config=config,
            db_path=self.db.db_path,
            race_type=race_type
        )
        
        self.current_worker.progress_update.connect(self.append_log)
        self.current_worker.training_complete.connect(self.on_training_complete)
        self.current_worker.training_error.connect(self.on_training_error)
        self.current_worker.finished.connect(self.on_worker_finished)
        
        self.current_worker.start()
    
    @Slot()
    def start_feature_regeneration(self):
        """Start feature regeneration in background"""
        # Disable buttons
        self.regen_button.setEnabled(False)
        self.train_button.setEnabled(False)
        self.regen_button.setText("Regenerating...")
        
        # Start worker thread
        self.feature_regen_worker = FeatureRegenWorker(
            db_path=self.db.db_path,
            limit=None  # No limit - full regeneration
        )
        
        self.feature_regen_worker.progress_update.connect(self.append_log)
        self.feature_regen_worker.regeneration_complete.connect(self.on_regeneration_complete)
        self.feature_regen_worker.regeneration_error.connect(self.on_regeneration_error)
        self.feature_regen_worker.finished.connect(self.on_regen_worker_finished)
        
        self.feature_regen_worker.start()
    
    @Slot(dict)
    def on_regeneration_complete(self, results: dict):
        """Handle feature regeneration completion"""
        self.append_log(f"\n✅ Feature regeneration complete!")
        self.append_log(f"   Processed {results['races_processed']:,} races")
        self.append_log(f"   Generated features for {results['runners_processed']:,} runners")
        self.append_log(f"   Total features in database: {results['total_features']:,}\n")
        
        # If this was a pre-training step, start training now
        if self.pending_training_config:
            self.append_log("="*60)
            self.append_log("Starting model training with fresh features...\n")
            
            config = self.pending_training_config
            self.pending_training_config = None
            
            # Start training
            self.current_worker = TrainingWorker(
                model_type=config['model_type'],
                config=config['config'],
                db_path=self.db.db_path,
                race_type=config.get('race_type', 'Flat')
            )
            
            self.current_worker.progress_update.connect(self.append_log)
            self.current_worker.training_complete.connect(self.on_training_complete)
            self.current_worker.training_error.connect(self.on_training_error)
            self.current_worker.finished.connect(self.on_worker_finished)
            
            self.current_worker.start()
        else:
            # Just regeneration - show completion message
            QMessageBox.information(
                self,
                "Features Regenerated",
                f"Successfully regenerated ML features!\n\n"
                f"Races: {results['races_processed']:,}\n"
                f"Runners: {results['runners_processed']:,}\n"
                f"Features: {results['total_features']:,}\n\n"
                f"You can now train the model with fresh data."
            )
    
    @Slot(str)
    def on_regeneration_error(self, error: str):
        """Handle feature regeneration error"""
        self.append_log(f"\n\n❌ REGENERATION ERROR:\n{error}")
        
        # Clear pending training if any
        if self.pending_training_config:
            self.pending_training_config = None
            QMessageBox.critical(
                self,
                "Feature Regeneration Failed",
                f"Feature regeneration failed. Training cancelled.\n\nError: {error}"
            )
        else:
            QMessageBox.critical(
                self,
                "Feature Regeneration Error",
                f"Feature regeneration failed.\n\nError: {error}"
            )
    
    @Slot()
    def on_regen_worker_finished(self):
        """Re-enable buttons when regeneration worker finishes"""
        # Only re-enable if not starting training next
        if not self.pending_training_config:
            self.regen_button.setEnabled(True)
            self.train_button.setEnabled(True)
        self.regen_button.setText("🔄 Regenerate Features Now")
    
    @Slot(str)
    def append_log(self, message: str):
        """Append message to training log"""
        self.training_log.append(message)
        # Auto-scroll to bottom
        self.training_log.verticalScrollBar().setValue(
            self.training_log.verticalScrollBar().maximum()
        )
    
    @Slot(dict)
    def on_training_complete(self, results: dict):
        """Handle training completion"""
        self.last_results = results
        self.display_results(results)
        
        QMessageBox.information(
            self,
            "Training Complete",
            f"Model trained successfully!\n\nModel saved to:\n{results.get('model_path', 'N/A')}"
        )
    
    @Slot(str)
    def on_training_error(self, error: str):
        """Handle training error"""
        self.append_log(f"\n\n❌ ERROR:\n{error}")
        QMessageBox.critical(self, "Training Error", error)
    
    @Slot()
    def on_worker_finished(self):
        """Re-enable training button when worker finishes"""
        self.train_button.setEnabled(True)
        self.train_button.setText("🚀 Train Model")
    
    def display_results(self, results: dict):
        """Display training results"""
        self.clear_results()
        
        metrics = results.get('metrics', {})
        
        # Metrics table
        metrics_table = self.create_metrics_table(metrics)
        self.results_layout.addWidget(metrics_table)
        
        # Feature importance
        feature_importance = results.get('feature_importance', [])
        if feature_importance:
            importance_label = QLabel("Top 10 Important Features")
            importance_label.setStyleSheet("color: white; font-weight: bold; margin-top: 10px;")
            self.results_layout.addWidget(importance_label)
            
            importance_table = self.create_feature_importance_table(feature_importance[:10])
            self.results_layout.addWidget(importance_table)
        
        # View full results button
        view_full_btn = QPushButton("📊 View Full Results")
        view_full_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
        """)
        view_full_btn.clicked.connect(lambda: self.show_full_results(results))
        self.results_layout.addWidget(view_full_btn)
    
    def create_metrics_table(self, metrics: dict) -> QTableWidget:
        """Create table showing key metrics"""
        table = QTableWidget()
        table.setStyleSheet("""
            QTableWidget {
                background-color: #2A2A2A;
                color: white;
                border: 1px solid #555;
                gridline-color: #555;
            }
            QHeaderView::section {
                background-color: #3A3A3A;
                color: white;
                padding: 8px;
                border: 1px solid #555;
                font-weight: bold;
            }
        """)
        
        # Display key metrics
        # Check if we have ranking metrics (new model) or classification metrics (old model)
        if 'mean_reciprocal_rank' in metrics:
            # Ranking model metrics
            key_metrics = [
                ('Top Pick Win Rate', metrics.get('top_pick_accuracy', 0)),
                ('Top 3 Hit Rate', metrics.get('top_3_hit_rate', 0)),
                ('NDCG@1', metrics.get('ndcg@1', 0)),
                ('NDCG@3', metrics.get('ndcg@3', 0)),
                ('NDCG@5', metrics.get('ndcg@5', 0)),
                ('Mean Reciprocal Rank', metrics.get('mean_reciprocal_rank', 0)),
                ('Avg Spearman Corr', metrics.get('avg_spearman', 0)),
                ('Test Races', metrics.get('num_test_races', 0))
            ]
        else:
            # Binary classification metrics (backward compatibility)
            key_metrics = [
                ('Accuracy', metrics.get('accuracy', 0)),
                ('Precision', metrics.get('precision', 0)),
                ('Recall', metrics.get('recall', 0)),
                ('F1 Score', metrics.get('f1', 0)),
                ('AUC-ROC', metrics.get('auc', 0)),
                ('Log Loss', metrics.get('log_loss', 0)),
                ('Top Pick Win Rate', metrics.get('top_pick_accuracy', 0)),
                ('Top 3 Hit Rate', metrics.get('top_3_hit_rate', 0))
            ]
        
        table.setRowCount(len(key_metrics))
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(['Metric', 'Value'])
        
        for i, (metric, value) in enumerate(key_metrics):
            table.setItem(i, 0, QTableWidgetItem(metric))
            
            if isinstance(value, float):
                display_value = f"{value:.4f}" if value < 10 else f"{value:.2f}"
            else:
                display_value = str(value)
            
            table.setItem(i, 1, QTableWidgetItem(display_value))
        
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        table.setMaximumHeight(300)
        
        return table
    
    def create_feature_importance_table(self, features: list) -> QTableWidget:
        """Create table showing feature importance"""
        table = QTableWidget()
        table.setStyleSheet("""
            QTableWidget {
                background-color: #2A2A2A;
                color: white;
                border: 1px solid #555;
                gridline-color: #555;
            }
            QHeaderView::section {
                background-color: #3A3A3A;
                color: white;
                padding: 8px;
                border: 1px solid #555;
                font-weight: bold;
            }
        """)
        
        table.setRowCount(len(features))
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(['Feature', 'Importance'])
        
        for i, feat in enumerate(features):
            table.setItem(i, 0, QTableWidgetItem(feat.get('feature', '')))
            importance = feat.get('importance', 0)
            table.setItem(i, 1, QTableWidgetItem(f"{importance:.4f}"))
        
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        table.setMaximumHeight(350)
        
        return table
    
    def clear_results(self):
        """Clear results display"""
        while self.results_layout.count():
            child = self.results_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    @Slot()
    def show_full_results(self, results: dict):
        """Show full results in a dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Full Training Results")
        dialog.setMinimumSize(600, 500)
        
        layout = QVBoxLayout()
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: white;
                font-family: 'Courier New', monospace;
            }
        """)
        
        # Format results as JSON
        formatted = json.dumps(results, indent=2, default=str)
        text_edit.setPlainText(formatted)
        
        layout.addWidget(text_edit)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    @Slot()
    def show_saved_models(self):
        """Show list of saved models"""
        models = self.ml_db.get_trained_models()
        
        if not models:
            QMessageBox.information(self, "Saved Models", "No trained models found.")
            return
        
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Saved Models")
        dialog.setMinimumSize(500, 300)
        
        layout = QVBoxLayout()
        
        table = QTableWidget()
        table.setRowCount(len(models))
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(['Model Name', 'Size (KB)', 'Modified'])
        
        for i, model in enumerate(models):
            table.setItem(i, 0, QTableWidgetItem(model['name']))
            table.setItem(i, 1, QTableWidgetItem(f"{model['size']/1024:.1f}"))
            
            from datetime import datetime
            mod_time = datetime.fromtimestamp(model['modified'])
            table.setItem(i, 2, QTableWidgetItem(mod_time.strftime('%Y-%m-%d %H:%M')))
        
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(table)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        dialog.exec()

