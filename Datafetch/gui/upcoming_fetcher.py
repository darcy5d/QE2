"""
Upcoming Races Fetcher - Fetch yesterday, today, and tomorrow's races
Creates/recreates upcoming_races.db with fresh data
"""

from PySide6.QtCore import QThread, Signal
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import requests
import time


class UpcomingRacesFetcher(QThread):
    """Fetch races for yesterday, today, tomorrow into separate database"""
    
    # Signals
    progress = Signal(int, int)  # current, total
    status = Signal(str)  # status message
    finished = Signal(int)  # total_races
    error = Signal(str)  # error message
    
    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path
        self.conn = None
        
    def run(self):
        """Fetch upcoming races"""
        try:
            # Calculate dates
            today = datetime.now()
            yesterday = today - timedelta(days=1)
            tomorrow = today + timedelta(days=1)
            
            dates = [
                yesterday.strftime("%Y-%m-%d"),
                today.strftime("%Y-%m-%d"),
                tomorrow.strftime("%Y-%m-%d")
            ]
            
            # Delete old database if exists
            db_file = Path(self.db_path)
            if db_file.exists():
                db_file.unlink()
            
            # Create new database with schema
            self.conn = sqlite3.connect(self.db_path)
            self.create_schema()
            
            # Fetch each date
            total_races = 0
            for i, date in enumerate(dates, 1):
                self.status.emit(f"Fetching {date}...")
                self.progress.emit(i, 3)
                races = self.fetch_date(date)
                total_races += races
                time.sleep(0.55)
            
            self.conn.close()
            self.finished.emit(total_races)
            
        except Exception as e:
            if self.conn:
                self.conn.close()
            self.error.emit(str(e))
    
    def create_schema(self):
        """Create database tables (same schema as racing_pro.db)"""
        cursor = self.conn.cursor()
        
        # Disable foreign keys for upcoming races (simpler, no constraints needed)
        cursor.execute("PRAGMA foreign_keys = OFF")
        
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
        
        # Dams
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS dams (
            dam_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            region TEXT
        )
        ''')
        
        # Sires
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sires (
            sire_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            region TEXT
        )
        ''')
        
        # Damsires
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS damsires (
            damsire_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            region TEXT
        )
        ''')
        
        # Trainers
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS trainers (
            trainer_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            location TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Jockeys
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS jockeys (
            jockey_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Owners
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS owners (
            owner_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Races table
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
        
        # Runners table
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
            form TEXT,
            trainer_rtf TEXT,
            last_run TEXT,
            comment TEXT,
            spotlight TEXT,
            silk_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (race_id) REFERENCES races (race_id),
            FOREIGN KEY (horse_id) REFERENCES horses (horse_id),
            FOREIGN KEY (trainer_id) REFERENCES trainers (trainer_id),
            FOREIGN KEY (jockey_id) REFERENCES jockeys (jockey_id),
            FOREIGN KEY (owner_id) REFERENCES owners (owner_id)
        )
        ''')
        
        self.conn.commit()
    
    def fetch_date(self, date: str) -> int:
        """Fetch and save races for specific date"""
        # Load credentials
        cred_file = Path(__file__).parent.parent / "reqd_files" / "cred.txt"
        with open(cred_file, "r") as f:
            username = f.readline().strip()
            password = f.readline().strip()
        
        # Make API request
        url = "https://api.theracingapi.com/v1/racecards/pro"
        params = {'date': date}
        
        try:
            response = requests.get(url, auth=(username, password), params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return self.process_and_save(data, date)
            else:
                return 0
                
        except Exception as e:
            print(f"Error fetching {date}: {e}")
            return 0
    
    def process_and_save(self, data: dict, date: str) -> int:
        """Process API response and save to database"""
        cursor = self.conn.cursor()
        racecards = data.get('racecards', [])
        
        races_count = 0
        
        try:
            for racecard in racecards:
                race_id = racecard.get('race_id')
                
                # Skip check since we're creating a fresh database each time
                # Check if race already exists
                # cursor.execute("SELECT race_id FROM races WHERE race_id = ?", (race_id,))
                # if cursor.fetchone():
                #     continue  # Skip if already exists
                
                # Insert race
                cursor.execute('''
                    INSERT INTO races (
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
                
                # Insert runners (basic data only for upcoming races)
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
                    
                    # Only insert runner if we have a valid horse_id
                    # Foreign keys can be NULL, but if provided they must exist
                    if horse_id:
                        cursor.execute('''
                            INSERT INTO runners (
                                race_id, horse_id, trainer_id, jockey_id, owner_id,
                                number, draw, lbs, ofr, rpr, ts, form, last_run
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            race_id, 
                            horse_id if horse_id else None,
                            trainer_id if trainer_id else None,
                            jockey_id if jockey_id else None,
                            owner_id if owner_id else None,
                            runner.get('number'), runner.get('draw'), runner.get('lbs'),
                            runner.get('ofr'), runner.get('rpr'), runner.get('ts'),
                            runner.get('form'), runner.get('last_run')
                        ))
            
            self.conn.commit()
            print(f"Successfully saved {races_count} races for {date}")
            return races_count
            
        except Exception as e:
            self.conn.rollback()
            print(f"Error processing {date}: {e}")
            import traceback
            traceback.print_exc()
            return 0

