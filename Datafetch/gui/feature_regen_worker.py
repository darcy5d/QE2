"""
Feature Regeneration Worker - Background thread for rebuilding ML features
Uses optimized parallel processing for maximum CPU utilization
"""

from PySide6.QtCore import QThread, Signal
from pathlib import Path
import sys
import time

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from ml.feature_engineer_optimized import generate_features_optimized


class FeatureRegenWorker(QThread):
    """Worker thread for regenerating ML features without blocking UI (OPTIMIZED)"""
    
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
        """Run OPTIMIZED feature regeneration in background"""
        try:
            self.progress_update.emit("="*60)
            self.progress_update.emit("REGENERATING ML FEATURES (OPTIMIZED)")
            self.progress_update.emit("="*60)
            self.progress_update.emit("")
            self.progress_update.emit("🚀 Using parallel processing for maximum speed")
            self.progress_update.emit("")
            
            if self.limit:
                self.progress_update.emit(f"NOTE: Limited to {self.limit} races (test mode)")
                self.progress_update.emit("")
            
            start_time = time.time()
            
            # Use the optimized parallel processor
            self.progress_update.emit("Starting optimized feature generation...")
            self.progress_update.emit("(Using all available CPU cores)")
            self.progress_update.emit("")
            
            # Note: The optimized version has its own logging
            # We'll capture the result
            result = generate_features_optimized(
                db_path=str(self.db_path),
                limit=self.limit
            )
            
            elapsed = time.time() - start_time
            
            if result:
                self.progress_update.emit("")
                self.progress_update.emit("="*60)
                self.progress_update.emit("✓ OPTIMIZED FEATURE REGENERATION COMPLETE")
                self.progress_update.emit("="*60)
                self.progress_update.emit(f"  Races processed: {result.get('races_processed', 0):,}")
                self.progress_update.emit(f"  Runners processed: {result.get('runners_processed', 0):,}")
                self.progress_update.emit(f"  Workers used: {result.get('workers', 0)}")
                self.progress_update.emit(f"  Total time: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
                self.progress_update.emit("")
                
                # Add column count
                import sqlite3
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM ml_features")
                feature_count = cursor.fetchone()[0]
                cursor.execute("PRAGMA table_info(ml_features)")
                column_count = len(cursor.fetchall())
                conn.close()
                
                self.progress_update.emit(f"  Total features in database: {feature_count:,}")
                self.progress_update.emit(f"  Feature columns: {column_count}")
                self.progress_update.emit("")
                
                # Emit success
                results = {
                    'races_processed': result.get('races_processed', 0),
                    'runners_processed': result.get('runners_processed', 0),
                    'errors': 0,
                    'total_features': feature_count,
                    'column_count': column_count,
                    'elapsed_time': elapsed,
                    'workers': result.get('workers', 0)
                }
                
                self.regeneration_complete.emit(results)
            else:
                self.regeneration_error.emit("Feature regeneration returned no results")
                
        except Exception as e:
            import traceback
            error_msg = f"Feature regeneration error: {str(e)}\n{traceback.format_exc()}"
            self.progress_update.emit("")
            self.progress_update.emit("="*60)
            self.progress_update.emit("❌ ERROR")
            self.progress_update.emit("="*60)
            self.progress_update.emit(error_msg)
            self.regeneration_error.emit(str(e))

