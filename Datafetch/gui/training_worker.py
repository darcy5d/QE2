"""
Training Worker - Background thread for model training
Runs ML model training without blocking the GUI
"""

from PySide6.QtCore import QThread, Signal
import sys
import logging
from pathlib import Path
from io import StringIO
import traceback


class LogCapture(logging.Handler):
    """Custom logging handler to capture logs and emit signals"""
    
    def __init__(self, signal):
        super().__init__()
        self.signal = signal
        
    def emit(self, record):
        msg = self.format(record)
        self.signal.emit(msg)


class TrainingWorker(QThread):
    """Worker thread for training ML models"""
    
    progress_update = Signal(str)  # Log messages
    training_complete = Signal(dict)  # Training results
    training_error = Signal(str)  # Error messages
    
    def __init__(self, model_type: str, config: dict, db_path: str):
        super().__init__()
        self.model_type = model_type
        self.config = config
        self.db_path = db_path
        
    def run(self):
        """Run the training process"""
        try:
            self.progress_update.emit("="*60)
            self.progress_update.emit(f"Starting training: {self.model_type}")
            self.progress_update.emit("="*60)
            
            # Import training module (inside run to avoid import issues)
            sys.path.insert(0, str(Path(self.db_path).parent / 'ml'))
            from train_baseline import BaselineTrainer
            
            # Setup logging capture
            logger = logging.getLogger('train_baseline')
            logger.setLevel(logging.INFO)
            
            # Add our custom handler
            log_capture = LogCapture(self.progress_update)
            log_capture.setFormatter(logging.Formatter('%(message)s'))
            logger.addHandler(log_capture)
            
            # Also capture root logger
            root_logger = logging.getLogger()
            root_logger.addHandler(log_capture)
            
            self.progress_update.emit("\nInitializing trainer...")
            
            # Create trainer
            trainer = BaselineTrainer(Path(self.db_path))
            
            self.progress_update.emit("Loading data and training model...")
            self.progress_update.emit("This may take 1-2 minutes...\n")
            
            # Get config parameters
            test_size = self.config.get('test_size', 0.2)
            output_dir = Path(self.db_path).parent / 'ml' / 'models'
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Run training pipeline
            if self.model_type == "XGBoost Winner Classifier":
                model, metrics = trainer.run_full_pipeline(
                    test_size=test_size,
                    save_dir=output_dir
                )
                
                # Prepare results
                results = {
                    'model_type': self.model_type,
                    'metrics': metrics,
                    'feature_importance': trainer.feature_importance.to_dict('records') if trainer.feature_importance is not None else [],
                    'model_path': str(output_dir / 'xgboost_baseline.json'),
                    'test_size': test_size
                }
                
                self.progress_update.emit("\n" + "="*60)
                self.progress_update.emit("TRAINING COMPLETE!")
                self.progress_update.emit("="*60)
                
                self.training_complete.emit(results)
                
            else:
                # Placeholder for other models
                self.training_error.emit(f"Model type '{self.model_type}' not yet implemented")
            
            # Remove handlers
            logger.removeHandler(log_capture)
            root_logger.removeHandler(log_capture)
            
        except Exception as e:
            error_msg = f"Training error: {str(e)}\n\n{traceback.format_exc()}"
            self.training_error.emit(error_msg)


