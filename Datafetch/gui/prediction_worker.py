"""
Prediction Worker - Background thread for generating ML predictions
"""

from PySide6.QtCore import QThread, Signal
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from ml.predictor import ModelPredictor


class PredictionWorker(QThread):
    """Worker thread for generating predictions without blocking UI"""
    
    # Signals
    progress = Signal(int, int, str)  # current, total, race_name
    predictions_ready = Signal(list)  # List of prediction dicts
    error_occurred = Signal(str)      # Error message
    
    def __init__(self, race_ids: list, upcoming_db_path: str, racing_db_path: str = None):
        """
        Initialize prediction worker
        
        Args:
            race_ids: List of race IDs to generate predictions for
            upcoming_db_path: Path to upcoming_races.db
            racing_db_path: Path to racing_pro.db (optional)
        """
        super().__init__()
        self.race_ids = race_ids
        self.upcoming_db_path = upcoming_db_path
        self.racing_db_path = racing_db_path
        self.predictor = None
    
    def run(self):
        """Run prediction generation in background"""
        try:
            # Initialize predictor
            print("Initializing ML predictor...")
            self.predictor = ModelPredictor(racing_db_path=self.racing_db_path)
            
            # Generate predictions for each race
            all_predictions = []
            total_races = len(self.race_ids)
            total_runners = 0
            predicted_runners = 0
            
            for i, race_id in enumerate(self.race_ids, 1):
                try:
                    # Emit progress
                    self.progress.emit(i, total_races, f"Processing race {i}/{total_races}")
                    
                    # Generate predictions
                    result = self.predictor.predict_race(race_id, self.upcoming_db_path)
                    
                    if result:
                        all_predictions.append(result)
                        race_name = result['race_info'].get('course', 'Unknown')
                        race_time = result['race_info'].get('time', '')
                        
                        # Count runners
                        num_predictions = len(result['predictions'])
                        predicted_runners += num_predictions
                        
                        # Get total runners from race (not just predicted ones)
                        # This is already calculated but we need to track it
                        print(f"✓ [{i}/{total_races}] {race_id} - {race_name} {race_time} ({num_predictions} runners)")
                    else:
                        print(f"⚠ [{i}/{total_races}] {race_id} - No predictions generated")
                
                except Exception as e:
                    import traceback
                    print(f"❌ [{i}/{total_races}] {race_id} - ERROR: {e}")
                    print(f"Full traceback:\n{traceback.format_exc()}")
                    continue
            
            # Emit results
            print(f"\n{'='*70}")
            print(f"🏁 PREDICTION SUMMARY")
            print(f"{'='*70}")
            print(f"Total races processed: {total_races}")
            print(f"Races with predictions: {len(all_predictions)}")
            print(f"Races failed: {total_races - len(all_predictions)}")
            print(f"Success rate: {len(all_predictions)/total_races*100:.1f}%")
            print(f"")
            print(f"Total runners predicted: {predicted_runners}")
            if len(all_predictions) > 0:
                avg_runners = predicted_runners / len(all_predictions)
                print(f"Average runners per race: {avg_runners:.1f}")
            print(f"{'='*70}\n")
            
            if all_predictions:
                self.predictions_ready.emit(all_predictions)
            else:
                self.error_occurred.emit("No predictions could be generated. Check that races have runner data.")
            
        except Exception as e:
            import traceback
            error_msg = f"Prediction error: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            self.error_occurred.emit(str(e))
        
        finally:
            # Clean up
            if self.predictor:
                try:
                    self.predictor.close()
                except:
                    pass

