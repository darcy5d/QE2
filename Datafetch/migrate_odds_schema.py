#!/usr/bin/env python3
"""
Migrate existing runner_odds table from JSON format to normalized format
"""

import sqlite3
import json
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "racing_pro.db"


def migrate_runner_odds(conn):
    """Migrate runner_odds from JSON format to normalized format"""
    cursor = conn.cursor()
    
    logger.info("Starting runner_odds migration...")
    
    # Step 1: Rename old table (if needed)
    logger.info("  Step 1: Checking existing tables...")
    
    # Check if runner_odds exists with old schema
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='runner_odds'")
    has_runner_odds = cursor.fetchone() is not None
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='runner_odds_old'")
    has_runner_odds_old = cursor.fetchone() is not None
    
    if has_runner_odds and not has_runner_odds_old:
        # Check if it's the old schema (has odds_value column)
        cursor.execute("PRAGMA table_info(runner_odds)")
        columns = {row[1] for row in cursor.fetchall()}
        if 'odds_value' in columns:
            logger.info("    Renaming old runner_odds to runner_odds_old...")
            cursor.execute("ALTER TABLE runner_odds RENAME TO runner_odds_old")
            conn.commit()
            logger.info("    ✓ Renamed")
            has_runner_odds_old = True
        else:
            logger.info("    - runner_odds already has new schema, skipping migration")
            return
    elif has_runner_odds_old:
        logger.info("    - runner_odds_old already exists")
        # Drop current runner_odds if it exists (might be empty from failed migration)
        if has_runner_odds:
            cursor.execute("DROP TABLE runner_odds")
            logger.info("    - Dropped empty runner_odds table")
    else:
        logger.info("    - No tables to migrate")
        return
    
    # Step 2: Create new normalized schema
    logger.info("  Step 2: Creating new normalized runner_odds table...")
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
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_runner_odds_runner ON runner_odds(runner_id)')
    logger.info("    ✓ Created")
    
    # Step 3: Migrate data
    logger.info("  Step 3: Migrating data from JSON format...")
    
    # Check if old table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='runner_odds_old'")
    if not cursor.fetchone():
        logger.info("    - No runner_odds_old table to migrate from")
        return
    
    cursor.execute("SELECT COUNT(*) FROM runner_odds_old")
    total_records = cursor.fetchone()[0]
    logger.info(f"    Found {total_records:,} records to migrate")
    
    # Fetch and parse JSON data
    cursor.execute("SELECT runner_id, odds_value, timestamp FROM runner_odds_old")
    
    migrated = 0
    errors = 0
    
    for row in cursor.fetchall():
        runner_id = row[0]
        odds_json = row[1]
        timestamp = row[2]
        
        if not odds_json:
            continue
        
        try:
            # Parse JSON or Python dict string
            if isinstance(odds_json, str):
                # Try JSON first
                try:
                    odds_data = json.loads(odds_json)
                except json.JSONDecodeError:
                    # Try Python's ast.literal_eval for dict strings
                    import ast
                    odds_data = ast.literal_eval(odds_json)
            else:
                odds_data = odds_json
            
            bookmaker = odds_data.get('bookmaker', '')
            fractional = odds_data.get('fractional', '')
            decimal_str = odds_data.get('decimal', '')
            ew_places = odds_data.get('ew_places', '')
            ew_denom = odds_data.get('ew_denom', '')
            updated = odds_data.get('updated', timestamp)
            
            # Convert decimal to float
            try:
                decimal_float = float(decimal_str) if decimal_str else None
            except (ValueError, TypeError):
                decimal_float = None
            
            # Insert into new table
            cursor.execute('''
                INSERT OR IGNORE INTO runner_odds (
                    runner_id, bookmaker, fractional, decimal,
                    ew_places, ew_denom, updated, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (runner_id, bookmaker, fractional, decimal_float,
                  ew_places, ew_denom, updated, timestamp))
            
            migrated += 1
            
            if migrated % 10000 == 0:
                logger.info(f"    Migrated {migrated:,}/{total_records:,} records...")
                conn.commit()
            
        except Exception as e:
            errors += 1
            if errors < 5:  # Only log first few errors
                logger.warning(f"    Error migrating record for runner_id={runner_id}: {e}")
    
    conn.commit()
    
    logger.info(f"    ✓ Migrated {migrated:,} records ({errors} errors)")
    
    # Step 4: Create market odds table
    logger.info("  Step 4: Creating runner_market_odds table...")
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
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_market_odds_runner ON runner_market_odds(runner_id)')
    logger.info("    ✓ Created")
    
    # Step 5: Populate market odds from individual odds
    logger.info("  Step 5: Computing market odds aggregates...")
    
    import statistics
    
    # Get all runners with odds
    cursor.execute("""
        SELECT runner_id, GROUP_CONCAT(decimal) as decimals
        FROM runner_odds
        WHERE decimal IS NOT NULL
        GROUP BY runner_id
    """)
    
    populated = 0
    for row in cursor.fetchall():
        runner_id = row[0]
        decimals_str = row[1]
        
        if not decimals_str:
            continue
        
        try:
            # Parse decimals
            decimal_odds = [float(d) for d in decimals_str.split(',') if d]
            
            if not decimal_odds:
                continue
            
            # Calculate aggregates
            avg_decimal = statistics.mean(decimal_odds)
            median_decimal = statistics.median(decimal_odds)
            min_decimal = min(decimal_odds)
            max_decimal = max(decimal_odds)
            bookmaker_count = len(decimal_odds)
            implied_prob = 1.0 / avg_decimal if avg_decimal > 0 else None
            
            cursor.execute('''
                INSERT OR REPLACE INTO runner_market_odds (
                    runner_id, avg_decimal, median_decimal, min_decimal,
                    max_decimal, bookmaker_count, implied_probability,
                    is_favorite, favorite_rank, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, CURRENT_TIMESTAMP)
            ''', (runner_id, avg_decimal, median_decimal, min_decimal,
                  max_decimal, bookmaker_count, implied_prob))
            
            populated += 1
            
            if populated % 1000 == 0:
                logger.info(f"    Computed market odds for {populated:,} runners...")
                conn.commit()
        
        except Exception as e:
            logger.warning(f"    Error computing market odds for runner_id={runner_id}: {e}")
    
    conn.commit()
    logger.info(f"    ✓ Computed market odds for {populated:,} runners")
    
    # Step 6: Update favorite status for each race
    logger.info("  Step 6: Computing favorite rankings...")
    
    # Get all races with market odds
    cursor.execute("""
        SELECT DISTINCT r.race_id
        FROM runner_market_odds mo
        JOIN runners r ON mo.runner_id = r.runner_id
    """)
    
    races = [row[0] for row in cursor.fetchall()]
    logger.info(f"    Found {len(races):,} races with odds data")
    
    for i, race_id in enumerate(races):
        try:
            # Rank runners by odds (lower = better = favorite)
            cursor.execute('''
                WITH race_odds AS (
                    SELECT mo.runner_id, mo.avg_decimal,
                           ROW_NUMBER() OVER (ORDER BY mo.avg_decimal ASC) as rank
                    FROM runner_market_odds mo
                    JOIN runners r ON mo.runner_id = r.runner_id
                    WHERE r.race_id = ? AND mo.avg_decimal IS NOT NULL
                )
                UPDATE runner_market_odds
                SET is_favorite = CASE WHEN race_odds.rank = 1 THEN 1 ELSE 0 END,
                    favorite_rank = race_odds.rank
                FROM race_odds
                WHERE runner_market_odds.runner_id = race_odds.runner_id
            ''', (race_id,))
            
            if i % 1000 == 0 and i > 0:
                logger.info(f"    Processed {i:,}/{len(races):,} races...")
                conn.commit()
        
        except Exception as e:
            logger.warning(f"    Error computing favorites for race {race_id}: {e}")
    
    conn.commit()
    logger.info(f"    ✓ Computed favorites for {len(races):,} races")
    
    logger.info("✓ Migration complete!")


def verify_migration(conn):
    """Verify migration was successful"""
    cursor = conn.cursor()
    
    logger.info("\nVerifying migration...")
    
    # Check new tables
    cursor.execute("SELECT COUNT(*) FROM runner_odds")
    odds_count = cursor.fetchone()[0]
    logger.info(f"  runner_odds: {odds_count:,} rows")
    
    cursor.execute("SELECT COUNT(*) FROM runner_market_odds")
    market_count = cursor.fetchone()[0]
    logger.info(f"  runner_market_odds: {market_count:,} rows")
    
    # Check sample data
    cursor.execute("""
        SELECT bookmaker, fractional, decimal
        FROM runner_odds
        WHERE decimal IS NOT NULL
        LIMIT 3
    """)
    logger.info("\n  Sample odds data:")
    for row in cursor.fetchall():
        logger.info(f"    {row[0]}: {row[1]} ({row[2]})")
    
    # Check favorites
    cursor.execute("""
        SELECT COUNT(*) 
        FROM runner_market_odds
        WHERE is_favorite = 1
    """)
    fav_count = cursor.fetchone()[0]
    logger.info(f"\n  Favorites marked: {fav_count:,}")


def main():
    """Main execution"""
    logger.info("="*60)
    logger.info("RUNNER ODDS SCHEMA MIGRATION")
    logger.info("="*60)
    
    if not DB_PATH.exists():
        logger.error(f"Database not found: {DB_PATH}")
        return 1
    
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("PRAGMA foreign_keys = ON")
        
        migrate_runner_odds(conn)
        verify_migration(conn)
        
        conn.close()
        
        logger.info("\n" + "="*60)
        logger.info("✓ MIGRATION COMPLETE")
        logger.info("="*60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

