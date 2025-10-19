#!/usr/bin/env python3
"""
Compute Career Statistics for Horses, Trainers, and Jockeys
Aggregates historical results data into statistics tables for fast lookup
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StatsComputer:
    """Compute and store career statistics for all entities"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None
        
    def connect(self):
        """Connect to database"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        
    def close(self):
        """Close connection"""
        if self.conn:
            self.conn.close()
    
    def compute_horse_career_stats(self):
        """Compute career statistics for all horses"""
        logger.info("Computing horse career statistics...")
        cursor = self.conn.cursor()
        
        # Get all horses that have results
        cursor.execute("""
            SELECT DISTINCT horse_id 
            FROM results
            WHERE position_int IS NOT NULL
        """)
        horse_ids = [row['horse_id'] for row in cursor.fetchall()]
        
        logger.info(f"Processing {len(horse_ids)} horses...")
        
        for i, horse_id in enumerate(horse_ids, 1):
            if i % 1000 == 0:
                logger.info(f"  Processed {i}/{len(horse_ids)} horses...")
            
            stats = self._compute_horse_stats(horse_id)
            self._save_horse_stats(horse_id, stats)
        
        self.conn.commit()
        logger.info(f"✓ Computed stats for {len(horse_ids)} horses")
    
    def _compute_horse_stats(self, horse_id: str) -> Dict:
        """Compute all statistics for a single horse"""
        cursor = self.conn.cursor()
        
        # Get all results for this horse (ordered by date DESC)
        cursor.execute("""
            SELECT 
                res.position_int,
                res.sp_dec,
                res.prize,
                rac.course,
                rac.distance_f,
                rac.going,
                rac.date
            FROM results res
            JOIN races rac ON res.race_id = rac.race_id
            WHERE res.horse_id = ?
            AND res.position_int < 900
            ORDER BY rac.date DESC
        """, (horse_id,))
        
        results = cursor.fetchall()
        
        if not results:
            return self._empty_horse_stats()
        
        # Basic counts
        total_runs = len(results)
        wins = sum(1 for r in results if r['position_int'] == 1)
        places = sum(1 for r in results if r['position_int'] <= 3)
        
        # Rates
        win_rate = wins / total_runs if total_runs > 0 else 0.0
        place_rate = places / total_runs if total_runs > 0 else 0.0
        
        # Positions
        positions = [r['position_int'] for r in results]
        avg_position = sum(positions) / len(positions) if positions else None
        median_position = sorted(positions)[len(positions)//2] if positions else None
        best_position = min(positions) if positions else None
        
        # Earnings (sum of prize money, handle currency symbols)
        earnings = 0.0
        for r in results:
            if r['prize']:
                try:
                    # Remove currency symbols and commas
                    prize_str = str(r['prize']).replace('£', '').replace('€', '').replace(',', '').strip()
                    earnings += float(prize_str)
                except (ValueError, AttributeError):
                    pass  # Skip if can't parse
        
        # Average SP
        sp_values = [float(r['sp_dec']) for r in results if r['sp_dec']]
        avg_sp = sum(sp_values) / len(sp_values) if sp_values else None
        
        # Course wins (JSON dict)
        courses_won = {}
        for r in results:
            if r['position_int'] == 1 and r['course']:
                courses_won[r['course']] = courses_won.get(r['course'], 0) + 1
        
        # Distance performance (JSON dict with win rates by distance band)
        distance_perf = self._compute_distance_performance(results)
        
        # Going preference (JSON dict with win rates by going)
        going_perf = self._compute_going_performance(results)
        
        return {
            'total_runs': total_runs,
            'wins': wins,
            'places': places,
            'win_rate': win_rate,
            'place_rate': place_rate,
            'avg_position': avg_position,
            'median_position': median_position,
            'best_position': best_position,
            'total_earnings': earnings,
            'avg_sp_dec': avg_sp,
            'best_rating': None,  # TODO: extract from OFR/RPR
            'courses_won': json.dumps(courses_won),
            'distance_performance': json.dumps(distance_perf),
            'going_preference': json.dumps(going_perf)
        }
    
    def _empty_horse_stats(self) -> Dict:
        """Return empty stats dict"""
        return {
            'total_runs': 0,
            'wins': 0,
            'places': 0,
            'win_rate': 0.0,
            'place_rate': 0.0,
            'avg_position': None,
            'median_position': None,
            'best_position': None,
            'total_earnings': 0.0,
            'avg_sp_dec': None,
            'best_rating': None,
            'courses_won': '{}',
            'distance_performance': '{}',
            'going_preference': '{}'
        }
    
    def _compute_distance_performance(self, results: List) -> Dict:
        """Compute win rates by distance bands"""
        distance_bands = {
            '5-6f': (5, 6),
            '7-8f': (7, 8),
            '9-10f': (9, 10),
            '11-12f': (11, 12),
            '13-16f': (13, 16),
            '17f+': (17, 999)
        }
        
        perf = {}
        for band_name, (min_f, max_f) in distance_bands.items():
            band_results = [r for r in results 
                           if r['distance_f'] and min_f <= float(r['distance_f']) <= max_f]
            if band_results:
                wins = sum(1 for r in band_results if r['position_int'] == 1)
                perf[band_name] = {
                    'runs': len(band_results),
                    'wins': wins,
                    'win_rate': wins / len(band_results)
                }
        
        return perf
    
    def _compute_going_performance(self, results: List) -> Dict:
        """Compute win rates by going"""
        going_types = {}
        
        for r in results:
            if not r['going']:
                continue
            
            going = r['going'].lower()
            if going not in going_types:
                going_types[going] = {'runs': 0, 'wins': 0}
            
            going_types[going]['runs'] += 1
            if r['position_int'] == 1:
                going_types[going]['wins'] += 1
        
        # Calculate win rates
        for going in going_types:
            runs = going_types[going]['runs']
            wins = going_types[going]['wins']
            going_types[going]['win_rate'] = wins / runs if runs > 0 else 0.0
        
        return going_types
    
    def _save_horse_stats(self, horse_id: str, stats: Dict):
        """Save horse statistics to database"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO horse_career_stats (
                horse_id, total_runs, wins, places, win_rate, place_rate,
                avg_position, median_position, best_position, total_earnings,
                avg_sp_dec, best_rating, courses_won, distance_performance,
                going_preference, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            horse_id,
            stats['total_runs'],
            stats['wins'],
            stats['places'],
            stats['win_rate'],
            stats['place_rate'],
            stats['avg_position'],
            stats['median_position'],
            stats['best_position'],
            stats['total_earnings'],
            stats['avg_sp_dec'],
            stats['best_rating'],
            stats['courses_won'],
            stats['distance_performance'],
            stats['going_preference']
        ))
    
    def compute_trainer_stats(self):
        """Compute rolling statistics for trainers"""
        logger.info("Computing trainer statistics...")
        cursor = self.conn.cursor()
        
        # Get all trainers
        cursor.execute("SELECT DISTINCT trainer_id FROM results WHERE trainer_id IS NOT NULL")
        trainer_ids = [row['trainer_id'] for row in cursor.fetchall()]
        
        logger.info(f"Processing {len(trainer_ids)} trainers...")
        
        periods = ['14d', '30d', '90d', '365d', 'career']
        
        for i, trainer_id in enumerate(trainer_ids, 1):
            if i % 500 == 0:
                logger.info(f"  Processed {i}/{len(trainer_ids)} trainers...")
            
            for period in periods:
                stats = self._compute_trainer_stats_for_period(trainer_id, period)
                self._save_trainer_stats(trainer_id, period, stats)
        
        self.conn.commit()
        logger.info(f"✓ Computed stats for {len(trainer_ids)} trainers")
    
    def _compute_trainer_stats_for_period(self, trainer_id: str, period: str) -> Dict:
        """Compute trainer stats for a specific period"""
        cursor = self.conn.cursor()
        
        # Determine date range
        if period == 'career':
            date_filter = ""
        else:
            days = int(period.replace('d', ''))
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            date_filter = f"AND rac.date >= '{cutoff_date}'"
        
        # Get results for this trainer in period
        cursor.execute(f"""
            SELECT 
                res.position_int,
                res.sp_dec,
                rac.course,
                rac.distance_f,
                rac.going,
                rac.date
            FROM results res
            JOIN races rac ON res.race_id = rac.race_id
            WHERE res.trainer_id = ?
            AND res.position_int < 900
            {date_filter}
            ORDER BY rac.date DESC
        """, (trainer_id,))
        
        results = cursor.fetchall()
        
        if not results:
            return self._empty_trainer_stats(period)
        
        return self._compute_entity_stats(results, period)
    
    def _compute_jockey_stats_for_period(self, jockey_id: str, period: str) -> Dict:
        """Compute jockey stats for a specific period"""
        cursor = self.conn.cursor()
        
        # Determine date range
        if period == 'career':
            date_filter = ""
        else:
            days = int(period.replace('d', ''))
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            date_filter = f"AND rac.date >= '{cutoff_date}'"
        
        cursor.execute(f"""
            SELECT 
                res.position_int,
                res.sp_dec,
                rac.course,
                rac.distance_f,
                rac.going,
                rac.date
            FROM results res
            JOIN races rac ON res.race_id = rac.race_id
            WHERE res.jockey_id = ?
            AND res.position_int < 900
            {date_filter}
            ORDER BY rac.date DESC
        """, (jockey_id,))
        
        results = cursor.fetchall()
        
        if not results:
            return self._empty_trainer_stats(period)  # Same structure
        
        return self._compute_entity_stats(results, period)
    
    def _compute_entity_stats(self, results: List, period: str) -> Dict:
        """Generic stats computation for trainer/jockey"""
        runs = len(results)
        wins = sum(1 for r in results if r['position_int'] == 1)
        places = sum(1 for r in results if r['position_int'] <= 3)
        
        win_rate = wins / runs if runs > 0 else 0.0
        place_rate = places / runs if runs > 0 else 0.0
        strike_rate = win_rate  # Same as win_rate
        
        # ROI calculation (assuming £1 stakes at SP)
        roi = 0.0
        for r in results:
            if r['sp_dec']:
                sp = float(r['sp_dec'])
                if r['position_int'] == 1:
                    roi += sp - 1  # Profit
                else:
                    roi -= 1  # Loss
        roi = (roi / runs) if runs > 0 else 0.0
        
        # A/E ratio (actual wins / expected wins from SP)
        expected_wins = sum(1/float(r['sp_dec']) for r in results if r['sp_dec'] and float(r['sp_dec']) > 0)
        ae_ratio = wins / expected_wins if expected_wins > 0 else 0.0
        
        # Specializations
        course_spec = self._compute_course_specialization(results)
        distance_spec = self._compute_distance_performance(results)
        going_spec = self._compute_going_performance(results)
        
        # Date range
        dates = [r['date'] for r in results if r['date']]
        start_date = min(dates) if dates else None
        end_date = max(dates) if dates else None
        
        return {
            'period': period,
            'start_date': start_date,
            'end_date': end_date,
            'runs': runs,
            'wins': wins,
            'places': places,
            'win_rate': win_rate,
            'place_rate': place_rate,
            'strike_rate': strike_rate,
            'roi': roi,
            'ae_ratio': ae_ratio,
            'course_specialization': json.dumps(course_spec),
            'distance_specialization': json.dumps(distance_spec),
            'going_specialization': json.dumps(going_spec)
        }
    
    def _empty_trainer_stats(self, period: str) -> Dict:
        """Empty stats for period"""
        return {
            'period': period,
            'start_date': None,
            'end_date': None,
            'runs': 0,
            'wins': 0,
            'places': 0,
            'win_rate': 0.0,
            'place_rate': 0.0,
            'strike_rate': 0.0,
            'roi': 0.0,
            'ae_ratio': 0.0,
            'course_specialization': '{}',
            'distance_specialization': '{}',
            'going_specialization': '{}'
        }
    
    def _compute_course_specialization(self, results: List) -> Dict:
        """Compute win rates by course"""
        courses = {}
        for r in results:
            if not r['course']:
                continue
            course = r['course']
            if course not in courses:
                courses[course] = {'runs': 0, 'wins': 0}
            courses[course]['runs'] += 1
            if r['position_int'] == 1:
                courses[course]['wins'] += 1
        
        # Calculate win rates
        for course in courses:
            runs = courses[course]['runs']
            wins = courses[course]['wins']
            courses[course]['win_rate'] = wins / runs if runs > 0 else 0.0
        
        return courses
    
    def _save_trainer_stats(self, trainer_id: str, period: str, stats: Dict):
        """Save trainer stats to database"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO trainer_stats (
                trainer_id, period, start_date, end_date, runs, wins, places,
                win_rate, place_rate, strike_rate, roi, ae_ratio,
                course_specialization, distance_specialization, going_specialization,
                last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            trainer_id,
            stats['period'],
            stats['start_date'],
            stats['end_date'],
            stats['runs'],
            stats['wins'],
            stats['places'],
            stats['win_rate'],
            stats['place_rate'],
            stats['strike_rate'],
            stats['roi'],
            stats['ae_ratio'],
            stats['course_specialization'],
            stats['distance_specialization'],
            stats['going_specialization']
        ))
    
    def compute_jockey_stats(self):
        """Compute rolling statistics for jockeys"""
        logger.info("Computing jockey statistics...")
        cursor = self.conn.cursor()
        
        # Get all jockeys
        cursor.execute("SELECT DISTINCT jockey_id FROM results WHERE jockey_id IS NOT NULL")
        jockey_ids = [row['jockey_id'] for row in cursor.fetchall()]
        
        logger.info(f"Processing {len(jockey_ids)} jockeys...")
        
        periods = ['14d', '30d', '90d', '365d', 'career']
        
        for i, jockey_id in enumerate(jockey_ids, 1):
            if i % 500 == 0:
                logger.info(f"  Processed {i}/{len(jockey_ids)} jockeys...")
            
            for period in periods:
                stats = self._compute_jockey_stats_for_period(jockey_id, period)
                self._save_jockey_stats(jockey_id, period, stats)
        
        self.conn.commit()
        logger.info(f"✓ Computed stats for {len(jockey_ids)} jockeys")
    
    def _save_jockey_stats(self, jockey_id: str, period: str, stats: Dict):
        """Save jockey stats to database"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO jockey_stats (
                jockey_id, period, start_date, end_date, runs, wins, places,
                win_rate, place_rate, strike_rate, roi, ae_ratio,
                course_specialization, distance_specialization, going_specialization,
                last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            jockey_id,
            stats['period'],
            stats['start_date'],
            stats['end_date'],
            stats['runs'],
            stats['wins'],
            stats['places'],
            stats['win_rate'],
            stats['place_rate'],
            stats['strike_rate'],
            stats['roi'],
            stats['ae_ratio'],
            stats['course_specialization'],
            stats['distance_specialization'],
            stats['going_specialization']
        ))
    
    def compute_trainer_jockey_combos(self):
        """Compute statistics for trainer-jockey partnerships"""
        logger.info("Computing trainer-jockey combo statistics...")
        cursor = self.conn.cursor()
        
        # Get all unique combinations
        cursor.execute("""
            SELECT DISTINCT trainer_id, jockey_id
            FROM results
            WHERE trainer_id IS NOT NULL AND jockey_id IS NOT NULL
        """)
        combos = cursor.fetchall()
        
        logger.info(f"Processing {len(combos)} trainer-jockey combinations...")
        
        periods = ['90d', '365d', 'career']
        
        for i, combo in enumerate(combos, 1):
            if i % 1000 == 0:
                logger.info(f"  Processed {i}/{len(combos)} combos...")
            
            trainer_id = combo['trainer_id']
            jockey_id = combo['jockey_id']
            
            for period in periods:
                stats = self._compute_combo_stats(trainer_id, jockey_id, period)
                if stats['runs'] >= 5:  # Only save if they've had at least 5 runs together
                    self._save_combo_stats(trainer_id, jockey_id, period, stats)
        
        self.conn.commit()
        logger.info(f"✓ Computed combo stats")
    
    def _compute_combo_stats(self, trainer_id: str, jockey_id: str, period: str) -> Dict:
        """Compute stats for a trainer-jockey combo"""
        cursor = self.conn.cursor()
        
        # Determine date range
        if period == 'career':
            date_filter = ""
        else:
            days = int(period.replace('d', ''))
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            date_filter = f"AND rac.date >= '{cutoff_date}'"
        
        cursor.execute(f"""
            SELECT 
                res.position_int,
                res.sp_dec
            FROM results res
            JOIN races rac ON res.race_id = rac.race_id
            WHERE res.trainer_id = ? AND res.jockey_id = ?
            AND res.position_int < 900
            {date_filter}
        """, (trainer_id, jockey_id))
        
        results = cursor.fetchall()
        
        runs = len(results)
        if runs == 0:
            return {'runs': 0, 'wins': 0, 'places': 0, 'win_rate': 0.0, 'strike_rate': 0.0, 'roi': 0.0}
        
        wins = sum(1 for r in results if r['position_int'] == 1)
        places = sum(1 for r in results if r['position_int'] <= 3)
        win_rate = wins / runs
        
        # ROI
        roi = 0.0
        for r in results:
            if r['sp_dec']:
                sp = float(r['sp_dec'])
                if r['position_int'] == 1:
                    roi += sp - 1
                else:
                    roi -= 1
        roi = roi / runs
        
        return {
            'runs': runs,
            'wins': wins,
            'places': places,
            'win_rate': win_rate,
            'strike_rate': win_rate,
            'roi': roi
        }
    
    def _save_combo_stats(self, trainer_id: str, jockey_id: str, period: str, stats: Dict):
        """Save combo stats"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO trainer_jockey_combos (
                trainer_id, jockey_id, period, runs, wins, places,
                win_rate, strike_rate, roi, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            trainer_id,
            jockey_id,
            period,
            stats['runs'],
            stats['wins'],
            stats['places'],
            stats['win_rate'],
            stats['strike_rate'],
            stats['roi']
        ))
    
    def compute_all_stats(self):
        """Compute all statistics"""
        logger.info("="*60)
        logger.info("COMPUTING ALL STATISTICS")
        logger.info("="*60)
        
        self.connect()
        
        try:
            # 1. Horse career stats
            self.compute_horse_career_stats()
            
            # 2. Trainer stats (multiple periods)
            self.compute_trainer_stats()
            
            # 3. Jockey stats (multiple periods)
            self.compute_jockey_stats()
            
            # 4. Trainer-Jockey combos
            self.compute_trainer_jockey_combos()
            
            logger.info("="*60)
            logger.info("✓ ALL STATISTICS COMPUTED")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"Error computing stats: {e}", exc_info=True)
            self.conn.rollback()
            raise
        finally:
            self.close()


def main():
    """Main execution"""
    db_path = Path(__file__).parent.parent / "racing_pro.db"
    
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        return
    
    computer = StatsComputer(db_path)
    computer.compute_all_stats()


if __name__ == "__main__":
    main()

