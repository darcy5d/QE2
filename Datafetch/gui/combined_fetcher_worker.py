"""
Combined Fetcher Worker - Fetches both racecards AND results in one go
"""

from PySide6.QtCore import QThread, Signal
from datetime import datetime, timedelta
from pathlib import Path
import sys
import sqlite3
import requests
from requests.auth import HTTPBasicAuth
import time

sys.path.insert(0, str(Path(__file__).parent.parent))
from .database import DatabaseHelper


class CombinedFetcherWorker(QThread):
    """
    Background worker that fetches:
    1. Racecards (pre-race data)
    2. Results (post-race data with positions, times, SP)
    
    This ensures we always have both datasets in sync
    """
    
    # Signals
    progress = Signal(int, int, str)  # current, total, phase
    status = Signal(str)  # status message
    finished = Signal(int, int, int)  # races_added, runners_added, results_added
    error = Signal(str)  # error message
    
    def __init__(self, db_helper: DatabaseHelper, end_date: str):
        super().__init__()
        self.db_path = str(db_helper.db_path)
        self.end_date = end_date
        self.start_date = "2023-01-23"  # API data starts here
        self.conn = None
        self.session = None
        
    def run(self):
        """Run the combined fetch in background thread"""
        try:
            # Create database connection in this thread
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys = ON")
            
            # Create session for API requests
            self.session = requests.Session()
            cred_file = Path(__file__).parent.parent / "reqd_files" / "cred.txt"
            with open(cred_file, "r") as f:
                username = f.readline().strip()
                password = f.readline().strip()
            self.session.auth = HTTPBasicAuth(username, password)
            
            # Phase 1: Fetch Racecards
            self.status.emit("Phase 1: Checking for missing racecards...")
            existing_dates = self.get_existing_dates()
            all_dates = self.generate_date_range(self.start_date, self.end_date)
            missing_dates = [d for d in all_dates if d not in existing_dates]
            
            total_races = 0
            total_runners = 0
            
            if missing_dates:
                self.status.emit(f"Found {len(missing_dates)} missing dates for racecards")
                
                for i, date in enumerate(missing_dates, 1):
                    self.status.emit(f"Fetching racecard: {date}")
                    self.progress.emit(i, len(missing_dates), "Racecards")
                    
                    races, runners = self.fetch_racecard(date)
                    total_races += races
                    total_runners += runners
                    
                    time.sleep(0.55)  # Rate limiting
            else:
                self.status.emit("No missing racecards - all up to date!")
            
            # Phase 2: Fetch Results
            self.status.emit("Phase 2: Checking for missing results...")
            races_without_results = self.get_races_without_results()
            
            total_results = 0
            
            if races_without_results:
                self.status.emit(f"Found {len(races_without_results)} races without results")
                
                for i, race_id in enumerate(races_without_results, 1):
                    if i % 10 == 0:  # Update status every 10 races
                        self.status.emit(f"Fetching results: {i}/{len(races_without_results)}")
                    self.progress.emit(i, len(races_without_results), "Results")
                    
                    results_count = self.fetch_results(race_id)
                    total_results += results_count
                    
                    time.sleep(0.55)  # Rate limiting
            else:
                self.status.emit("No missing results - all up to date!")
            
            # Optimize database
            self.status.emit("Optimizing database...")
            self.optimize_database()
            
            # Close connections
            if self.conn:
                self.conn.close()
            if self.session:
                self.session.close()
            
            self.finished.emit(total_races, total_runners, total_results)
            
        except Exception as e:
            if self.conn:
                self.conn.close()
            if self.session:
                self.session.close()
            self.error.emit(str(e))
    
    def get_existing_dates(self):
        """Get set of existing dates in database"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT date FROM races ORDER BY date")
        return {row[0] for row in cursor.fetchall()}
    
    def get_races_without_results(self):
        """Get race_ids that don't have results yet and are not abandoned"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT r.race_id
            FROM races r
            LEFT JOIN results res ON r.race_id = res.race_id
            WHERE res.result_id IS NULL
            AND r.is_abandoned = 0
            AND r.date < date('now')
            ORDER BY r.date
        """)
        return [row['race_id'] for row in cursor.fetchall()]
    
    def generate_date_range(self, start_date: str, end_date: str):
        """Generate list of dates between start and end"""
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        dates = []
        current = start
        while current <= end:
            dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        
        return dates
    
    def fetch_racecard(self, date: str):
        """Fetch racecard data for a specific date"""
        url = "https://api.theracingapi.com/v1/racecards/pro"
        params = {'date': date}
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return self.process_and_save_racecards(data)
            else:
                return 0, 0
                
        except Exception as e:
            print(f"Error fetching racecard {date}: {e}")
            return 0, 0
    
    def fetch_results(self, race_id: str):
        """Fetch results for a specific race"""
        url = f"https://api.theracingapi.com/v1/results/{race_id}"
        
        try:
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return self.process_and_save_results(race_id, data)
            elif response.status_code == 404:
                # Results not available yet (future race or not posted)
                return 0
            else:
                return 0
                
        except Exception as e:
            print(f"Error fetching results {race_id}: {e}")
            return 0
    
    def process_and_save_racecards(self, data: dict):
        """Process and save racecard data (simplified version)"""
        cursor = self.conn.cursor()
        racecards = data.get('racecards', [])
        
        races_count = 0
        runners_count = 0
        
        try:
            for racecard in racecards:
                race_id = racecard.get('race_id')
                
                # Check if race exists
                cursor.execute("SELECT race_id FROM races WHERE race_id = ?", (race_id,))
                if cursor.fetchone():
                    continue
                
                # Insert race (minimal version - the full fetcher does more)
                cursor.execute('''
                    INSERT OR REPLACE INTO races (
                        race_id, course, course_id, date, off_time, race_name,
                        distance, distance_f, region, type, race_class, going,
                        surface, prize, field_size, is_abandoned
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    race_id,
                    racecard.get('course'),
                    racecard.get('course_id'),
                    racecard.get('date'),
                    racecard.get('off_time'),
                    racecard.get('race_name'),
                    racecard.get('distance'),
                    racecard.get('distance_f'),
                    racecard.get('region'),
                    racecard.get('type'),
                    racecard.get('race_class'),
                    racecard.get('going'),
                    racecard.get('surface'),
                    racecard.get('prize'),
                    racecard.get('field_size'),
                    1 if racecard.get('is_abandoned') else 0
                ))
                
                # Verify race was inserted
                cursor.execute("SELECT race_id FROM races WHERE race_id = ?", (race_id,))
                if not cursor.fetchone():
                    print(f"WARNING: Race {race_id} was not inserted!")
                    continue
                
                races_count += 1
                
                # Insert runners (simplified)
                for runner in racecard.get('runners', []):
                    horse_id = runner.get('horse_id')
                    if not horse_id:
                        continue
                    
                    # Insert horse if not exists
                    cursor.execute('''
                        INSERT OR IGNORE INTO horses (horse_id, name)
                        VALUES (?, ?)
                    ''', (horse_id, runner.get('horse')))
                    
                    # Insert trainer if not exists
                    trainer_id = runner.get('trainer_id')
                    # Convert empty string to None (NULL) for foreign key compatibility
                    if trainer_id == '':
                        trainer_id = None
                    if trainer_id:
                        cursor.execute('''
                            INSERT OR IGNORE INTO trainers (trainer_id, name)
                            VALUES (?, ?)
                        ''', (trainer_id, runner.get('trainer')))
                    
                    # Insert jockey if not exists
                    jockey_id = runner.get('jockey_id')
                    # Convert empty string to None (NULL) for foreign key compatibility
                    if jockey_id == '':
                        jockey_id = None
                    if jockey_id:
                        cursor.execute('''
                            INSERT OR IGNORE INTO jockeys (jockey_id, name)
                            VALUES (?, ?)
                        ''', (jockey_id, runner.get('jockey')))
                    
                    # Insert owner if not exists (FOREIGN KEY FIX!)
                    owner_id = runner.get('owner_id')
                    # Convert empty string to None (NULL) for foreign key compatibility
                    if owner_id == '':
                        owner_id = None
                    if owner_id:
                        cursor.execute('''
                            INSERT OR IGNORE INTO owners (owner_id, name)
                            VALUES (?, ?)
                        ''', (owner_id, runner.get('owner', 'Unknown')))
                    
                    # Insert runner (including owner_id to satisfy foreign key)
                    cursor.execute('''
                        INSERT OR IGNORE INTO runners (
                            race_id, horse_id, trainer_id, jockey_id, owner_id,
                            number, draw, lbs, ofr, rpr, ts, form, last_run
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        race_id, horse_id, trainer_id, jockey_id, owner_id,
                        runner.get('number'),
                        runner.get('draw'),
                        runner.get('lbs'),
                        runner.get('ofr'),
                        runner.get('rpr'),
                        runner.get('ts'),
                        runner.get('form'),
                        runner.get('last_run')
                    ))
                    
                    runners_count += 1
            
            self.conn.commit()
            
        except Exception as e:
            self.conn.rollback()
            import traceback
            print(f"Error processing racecards: {e}")
            print(f"Full error: {traceback.format_exc()}")
            # Print the problematic data for debugging
            if 'runner' in locals():
                print(f"Problematic runner: horse={runner.get('horse')}, horse_id={runner.get('horse_id')}, "
                      f"trainer_id={runner.get('trainer_id')}, jockey_id={runner.get('jockey_id')}, "
                      f"owner_id={runner.get('owner_id')}")
        
        return races_count, runners_count
    
    def process_and_save_results(self, race_id: str, data: dict):
        """Process and save results data"""
        cursor = self.conn.cursor()
        runners = data.get('runners', [])
        
        results_count = 0
        
        try:
            for runner in runners:
                horse_id = runner.get('horse_id')
                if not horse_id:
                    continue
                
                # Check if result already exists
                cursor.execute("""
                    SELECT result_id FROM results 
                    WHERE race_id = ? AND horse_id = ?
                """, (race_id, horse_id))
                if cursor.fetchone():
                    continue
                
                # Ensure related entities exist (results might have entities not in racecards)
                # Insert horse if not exists
                cursor.execute('''
                    INSERT OR IGNORE INTO horses (horse_id, name)
                    VALUES (?, ?)
                ''', (horse_id, runner.get('horse')))
                
                # Handle trainer
                trainer_id = runner.get('trainer_id')
                if trainer_id == '':
                    trainer_id = None
                if trainer_id:
                    cursor.execute('''
                        INSERT OR IGNORE INTO trainers (trainer_id, name)
                        VALUES (?, ?)
                    ''', (trainer_id, runner.get('trainer')))
                
                # Handle jockey
                jockey_id = runner.get('jockey_id')
                if jockey_id == '':
                    jockey_id = None
                if jockey_id:
                    cursor.execute('''
                        INSERT OR IGNORE INTO jockeys (jockey_id, name)
                        VALUES (?, ?)
                    ''', (jockey_id, runner.get('jockey')))
                
                # Handle owner
                owner_id = runner.get('owner_id')
                if owner_id == '':
                    owner_id = None
                if owner_id:
                    cursor.execute('''
                        INSERT OR IGNORE INTO owners (owner_id, name)
                        VALUES (?, ?)
                    ''', (owner_id, runner.get('owner', 'Unknown')))
                
                # Parse position
                position_str = runner.get('position', '')
                try:
                    position_int = int(position_str)
                except:
                    position_int = 999 if position_str else None
                
                # Insert result
                cursor.execute('''
                    INSERT OR IGNORE INTO results (
                        race_id, horse_id, trainer_id, jockey_id, owner_id,
                        position, position_int, btn, ovr_btn, time,
                        sp, sp_dec, prize, weight, weight_lbs,
                        headgear, ofr, rpr, tsr, comment, jockey_claim_lbs
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    race_id,
                    horse_id,
                    trainer_id,
                    jockey_id,
                    owner_id,
                    position_str,
                    position_int,
                    runner.get('btn'),
                    runner.get('ovr_btn'),
                    runner.get('time'),
                    runner.get('sp'),
                    runner.get('sp_dec'),
                    runner.get('prize'),
                    runner.get('weight'),
                    runner.get('weight_lbs'),
                    runner.get('headgear'),
                    runner.get('or'),
                    runner.get('rpr'),
                    runner.get('tsr'),
                    runner.get('comment'),
                    runner.get('jockey_claim_lbs', '0')
                ))
                
                results_count += 1
            
            self.conn.commit()
            
        except Exception as e:
            self.conn.rollback()
            print(f"Error processing results for {race_id}: {e}")
        
        return results_count
    
    def optimize_database(self):
        """Optimize database after bulk inserts"""
        cursor = self.conn.cursor()
        cursor.execute("VACUUM")
        cursor.execute("ANALYZE")
        self.conn.commit()

