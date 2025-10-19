"""
Feature Regeneration Worker - Background thread for rebuilding ML features
"""

from PySide6.QtCore import QThread, Signal
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from ml.feature_engineer import FeatureEngineer


class FeatureRegenWorker(QThread):
    """Worker thread for regenerating ML features without blocking UI"""
    
    # Signals
    progress_update = Signal(str)       # Progress message
    regeneration_complete = Signal(dict)  # Results dict
    regeneration_error = Signal(str)    # Error message
    
    def __init__(self, db_path: str, limit: int = None):
        """
        Initialize feature regeneration worker
        
        Args:
            db_path: Path to racing_pro.db
            limit: Optional limit on number of races (for testing)
        """
        super().__init__()
        self.db_path = Path(db_path)
        self.limit = limit
    
    def run(self):
        """Run feature regeneration in background"""
        try:
            self.progress_update.emit("="*60)
            self.progress_update.emit("REGENERATING ML FEATURES")
            self.progress_update.emit("="*60)
            self.progress_update.emit("")
            
            if self.limit:
                self.progress_update.emit(f"NOTE: Limited to {self.limit} races (test mode)")
                self.progress_update.emit("")
            
            # Initialize feature engineer
            self.progress_update.emit("Initializing feature engineer...")
            engineer = FeatureEngineer(self.db_path)
            engineer.connect()
            
            try:
                # Get races with results
                self.progress_update.emit("Finding races with results...")
                race_ids = engineer.get_races_with_results(limit=self.limit)
                
                if not race_ids:
                    self.regeneration_error.emit("No races with results found. Ensure results data has been fetched.")
                    return
                
                self.progress_update.emit(f"Found {len(race_ids)} races with results")
                self.progress_update.emit("")
                self.progress_update.emit("Processing races...")
                self.progress_update.emit("(This may take 10-20 minutes for full dataset)")
                self.progress_update.emit("")
                
                # Process races
                total_runners = 0
                errors = 0
                
                for i, race_id in enumerate(race_ids, 1):
                    try:
                        runners_processed = engineer.process_race(race_id)
                        total_runners += runners_processed
                        
                        # Progress updates every 50 races
                        if i % 50 == 0:
                            self.progress_update.emit(f"  Processed {i}/{len(race_ids)} races ({total_runners} runners)...")
                            engineer.conn.commit()  # Commit periodically
                        
                    except Exception as e:
                        errors += 1
                        if errors <= 5:  # Only show first 5 errors
                            self.progress_update.emit(f"  ⚠ Error processing {race_id}: {e}")
                
                # Final commit
                engineer.conn.commit()
                
                self.progress_update.emit("")
                self.progress_update.emit("="*60)
                self.progress_update.emit("✓ FEATURE REGENERATION COMPLETE")
                self.progress_update.emit("="*60)
                self.progress_update.emit(f"  Races processed: {len(race_ids)}")
                self.progress_update.emit(f"  Runners processed: {total_runners}")
                if errors > 0:
                    self.progress_update.emit(f"  Errors encountered: {errors}")
                self.progress_update.emit("")
                
                # Count features in database
                cursor = engineer.conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM ml_features")
                feature_count = cursor.fetchone()[0]
                self.progress_update.emit(f"  Total features in database: {feature_count:,}")
                
                # Get feature column count
                cursor.execute("PRAGMA table_info(ml_features)")
                column_count = len(cursor.fetchall())
                self.progress_update.emit(f"  Feature columns: {column_count}")
                self.progress_update.emit("")
                
                # Emit success
                results = {
                    'races_processed': len(race_ids),
                    'runners_processed': total_runners,
                    'errors': errors,
                    'total_features': feature_count,
                    'column_count': column_count
                }
                
                self.regeneration_complete.emit(results)
                
            finally:
                engineer.close()
                
        except Exception as e:
            import traceback
            error_msg = f"Feature regeneration error: {str(e)}\n{traceback.format_exc()}"
            self.progress_update.emit("")
            self.progress_update.emit("="*60)
            self.progress_update.emit("❌ ERROR")
            self.progress_update.emit("="*60)
            self.progress_update.emit(error_msg)
            self.regeneration_error.emit(str(e))

