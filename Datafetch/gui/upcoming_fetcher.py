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
            age INTEGER,
            sex TEXT,
            sex_code TEXT,
            dob TEXT,
            sire TEXT,
            sire_id TEXT,
            dam TEXT,
            dam_id TEXT,
            damsire TEXT,
            damsire_id TEXT,
            region TEXT,
            breeder TEXT,
            colour TEXT,
            trainer_location TEXT,
            trainer_14d_runs INTEGER,
            trainer_14d_wins INTEGER,
            trainer_14d_percent REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (race_id) REFERENCES races (race_id),
            FOREIGN KEY (horse_id) REFERENCES horses (horse_id),
            FOREIGN KEY (trainer_id) REFERENCES trainers (trainer_id),
            FOREIGN KEY (jockey_id) REFERENCES jockeys (jockey_id),
            FOREIGN KEY (owner_id) REFERENCES owners (owner_id)
        )
        ''')
        
        # Runner odds table
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
        
        # Market odds summary
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
        
        self.conn.commit()
    
    def save_runner_odds(self, cursor, runner_id: int, odds_data: list):
        """Save bookmaker odds for a runner"""
        if not odds_data:
            return
        
        import statistics
        decimal_odds = []
        
        for odds in odds_data:
            bookmaker = odds.get('bookmaker', '')
            fractional = odds.get('fractional', '')
            decimal_str = odds.get('decimal', '')
            ew_places = odds.get('ew_places', '')
            ew_denom = odds.get('ew_denom', '')
            updated = odds.get('updated', '')
            
            try:
                decimal_float = float(decimal_str) if decimal_str else None
                if decimal_float:
                    decimal_odds.append(decimal_float)
            except (ValueError, TypeError):
                decimal_float = None
            
            cursor.execute('''
                INSERT OR REPLACE INTO runner_odds (
                    runner_id, bookmaker, fractional, decimal,
                    ew_places, ew_denom, updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (runner_id, bookmaker, fractional, decimal_float,
                  ew_places, ew_denom, updated))
        
        # Calculate market aggregates
        if decimal_odds:
            cursor.execute('''
                INSERT OR REPLACE INTO runner_market_odds (
                    runner_id, avg_decimal, median_decimal, min_decimal,
                    max_decimal, bookmaker_count, implied_probability,
                    is_favorite, favorite_rank, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, CURRENT_TIMESTAMP)
            ''', (
                runner_id,
                statistics.mean(decimal_odds),
                statistics.median(decimal_odds),
                min(decimal_odds),
                max(decimal_odds),
                len(decimal_odds),
                1.0 / statistics.mean(decimal_odds)
            ))
    
    def update_favorite_status(self, cursor, race_id: str):
        """Update favorite rankings for all runners in a race"""
        cursor.execute('''
            WITH race_odds AS (
                SELECT mo.runner_id, mo.avg_decimal,
                       ROW_NUMBER() OVER (ORDER BY mo.avg_decimal ASC) as rank
                FROM runner_market_odds mo
                JOIN runners r ON mo.runner_id = r.runner_id
                WHERE r.race_id = ?
            )
            UPDATE runner_market_odds
            SET is_favorite = CASE WHEN race_odds.rank = 1 THEN 1 ELSE 0 END,
                favorite_rank = race_odds.rank
            FROM race_odds
            WHERE runner_market_odds.runner_id = race_odds.runner_id
        ''', (race_id,))
    
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
                
                # Insert runners with all new fields
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
                    
                    # Extract all new fields
                    age = runner.get('age', '')
                    sex = runner.get('sex', '')
                    sex_code = runner.get('sex_code', '')
                    dob = runner.get('dob', '')
                    sire = runner.get('sire', '')
                    sire_id = runner.get('sire_id', '')
                    dam = runner.get('dam', '')
                    dam_id = runner.get('dam_id', '')
                    damsire = runner.get('damsire', '')
                    damsire_id = runner.get('damsire_id', '')
                    region = runner.get('region', '')
                    breeder = runner.get('breeder', '')
                    colour = runner.get('colour', '')
                    trainer_location = runner.get('trainer_location', '')
                    
                    # Trainer 14 day stats
                    trainer_14d = runner.get('trainer_14_days', {})
                    trainer_14d_runs = trainer_14d.get('runs', '') if trainer_14d else ''
                    trainer_14d_wins = trainer_14d.get('wins', '') if trainer_14d else ''
                    trainer_14d_percent = trainer_14d.get('percent', '') if trainer_14d else ''
                    
                    # Convert to proper types
                    try:
                        age_int = int(age) if age else None
                    except:
                        age_int = None
                    
                    try:
                        trainer_14d_runs_int = int(trainer_14d_runs) if trainer_14d_runs else None
                        trainer_14d_wins_int = int(trainer_14d_wins) if trainer_14d_wins else None
                        # Remove % symbol if present
                        if isinstance(trainer_14d_percent, str):
                            trainer_14d_percent_clean = trainer_14d_percent.replace('%', '').strip()
                        else:
                            trainer_14d_percent_clean = trainer_14d_percent
                        trainer_14d_percent_float = float(trainer_14d_percent_clean) if trainer_14d_percent_clean else None
                    except:
                        trainer_14d_runs_int = None
                        trainer_14d_wins_int = None
                        trainer_14d_percent_float = None
                    
                    # Only insert runner if we have a valid horse_id
                    if horse_id:
                        cursor.execute('''
                            INSERT INTO runners (
                                race_id, horse_id, trainer_id, jockey_id, owner_id,
                                number, draw, lbs, ofr, rpr, ts, form, last_run,
                                headgear, headgear_run, wind_surgery, wind_surgery_run,
                                trainer_rtf, comment, spotlight, silk_url,
                                age, sex, sex_code, dob, sire, sire_id, dam, dam_id,
                                damsire, damsire_id, region, breeder, colour, trainer_location,
                                trainer_14d_runs, trainer_14d_wins, trainer_14d_percent
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                                      ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            race_id, 
                            horse_id,
                            trainer_id if trainer_id else None,
                            jockey_id if jockey_id else None,
                            owner_id if owner_id else None,
                            runner.get('number'), runner.get('draw'), runner.get('lbs'),
                            runner.get('ofr'), runner.get('rpr'), runner.get('ts'),
                            runner.get('form'), runner.get('last_run'),
                            runner.get('headgear'), runner.get('headgear_run'),
                            runner.get('wind_surgery'), runner.get('wind_surgery_run'),
                            runner.get('trainer_rtf'), runner.get('comment'),
                            runner.get('spotlight'), runner.get('silk_url'),
                            age_int, sex, sex_code, dob, sire, sire_id, dam, dam_id,
                            damsire, damsire_id, region, breeder, colour, trainer_location,
                            trainer_14d_runs_int, trainer_14d_wins_int, trainer_14d_percent_float
                        ))
                        
                        runner_id = cursor.lastrowid
                        
                        # Save odds data
                        if 'odds' in runner and runner['odds']:
                            self.save_runner_odds(cursor, runner_id, runner['odds'])
                
                # After all runners processed, update favorite rankings
                self.update_favorite_status(cursor, race_id)
            
            self.conn.commit()
            print(f"Successfully saved {races_count} races for {date}")
            return races_count
            
        except Exception as e:
            self.conn.rollback()
            print(f"Error processing {date}: {e}")
            import traceback
            traceback.print_exc()
            return 0

