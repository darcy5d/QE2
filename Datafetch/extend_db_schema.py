#!/usr/bin/env python3
"""
Extend racing_pro.db schema with ML-related tables
Adds: results, horse_career_stats, trainer_stats, jockey_stats, 
      trainer_jockey_combos, form_history, ml_features, ml_targets
"""

import sqlite3
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "racing_pro.db"


def extend_schema(conn):
    """Add new tables to the database"""
    cursor = conn.cursor()
    
    logger.info("Creating results table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            race_id TEXT NOT NULL,
            horse_id TEXT NOT NULL,
            trainer_id TEXT,
            jockey_id TEXT,
            owner_id TEXT,
            position TEXT,
            position_int INTEGER,
            btn TEXT,
            ovr_btn TEXT,
            time TEXT,
            sp TEXT,
            sp_dec TEXT,
            prize TEXT,
            weight TEXT,
            weight_lbs TEXT,
            headgear TEXT,
            ofr TEXT,
            rpr TEXT,
            tsr TEXT,
            comment TEXT,
            jockey_claim_lbs TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (race_id) REFERENCES races(race_id) ON DELETE CASCADE,
            FOREIGN KEY (horse_id) REFERENCES horses(horse_id),
            FOREIGN KEY (trainer_id) REFERENCES trainers(trainer_id),
            FOREIGN KEY (jockey_id) REFERENCES jockeys(jockey_id),
            FOREIGN KEY (owner_id) REFERENCES owners(owner_id),
            UNIQUE(race_id, horse_id)
        )
    ''')
    
    logger.info("Creating indexes for results...")
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_results_race_id ON results(race_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_results_horse_id ON results(horse_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_results_position ON results(position_int)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_results_trainer_id ON results(trainer_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_results_jockey_id ON results(jockey_id)')
    
    logger.info("Creating horse_career_stats table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS horse_career_stats (
            horse_id TEXT PRIMARY KEY,
            total_runs INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            places INTEGER DEFAULT 0,
            win_rate REAL DEFAULT 0.0,
            place_rate REAL DEFAULT 0.0,
            avg_position REAL,
            median_position REAL,
            best_position INTEGER,
            total_earnings REAL DEFAULT 0.0,
            avg_sp_dec REAL,
            best_rating INTEGER,
            courses_won TEXT,
            distance_performance TEXT,
            going_preference TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (horse_id) REFERENCES horses(horse_id) ON DELETE CASCADE
        )
    ''')
    
    logger.info("Creating trainer_stats table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trainer_stats (
            stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            trainer_id TEXT NOT NULL,
            period TEXT NOT NULL,
            start_date TEXT,
            end_date TEXT,
            runs INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            places INTEGER DEFAULT 0,
            win_rate REAL DEFAULT 0.0,
            place_rate REAL DEFAULT 0.0,
            strike_rate REAL DEFAULT 0.0,
            roi REAL DEFAULT 0.0,
            ae_ratio REAL DEFAULT 0.0,
            course_specialization TEXT,
            distance_specialization TEXT,
            going_specialization TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (trainer_id) REFERENCES trainers(trainer_id) ON DELETE CASCADE,
            UNIQUE(trainer_id, period, start_date, end_date)
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_trainer_stats_trainer ON trainer_stats(trainer_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_trainer_stats_period ON trainer_stats(period)')
    
    logger.info("Creating jockey_stats table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jockey_stats (
            stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            jockey_id TEXT NOT NULL,
            period TEXT NOT NULL,
            start_date TEXT,
            end_date TEXT,
            runs INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            places INTEGER DEFAULT 0,
            win_rate REAL DEFAULT 0.0,
            place_rate REAL DEFAULT 0.0,
            strike_rate REAL DEFAULT 0.0,
            roi REAL DEFAULT 0.0,
            ae_ratio REAL DEFAULT 0.0,
            course_specialization TEXT,
            distance_specialization TEXT,
            going_specialization TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (jockey_id) REFERENCES jockeys(jockey_id) ON DELETE CASCADE,
            UNIQUE(jockey_id, period, start_date, end_date)
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_jockey_stats_jockey ON jockey_stats(jockey_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_jockey_stats_period ON jockey_stats(period)')
    
    logger.info("Creating trainer_jockey_combos table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trainer_jockey_combos (
            combo_id INTEGER PRIMARY KEY AUTOINCREMENT,
            trainer_id TEXT NOT NULL,
            jockey_id TEXT NOT NULL,
            period TEXT NOT NULL,
            runs INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            places INTEGER DEFAULT 0,
            win_rate REAL DEFAULT 0.0,
            strike_rate REAL DEFAULT 0.0,
            roi REAL DEFAULT 0.0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (trainer_id) REFERENCES trainers(trainer_id) ON DELETE CASCADE,
            FOREIGN KEY (jockey_id) REFERENCES jockeys(jockey_id) ON DELETE CASCADE,
            UNIQUE(trainer_id, jockey_id, period)
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_combos_trainer ON trainer_jockey_combos(trainer_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_combos_jockey ON trainer_jockey_combos(jockey_id)')
    
    logger.info("Creating form_history table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS form_history (
            form_id INTEGER PRIMARY KEY AUTOINCREMENT,
            horse_id TEXT NOT NULL,
            race_id TEXT NOT NULL,
            form_string TEXT,
            parsed_positions TEXT,
            last_5_avg REAL,
            last_10_avg REAL,
            improving_trend INTEGER,
            consistency_score REAL,
            races_since_win INTEGER,
            days_since_last_run INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (horse_id) REFERENCES horses(horse_id) ON DELETE CASCADE,
            FOREIGN KEY (race_id) REFERENCES races(race_id) ON DELETE CASCADE,
            UNIQUE(horse_id, race_id)
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_form_horse ON form_history(horse_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_form_race ON form_history(race_id)')
    
    logger.info("Creating ml_features table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ml_features (
            feature_id INTEGER PRIMARY KEY AUTOINCREMENT,
            race_id TEXT NOT NULL,
            runner_id INTEGER NOT NULL,
            horse_id TEXT NOT NULL,
            
            -- Horse features
            horse_age INTEGER,
            horse_career_runs INTEGER,
            horse_career_wins INTEGER,
            horse_win_rate REAL,
            horse_place_rate REAL,
            horse_avg_position REAL,
            horse_course_wins INTEGER,
            horse_distance_win_rate REAL,
            horse_going_win_rate REAL,
            horse_days_since_last REAL,
            horse_form_last_5_avg REAL,
            horse_form_improving INTEGER,
            horse_consistency REAL,
            horse_best_rating INTEGER,
            
            -- Trainer features
            trainer_win_rate_14d REAL,
            trainer_win_rate_90d REAL,
            trainer_strike_rate REAL,
            trainer_course_win_rate REAL,
            trainer_distance_win_rate REAL,
            trainer_roi REAL,
            trainer_form_with_horse REAL,
            
            -- Jockey features
            jockey_win_rate_14d REAL,
            jockey_win_rate_90d REAL,
            jockey_strike_rate REAL,
            jockey_course_win_rate REAL,
            jockey_distance_win_rate REAL,
            jockey_roi REAL,
            
            -- Trainer-Jockey combo
            combo_win_rate REAL,
            combo_strike_rate REAL,
            combo_runs INTEGER,
            
            -- Race context features
            field_size INTEGER,
            race_class TEXT,
            race_class_encoded INTEGER,
            distance_f REAL,
            going_encoded INTEGER,
            surface_encoded INTEGER,
            prize_money REAL,
            
            -- Runner-specific features
            runner_number INTEGER,
            draw INTEGER,
            weight_lbs REAL,
            ofr REAL,
            rpr REAL,
            ts REAL,
            headgear_encoded INTEGER,
            
            -- Relative features (vs field)
            rating_vs_avg REAL,
            weight_vs_avg REAL,
            age_vs_avg REAL,
            odds_rank INTEGER,
            
            -- Market features
            opening_odds REAL,
            final_odds REAL,
            odds_movement REAL,
            market_rank INTEGER,
            
            -- Pedigree features
            sire_distance_win_rate REAL,
            sire_surface_win_rate REAL,
            dam_produce_win_rate REAL,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (race_id) REFERENCES races(race_id) ON DELETE CASCADE,
            FOREIGN KEY (runner_id) REFERENCES runners(runner_id) ON DELETE CASCADE,
            FOREIGN KEY (horse_id) REFERENCES horses(horse_id),
            UNIQUE(race_id, runner_id)
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ml_features_race ON ml_features(race_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ml_features_runner ON ml_features(runner_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ml_features_horse ON ml_features(horse_id)')
    
    logger.info("Creating ml_targets table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ml_targets (
            target_id INTEGER PRIMARY KEY AUTOINCREMENT,
            race_id TEXT NOT NULL,
            runner_id INTEGER NOT NULL,
            horse_id TEXT NOT NULL,
            position INTEGER,
            won INTEGER DEFAULT 0,
            placed INTEGER DEFAULT 0,
            top_5 INTEGER DEFAULT 0,
            time_behind_winner REAL,
            beaten_lengths REAL,
            finishing_time TEXT,
            prize_money REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (race_id) REFERENCES races(race_id) ON DELETE CASCADE,
            FOREIGN KEY (runner_id) REFERENCES runners(runner_id) ON DELETE CASCADE,
            FOREIGN KEY (horse_id) REFERENCES horses(horse_id),
            UNIQUE(race_id, runner_id)
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ml_targets_race ON ml_targets(race_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ml_targets_runner ON ml_targets(runner_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ml_targets_position ON ml_targets(position)')
    
    conn.commit()
    logger.info("✓ All new tables created successfully!")


def verify_schema(conn):
    """Verify that all new tables exist"""
    cursor = conn.cursor()
    
    expected_tables = [
        'results',
        'horse_career_stats',
        'trainer_stats',
        'jockey_stats',
        'trainer_jockey_combos',
        'form_history',
        'ml_features',
        'ml_targets'
    ]
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [row[0] for row in cursor.fetchall()]
    
    logger.info("\nVerifying schema...")
    for table in expected_tables:
        if table in existing_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            logger.info(f"  ✓ {table}: {count} rows")
        else:
            logger.error(f"  ✗ {table}: NOT FOUND")
    
    # Count existing data
    cursor.execute("SELECT COUNT(*) FROM races")
    race_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM runners")
    runner_count = cursor.fetchone()[0]
    
    logger.info(f"\nExisting data:")
    logger.info(f"  Races: {race_count:,}")
    logger.info(f"  Runners: {runner_count:,}")


def main():
    """Main execution"""
    logger.info(f"Extending database schema: {DB_PATH}")
    
    if not DB_PATH.exists():
        logger.error(f"Database not found: {DB_PATH}")
        return
    
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Extend schema
        extend_schema(conn)
        
        # Verify
        verify_schema(conn)
        
        logger.info("\n✓ Database schema extension complete!")
        
    except Exception as e:
        logger.error(f"Error extending schema: {e}")
        raise
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()

