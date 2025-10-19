#!/usr/bin/env python3
"""
Migrate ml_features table schema to add new race-context features
Adds ~30 new columns for field strength, draw bias, pace/speed features
"""

import sqlite3
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "racing_pro.db"


def add_columns_if_not_exist(cursor, table, columns):
    """Add multiple columns to table if they don't already exist"""
    # Get existing columns
    cursor.execute(f"PRAGMA table_info({table})")
    existing_cols = {row[1] for row in cursor.fetchall()}
    
    added = 0
    for col_name, col_type in columns:
        if col_name not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
                logger.info(f"  ✓ Added column: {col_name} ({col_type})")
                added += 1
            except sqlite3.OperationalError as e:
                logger.warning(f"  ✗ Could not add {col_name}: {e}")
        else:
            logger.debug(f"  - Column {col_name} already exists")
    
    return added


def migrate_schema():
    """Add new feature columns to ml_features table"""
    logger.info("="*60)
    logger.info("ML FEATURES SCHEMA MIGRATION")
    logger.info("="*60)
    
    if not DB_PATH.exists():
        logger.error(f"Database not found: {DB_PATH}")
        return False
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    try:
        # New columns to add
        new_columns = [
            # Pace/Speed features
            ('horse_best_tsr', 'REAL'),
            ('horse_avg_tsr_last_5', 'REAL'),
            ('speed_improving', 'INTEGER'),
            ('typical_running_style', 'INTEGER'),  # 1=leader, 2=prominent, 3=midfield, 4=held up
            
            # Additional trainer/jockey features
            ('trainer_rating', 'REAL'),  # vs field average
            ('jockey_rating', 'REAL'),   # vs field average
            
            # Additional ranking features
            ('weight_lbs_rank', 'INTEGER'),
            ('age_rank', 'INTEGER'),
            
            # Field strength features
            ('field_best_rpr', 'REAL'),
            ('field_worst_rpr', 'REAL'),
            ('field_avg_rpr', 'REAL'),
            ('horse_rpr_rank', 'INTEGER'),
            ('horse_rpr_vs_best', 'REAL'),
            ('horse_rpr_vs_worst', 'REAL'),
            ('field_rpr_spread', 'REAL'),
            ('top_3_rpr_avg', 'REAL'),
            ('horse_in_top_quartile', 'INTEGER'),
            ('tsr_vs_field_avg', 'REAL'),
            ('pace_pressure_likely', 'INTEGER'),  # Number of front-runners in field
            
            # Draw bias features
            ('course_distance_draw_bias', 'REAL'),
            ('draw_position_normalized', 'REAL'),  # 0-1 scale
            ('low_draw_advantage', 'INTEGER'),     # Boolean
            ('high_draw_advantage', 'INTEGER'),    # Boolean
        ]
        
        logger.info(f"\nAdding {len(new_columns)} new columns to ml_features table...")
        added = add_columns_if_not_exist(cursor, 'ml_features', new_columns)
        
        conn.commit()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"✓ MIGRATION COMPLETE")
        logger.info(f"  Added {added} new columns")
        logger.info(f"  Skipped {len(new_columns) - added} existing columns")
        logger.info(f"{'='*60}\n")
        
        # Verify schema
        cursor.execute("PRAGMA table_info(ml_features)")
        total_cols = len(cursor.fetchall())
        logger.info(f"ml_features table now has {total_cols} columns")
        
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    success = migrate_schema()
    sys.exit(0 if success else 1)

