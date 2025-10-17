"""
Fetcher Worker - Background thread for fetching racecard data
"""

from PySide6.QtCore import QThread, Signal
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from .database import DatabaseHelper


class FetcherWorker(QThread):
    """Background worker for fetching racecard data"""
    
    # Signals
    progress = Signal(int, int)  # current, total
    status = Signal(str)  # status message
    finished = Signal(int, int)  # races_added, runners_added
    error = Signal(str)  # error message
    
    def __init__(self, db_helper: DatabaseHelper, end_date: str):
        super().__init__()
        self.db_path = str(db_helper.db_path)  # Store path as string instead of connection
        self.end_date = end_date
        self.start_date = "2023-01-23"  # API data starts here
        self.conn = None  # Will create in thread
    
    def run(self):
        """Run the data fetch in background thread"""
        try:
            # Import the fetch logic
            import requests
            import time
            from datetime import datetime, timedelta
            import sqlite3
            
            # Create database connection in this thread
            self.conn = sqlite3.connect(self.db_path)
            
            # Get existing dates
            self.status.emit("Checking existing dates...")
            existing_dates = self.get_existing_dates()
            
            # Generate target date range
            all_dates = self.generate_date_range(self.start_date, self.end_date)
            
            # Find missing dates
            missing_dates = [d for d in all_dates if d not in existing_dates]
            
            if not missing_dates:
                self.status.emit("No missing dates to fetch")
                self.finished.emit(0, 0)
                return
            
            self.status.emit(f"Found {len(missing_dates)} missing dates")
            
            # Fetch missing dates
            total_races = 0
            total_runners = 0
            
            for i, date in enumerate(missing_dates, 1):
                self.status.emit(f"Fetching {date}... ({i}/{len(missing_dates)})")
                self.progress.emit(i, len(missing_dates))
                
                # Fetch data for this date
                races, runners = self.fetch_date(date)
                total_races += races
                total_runners += runners
                
                # Small delay to respect rate limiting
                time.sleep(0.55)
            
            # Emit completion
            self.status.emit("Optimizing database...")
            self.optimize_database()
            
            # Close connection
            if self.conn:
                self.conn.close()
            
            self.finished.emit(total_races, total_runners)
            
        except Exception as e:
            # Close connection on error
            if self.conn:
                self.conn.close()
            self.error.emit(str(e))
    
    def get_existing_dates(self):
        """Get set of existing dates in database"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT date FROM races ORDER BY date")
        return {row[0] for row in cursor.fetchall()}
    
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
    
    def fetch_date(self, date: str):
        """Fetch data for a specific date and insert into database"""
        import requests
        import sqlite3
        
        # Load credentials
        cred_file = Path(__file__).parent.parent / "reqd_files" / "cred.txt"
        with open(cred_file, "r") as f:
            username = f.readline().strip()
            password = f.readline().strip()
        
        # Make API request
        url = f"https://api.theracingapi.com/v1/racecards/pro"
        params = {'date': date}
        
        try:
            response = requests.get(url, auth=(username, password), params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return self.process_and_save(data, date)
            else:
                return 0, 0
                
        except Exception as e:
            print(f"Error fetching {date}: {e}")
            return 0, 0
    
    def process_and_save(self, data: dict, date: str):
        """Process API response and save to database"""
        cursor = self.conn.cursor()
        racecards = data.get('racecards', [])
        
        races_count = 0
        runners_count = 0
        
        try:
            for racecard in racecards:
                # Insert race (simplified version - you may want to import full logic)
                race_id = racecard.get('race_id')
                
                # Check if race already exists
                cursor.execute("SELECT race_id FROM races WHERE race_id = ?", (race_id,))
                if cursor.fetchone():
                    continue  # Skip if already exists
                
                # Insert race
                cursor.execute('''
                    INSERT OR IGNORE INTO races (
                        race_id, course, course_id, date, off_time, off_dt, race_name,
                        distance_round, distance, distance_f, region, pattern, sex_restriction,
                        race_class, type, age_band, rating_band, prize, field_size,
                        going_detailed, rail_movements, stalls, weather, going, surface, jumps,
                        big_race, is_abandoned, tip, verdict, betting_forecast
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    race_id, racecard.get('course'), racecard.get('course_id'),
                    racecard.get('date'), racecard.get('off_time'), racecard.get('off_dt'),
                    racecard.get('race_name'), racecard.get('distance_round'),
                    racecard.get('distance'), racecard.get('distance_f'),
                    racecard.get('region'), racecard.get('pattern'),
                    racecard.get('sex_restriction'), racecard.get('race_class'),
                    racecard.get('type'), racecard.get('age_band'),
                    racecard.get('rating_band'), racecard.get('prize'),
                    racecard.get('field_size'), racecard.get('going_detailed'),
                    racecard.get('rail_movements'), racecard.get('stalls'),
                    racecard.get('weather'), racecard.get('going'),
                    racecard.get('surface'), racecard.get('jumps'),
                    1 if racecard.get('big_race') else 0,
                    1 if racecard.get('is_abandoned') else 0,
                    racecard.get('tip'), racecard.get('verdict'),
                    racecard.get('betting_forecast')
                ))
                
                races_count += 1
                
                # Insert runners (simplified - just basic data)
                runners = racecard.get('runners', [])
                for runner in runners:
                    # Insert horse if needed
                    horse_id = runner.get('horse_id')
                    if horse_id:
                        cursor.execute('''
                            INSERT OR IGNORE INTO horses (horse_id, name, age, sex, colour, region)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (horse_id, runner.get('horse'), runner.get('age'), 
                             runner.get('sex'), runner.get('colour'), runner.get('region')))
                    
                    # Insert trainer if needed
                    trainer_id = runner.get('trainer_id')
                    if trainer_id:
                        cursor.execute('''
                            INSERT OR IGNORE INTO trainers (trainer_id, name, location)
                            VALUES (?, ?, ?)
                        ''', (trainer_id, runner.get('trainer'), runner.get('trainer_location')))
                    
                    # Insert jockey if needed
                    jockey_id = runner.get('jockey_id')
                    if jockey_id:
                        cursor.execute('''
                            INSERT OR IGNORE INTO jockeys (jockey_id, name)
                            VALUES (?, ?)
                        ''', (jockey_id, runner.get('jockey')))
                    
                    # Insert owner if needed
                    owner_id = runner.get('owner_id')
                    if owner_id:
                        cursor.execute('''
                            INSERT OR IGNORE INTO owners (owner_id, name)
                            VALUES (?, ?)
                        ''', (owner_id, runner.get('owner')))
                    
                    # Insert runner
                    cursor.execute('''
                        INSERT INTO runners (
                            race_id, horse_id, trainer_id, jockey_id, owner_id,
                            number, draw, lbs, ofr, rpr, ts, form, last_run
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        race_id, horse_id, trainer_id, jockey_id, owner_id,
                        runner.get('number'), runner.get('draw'), runner.get('lbs'),
                        runner.get('ofr'), runner.get('rpr'), runner.get('ts'),
                        runner.get('form'), runner.get('last_run')
                    ))
                    
                    runners_count += 1
            
            self.conn.commit()
            return races_count, runners_count
            
        except Exception as e:
            self.conn.rollback()
            print(f"Error processing {date}: {e}")
            return 0, 0
    
    def optimize_database(self):
        """Optimize database after bulk insert"""
        cursor = self.conn.cursor()
        cursor.execute("VACUUM")
        cursor.execute("ANALYZE")
        self.conn.commit()

