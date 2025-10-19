#!/usr/bin/env python3
"""
Fetch historical race results from The Racing API
Matches results to existing racecard data in racing_pro.db

Usage:
    python fetch_historical_results.py [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--test]
"""

import sqlite3
import requests
from requests.auth import HTTPBasicAuth
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
import json
import argparse
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fetch_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Paths
DB_PATH = Path(__file__).parent / "racing_pro.db"
CRED_FILE = Path(__file__).parent / "reqd_files" / "cred.txt"

# API Configuration
API_BASE = "https://api.theracingapi.com"
RATE_LIMIT = 0.55  # seconds between requests

# Load credentials
def load_credentials():
    """Load API credentials from file"""
    try:
        with open(CRED_FILE, 'r') as f:
            lines = f.read().strip().split('\n')
            username = lines[0].strip()
            password = lines[1].strip()
        return username, password
    except Exception as e:
        logger.error(f"Failed to load credentials: {e}")
        raise

USERNAME, PASSWORD = load_credentials()


class ResultsFetcher:
    """Fetch and store race results"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(USERNAME, PASSWORD)
        
    def connect_db(self):
        """Connect to database"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            
    def get_dates_with_races(self, start_date: str, end_date: str) -> List[str]:
        """Get list of dates that have races in the database"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT date 
            FROM races 
            WHERE date >= ? AND date <= ?
            AND is_abandoned = 0
            ORDER BY date
        """, (start_date, end_date))
        return [row['date'] for row in cursor.fetchall()]
    
    def get_races_for_date(self, date: str) -> List[Dict]:
        """Get all races for a specific date"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT race_id, course, course_id, race_name, off_time, date
            FROM races
            WHERE date = ?
            AND is_abandoned = 0
            ORDER BY off_time
        """, (date,))
        return [dict(row) for row in cursor.fetchall()]
    
    def fetch_results_for_race(self, race_id: str, retries: int = 3) -> Optional[Dict]:
        """Fetch results from API for a specific race_id"""
        url = f"{API_BASE}/v1/results/{race_id}"
        
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    # Race results not available (might be future race or not yet posted)
                    logger.debug(f"No results found for race {race_id}")
                    return None
                logger.warning(f"Attempt {attempt + 1}/{retries} failed for {race_id}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed to fetch results for {race_id} after {retries} attempts")
                    return None
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1}/{retries} failed for {race_id}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    logger.error(f"Failed to fetch results for {race_id} after {retries} attempts")
                    return None
        
        return None
    
    def match_result_to_race(self, result: Dict, races_on_date: List[Dict]) -> Optional[str]:
        """
        Match a result to a race in our database
        Returns race_id if match found, None otherwise
        """
        result_course = result.get('course', '').lower().strip()
        result_time = result.get('off_time', '').strip()
        result_name = result.get('race_name', '').lower().strip()
        
        # Try exact match first
        for race in races_on_date:
            if (race['course'].lower() == result_course and 
                race['off_time'] == result_time):
                return race['race_id']
        
        # Try course + approximate time match
        for race in races_on_date:
            if race['course'].lower() == result_course:
                # Check if times are within 5 minutes
                try:
                    race_time = datetime.strptime(race['off_time'], '%H:%M')
                    result_time_dt = datetime.strptime(result_time, '%H:%M')
                    diff = abs((race_time - result_time_dt).total_seconds())
                    if diff <= 300:  # 5 minutes
                        return race['race_id']
                except:
                    pass
        
        # Try course + name similarity
        for race in races_on_date:
            if race['course'].lower() == result_course:
                # Simple substring match
                race_name_lower = race['race_name'].lower()
                if (result_name in race_name_lower or 
                    race_name_lower in result_name):
                    return race['race_id']
        
        return None
    
    def get_runner_id_for_result(self, race_id: str, horse_id: str) -> Optional[int]:
        """Get runner_id for a specific horse in a specific race"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT runner_id 
            FROM runners 
            WHERE race_id = ? AND horse_id = ?
        """, (race_id, horse_id))
        row = cursor.fetchone()
        return row['runner_id'] if row else None
    
    def insert_result(self, race_id: str, result_runner: Dict) -> bool:
        """Insert a single result into the database"""
        cursor = self.conn.cursor()
        
        horse_id = result_runner.get('horse_id')
        if not horse_id:
            logger.warning(f"No horse_id in result for race {race_id}")
            return False
        
        # Check if result already exists
        cursor.execute("""
            SELECT result_id FROM results 
            WHERE race_id = ? AND horse_id = ?
        """, (race_id, horse_id))
        if cursor.fetchone():
            logger.debug(f"Result already exists for race {race_id}, horse {horse_id}")
            return False
        
        # Convert position to integer (handle 'DNF', 'PU', etc.)
        position_str = result_runner.get('position', '')
        try:
            position_int = int(position_str)
        except:
            # Handle non-finishers
            position_int = 999 if position_str else None
        
        try:
            cursor.execute('''
                INSERT INTO results (
                    race_id, horse_id, trainer_id, jockey_id, owner_id,
                    position, position_int, btn, ovr_btn, time,
                    sp, sp_dec, prize, weight, weight_lbs,
                    headgear, ofr, rpr, tsr, comment, jockey_claim_lbs
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                race_id,
                horse_id,
                result_runner.get('trainer_id'),
                result_runner.get('jockey_id'),
                result_runner.get('owner_id'),
                position_str,
                position_int,
                result_runner.get('btn'),
                result_runner.get('ovr_btn'),
                result_runner.get('time'),
                result_runner.get('sp'),
                result_runner.get('sp_dec'),
                result_runner.get('prize'),
                result_runner.get('weight'),
                result_runner.get('weight_lbs'),
                result_runner.get('headgear'),
                result_runner.get('or'),  # Note: 'or' maps to 'ofr'
                result_runner.get('rpr'),
                result_runner.get('tsr'),
                result_runner.get('comment'),
                result_runner.get('jockey_claim_lbs', '0')
            ))
            return True
        except sqlite3.IntegrityError as e:
            logger.warning(f"Integrity error inserting result: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inserting result: {e}")
            return False
    
    def process_date(self, date: str) -> Dict[str, int]:
        """
        Process all results for a given date
        Returns stats dict with counts
        """
        stats = {
            'races_in_db': 0,
            'races_with_results': 0,
            'races_no_results': 0,
            'results_inserted': 0
        }
        
        # Get our races for this date
        our_races = self.get_races_for_date(date)
        stats['races_in_db'] = len(our_races)
        
        if not our_races:
            logger.info(f"No races in database for {date}")
            return stats
        
        logger.info(f"  Processing {len(our_races)} races...")
        
        # Fetch results for each race
        for race in our_races:
            race_id = race['race_id']
            
            # Check if we already have results for this race
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM results WHERE race_id = ?", (race_id,))
            if cursor.fetchone()[0] > 0:
                logger.debug(f"  Skipping {race_id} - already have results")
                stats['races_with_results'] += 1
                continue
            
            # Fetch results from API
            result_data = self.fetch_results_for_race(race_id)
            
            if not result_data:
                stats['races_no_results'] += 1
                continue
            
            # Process runners
            runners = result_data.get('runners', [])
            if not runners:
                logger.debug(f"  No runners in result for {race_id}")
                stats['races_no_results'] += 1
                continue
            
            stats['races_with_results'] += 1
            
            # Insert each runner's result
            for runner in runners:
                if self.insert_result(race_id, runner):
                    stats['results_inserted'] += 1
            
            # Rate limiting between races
            time.sleep(RATE_LIMIT)
        
        # Commit after each date
        self.conn.commit()
        
        return stats
    
    def fetch_results(self, start_date: str, end_date: str):
        """Main execution: fetch results for date range"""
        logger.info(f"Starting results fetch: {start_date} to {end_date}")
        logger.info(f"Database: {self.db_path}")
        
        self.connect_db()
        
        # Get dates that have races
        dates = self.get_dates_with_races(start_date, end_date)
        logger.info(f"Found {len(dates)} dates with races")
        
        total_stats = {
            'dates_processed': 0,
            'races_in_db': 0,
            'races_with_results': 0,
            'races_no_results': 0,
            'results_inserted': 0
        }
        
        start_time = time.time()
        
        try:
            for i, date in enumerate(dates, 1):
                logger.info(f"[{i}/{len(dates)}] Processing {date}...")
                
                stats = self.process_date(date)
                total_stats['dates_processed'] += 1
                total_stats['races_in_db'] += stats['races_in_db']
                total_stats['races_with_results'] += stats['races_with_results']
                total_stats['races_no_results'] += stats['races_no_results']
                total_stats['results_inserted'] += stats['results_inserted']
                
                logger.info(f"  ✓ {stats['races_with_results']} races with results, {stats['results_inserted']} results inserted")
        
        except KeyboardInterrupt:
            logger.warning("Interrupted by user")
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error during fetch: {e}", exc_info=True)
            self.conn.rollback()
            raise
        finally:
            elapsed = time.time() - start_time
            logger.info("\n" + "="*60)
            logger.info("FETCH COMPLETE")
            logger.info("="*60)
            logger.info(f"Dates processed: {total_stats['dates_processed']}")
            logger.info(f"Races in DB: {total_stats['races_in_db']}")
            logger.info(f"Races with results: {total_stats['races_with_results']}")
            logger.info(f"Races without results: {total_stats['races_no_results']}")
            logger.info(f"Total results inserted: {total_stats['results_inserted']}")
            logger.info(f"Time elapsed: {elapsed/60:.1f} minutes")
            logger.info(f"Average: {total_stats['results_inserted']/elapsed:.1f} results/second")
            logger.info("="*60)
            
            self.close()


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(description='Fetch historical race results')
    parser.add_argument('--start-date', default='2023-01-23', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', default='2023-04-30', help='End date (YYYY-MM-DD)')
    parser.add_argument('--test', action='store_true', help='Test mode (first 3 days only)')
    
    args = parser.parse_args()
    
    start_date = args.start_date
    end_date = args.end_date
    
    if args.test:
        logger.info("TEST MODE: Fetching first 3 days only")
        # Calculate 3 days from start
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = start_dt + timedelta(days=2)
        end_date = end_dt.strftime('%Y-%m-%d')
    
    if not DB_PATH.exists():
        logger.error(f"Database not found: {DB_PATH}")
        return
    
    fetcher = ResultsFetcher(DB_PATH)
    fetcher.fetch_results(start_date, end_date)


if __name__ == "__main__":
    main()

