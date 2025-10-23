#!/usr/bin/env python3
"""
Enrich existing database with SP odds from results endpoint
"""

import sqlite3
import requests
from requests.auth import HTTPBasicAuth
import time
from pathlib import Path


class OddsEnricher:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Load credentials
        cred_file = Path(__file__).parent / "reqd_files" / "cred.txt"
        with open(cred_file, "r") as f:
            self.username = f.readline().strip()
            self.password = f.readline().strip()
        
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(self.username, self.password)
        self.api_base = "https://api.theracingapi.com"
        
    def get_races_without_odds(self):
        """Get races that don't have aggregated odds yet"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT r.race_id, r.date
            FROM races r
            JOIN runners run ON r.race_id = run.race_id
            LEFT JOIN runner_market_odds mo ON run.runner_id = mo.runner_id
            WHERE r.date < date('now')
            AND mo.market_odds_id IS NULL
            ORDER BY r.date DESC
        """)
        return cursor.fetchall()
    
    def fetch_and_enrich_race(self, race_id: str):
        """Fetch results and enrich with SP odds"""
        url = f"{self.api_base}/v1/results/{race_id}"
        
        try:
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'runners' in data and data['runners']:
                    self.process_results(race_id, data['runners'])
                    return len(data['runners'])
            
            return 0
            
        except Exception as e:
            print(f"Error fetching {race_id}: {e}")
            return 0
    
    def process_results(self, race_id: str, results: list):
        """Process results and add SP odds to runner_market_odds"""
        cursor = self.conn.cursor()
        
        # Map horse_id to runner_id
        cursor.execute("""
            SELECT runner_id, horse_id
            FROM runners
            WHERE race_id = ?
        """, (race_id,))
        
        runner_map = {row['horse_id']: row['runner_id'] for row in cursor.fetchall()}
        
        # Process each result
        for result in results:
            horse_id = result.get('horse_id')
            sp_dec = result.get('sp_dec')
            sp_frac = result.get('sp')
            
            if horse_id in runner_map and sp_dec:
                runner_id = runner_map[horse_id]
                
                try:
                    decimal_odds = float(sp_dec)
                    
                    # Insert into runner_market_odds
                    cursor.execute('''
                        INSERT OR IGNORE INTO runner_market_odds (
                            runner_id, avg_decimal, median_decimal,
                            min_decimal, max_decimal, bookmaker_count,
                            implied_probability, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (
                        runner_id,
                        decimal_odds,  # avg = SP
                        decimal_odds,  # median = SP
                        decimal_odds,  # min = SP
                        decimal_odds,  # max = SP
                        1,  # bookmaker_count = 1 (SP is consensus)
                        1.0 / decimal_odds if decimal_odds > 0 else 0
                    ))
                    
                    # Also save to runner_odds for completeness
                    cursor.execute('''
                        INSERT OR IGNORE INTO runner_odds (
                            runner_id, bookmaker, fractional, decimal
                        ) VALUES (?, ?, ?, ?)
                    ''', (runner_id, 'Starting Price', sp_frac, decimal_odds))
                    
                except (ValueError, TypeError) as e:
                    print(f"  Warning: Invalid SP for runner {runner_id}: {sp_dec}")
        
        self.conn.commit()
    
    def run(self):
        """Main enrichment process"""
        print("="*60)
        print("ODDS ENRICHMENT FROM RESULTS ENDPOINT")
        print("="*60)
        
        races = self.get_races_without_odds()
        total = len(races)
        
        print(f"\nFound {total:,} races needing odds enrichment")
        print(f"Estimated time: {(total * 0.55) / 3600:.1f} hours\n")
        
        enriched = 0
        runners_processed = 0
        
        for i, (race_id, date) in enumerate(races, 1):
            count = self.fetch_and_enrich_race(race_id)
            
            if count > 0:
                enriched += 1
                runners_processed += count
            
            # Progress every 50 races
            if i % 50 == 0:
                pct = (i / total) * 100
                print(f"  {i:,}/{total:,} ({pct:.1f}%) - {enriched:,} enriched, {runners_processed:,} runners")
            
            # Rate limiting
            time.sleep(0.55)
        
        print(f"\n✓ Complete!")
        print(f"  Races enriched: {enriched:,}")
        print(f"  Runners processed: {runners_processed:,}")
        
        # Check final coverage
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN mo.runner_id IS NOT NULL THEN 1 END) as with_odds,
                ROUND(100.0 * COUNT(CASE WHEN mo.runner_id IS NOT NULL THEN 1 END) / COUNT(*), 2) as pct
            FROM runners r
            LEFT JOIN runner_market_odds mo ON r.runner_id = mo.runner_id
        """)
        
        result = cursor.fetchone()
        print(f"\n📊 Final Odds Coverage:")
        print(f"  {result['with_odds']:,}/{result['total']:,} ({result['pct']}%)")
        
        self.conn.close()


if __name__ == "__main__":
    enricher = OddsEnricher("racing_pro.db")
    enricher.run()


