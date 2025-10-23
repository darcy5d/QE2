"""
Complete Database Rebuild Worker
Re-fetches all historical data with proper odds aggregation
"""

from PySide6.QtCore import QThread, Signal
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
import shutil
import requests
from requests.auth import HTTPBasicAuth
import time
import statistics
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))


class RebuildDatabaseWorker(QThread):
    """Complete database rebuild with proper odds aggregation"""
    
    # Signals
    progress_update = Signal(str)       # Progress message
    phase_changed = Signal(str, int)    # Phase name, total items
    item_processed = Signal(int)        # Current item count
    rebuild_complete = Signal(dict)     # Final stats
    rebuild_error = Signal(str)         # Error message
    
    def __init__(self, start_date: str, end_date: str, db_path: str):
        super().__init__()
        self.start_date = start_date
        self.end_date = end_date
        self.db_path = Path(db_path)
        self.backup_path = None
        self.conn = None
        self.session = None
        self.username = None
        self.password = None
        
        # API config
        self.api_base = "https://api.theracingapi.com"
        self.rate_limit = 0.55
        
        # Stats tracking
        self.stats = {
            'races_fetched': 0,
            'runners_processed': 0,
            'results_fetched': 0,
            'odds_aggregated': 0,
            'features_generated': 0
        }
    
    def run(self):
        """Execute full rebuild"""
        print(f"\n[RebuildWorker] Thread started!")
        print(f"[RebuildWorker] Date range: {self.start_date} to {self.end_date}")
        print(f"[RebuildWorker] Database: {self.db_path}")
        try:
            print("\n" + "="*60)
            print("DATABASE REBUILD STARTING")
            print("="*60 + "\n")
            self.progress_update.emit("="*60)
            self.progress_update.emit("DATABASE REBUILD STARTING")
            self.progress_update.emit("="*60)
            self.progress_update.emit("")
            
            # Load credentials
            print("Loading API credentials...")
            self.progress_update.emit("Loading API credentials...")
            try:
                cred_file = Path(__file__).parent.parent / "reqd_files" / "cred.txt"
                print(f"Looking for cred file at: {cred_file}")
                with open(cred_file, "r") as f:
                    self.username = f.readline().strip()
                    self.password = f.readline().strip()
                print("✓ Credentials loaded\n")
                self.progress_update.emit("✓ Credentials loaded")
                self.progress_update.emit("")
            except Exception as e:
                error_msg = f"Failed to load API credentials from {cred_file}: {e}"
                print(f"ERROR: {error_msg}")
                raise Exception(error_msg)
            
            # Phase 1: Backup
            self.phase_changed.emit("Phase 1/6: Backing up database", 1)
            self.backup_database()
            self.item_processed.emit(1)
            
            # Phase 2: Create fresh schema
            self.phase_changed.emit("Phase 2/6: Creating fresh schema", 1)
            self.create_fresh_schema()
            self.item_processed.emit(1)
            
            # Phase 3: Fetch racecards
            dates = self.generate_date_range(self.start_date, self.end_date)
            self.phase_changed.emit(f"Phase 3/6: Fetching racecards ({len(dates)} dates)", len(dates))
            self.fetch_all_racecards(dates)
            
            # Phase 4: Fetch results
            race_ids = self.get_completed_races()
            self.phase_changed.emit(f"Phase 4/6: Fetching results ({len(race_ids)} races)", len(race_ids))
            self.fetch_all_results(race_ids)
            
            # Phase 5: Verify odds aggregation
            self.phase_changed.emit("Phase 5/6: Verifying odds aggregation", 1)
            self.verify_odds_coverage()
            self.item_processed.emit(1)
            
            # Phase 6: Regenerate features
            self.phase_changed.emit("Phase 6/6: Regenerating ML features", 1)
            self.regenerate_features()
            self.item_processed.emit(1)
            
            # Success!
            self.progress_update.emit("")
            self.progress_update.emit("="*60)
            self.progress_update.emit("✓ DATABASE REBUILD COMPLETE!")
            self.progress_update.emit("="*60)
            
            final_stats = self.get_final_stats()
            self.rebuild_complete.emit(final_stats)
            
        except Exception as e:
            import traceback
            error_msg = f"Rebuild failed: {str(e)}\n{traceback.format_exc()}"
            print("\n" + "="*60)
            print("❌ REBUILD FAILED")
            print("="*60)
            print(error_msg)
            self.progress_update.emit("")
            self.progress_update.emit("="*60)
            self.progress_update.emit("❌ REBUILD FAILED")
            self.progress_update.emit("="*60)
            self.progress_update.emit(error_msg)
            self.rebuild_error.emit(str(e))
        finally:
            if self.conn:
                self.conn.close()
            if self.session:
                self.session.close()
    
    def backup_database(self):
        """Create backup of current database"""
        if not self.db_path.exists():
            self.progress_update.emit("No existing database to backup")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_path = self.db_path.parent / f"racing_pro_backup_{timestamp}.db"
        
        self.progress_update.emit(f"Creating backup: {self.backup_path.name}")
        shutil.copy2(self.db_path, self.backup_path)
        
        backup_size = self.backup_path.stat().st_size / (1024 * 1024)  # MB
        self.progress_update.emit(f"✓ Backup created ({backup_size:.1f} MB)")
        self.progress_update.emit(f"  Location: {self.backup_path}")
        self.progress_update.emit("")
    
    def create_fresh_schema(self):
        """Create fresh database with new schema"""
        print("Removing old database...")
        self.progress_update.emit("Removing old database...")
        if self.db_path.exists():
            self.db_path.unlink()
            print(f"✓ Deleted old database")
        
        print("Creating fresh schema...")
        self.progress_update.emit("Creating fresh schema...")
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        print(f"✓ Connected to new database: {self.db_path}")
        
        # Import schema creation from upcoming_fetcher
        print("Importing UpcomingRacesFetcher...")
        from .upcoming_fetcher import UpcomingRacesFetcher
        # Create fetcher with our db_path, then use our connection
        print("Creating fetcher instance...")
        fetcher = UpcomingRacesFetcher(str(self.db_path))
        # Override the connection to use ours (already created)
        fetcher.conn = self.conn
        print("Calling create_schema()...")
        
        # Use the create_schema method which has the new format
        fetcher.create_schema()
        print("✓ Base schema created")
        
        # Add results table (not in upcoming_fetcher)
        print("Adding results table...")
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS results (
                result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                race_id TEXT NOT NULL,
                horse_id TEXT NOT NULL,
                position TEXT,
                position_int INTEGER,
                distance TEXT,
                distance_full TEXT,
                time_seconds REAL,
                rpr TEXT,
                ts TEXT,
                comment TEXT,
                FOREIGN KEY (race_id) REFERENCES races (race_id),
                FOREIGN KEY (horse_id) REFERENCES horses (horse_id)
            )
        ''')
        print("✓ Results table created")
        
        # Add ml_features table stub (will be populated by feature generation)
        print("Adding ml_features table stub...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ml_features (
                feature_id INTEGER PRIMARY KEY AUTOINCREMENT,
                race_id TEXT NOT NULL,
                runner_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (race_id) REFERENCES races (race_id),
                FOREIGN KEY (runner_id) REFERENCES runners (runner_id)
            )
        ''')
        print("✓ ML features table created")
        
        self.conn.commit()
        print("✓ Schema committed to database\n")
        
        self.progress_update.emit("✓ Fresh schema created with runner_market_odds table")
        self.progress_update.emit("")
    
    def generate_date_range(self, start: str, end: str):
        """Generate list of dates"""
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")
        
        dates = []
        current = start_dt
        while current <= end_dt:
            dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        
        return dates
    
    def fetch_all_racecards(self, dates):
        """Fetch racecards for all dates"""
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(self.username, self.password)
        
        total = len(dates)
        start_time = time.time()
        
        for i, date in enumerate(dates, 1):
            try:
                # Fetch data
                url = f"{self.api_base}/v1/racecards/pro"
                params = {'date': date}
                
                print(f"Fetching {date}...")
                response = self.session.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"  Processing {len(data.get('races', []))} races for {date}...")
                    races_count, runners_count = self.process_and_save_racecards(data, date)
                    
                    self.stats['races_fetched'] += races_count
                    self.stats['runners_processed'] += runners_count
                    print(f"  ✓ Saved {races_count} races, {runners_count} runners")
                    
                    # Progress update every 10 dates
                    if i % 10 == 0:
                        elapsed = time.time() - start_time
                        rate = i / elapsed if elapsed > 0 else 0
                        remaining = (total - i) / rate if rate > 0 else 0
                        
                        self.progress_update.emit(
                            f"  {i}/{total} dates ({i*100/total:.1f}%) - "
                            f"{self.stats['races_fetched']} races, "
                            f"{self.stats['runners_processed']} runners - "
                            f"ETA: {remaining/3600:.1f}h"
                        )
                
                self.item_processed.emit(i)
                
                # Rate limiting
                time.sleep(self.rate_limit)
                
            except Exception as e:
                import traceback
                error_detail = f"  ⚠️  Error fetching {date}: {e}\n{traceback.format_exc()}"
                print(error_detail)
                self.progress_update.emit(f"  ⚠️  Error fetching {date}: {e}")
                continue
        
        print(f"\n✓ Racecards complete: {self.stats['races_fetched']} races, {self.stats['runners_processed']} runners\n")
        self.progress_update.emit(f"✓ Racecards complete: {self.stats['races_fetched']} races, {self.stats['runners_processed']} runners")
        self.progress_update.emit("")
    
    def process_and_save_racecards(self, data: dict, date: str):
        """Process and save racecard data with odds aggregation"""
        if not data or 'races' not in data:
            return 0, 0
        
        cursor = self.conn.cursor()
        races_count = 0
        runners_count = 0
        
        try:
            for race_data in data['races']:
                # Save race
                race_id = self.save_race(cursor, race_data, date)
                if not race_id:
                    continue
                
                races_count += 1
                
                # Save runners with odds aggregation
                runners = race_data.get('runners', [])
                for runner in runners:
                    runner_id = self.save_runner(cursor, race_id, runner)
                    if runner_id:
                        runners_count += 1
                        
                        # Save and aggregate odds (KEY PART!)
                        if 'odds' in runner and runner['odds']:
                            self.save_runner_odds(cursor, runner_id, runner['odds'])
                            self.stats['odds_aggregated'] += 1
            
            # Update favorite rankings per race
            for race_data in data['races']:
                race_id = race_data.get('race_id')
                if race_id:
                    self.update_favorite_status(cursor, race_id)
            
            self.conn.commit()
            return races_count, runners_count
            
        except Exception as e:
            self.conn.rollback()
            raise e
    
    def save_race(self, cursor, race_data: dict, date: str):
        """Save race to database"""
        race_id = race_data.get('race_id')
        if not race_id:
            return None
        
        # Set is_abandoned to 0 by default if not specified
        is_abandoned = 1 if race_data.get('is_abandoned') else 0
        
        cursor.execute('''
            INSERT OR REPLACE INTO races (
                race_id, course, date, time, distance_f, going, surface,
                type, race_class, prize, age_band, pattern, region, is_abandoned
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            race_id,
            race_data.get('course'),
            date,
            race_data.get('time'),
            race_data.get('distance_f'),
            race_data.get('going'),
            race_data.get('surface'),
            race_data.get('type'),
            race_data.get('race_class'),
            race_data.get('prize'),
            race_data.get('age_band'),
            race_data.get('pattern'),
            race_data.get('region'),
            is_abandoned
        ))
        
        return race_id
    
    def save_runner(self, cursor, race_id: str, runner: dict):
        """Save runner to database"""
        # Extract IDs
        horse_id = runner.get('horse_id') or runner.get('horse', {}).get('id')
        trainer_id = runner.get('trainer_id') or runner.get('trainer', {}).get('id')
        jockey_id = runner.get('jockey_id') or runner.get('jockey', {}).get('id')
        
        if not horse_id:
            return None
        
        # Save entities first
        if horse_id:
            self.save_horse(cursor, runner.get('horse', {}), horse_id)
        if trainer_id:
            self.save_trainer(cursor, runner.get('trainer', {}), trainer_id)
        if jockey_id:
            self.save_jockey(cursor, runner.get('jockey', {}), jockey_id)
        
        # Save runner
        cursor.execute('''
            INSERT INTO runners (
                race_id, horse_id, trainer_id, jockey_id,
                number, draw, lbs, ofr, rpr, ts, form, last_run,
                headgear, comment, silk_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            race_id, horse_id, trainer_id, jockey_id,
            runner.get('number'), runner.get('draw'), runner.get('lbs'),
            runner.get('ofr'), runner.get('rpr'), runner.get('ts'),
            runner.get('form'), runner.get('last_run'),
            runner.get('headgear'), runner.get('comment'), runner.get('silk_url')
        ))
        
        return cursor.lastrowid
    
    def save_horse(self, cursor, horse_data: dict, horse_id: str):
        """Save horse entity"""
        cursor.execute('''
            INSERT OR IGNORE INTO horses (horse_id, name, age, sex, region)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            horse_id,
            horse_data.get('name'),
            horse_data.get('age'),
            horse_data.get('sex'),
            horse_data.get('region')
        ))
    
    def save_trainer(self, cursor, trainer_data: dict, trainer_id: str):
        """Save trainer entity"""
        cursor.execute('''
            INSERT OR IGNORE INTO trainers (trainer_id, name, location)
            VALUES (?, ?, ?)
        ''', (
            trainer_id,
            trainer_data.get('name'),
            trainer_data.get('location')
        ))
    
    def save_jockey(self, cursor, jockey_data: dict, jockey_id: str):
        """Save jockey entity"""
        cursor.execute('''
            INSERT OR IGNORE INTO jockeys (jockey_id, name)
            VALUES (?, ?)
        ''', (jockey_id, jockey_data.get('name'))
        )
    
    def save_runner_odds(self, cursor, runner_id: int, odds_data: list):
        """
        Save individual odds and compute market aggregates
        CRITICAL: This is the same logic as upcoming_fetcher.py
        """
        if not odds_data:
            return
        
        decimal_odds = []
        
        for odds in odds_data:
            if not odds:
                continue
            
            # Handle different formats
            if isinstance(odds, dict):
                bookmaker = odds.get('bookmaker', 'Unknown')
                price = odds.get('price')
                
                # Convert fractional to decimal
                if price and '/' in str(price):
                    try:
                        parts = str(price).split('/')
                        if len(parts) == 2:
                            num, den = map(float, parts)
                            if den > 0:  # Avoid division by zero
                                decimal = (num / den) + 1.0
                                if decimal > 0:  # Ensure valid decimal odds
                                    decimal_odds.append(decimal)
                                    
                                    cursor.execute('''
                                        INSERT INTO runner_odds (
                                            runner_id, bookmaker, fractional, decimal
                                        ) VALUES (?, ?, ?, ?)
                                    ''', (runner_id, bookmaker, price, decimal))
                    except Exception as e:
                        # Log but don't crash
                        print(f"Warning: Failed to parse odds {price} for runner {runner_id}: {e}")
                        continue
        
        # Filter out any None values that might have slipped through
        decimal_odds = [x for x in decimal_odds if x is not None and x > 0]
        
        # Compute market aggregates (need at least 2 bookmakers)
        if decimal_odds and len(decimal_odds) >= 2:
            try:
                avg = statistics.mean(decimal_odds)
                cursor.execute('''
                    INSERT INTO runner_market_odds (
                        runner_id, avg_decimal, median_decimal,
                        min_decimal, max_decimal, bookmaker_count,
                        implied_probability, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    runner_id,
                    avg,
                    statistics.median(decimal_odds),
                    min(decimal_odds),
                    max(decimal_odds),
                    len(decimal_odds),
                    1.0 / avg if avg > 0 else 0
                ))
            except Exception as e:
                print(f"Warning: Failed to save market odds for runner {runner_id}: {e}")
                print(f"  Decimal odds: {decimal_odds}")
    
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
    
    def get_completed_races(self):
        """Get race IDs that are in the past and need results"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT race_id FROM races
            WHERE date < date('now')
            AND (is_abandoned = 0 OR is_abandoned IS NULL)
            ORDER BY date
        """)
        return [row['race_id'] for row in cursor.fetchall()]
    
    def fetch_all_results(self, race_ids):
        """Fetch results for all completed races"""
        total = len(race_ids)
        start_time = time.time()
        
        for i, race_id in enumerate(race_ids, 1):
            try:
                url = f"{self.api_base}/v1/results/{race_id}"
                response = self.session.get(url, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    self.save_results(data, race_id)
                    self.stats['results_fetched'] += 1
                elif response.status_code == 404:
                    # Results not available yet
                    pass
                
                # Progress update every 50 races
                if i % 50 == 0:
                    elapsed = time.time() - start_time
                    rate = i / elapsed if elapsed > 0 else 0
                    remaining = (total - i) / rate if rate > 0 else 0
                    
                    self.progress_update.emit(
                        f"  {i}/{total} races ({i*100/total:.1f}%) - "
                        f"{self.stats['results_fetched']} results - "
                        f"ETA: {remaining/60:.1f}m"
                    )
                
                self.item_processed.emit(i)
                
                # Rate limiting
                time.sleep(self.rate_limit)
                
            except Exception as e:
                continue
        
        self.progress_update.emit(f"✓ Results complete: {self.stats['results_fetched']} races")
        self.progress_update.emit("")
    
    def save_results(self, data: dict, race_id: str):
        """Save results to database"""
        if not data or 'results' not in data:
            return
        
        cursor = self.conn.cursor()
        
        try:
            for result in data['results']:
                horse_id = result.get('horse_id')
                if not horse_id:
                    continue
                
                cursor.execute('''
                    INSERT OR REPLACE INTO results (
                        race_id, horse_id, position, position_int,
                        distance, distance_full, time_seconds,
                        rpr, ts, comment
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    race_id, horse_id,
                    result.get('position'),
                    result.get('position_int'),
                    result.get('distance'),
                    result.get('distance_full'),
                    result.get('time_seconds'),
                    result.get('rpr'),
                    result.get('ts'),
                    result.get('comment')
                ))
            
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e
    
    def verify_odds_coverage(self):
        """Verify that odds were properly aggregated"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_runners,
                COUNT(CASE WHEN mo.runner_id IS NOT NULL THEN 1 END) as with_odds,
                CASE 
                    WHEN COUNT(*) > 0 THEN ROUND(100.0 * COUNT(CASE WHEN mo.runner_id IS NOT NULL THEN 1 END) / COUNT(*), 2)
                    ELSE 0
                END as pct
            FROM runners r
            LEFT JOIN runner_market_odds mo ON r.runner_id = mo.runner_id
        """)
        
        result = cursor.fetchone()
        total = result['total_runners']
        with_odds = result['with_odds']
        pct = result['pct'] or 0  # Handle None
        
        print(f"Odds coverage: {with_odds:,}/{total:,} ({pct}%)")
        self.progress_update.emit(f"✓ Odds coverage: {with_odds:,}/{total:,} ({pct}%)")
        
        if total == 0:
            print("⚠️  WARNING: No runners found in database!")
            self.progress_update.emit(f"⚠️  WARNING: No runners found! The API may not have data for the selected date range.")
        elif pct < 50:
            print(f"⚠️  WARNING: Low odds coverage: {pct}%. Expected 80%+")
            self.progress_update.emit(f"⚠️  WARNING: Low odds coverage: {pct}%. Expected 80%+")
        
        self.progress_update.emit("")
    
    def regenerate_features(self):
        """Regenerate ML features using optimized parallel processor"""
        self.progress_update.emit("Starting optimized feature generation...")
        
        try:
            from ml.feature_engineer_optimized import generate_features_optimized
            
            result = generate_features_optimized(db_path=str(self.db_path))
            
            if result:
                self.stats['features_generated'] = result.get('runners_processed', 0)
                self.progress_update.emit(f"✓ Features generated: {self.stats['features_generated']:,} runners")
            
        except Exception as e:
            self.progress_update.emit(f"⚠️  Feature generation error: {e}")
            self.progress_update.emit("  You can regenerate features manually later")
        
        self.progress_update.emit("")
    
    def get_final_stats(self):
        """Get final statistics"""
        cursor = self.conn.cursor()
        
        # Count everything
        cursor.execute("SELECT COUNT(*) FROM races")
        total_races = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM runners")
        total_runners = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM results")
        total_results = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM runner_market_odds")
        total_odds = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ml_features")
        total_features = cursor.fetchone()[0] if cursor.fetchone() else 0
        
        return {
            'races': total_races,
            'runners': total_runners,
            'results': total_results,
            'odds': total_odds,
            'features': total_features,
            'backup_path': str(self.backup_path) if self.backup_path else None
        }

