#!/usr/bin/env python3
"""
Extend database schema with odds tables and additional runner fields
Adds: runner_odds, runner_market_odds, plus new columns to runners table
"""

import sqlite3
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "racing_pro.db"
UPCOMING_DB_PATH = Path(__file__).parent / "upcoming_races.db"


def extend_odds_schema(conn):
    """Add odds tables and new runner columns"""
    cursor = conn.cursor()
    
    logger.info("Creating runner_odds table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS runner_odds (
            odds_id INTEGER PRIMARY KEY AUTOINCREMENT,
            runner_id INTEGER NOT NULL,
            bookmaker TEXT NOT NULL,
            fractional TEXT,
            decimal REAL,
            ew_places TEXT,
            ew_denom TEXT,
            updated TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (runner_id) REFERENCES runners (runner_id),
            UNIQUE(runner_id, bookmaker)
        )
    ''')
    
    logger.info("Creating runner_market_odds table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS runner_market_odds (
            market_odds_id INTEGER PRIMARY KEY AUTOINCREMENT,
            runner_id INTEGER NOT NULL UNIQUE,
            avg_decimal REAL,
            median_decimal REAL,
            min_decimal REAL,
            max_decimal REAL,
            bookmaker_count INTEGER,
            implied_probability REAL,
            is_favorite INTEGER,
            favorite_rank INTEGER,
            updated_at TIMESTAMP,
            FOREIGN KEY (runner_id) REFERENCES runners (runner_id)
        )
    ''')
    
    logger.info("Creating indexes for odds tables...")
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_runner_odds_runner ON runner_odds(runner_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_market_odds_runner ON runner_market_odds(runner_id)')
    
    # Add new columns to runners table
    logger.info("Adding new columns to runners table...")
    
    new_columns = [
        ('age', 'INTEGER'),
        ('sex', 'TEXT'),
        ('sex_code', 'TEXT'),
        ('dob', 'TEXT'),
        ('sire', 'TEXT'),
        ('sire_id', 'TEXT'),
        ('dam', 'TEXT'),
        ('dam_id', 'TEXT'),
        ('damsire', 'TEXT'),
        ('damsire_id', 'TEXT'),
        ('region', 'TEXT'),
        ('breeder', 'TEXT'),
        ('colour', 'TEXT'),
        ('trainer_location', 'TEXT'),
        ('trainer_14d_runs', 'INTEGER'),
        ('trainer_14d_wins', 'INTEGER'),
        ('trainer_14d_percent', 'REAL'),
    ]
    
    for col_name, col_type in new_columns:
        try:
            cursor.execute(f'ALTER TABLE runners ADD COLUMN {col_name} {col_type}')
            logger.info(f"  ✓ Added column: {col_name}")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e).lower():
                logger.info(f"  - Column {col_name} already exists")
            else:
                raise
    
    conn.commit()
    logger.info("✓ Odds schema extension complete!")


def extend_ml_features_schema(conn):
    """Add new feature columns to ml_features table"""
    cursor = conn.cursor()
    
    logger.info("Adding new feature columns to ml_features table...")
    
    new_feature_columns = [
        # Odds features (7)
        ('odds_implied_prob', 'REAL'),
        ('odds_is_favorite', 'INTEGER'),
        ('odds_favorite_rank', 'INTEGER'),
        ('odds_decimal', 'REAL'),
        ('odds_bookmaker_count', 'INTEGER'),
        ('odds_spread', 'REAL'),
        ('odds_market_stability', 'REAL'),
        
        # Demographic features (4)
        ('horse_sex_encoded', 'INTEGER'),
        ('horse_is_filly_mare', 'INTEGER'),
        ('horse_is_gelding', 'INTEGER'),
        
        # Trainer form features (4)
        ('trainer_14d_runs', 'INTEGER'),
        ('trainer_14d_wins', 'INTEGER'),
        ('trainer_14d_win_pct', 'REAL'),
        ('trainer_is_hot', 'INTEGER'),
    ]
    
    for col_name, col_type in new_feature_columns:
        try:
            cursor.execute(f'ALTER TABLE ml_features ADD COLUMN {col_name} {col_type}')
            logger.info(f"  ✓ Added column: {col_name}")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e).lower():
                logger.info(f"  - Column {col_name} already exists")
            else:
                raise
    
    conn.commit()
    logger.info("✓ ML features schema extension complete!")


def verify_schema(conn):
    """Verify that new tables and columns exist"""
    cursor = conn.cursor()
    
    logger.info("\nVerifying schema...")
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('runner_odds', 'runner_market_odds')")
    tables = [row[0] for row in cursor.fetchall()]
    
    for table in ['runner_odds', 'runner_market_odds']:
        if table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            logger.info(f"  ✓ {table}: {count} rows")
        else:
            logger.error(f"  ✗ {table}: NOT FOUND")
    
    # Check new columns in runners
    cursor.execute("PRAGMA table_info(runners)")
    runner_cols = [row[1] for row in cursor.fetchall()]
    
    new_cols_check = ['age', 'sex_code', 'sire', 'trainer_14d_runs']
    logger.info("\nChecking new runner columns:")
    for col in new_cols_check:
        if col in runner_cols:
            logger.info(f"  ✓ {col}")
        else:
            logger.error(f"  ✗ {col} NOT FOUND")
    
    # Check new columns in ml_features
    cursor.execute("PRAGMA table_info(ml_features)")
    feature_cols = [row[1] for row in cursor.fetchall()]
    
    new_feature_check = ['odds_implied_prob', 'horse_sex_encoded', 'trainer_14d_win_pct']
    logger.info("\nChecking new ml_features columns:")
    for col in new_feature_check:
        if col in feature_cols:
            logger.info(f"  ✓ {col}")
        else:
            logger.error(f"  ✗ {col} NOT FOUND")


def main():
    """Main execution"""
    logger.info("="*60)
    logger.info("EXTENDING DATABASE SCHEMA FOR ODDS + NEW FIELDS")
    logger.info("="*60)
    
    # Extend racing_pro.db
    if DB_PATH.exists():
        logger.info(f"\nExtending main database: {DB_PATH}")
        try:
            conn = sqlite3.connect(str(DB_PATH))
            conn.execute("PRAGMA foreign_keys = ON")
            
            extend_odds_schema(conn)
            extend_ml_features_schema(conn)
            verify_schema(conn)
            
            conn.close()
            logger.info("\n✓ Main database extended successfully!")
        except Exception as e:
            logger.error(f"Error extending main database: {e}")
            raise
    else:
        logger.warning(f"Main database not found: {DB_PATH}")
    
    # Extend upcoming_races.db
    if UPCOMING_DB_PATH.exists():
        logger.info(f"\nExtending upcoming races database: {UPCOMING_DB_PATH}")
        try:
            conn = sqlite3.connect(str(UPCOMING_DB_PATH))
            conn.execute("PRAGMA foreign_keys = OFF")  # Upcoming DB has FK disabled
            
            extend_odds_schema(conn)
            
            conn.close()
            logger.info("\n✓ Upcoming races database extended successfully!")
        except Exception as e:
            logger.error(f"Error extending upcoming database: {e}")
            raise
    else:
        logger.info(f"\nUpcoming races database not found (will be created on first fetch): {UPCOMING_DB_PATH}")
    
    logger.info("\n" + "="*60)
    logger.info("✓ SCHEMA EXTENSION COMPLETE")
    logger.info("="*60)


if __name__ == "__main__":
    main()


