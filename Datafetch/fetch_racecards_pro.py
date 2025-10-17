#!/usr/bin/env python3
"""
Fetch Historical Racecards Pro Data from The Racing API
Stores data in a fully normalized SQLite database

Date Range: 2023-01-23 to 2023-04-30
Endpoint: /v1/racecards/pro
"""

# Standard Libraries
import requests
import sqlite3
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fetch_racecards_pro.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("RacecardsProFetcher")

# ============================================================================
# CONFIGURATION
# ============================================================================

# Load API credentials
CRED_FILE = Path(__file__).parent / "reqd_files" / "cred.txt"
with open(CRED_FILE, "r") as file:
    USERNAME = file.readline().strip()
    PASSWORD = file.readline().strip()

BASE_URL = "https://api.theracingapi.com"
RATE_LIMIT = 0.55  # seconds between requests
DB_PATH = Path(__file__).parent / "racing_pro.db"

# API data start date
START_DATE = "2023-01-23"
END_DATE = "2023-04-30"

# ============================================================================
# DATABASE SCHEMA CREATION
# ============================================================================

def create_normalized_schema(conn: sqlite3.Connection) -> None:
    """Create fully normalized database schema with all tables and relationships"""
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")
    
    logger.info("Creating normalized database schema...")
    
    # ========================================================================
    # CORE ENTITY TABLES
    # ========================================================================
    
    # Horses table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS horses (
        horse_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        dob TEXT,
        age TEXT,
        sex TEXT,
        sex_code TEXT,
        colour TEXT,
        region TEXT,
        breeder TEXT,
        dam_id TEXT,
        dam_region TEXT,
        sire_id TEXT,
        sire_region TEXT,
        damsire_id TEXT,
        damsire_region TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Dams (mother horses)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS dams (
        dam_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        region TEXT
    )
    ''')
    
    # Sires (father horses)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sires (
        sire_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        region TEXT
    )
    ''')
    
    # Damsires (maternal grandsires)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS damsires (
        damsire_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        region TEXT
    )
    ''')
    
    # Trainers table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trainers (
        trainer_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        location TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Jockeys table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS jockeys (
        jockey_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Owners table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS owners (
        owner_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # ========================================================================
    # RACES TABLE
    # ========================================================================
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS races (
        race_id TEXT PRIMARY KEY,
        course TEXT,
        course_id TEXT,
        date TEXT NOT NULL,
        off_time TEXT,
        off_dt TEXT,
        race_name TEXT,
        distance_round TEXT,
        distance TEXT,
        distance_f TEXT,
        region TEXT,
        pattern TEXT,
        sex_restriction TEXT,
        race_class TEXT,
        type TEXT,
        age_band TEXT,
        rating_band TEXT,
        prize TEXT,
        field_size TEXT,
        going_detailed TEXT,
        rail_movements TEXT,
        stalls TEXT,
        weather TEXT,
        going TEXT,
        surface TEXT,
        jumps TEXT,
        big_race INTEGER,
        is_abandoned INTEGER,
        tip TEXT,
        verdict TEXT,
        betting_forecast TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # ========================================================================
    # RUNNERS TABLE (links horses to races)
    # ========================================================================
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS runners (
        runner_id INTEGER PRIMARY KEY AUTOINCREMENT,
        race_id TEXT NOT NULL,
        horse_id TEXT NOT NULL,
        trainer_id TEXT,
        jockey_id TEXT,
        owner_id TEXT,
        number TEXT,
        draw TEXT,
        headgear TEXT,
        headgear_run TEXT,
        wind_surgery TEXT,
        wind_surgery_run TEXT,
        lbs TEXT,
        ofr TEXT,
        rpr TEXT,
        ts TEXT,
        silk_url TEXT,
        last_run TEXT,
        form TEXT,
        trainer_rtf TEXT,
        comment TEXT,
        spotlight TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (race_id) REFERENCES races(race_id) ON DELETE CASCADE,
        FOREIGN KEY (horse_id) REFERENCES horses(horse_id) ON DELETE CASCADE,
        FOREIGN KEY (trainer_id) REFERENCES trainers(trainer_id),
        FOREIGN KEY (jockey_id) REFERENCES jockeys(jockey_id),
        FOREIGN KEY (owner_id) REFERENCES owners(owner_id)
    )
    ''')
    
    # ========================================================================
    # NESTED DATA TABLES
    # ========================================================================
    
    # Runner odds (array of odds values)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS runner_odds (
        odds_id INTEGER PRIMARY KEY AUTOINCREMENT,
        runner_id INTEGER NOT NULL,
        odds_value TEXT,
        timestamp TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (runner_id) REFERENCES runners(runner_id) ON DELETE CASCADE
    )
    ''')
    
    # Runner quotes (press quotes about runners)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS runner_quotes (
        quote_id INTEGER PRIMARY KEY AUTOINCREMENT,
        runner_id INTEGER NOT NULL,
        quote_text TEXT,
        source TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (runner_id) REFERENCES runners(runner_id) ON DELETE CASCADE
    )
    ''')
    
    # Runner medical records
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS runner_medical (
        medical_id INTEGER PRIMARY KEY AUTOINCREMENT,
        runner_id INTEGER NOT NULL,
        medical_note TEXT,
        date TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (runner_id) REFERENCES runners(runner_id) ON DELETE CASCADE
    )
    ''')
    
    # Runner stable tour comments
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS runner_stable_tour (
        stable_tour_id INTEGER PRIMARY KEY AUTOINCREMENT,
        runner_id INTEGER NOT NULL,
        comment TEXT,
        date TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (runner_id) REFERENCES runners(runner_id) ON DELETE CASCADE
    )
    ''')
    
    # Runner past results flags
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS runner_past_results_flags (
        flag_id INTEGER PRIMARY KEY AUTOINCREMENT,
        runner_id INTEGER NOT NULL,
        flag_value TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (runner_id) REFERENCES runners(runner_id) ON DELETE CASCADE
    )
    ''')
    
    # Previous trainers (historical trainer changes)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS prev_trainers (
        prev_trainer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        horse_id TEXT NOT NULL,
        trainer_name TEXT,
        date_from TEXT,
        date_to TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (horse_id) REFERENCES horses(horse_id) ON DELETE CASCADE
    )
    ''')
    
    # Previous owners (historical owner changes)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS prev_owners (
        prev_owner_id INTEGER PRIMARY KEY AUTOINCREMENT,
        horse_id TEXT NOT NULL,
        owner_name TEXT,
        date_from TEXT,
        date_to TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (horse_id) REFERENCES horses(horse_id) ON DELETE CASCADE
    )
    ''')
    
    # Trainer 14 days statistics
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trainer_14_days (
        stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
        trainer_id TEXT NOT NULL,
        stat_key TEXT,
        stat_value TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (trainer_id) REFERENCES trainers(trainer_id) ON DELETE CASCADE
    )
    ''')
    
    conn.commit()
    logger.info("Database schema created successfully")


def create_indexes(conn: sqlite3.Connection) -> None:
    """Create indexes on frequently queried fields"""
    cursor = conn.cursor()
    
    logger.info("Creating database indexes...")
    
    indexes = [
        # Races indexes
        "CREATE INDEX IF NOT EXISTS idx_races_date ON races(date)",
        "CREATE INDEX IF NOT EXISTS idx_races_course ON races(course)",
        "CREATE INDEX IF NOT EXISTS idx_races_course_id ON races(course_id)",
        "CREATE INDEX IF NOT EXISTS idx_races_region ON races(region)",
        
        # Runners indexes
        "CREATE INDEX IF NOT EXISTS idx_runners_race_id ON runners(race_id)",
        "CREATE INDEX IF NOT EXISTS idx_runners_horse_id ON runners(horse_id)",
        "CREATE INDEX IF NOT EXISTS idx_runners_trainer_id ON runners(trainer_id)",
        "CREATE INDEX IF NOT EXISTS idx_runners_jockey_id ON runners(jockey_id)",
        
        # Horses indexes
        "CREATE INDEX IF NOT EXISTS idx_horses_name ON horses(name)",
        "CREATE INDEX IF NOT EXISTS idx_horses_sire_id ON horses(sire_id)",
        "CREATE INDEX IF NOT EXISTS idx_horses_dam_id ON horses(dam_id)",
        
        # Nested data indexes
        "CREATE INDEX IF NOT EXISTS idx_runner_odds_runner_id ON runner_odds(runner_id)",
        "CREATE INDEX IF NOT EXISTS idx_runner_quotes_runner_id ON runner_quotes(runner_id)",
        "CREATE INDEX IF NOT EXISTS idx_prev_trainers_horse_id ON prev_trainers(horse_id)",
        "CREATE INDEX IF NOT EXISTS idx_prev_owners_horse_id ON prev_owners(horse_id)",
    ]
    
    for index_sql in indexes:
        cursor.execute(index_sql)
    
    conn.commit()
    logger.info("Indexes created successfully")


def optimize_database(conn: sqlite3.Connection) -> None:
    """Optimize database with VACUUM and ANALYZE"""
    logger.info("Optimizing database...")
    cursor = conn.cursor()
    cursor.execute("VACUUM")
    cursor.execute("ANALYZE")
    conn.commit()
    logger.info("Database optimization complete")


# ============================================================================
# DATABASE HELPER FUNCTIONS
# ============================================================================

def insert_or_get_dam(cursor: sqlite3.Cursor, dam_id: Optional[str], dam_name: Optional[str], 
                      dam_region: Optional[str]) -> Optional[str]:
    """Insert or get dam (mother horse)"""
    if not dam_id or not dam_name:
        return None
    
    cursor.execute('''
        INSERT OR IGNORE INTO dams (dam_id, name, region)
        VALUES (?, ?, ?)
    ''', (dam_id, dam_name, dam_region))
    
    return dam_id


def insert_or_get_sire(cursor: sqlite3.Cursor, sire_id: Optional[str], sire_name: Optional[str], 
                       sire_region: Optional[str]) -> Optional[str]:
    """Insert or get sire (father horse)"""
    if not sire_id or not sire_name:
        return None
    
    cursor.execute('''
        INSERT OR IGNORE INTO sires (sire_id, name, region)
        VALUES (?, ?, ?)
    ''', (sire_id, sire_name, sire_region))
    
    return sire_id


def insert_or_get_damsire(cursor: sqlite3.Cursor, damsire_id: Optional[str], damsire_name: Optional[str], 
                          damsire_region: Optional[str]) -> Optional[str]:
    """Insert or get damsire (maternal grandsire)"""
    if not damsire_id or not damsire_name:
        return None
    
    cursor.execute('''
        INSERT OR IGNORE INTO damsires (damsire_id, name, region)
        VALUES (?, ?, ?)
    ''', (damsire_id, damsire_name, damsire_region))
    
    return damsire_id


def insert_or_get_horse(cursor: sqlite3.Cursor, runner_data: Dict[str, Any]) -> Optional[str]:
    """Insert or update horse, return horse_id"""
    horse_id = runner_data.get('horse_id')
    if not horse_id:
        return None
    
    # First, handle pedigree entries
    insert_or_get_dam(cursor, runner_data.get('dam_id'), runner_data.get('dam'), 
                     runner_data.get('dam_region'))
    insert_or_get_sire(cursor, runner_data.get('sire_id'), runner_data.get('sire'), 
                      runner_data.get('sire_region'))
    insert_or_get_damsire(cursor, runner_data.get('damsire_id'), runner_data.get('damsire'), 
                         runner_data.get('damsire_region'))
    
    # Insert or update horse
    cursor.execute('''
        INSERT INTO horses (
            horse_id, name, dob, age, sex, sex_code, colour, region, breeder,
            dam_id, dam_region, sire_id, sire_region, damsire_id, damsire_region
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(horse_id) DO UPDATE SET
            name = excluded.name,
            dob = excluded.dob,
            age = excluded.age,
            sex = excluded.sex,
            sex_code = excluded.sex_code,
            colour = excluded.colour,
            region = excluded.region,
            breeder = excluded.breeder,
            dam_id = excluded.dam_id,
            dam_region = excluded.dam_region,
            sire_id = excluded.sire_id,
            sire_region = excluded.sire_region,
            damsire_id = excluded.damsire_id,
            damsire_region = excluded.damsire_region,
            updated_at = CURRENT_TIMESTAMP
    ''', (
        horse_id, runner_data.get('horse'), runner_data.get('dob'), 
        runner_data.get('age'), runner_data.get('sex'), runner_data.get('sex_code'),
        runner_data.get('colour'), runner_data.get('region'), runner_data.get('breeder'),
        runner_data.get('dam_id'), runner_data.get('dam_region'),
        runner_data.get('sire_id'), runner_data.get('sire_region'),
        runner_data.get('damsire_id'), runner_data.get('damsire_region')
    ))
    
    # Handle previous trainers
    prev_trainers = runner_data.get('prev_trainers', [])
    if prev_trainers:
        for prev_trainer in prev_trainers:
            if isinstance(prev_trainer, dict):
                cursor.execute('''
                    INSERT INTO prev_trainers (horse_id, trainer_name, date_from, date_to)
                    VALUES (?, ?, ?, ?)
                ''', (horse_id, prev_trainer.get('name'), prev_trainer.get('from'), 
                     prev_trainer.get('to')))
    
    # Handle previous owners
    prev_owners = runner_data.get('prev_owners', [])
    if prev_owners:
        for prev_owner in prev_owners:
            if isinstance(prev_owner, dict):
                cursor.execute('''
                    INSERT INTO prev_owners (horse_id, owner_name, date_from, date_to)
                    VALUES (?, ?, ?, ?)
                ''', (horse_id, prev_owner.get('name'), prev_owner.get('from'), 
                     prev_owner.get('to')))
    
    return horse_id


def insert_or_get_trainer(cursor: sqlite3.Cursor, trainer_id: Optional[str], 
                         trainer_name: Optional[str], trainer_location: Optional[str],
                         trainer_14_days: Optional[Dict]) -> Optional[str]:
    """Insert or get trainer, return trainer_id"""
    if not trainer_id:
        return None
    
    cursor.execute('''
        INSERT INTO trainers (trainer_id, name, location)
        VALUES (?, ?, ?)
        ON CONFLICT(trainer_id) DO UPDATE SET
            name = excluded.name,
            location = excluded.location
    ''', (trainer_id, trainer_name, trainer_location))
    
    # Handle trainer 14 days statistics
    if trainer_14_days and isinstance(trainer_14_days, dict):
        for key, value in trainer_14_days.items():
            cursor.execute('''
                INSERT INTO trainer_14_days (trainer_id, stat_key, stat_value)
                VALUES (?, ?, ?)
            ''', (trainer_id, key, str(value)))
    
    return trainer_id


def insert_or_get_jockey(cursor: sqlite3.Cursor, jockey_id: Optional[str], 
                        jockey_name: Optional[str]) -> Optional[str]:
    """Insert or get jockey, return jockey_id"""
    if not jockey_id:
        return None
    
    cursor.execute('''
        INSERT INTO jockeys (jockey_id, name)
        VALUES (?, ?)
        ON CONFLICT(jockey_id) DO UPDATE SET
            name = excluded.name
    ''', (jockey_id, jockey_name))
    
    return jockey_id


def insert_or_get_owner(cursor: sqlite3.Cursor, owner_id: Optional[str], 
                       owner_name: Optional[str]) -> Optional[str]:
    """Insert or get owner, return owner_id"""
    if not owner_id:
        return None
    
    cursor.execute('''
        INSERT INTO owners (owner_id, name)
        VALUES (?, ?)
        ON CONFLICT(owner_id) DO UPDATE SET
            name = excluded.name
    ''', (owner_id, owner_name))
    
    return owner_id


def insert_race(cursor: sqlite3.Cursor, race_data: Dict[str, Any]) -> str:
    """Insert race data, return race_id"""
    race_id = race_data.get('race_id')
    
    cursor.execute('''
        INSERT OR REPLACE INTO races (
            race_id, course, course_id, date, off_time, off_dt, race_name,
            distance_round, distance, distance_f, region, pattern, sex_restriction,
            race_class, type, age_band, rating_band, prize, field_size,
            going_detailed, rail_movements, stalls, weather, going, surface, jumps,
            big_race, is_abandoned, tip, verdict, betting_forecast
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        race_id, race_data.get('course'), race_data.get('course_id'),
        race_data.get('date'), race_data.get('off_time'), race_data.get('off_dt'),
        race_data.get('race_name'), race_data.get('distance_round'),
        race_data.get('distance'), race_data.get('distance_f'),
        race_data.get('region'), race_data.get('pattern'),
        race_data.get('sex_restriction'), race_data.get('race_class'),
        race_data.get('type'), race_data.get('age_band'),
        race_data.get('rating_band'), race_data.get('prize'),
        race_data.get('field_size'), race_data.get('going_detailed'),
        race_data.get('rail_movements'), race_data.get('stalls'),
        race_data.get('weather'), race_data.get('going'),
        race_data.get('surface'), race_data.get('jumps'),
        1 if race_data.get('big_race') else 0,
        1 if race_data.get('is_abandoned') else 0,
        race_data.get('tip'), race_data.get('verdict'),
        race_data.get('betting_forecast')
    ))
    
    return race_id


def insert_runner(cursor: sqlite3.Cursor, race_id: str, runner_data: Dict[str, Any]) -> int:
    """Insert runner with all foreign keys, return runner_id"""
    
    # Insert/update related entities
    horse_id = insert_or_get_horse(cursor, runner_data)
    trainer_id = insert_or_get_trainer(
        cursor, 
        runner_data.get('trainer_id'), 
        runner_data.get('trainer'),
        runner_data.get('trainer_location'),
        runner_data.get('trainer_14_days')
    )
    jockey_id = insert_or_get_jockey(
        cursor, 
        runner_data.get('jockey_id'), 
        runner_data.get('jockey')
    )
    owner_id = insert_or_get_owner(
        cursor, 
        runner_data.get('owner_id'), 
        runner_data.get('owner')
    )
    
    # Insert runner
    cursor.execute('''
        INSERT INTO runners (
            race_id, horse_id, trainer_id, jockey_id, owner_id,
            number, draw, headgear, headgear_run, wind_surgery, wind_surgery_run,
            lbs, ofr, rpr, ts, silk_url, last_run, form, trainer_rtf,
            comment, spotlight
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        race_id, horse_id, trainer_id, jockey_id, owner_id,
        runner_data.get('number'), runner_data.get('draw'),
        runner_data.get('headgear'), runner_data.get('headgear_run'),
        runner_data.get('wind_surgery'), runner_data.get('wind_surgery_run'),
        runner_data.get('lbs'), runner_data.get('ofr'),
        runner_data.get('rpr'), runner_data.get('ts'),
        runner_data.get('silk_url'), runner_data.get('last_run'),
        runner_data.get('form'), runner_data.get('trainer_rtf'),
        runner_data.get('comment'), runner_data.get('spotlight')
    ))
    
    runner_id = cursor.lastrowid
    
    # Insert nested data
    insert_nested_data(cursor, runner_id, runner_data)
    
    return runner_id


def insert_nested_data(cursor: sqlite3.Cursor, runner_id: int, runner_data: Dict[str, Any]) -> None:
    """Insert nested array data for a runner"""
    
    # Insert odds
    odds_list = runner_data.get('odds', [])
    if odds_list:
        for odds in odds_list:
            if odds:  # Skip empty/null values
                cursor.execute('''
                    INSERT INTO runner_odds (runner_id, odds_value)
                    VALUES (?, ?)
                ''', (runner_id, str(odds)))
    
    # Insert quotes
    quotes_list = runner_data.get('quotes', [])
    if quotes_list:
        for quote in quotes_list:
            if isinstance(quote, dict):
                cursor.execute('''
                    INSERT INTO runner_quotes (runner_id, quote_text, source)
                    VALUES (?, ?, ?)
                ''', (runner_id, quote.get('text'), quote.get('source')))
            elif quote:  # If it's just a string
                cursor.execute('''
                    INSERT INTO runner_quotes (runner_id, quote_text)
                    VALUES (?, ?)
                ''', (runner_id, str(quote)))
    
    # Insert medical records
    medical_list = runner_data.get('medical', [])
    if medical_list:
        for medical in medical_list:
            if isinstance(medical, dict):
                cursor.execute('''
                    INSERT INTO runner_medical (runner_id, medical_note, date)
                    VALUES (?, ?, ?)
                ''', (runner_id, medical.get('note'), medical.get('date')))
            elif medical:
                cursor.execute('''
                    INSERT INTO runner_medical (runner_id, medical_note)
                    VALUES (?, ?)
                ''', (runner_id, str(medical)))
    
    # Insert stable tour comments
    stable_tour_list = runner_data.get('stable_tour', [])
    if stable_tour_list:
        for stable_tour in stable_tour_list:
            if isinstance(stable_tour, dict):
                cursor.execute('''
                    INSERT INTO runner_stable_tour (runner_id, comment, date)
                    VALUES (?, ?, ?)
                ''', (runner_id, stable_tour.get('comment'), stable_tour.get('date')))
            elif stable_tour:
                cursor.execute('''
                    INSERT INTO runner_stable_tour (runner_id, comment)
                    VALUES (?, ?)
                ''', (runner_id, str(stable_tour)))
    
    # Insert past results flags
    flags_list = runner_data.get('past_results_flags', [])
    if flags_list:
        for flag in flags_list:
            if flag:
                cursor.execute('''
                    INSERT INTO runner_past_results_flags (runner_id, flag_value)
                    VALUES (?, ?)
                ''', (runner_id, str(flag)))


def get_existing_dates(conn: sqlite3.Connection) -> set:
    """Query dates already in database"""
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT date FROM races")
    return {row[0] for row in cursor.fetchall()}


# ============================================================================
# API FUNCTIONS
# ============================================================================

def fetch_and_process(endpoint: str, params: Optional[Dict] = None, 
                     max_retries: int = 5) -> Optional[Dict]:
    """
    Make API request with error handling, retries, and rate limiting
    
    Args:
        endpoint: API endpoint to call
        params: Request parameters
        max_retries: Maximum number of retry attempts
        
    Returns:
        JSON response data or None if request failed
    """
    retry_delay = 1  # Start with 1 second delay
    
    for attempt in range(max_retries):
        try:
            response = requests.get(
                f"{BASE_URL}{endpoint}", 
                auth=(USERNAME, PASSWORD), 
                params=params,
                timeout=30
            )
            
            # Handle 503 Service Unavailable with exponential backoff
            if response.status_code == 503:
                logger.warning(f"Error 503 on attempt {attempt + 1}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            
            # Rate limiting
            time.sleep(RATE_LIMIT)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                return None
    
    return None


def fetch_racecards_for_date(date_str: str) -> Optional[Dict]:
    """Fetch racecards for a specific date"""
    endpoint = "/v1/racecards/pro"
    params = {
        'date': date_str
    }
    
    logger.info(f"Fetching racecards for {date_str}...")
    return fetch_and_process(endpoint, params)


# ============================================================================
# DATA PROCESSING
# ============================================================================

def process_racecard_response(conn: sqlite3.Connection, data: Dict, date_str: str) -> Tuple[int, int]:
    """
    Process API response and insert into database
    
    Returns:
        Tuple of (races_count, runners_count)
    """
    cursor = conn.cursor()
    races_count = 0
    runners_count = 0
    
    try:
        racecards = data.get('racecards', [])
        
        for racecard in racecards:
            # Insert race
            race_id = insert_race(cursor, racecard)
            races_count += 1
            
            # Insert runners
            runners = racecard.get('runners', [])
            for runner in runners:
                insert_runner(cursor, race_id, runner)
                runners_count += 1
        
        conn.commit()
        logger.info(f"Processed {races_count} races and {runners_count} runners for {date_str}")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error processing data for {date_str}: {e}")
        logger.error(traceback.format_exc())
        raise
    
    return races_count, runners_count


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def generate_date_range(start_date: str, end_date: str) -> List[str]:
    """Generate list of dates between start and end (inclusive)"""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    
    return dates


def main():
    """Main execution flow"""
    logger.info("=" * 80)
    logger.info("Starting Racecards Pro Data Fetch")
    logger.info("=" * 80)
    logger.info(f"Date range: {START_DATE} to {END_DATE}")
    logger.info(f"Database: {DB_PATH}")
    logger.info(f"Rate limit: {RATE_LIMIT} seconds")
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Create schema
        create_normalized_schema(conn)
        
        # Generate date range
        all_dates = generate_date_range(START_DATE, END_DATE)
        logger.info(f"Total dates in range: {len(all_dates)}")
        
        # Check existing dates
        existing_dates = get_existing_dates(conn)
        logger.info(f"Dates already in database: {len(existing_dates)}")
        
        # Find missing dates
        missing_dates = [d for d in all_dates if d not in existing_dates]
        logger.info(f"Dates to fetch: {len(missing_dates)}")
        
        if not missing_dates:
            logger.info("No missing dates to fetch. Database is up to date.")
            return
        
        # Fetch data for each missing date
        total_races = 0
        total_runners = 0
        
        for i, date_str in enumerate(missing_dates, 1):
            logger.info(f"Progress: {i}/{len(missing_dates)} - {date_str}")
            
            # Fetch data
            data = fetch_racecards_for_date(date_str)
            
            if data:
                # Process and insert into database
                races, runners = process_racecard_response(conn, data, date_str)
                total_races += races
                total_runners += runners
            else:
                logger.warning(f"No data returned for {date_str}")
        
        # Create indexes after bulk insert
        create_indexes(conn)
        
        # Optimize database
        optimize_database(conn)
        
        logger.info("=" * 80)
        logger.info("Data fetch complete!")
        logger.info(f"Total races fetched: {total_races}")
        logger.info(f"Total runners fetched: {total_runners}")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Fatal error in main execution: {e}")
        logger.error(traceback.format_exc())
        raise
    
    finally:
        conn.close()
        logger.info("Database connection closed")


if __name__ == "__main__":
    main()

