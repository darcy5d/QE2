#!/usr/bin/env python3
"""
Feature Engineering Pipeline
Combines all data sources to generate ML-ready features for each runner in each race
"""

import sqlite3
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

from .form_parser import FormParser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FeatureEngineer:
    """Generate ML features for race runners"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None
        self.form_parser = FormParser()
        
    def connect(self):
        """Connect to database"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        
    def close(self):
        """Close connection"""
        if self.conn:
            self.conn.close()
    
    def get_races_with_results(self, limit: Optional[int] = None) -> List[str]:
        """Get race_ids that have results data"""
        cursor = self.conn.cursor()
        
        query = """
            SELECT DISTINCT r.race_id, r.date
            FROM races r
            JOIN results res ON r.race_id = res.race_id
            WHERE r.is_abandoned = 0
            ORDER BY r.date
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        return [row['race_id'] for row in cursor.fetchall()]
    
    def get_race_context_features(self, race_id: str) -> Dict:
        """Get race-level context features"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                course, course_id, distance_f, going, surface,
                type as race_type, race_class,
                prize, age_band, pattern, date, region
            FROM races
            WHERE race_id = ?
        """, (race_id,))
        
        race = cursor.fetchone()
        if not race:
            return {}
        
        # Encode categorical features
        going_map = {
            'heavy': 1, 'soft': 2, 'good to soft': 3, 'good': 4, 
            'good to firm': 5, 'firm': 6, 'hard': 7, 'standard': 4, 'slow': 3
        }
        
        surface_map = {'turf': 1, 'aw': 2, 'tapeta': 2, 'polytrack': 2, 'dirt': 3}
        
        race_type_map = {
            'flat': 1, 'chase': 2, 'hurdle': 3, 'nhf': 4, 'bumper': 4
        }
        
        going_str = str(race['going'] or 'good').lower()
        going_encoded = going_map.get(going_str, 4)
        
        surface_str = str(race['surface'] or 'turf').lower()
        surface_encoded = surface_map.get(surface_str, 1)
        
        race_type_str = str(race['race_type'] or 'flat').lower()
        race_type_encoded = race_type_map.get(race_type_str, 1)
        
        # Extract class number from race_class string (e.g., "Class 3" -> 3)
        race_class_num = None
        if race['race_class']:
            import re
            match = re.search(r'\d+', str(race['race_class']))
            if match:
                race_class_num = int(match.group())
        
        # Prize money
        prize_money = 0.0
        if race['prize']:
            try:
                # Remove currency symbols and commas
                prize_str = str(race['prize']).replace('£', '').replace(',', '').strip()
                prize_money = float(prize_str)
            except:
                pass
        
        # Safely convert distance_f to float
        distance_f_val = None
        if race['distance_f']:
            try:
                distance_f_val = float(race['distance_f'])
            except (ValueError, TypeError):
                pass
        
        return {
            'race_id': race_id,
            'course': race['course'],
            'course_id': race['course_id'],
            'distance_f': distance_f_val,
            'going': race['going'],
            'going_encoded': going_encoded,
            'surface': race['surface'],
            'surface_encoded': surface_encoded,
            'race_class': race['race_class'],
            'race_class_encoded': race_class_num,
            'race_type': race['race_type'],
            'race_type_encoded': race_type_encoded,
            'prize_money': prize_money,
            'date': race['date'],
            'region': race['region']
        }
    
    def get_runners_for_race(self, race_id: str) -> List[Dict]:
        """Get all runners for a race with their data"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                r.runner_id, r.horse_id, r.trainer_id, r.jockey_id,
                r.number, r.draw, h.age, r.lbs as weight_lbs_combined,
                r.ofr, r.rpr, r.ts, r.headgear, r.form,
                h.sex, h.sire_id, h.dam_id,
                t.name as trainer_name,
                j.name as jockey_name
            FROM runners r
            LEFT JOIN horses h ON r.horse_id = h.horse_id
            LEFT JOIN trainers t ON r.trainer_id = t.trainer_id
            LEFT JOIN jockeys j ON r.jockey_id = j.jockey_id
            WHERE r.race_id = ?
            ORDER BY r.number
        """, (race_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_runner_result(self, race_id: str, horse_id: str) -> Optional[Dict]:
        """Get result for a runner"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT position_int, ovr_btn, time, sp_dec, prize
            FROM results
            WHERE race_id = ? AND horse_id = ?
        """, (race_id, horse_id))
        
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_horse_career_stats(self, horse_id: str, race_date: str = None) -> Dict:
        """
        Get horse career statistics BEFORE given race date to prevent data leakage.
        If race_date is None, returns all-time stats (for non-ML purposes).
        """
        cursor = self.conn.cursor()
        
        # Add date filter to prevent data leakage
        date_filter = "AND rac.date < ?" if race_date else ""
        params = [horse_id]
        if race_date:
            params.append(race_date)
        
        cursor.execute(f"""
            SELECT 
                COUNT(*) as total_runs,
                SUM(CASE WHEN res.position_int = 1 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN res.position_int <= 3 THEN 1 ELSE 0 END) as places,
                AVG(CASE WHEN res.position_int < 900 THEN res.position_int ELSE NULL END) as avg_position
            FROM results res
            JOIN races rac ON res.race_id = rac.race_id
            WHERE res.horse_id = ?
            {date_filter}
            AND res.position_int < 900
        """, tuple(params))
        
        row = cursor.fetchone()
        if not row or not row['total_runs']:
            return {
                'total_runs': 0,
                'wins': 0,
                'places': 0,
                'win_rate': 0.0,
                'place_rate': 0.0,
                'avg_position': None
            }
        
        total_runs = row['total_runs'] or 0
        wins = row['wins'] or 0
        places = row['places'] or 0
        
        return {
            'total_runs': total_runs,
            'wins': wins,
            'places': places,
            'win_rate': wins / total_runs if total_runs > 0 else 0.0,
            'place_rate': places / total_runs if total_runs > 0 else 0.0,
            'avg_position': row['avg_position']
        }
    
    def get_trainer_stats(self, trainer_id: str, period: str = '90d') -> Dict:
        """Get trainer statistics for a period"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                runs, wins, places, win_rate, place_rate, strike_rate,
                roi, ae_ratio, course_specialization, distance_specialization
            FROM trainer_stats
            WHERE trainer_id = ? AND period = ?
        """, (trainer_id, period))
        
        row = cursor.fetchone()
        if not row:
            return {}
        
        return {
            'runs': row['runs'],
            'wins': row['wins'],
            'win_rate': row['win_rate'],
            'strike_rate': row['strike_rate'],
            'roi': row['roi'],
            'ae_ratio': row['ae_ratio'],
            'course_spec': json.loads(row['course_specialization'] or '{}'),
            'distance_spec': json.loads(row['distance_specialization'] or '{}')
        }
    
    def get_jockey_stats(self, jockey_id: str, period: str = '90d') -> Dict:
        """Get jockey statistics for a period"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                runs, wins, places, win_rate, place_rate, strike_rate,
                roi, ae_ratio, course_specialization, distance_specialization
            FROM jockey_stats
            WHERE jockey_id = ? AND period = ?
        """, (jockey_id, period))
        
        row = cursor.fetchone()
        if not row:
            return {}
        
        return {
            'runs': row['runs'],
            'wins': row['wins'],
            'win_rate': row['win_rate'],
            'strike_rate': row['strike_rate'],
            'roi': row['roi'],
            'ae_ratio': row['ae_ratio'],
            'course_spec': json.loads(row['course_specialization'] or '{}'),
            'distance_spec': json.loads(row['distance_specialization'] or '{}')
        }
    
    def get_trainer_jockey_combo_stats(self, trainer_id: str, jockey_id: str) -> Dict:
        """Get trainer-jockey partnership statistics"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT runs, wins, win_rate, strike_rate, roi
            FROM trainer_jockey_combos
            WHERE trainer_id = ? AND jockey_id = ? AND period = 'career'
        """, (trainer_id, jockey_id))
        
        row = cursor.fetchone()
        if not row:
            return {'runs': 0, 'wins': 0, 'win_rate': 0.0, 'strike_rate': 0.0, 'roi': 0.0}
        
        return dict(row)
    
    def get_days_since_last_run(self, horse_id: str, current_date: str) -> Optional[int]:
        """Calculate days since horse's last race"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT MAX(rac.date) as last_date
            FROM results res
            JOIN races rac ON res.race_id = rac.race_id
            WHERE res.horse_id = ? AND rac.date < ?
        """, (horse_id, current_date))
        
        row = cursor.fetchone()
        if not row or not row['last_date']:
            return None
        
        try:
            last_dt = datetime.strptime(row['last_date'], '%Y-%m-%d')
            current_dt = datetime.strptime(current_date, '%Y-%m-%d')
            return (current_dt - last_dt).days
        except:
            return None
    
    def compute_course_specific_stats(self, entity_id: str, course: str, 
                                     entity_type: str = 'horse', race_date: str = None) -> Dict:
        """Get win rate at specific course for horse/trainer/jockey BEFORE given race date"""
        cursor = self.conn.cursor()
        
        # Build query based on entity type
        if entity_type == 'horse':
            where_clause = "res.horse_id = ?"
        elif entity_type == 'trainer':
            where_clause = "res.trainer_id = ?"
        elif entity_type == 'jockey':
            where_clause = "res.jockey_id = ?"
        else:
            return {}
        
        # Add date filter to prevent data leakage
        date_filter = "AND rac.date < ?" if race_date else ""
        params = [entity_id, course]
        if race_date:
            params.append(race_date)
        
        cursor.execute(f"""
            SELECT 
                COUNT(*) as runs,
                SUM(CASE WHEN res.position_int = 1 THEN 1 ELSE 0 END) as wins
            FROM results res
            JOIN races rac ON res.race_id = rac.race_id
            WHERE {where_clause} AND rac.course = ?
            {date_filter}
            AND res.position_int < 900
        """, tuple(params))
        
        row = cursor.fetchone()
        runs = row['runs'] or 0
        wins = row['wins'] or 0
        
        return {
            'course_runs': runs,
            'course_wins': wins,
            'course_win_rate': wins / runs if runs > 0 else 0.0
        }
    
    def compute_distance_specific_stats(self, horse_id: str, distance_f: float, race_date: str = None) -> Dict:
        """Get horse performance at similar distances BEFORE given race date"""
        if not distance_f:
            return {'distance_runs': 0, 'distance_wins': 0, 'distance_win_rate': 0.0}
        
        # Ensure distance_f is a float (defensive check)
        try:
            distance_f = float(distance_f)
        except (ValueError, TypeError):
            return {'distance_runs': 0, 'distance_wins': 0, 'distance_win_rate': 0.0}
        
        cursor = self.conn.cursor()
        
        # Similar distance = within 2 furlongs
        min_dist = distance_f - 2
        max_dist = distance_f + 2
        
        # Add date filter to prevent data leakage
        date_filter = "AND rac.date < ?" if race_date else ""
        params = [horse_id, min_dist, max_dist]
        if race_date:
            params.append(race_date)
        
        cursor.execute(f"""
            SELECT 
                COUNT(*) as runs,
                SUM(CASE WHEN res.position_int = 1 THEN 1 ELSE 0 END) as wins
            FROM results res
            JOIN races rac ON res.race_id = rac.race_id
            WHERE res.horse_id = ? 
            AND rac.distance_f BETWEEN ? AND ?
            {date_filter}
            AND res.position_int < 900
        """, tuple(params))
        
        row = cursor.fetchone()
        runs = row['runs'] or 0
        wins = row['wins'] or 0
        
        return {
            'distance_runs': runs,
            'distance_wins': wins,
            'distance_win_rate': wins / runs if runs > 0 else 0.0
        }
    
    def compute_going_specific_stats(self, horse_id: str, going: str, race_date: str = None) -> Dict:
        """Get horse performance on similar going BEFORE given race date"""
        if not going:
            return {'going_runs': 0, 'going_wins': 0, 'going_win_rate': 0.0}
        
        cursor = self.conn.cursor()
        
        # Add date filter to prevent data leakage
        date_filter = "AND rac.date < ?" if race_date else ""
        params = [horse_id, going]
        if race_date:
            params.append(race_date)
        
        cursor.execute(f"""
            SELECT 
                COUNT(*) as runs,
                SUM(CASE WHEN res.position_int = 1 THEN 1 ELSE 0 END) as wins
            FROM results res
            JOIN races rac ON res.race_id = rac.race_id
            WHERE res.horse_id = ? 
            AND LOWER(rac.going) = LOWER(?)
            {date_filter}
            AND res.position_int < 900
        """, tuple(params))
        
        row = cursor.fetchone()
        runs = row['runs'] or 0
        wins = row['wins'] or 0
        
        return {
            'going_runs': runs,
            'going_wins': wins,
            'going_win_rate': wins / runs if runs > 0 else 0.0
        }
    
    def get_opening_odds(self, runner_id: int) -> Optional[float]:
        """Get opening odds for runner from runner_odds table"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT odds_decimal
            FROM runner_odds
            WHERE runner_id = ?
            ORDER BY created_at ASC
            LIMIT 1
        """, (runner_id,))
        
        row = cursor.fetchone()
        if row and row['odds_decimal']:
            try:
                return float(row['odds_decimal'])
            except (ValueError, TypeError):
                return None
        return None
    
    def compute_pace_features(self, horse_id: str, race_date: str = None) -> Dict:
        """
        Compute pace/speed features from TSR (Time Speed Rating) and race comments
        """
        cursor = self.conn.cursor()
        
        # Get recent TSR values (last 10 runs before this race)
        date_filter = "AND rac.date < ?" if race_date else ""
        params = [horse_id]
        if race_date:
            params.append(race_date)
        
        cursor.execute(f"""
            SELECT res.tsr, res.comment, rac.date
            FROM results res
            JOIN races rac ON res.race_id = rac.race_id
            WHERE res.horse_id = ?
            {date_filter}
            AND res.position_int < 900
            ORDER BY rac.date DESC
            LIMIT 10
        """, tuple(params))
        
        rows = cursor.fetchall()
        
        # TSR features
        tsr_values = []
        for row in rows:
            if row['tsr']:
                try:
                    tsr_values.append(float(row['tsr']))
                except (ValueError, TypeError):
                    pass
        
        horse_best_tsr = max(tsr_values) if tsr_values else None
        horse_avg_tsr_last_5 = np.mean(tsr_values[:5]) if len(tsr_values) >= 5 else (np.mean(tsr_values) if tsr_values else None)
        
        # Speed improving trend (compare recent 3 vs previous 3)
        speed_improving = 0
        if len(tsr_values) >= 6:
            recent_3 = np.mean(tsr_values[:3])
            previous_3 = np.mean(tsr_values[3:6])
            if recent_3 > previous_3 + 2:  # Threshold of 2 points improvement
                speed_improving = 1
        
        # Running style from comments (keywords analysis)
        running_style = self._parse_running_style(rows)
        
        return {
            'horse_best_tsr': horse_best_tsr,
            'horse_avg_tsr_last_5': horse_avg_tsr_last_5,
            'speed_improving': speed_improving,
            'typical_running_style': running_style  # 1=leader, 2=prominent, 3=midfield, 4=held up
        }
    
    def _parse_running_style(self, race_rows: List) -> int:
        """
        Parse running style from race comments
        1 = Leader/front-runner
        2 = Prominent/tracked leaders
        3 = Midfield
        4 = Held up/closer
        """
        if not race_rows:
            return 3  # Default to midfield
        
        style_scores = []
        
        for row in race_rows[:5]:  # Look at last 5 comments
            comment = str(row.get('comment', '')).lower()
            
            # Leader keywords
            if any(word in comment for word in ['led', 'front', 'made all', 'led throughout', 'front-ran']):
                style_scores.append(1)
            # Prominent keywords
            elif any(word in comment for word in ['prominent', 'tracked', 'pressed', 'close up', 'disputed']):
                style_scores.append(2)
            # Held up keywords
            elif any(word in comment for word in ['held up', 'rear', 'behind', 'switched', 'waited']):
                style_scores.append(4)
            # Midfield
            else:
                style_scores.append(3)
        
        # Return most common style (mode)
        if style_scores:
            return int(np.median(style_scores))
        return 3
    
    def compute_draw_bias(self, course: str, distance_f: float, draw: int, field_size: int, race_date: str = None) -> Dict:
        """
        Compute draw bias features from historical data at this course/distance
        """
        if not draw or not course or not distance_f:
            return {
                'course_distance_draw_bias': None,
                'draw_position_normalized': None,
                'low_draw_advantage': 0,
                'high_draw_advantage': 0
            }
        
        cursor = self.conn.cursor()
        
        # Historical draw performance at this course/distance (±1f)
        date_filter = "AND rac.date < ?" if race_date else ""
        params = [course, distance_f - 1, distance_f + 1]
        if race_date:
            params.append(race_date)
        
        cursor.execute(f"""
            SELECT ru.draw,
                   COUNT(*) as runs,
                   SUM(CASE WHEN res.position_int = 1 THEN 1 ELSE 0 END) as wins,
                   AVG(res.position_int) as avg_position
            FROM results res
            JOIN runners ru ON res.race_id = ru.race_id AND res.horse_id = ru.horse_id
            JOIN races rac ON res.race_id = rac.race_id
            WHERE rac.course = ?
            AND rac.distance_f BETWEEN ? AND ?
            {date_filter}
            AND res.position_int < 900
            AND ru.draw IS NOT NULL
            AND CAST(ru.draw AS INTEGER) > 0
            GROUP BY ru.draw
            HAVING runs >= 5
        """, tuple(params))
        
        draw_stats = {int(row['draw']): {
            'runs': row['runs'],
            'wins': row['wins'],
            'win_rate': row['wins'] / row['runs'],
            'avg_position': row['avg_position']
        } for row in cursor.fetchall()}
        
        # Get bias for this specific draw
        course_distance_draw_bias = None
        if draw in draw_stats:
            # Bias is difference from expected (1 / number of draws with data)
            expected_win_rate = 1 / len(draw_stats) if draw_stats else 0.1
            course_distance_draw_bias = draw_stats[draw]['win_rate'] - expected_win_rate
        
        # Normalized draw position (0 to 1)
        draw_position_normalized = draw / field_size if field_size > 0 else 0.5
        
        # Check for systematic low/high draw advantage
        low_draws_win_rate = np.mean([stats['win_rate'] for d, stats in draw_stats.items() if d <= 5]) if draw_stats else None
        high_draws_win_rate = np.mean([stats['win_rate'] for d, stats in draw_stats.items() if d >= max(10, field_size - 5)]) if draw_stats else None
        
        low_draw_advantage = 0
        high_draw_advantage = 0
        
        if low_draws_win_rate and high_draws_win_rate:
            if low_draws_win_rate > high_draws_win_rate * 1.2:  # 20% better
                low_draw_advantage = 1 if draw <= 5 else 0
            elif high_draws_win_rate > low_draws_win_rate * 1.2:
                high_draw_advantage = 1 if draw >= field_size - 5 else 0
        
        return {
            'course_distance_draw_bias': course_distance_draw_bias,
            'draw_position_normalized': draw_position_normalized,
            'low_draw_advantage': low_draw_advantage,
            'high_draw_advantage': high_draw_advantage
        }
    
    def compute_runner_features(self, runner: Dict, race_context: Dict, 
                                result: Optional[Dict]) -> Dict:
        """
        Compute all features for a single runner
        
        Returns dict with ~50-100 features ready for ML
        """
        horse_id = runner['horse_id']
        trainer_id = runner['trainer_id']
        jockey_id = runner['jockey_id']
        race_date = race_context['date']
        
        features = {
            'race_id': race_context['race_id'],
            'runner_id': runner['runner_id'],
            'horse_id': horse_id
        }
        
        # === HORSE FEATURES ===
        features['horse_age'] = self._to_int(runner.get('age'))
        
        # Career stats (time-aware to prevent data leakage)
        horse_stats = self.get_horse_career_stats(horse_id, race_date)
        features['horse_career_runs'] = horse_stats.get('total_runs', 0)
        features['horse_career_wins'] = horse_stats.get('wins', 0)
        features['horse_win_rate'] = horse_stats.get('win_rate', 0.0)
        features['horse_place_rate'] = horse_stats.get('place_rate', 0.0)
        features['horse_avg_position'] = horse_stats.get('avg_position')
        features['horse_best_rating'] = self._to_float(runner.get('ofr'))  # Official rating
        
        # Form features
        form_features = self.form_parser.compute_form_features(runner.get('form', ''))
        features['horse_form_last_5_avg'] = form_features.get('avg_last_5')
        features['horse_form_improving'] = form_features.get('improving_trend', 0)
        features['horse_consistency'] = form_features.get('consistency')
        features['races_since_win'] = form_features.get('races_since_win')
        features['races_since_place'] = form_features.get('races_since_place')
        
        # Days since last run
        features['horse_days_since_last'] = self.get_days_since_last_run(horse_id, race_date)
        
        # Course-specific performance (time-aware to prevent data leakage)
        course_stats = self.compute_course_specific_stats(
            horse_id, race_context['course'], 'horse', race_date
        )
        features['horse_course_wins'] = course_stats.get('course_wins', 0)
        features['horse_course_win_rate'] = course_stats.get('course_win_rate', 0.0)
        
        # Distance-specific performance (time-aware to prevent data leakage)
        distance_stats = self.compute_distance_specific_stats(
            horse_id, race_context['distance_f'], race_date
        )
        features['horse_distance_win_rate'] = distance_stats.get('distance_win_rate', 0.0)
        
        # Going-specific performance (time-aware to prevent data leakage)
        going_stats = self.compute_going_specific_stats(
            horse_id, race_context['going'], race_date
        )
        features['horse_going_win_rate'] = going_stats.get('going_win_rate', 0.0)
        
        # === PACE/SPEED FEATURES ===
        pace_features = self.compute_pace_features(horse_id, race_date)
        features['horse_best_tsr'] = pace_features.get('horse_best_tsr')
        features['horse_avg_tsr_last_5'] = pace_features.get('horse_avg_tsr_last_5')
        features['speed_improving'] = pace_features.get('speed_improving', 0)
        features['typical_running_style'] = pace_features.get('typical_running_style', 3)
        
        # === TRAINER FEATURES ===
        trainer_stats_14d = self.get_trainer_stats(trainer_id, '14d')
        trainer_stats_90d = self.get_trainer_stats(trainer_id, '90d')
        
        features['trainer_win_rate_14d'] = trainer_stats_14d.get('win_rate', 0.0)
        features['trainer_win_rate_90d'] = trainer_stats_90d.get('win_rate', 0.0)
        features['trainer_strike_rate'] = trainer_stats_90d.get('strike_rate', 0.0)
        features['trainer_roi'] = trainer_stats_90d.get('roi', 0.0)
        
        # Trainer course specialization (time-aware to prevent data leakage)
        trainer_course_stats = self.compute_course_specific_stats(
            trainer_id, race_context['course'], 'trainer', race_date
        )
        features['trainer_course_win_rate'] = trainer_course_stats.get('course_win_rate', 0.0)
        
        # Trainer distance specialization
        trainer_distance_spec = trainer_stats_90d.get('distance_spec', {})
        # Find matching distance band
        features['trainer_distance_win_rate'] = 0.0
        if race_context['distance_f']:
            for band_name, band_stats in trainer_distance_spec.items():
                if self._distance_in_band(race_context['distance_f'], band_name):
                    features['trainer_distance_win_rate'] = band_stats.get('win_rate', 0.0)
                    break
        
        # === JOCKEY FEATURES ===
        jockey_stats_14d = self.get_jockey_stats(jockey_id, '14d')
        jockey_stats_90d = self.get_jockey_stats(jockey_id, '90d')
        
        features['jockey_win_rate_14d'] = jockey_stats_14d.get('win_rate', 0.0)
        features['jockey_win_rate_90d'] = jockey_stats_90d.get('win_rate', 0.0)
        features['jockey_strike_rate'] = jockey_stats_90d.get('strike_rate', 0.0)
        features['jockey_roi'] = jockey_stats_90d.get('roi', 0.0)
        
        # Jockey course performance (time-aware to prevent data leakage)
        jockey_course_stats = self.compute_course_specific_stats(
            jockey_id, race_context['course'], 'jockey', race_date
        )
        features['jockey_course_win_rate'] = jockey_course_stats.get('course_win_rate', 0.0)
        
        # === TRAINER-JOCKEY COMBO ===
        combo_stats = self.get_trainer_jockey_combo_stats(trainer_id, jockey_id)
        features['combo_win_rate'] = combo_stats.get('win_rate', 0.0)
        features['combo_strike_rate'] = combo_stats.get('strike_rate', 0.0)
        features['combo_runs'] = combo_stats.get('runs', 0)
        
        # === RACE CONTEXT FEATURES ===
        features['distance_f'] = race_context['distance_f']
        features['going_encoded'] = race_context['going_encoded']
        features['surface_encoded'] = race_context['surface_encoded']
        features['race_class'] = race_context.get('race_class')
        features['race_class_encoded'] = race_context['race_class_encoded']
        features['prize_money'] = race_context['prize_money']
        
        # === RUNNER-SPECIFIC FEATURES ===
        features['runner_number'] = self._to_int(runner.get('number'))
        features['draw'] = self._to_int(runner.get('draw'))
        features['weight_lbs'] = self._to_float(runner.get('weight_lbs_combined'))
        features['ofr'] = self._to_float(runner.get('ofr'))
        features['rpr'] = self._to_float(runner.get('rpr'))
        features['ts'] = self._to_float(runner.get('ts'))
        
        # Headgear encoding (0 = none, 1 = has headgear)
        features['headgear_encoded'] = 1 if runner.get('headgear') else 0
        
        # === MARKET FEATURES (PLACEHOLDERS) ===
        # These will be populated after computing relative features
        features['opening_odds'] = None
        features['final_odds'] = None
        features['odds_movement'] = None
        features['odds_rank'] = None
        features['market_rank'] = None
        
        # === RELATIVE FEATURES (PLACEHOLDERS) ===
        # These are computed after we have all runners
        features['rating_vs_avg'] = None
        features['weight_vs_avg'] = None
        features['age_vs_avg'] = None
        features['weight_lbs_rank'] = None
        features['age_rank'] = None
        features['jockey_rating'] = None
        features['trainer_rating'] = None
        
        # === FIELD STRENGTH FEATURES (PLACEHOLDERS) ===
        features['field_best_rpr'] = None
        features['field_worst_rpr'] = None
        features['field_avg_rpr'] = None
        features['horse_rpr_rank'] = None
        features['horse_rpr_vs_best'] = None
        features['horse_rpr_vs_worst'] = None
        features['field_rpr_spread'] = None
        features['top_3_rpr_avg'] = None
        features['horse_in_top_quartile'] = None
        features['tsr_vs_field_avg'] = None
        features['pace_pressure_likely'] = None
        
        # === DRAW BIAS FEATURES (PLACEHOLDERS - need field size first) ===
        features['course_distance_draw_bias'] = None
        features['draw_position_normalized'] = None
        features['low_draw_advantage'] = None
        features['high_draw_advantage'] = None
        
        # === PEDIGREE FEATURES (PLACEHOLDERS) ===
        # TODO: Implement sire/dam statistics
        features['sire_distance_win_rate'] = None
        features['sire_surface_win_rate'] = None
        features['dam_produce_win_rate'] = None
        
        # Field size (will be set after processing all runners)
        features['field_size'] = None
        
        return features
    
    def _to_float(self, value) -> Optional[float]:
        """Safely convert value to float"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _to_int(self, value) -> Optional[int]:
        """Safely convert value to int"""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    def _parse_prize(self, prize_str) -> float:
        """Parse prize money removing currency symbols"""
        if not prize_str:
            return 0.0
        try:
            # Remove currency symbols and commas
            cleaned = str(prize_str).replace('£', '').replace('€', '').replace(',', '').strip()
            return float(cleaned)
        except (ValueError, TypeError):
            return 0.0
    
    def _distance_in_band(self, distance_f: float, band_name: str) -> bool:
        """Check if distance falls within a band"""
        bands = {
            '5-6f': (5, 6),
            '7-8f': (7, 8),
            '9-10f': (9, 10),
            '11-12f': (11, 12),
            '13-16f': (13, 16),
            '17f+': (17, 999)
        }
        
        if band_name not in bands:
            return False
        
        min_f, max_f = bands[band_name]
        return min_f <= distance_f <= max_f
    
    def compute_relative_features(self, all_runner_features: List[Dict]) -> List[Dict]:
        """
        Compute relative features, field strength, and draw bias for all runners
        This is where race-context features come together!
        Modifies features in place
        """
        if not all_runner_features:
            return all_runner_features
        
        # === FIELD SIZE ===
        field_size = len(all_runner_features)
        for features in all_runner_features:
            features['field_size'] = field_size
        
        # === COLLECT VALUES FOR ANALYSIS ===
        ratings = []
        weights = []
        ages = []
        tsr_values = []
        jockey_win_rates = []
        trainer_win_rates = []
        running_styles = []
        
        for f in all_runner_features:
            if f['ofr'] is not None:
                try:
                    ratings.append((float(f['ofr']), f))
                except (ValueError, TypeError):
                    pass
            
            if f['weight_lbs'] is not None:
                try:
                    weights.append((float(f['weight_lbs']), f))
                except (ValueError, TypeError):
                    pass
            
            if f['horse_age'] is not None:
                try:
                    ages.append((float(f['horse_age']), f))
                except (ValueError, TypeError):
                    pass
            
            if f['horse_avg_tsr_last_5'] is not None:
                try:
                    tsr_values.append(float(f['horse_avg_tsr_last_5']))
                except (ValueError, TypeError):
                    pass
            
            # Collect jockey/trainer ratings
            jockey_wr = f.get('jockey_win_rate_90d', 0) or 0
            trainer_wr = f.get('trainer_win_rate_90d', 0) or 0
            jockey_win_rates.append(jockey_wr)
            trainer_win_rates.append(trainer_wr)
            
            # Collect running styles
            if f['typical_running_style']:
                running_styles.append(f['typical_running_style'])
        
        # === FIELD STRENGTH METRICS ===
        if ratings:
            rating_values = [r[0] for r in ratings]
            field_best_rpr = max(rating_values)
            field_worst_rpr = min(rating_values)
            field_avg_rpr = np.mean(rating_values)
            field_rpr_spread = field_best_rpr - field_worst_rpr
            
            # Top 3 RPR average
            sorted_ratings = sorted(rating_values, reverse=True)
            top_3_rpr_avg = np.mean(sorted_ratings[:3]) if len(sorted_ratings) >= 3 else field_avg_rpr
            
            # Top quartile threshold
            top_quartile_threshold = np.percentile(rating_values, 75) if len(rating_values) >= 4 else field_avg_rpr
        else:
            field_best_rpr = None
            field_worst_rpr = None
            field_avg_rpr = None
            field_rpr_spread = None
            top_3_rpr_avg = None
            top_quartile_threshold = None
        
        # Average TSR
        avg_tsr = np.mean(tsr_values) if tsr_values else None
        
        # Average jockey/trainer ratings
        avg_jockey_wr = np.mean(jockey_win_rates) if jockey_win_rates else 0
        avg_trainer_wr = np.mean(trainer_win_rates) if trainer_win_rates else 0
        
        # Pace pressure (count of front-runners/prominent horses)
        pace_pressure = sum(1 for style in running_styles if style in [1, 2])
        
        # === POPULATE FIELD STRENGTH FEATURES ===
        for features in all_runner_features:
            features['field_best_rpr'] = field_best_rpr
            features['field_worst_rpr'] = field_worst_rpr
            features['field_avg_rpr'] = field_avg_rpr
            features['field_rpr_spread'] = field_rpr_spread
            features['top_3_rpr_avg'] = top_3_rpr_avg
            features['pace_pressure_likely'] = pace_pressure
        
        # === RANKINGS ===
        # RPR rank
        if ratings:
            sorted_ratings = sorted(ratings, key=lambda x: x[0], reverse=True)
            for rank, (rating_val, f) in enumerate(sorted_ratings, 1):
                f['horse_rpr_rank'] = rank
                f['horse_rpr_vs_best'] = rating_val - field_best_rpr
                f['horse_rpr_vs_worst'] = rating_val - field_worst_rpr
                f['horse_in_top_quartile'] = 1 if rating_val >= top_quartile_threshold else 0
        
        # Weight rank
        if weights:
            sorted_weights = sorted(weights, key=lambda x: x[0])  # Lower weight = better rank
            for rank, (weight_val, f) in enumerate(sorted_weights, 1):
                f['weight_lbs_rank'] = rank
        
        # Age rank
        if ages:
            sorted_ages = sorted(ages, key=lambda x: x[0])
            for rank, (age_val, f) in enumerate(sorted_ages, 1):
                f['age_rank'] = rank
        
        # === RELATIVE FEATURES (vs average) ===
        for features in all_runner_features:
            # Rating vs avg
            if features['ofr'] is not None and field_avg_rpr is not None:
                try:
                    features['rating_vs_avg'] = float(features['ofr']) - field_avg_rpr
                except (ValueError, TypeError):
                    pass
            
            # Weight vs avg
            if weights:
                avg_weight = np.mean([w[0] for w in weights])
                if features['weight_lbs'] is not None:
                    try:
                        features['weight_vs_avg'] = float(features['weight_lbs']) - avg_weight
                    except (ValueError, TypeError):
                        pass
            
            # Age vs avg
            if ages:
                avg_age = np.mean([a[0] for a in ages])
                if features['horse_age'] is not None:
                    try:
                        features['age_vs_avg'] = float(features['horse_age']) - avg_age
                    except (ValueError, TypeError):
                        pass
            
            # TSR vs field average
            if features['horse_avg_tsr_last_5'] is not None and avg_tsr is not None:
                try:
                    features['tsr_vs_field_avg'] = float(features['horse_avg_tsr_last_5']) - avg_tsr
                except (ValueError, TypeError):
                    pass
            
            # Jockey/trainer rating (vs field average)
            jockey_wr = features.get('jockey_win_rate_90d', 0) or 0
            trainer_wr = features.get('trainer_win_rate_90d', 0) or 0
            features['jockey_rating'] = jockey_wr - avg_jockey_wr
            features['trainer_rating'] = trainer_wr - avg_trainer_wr
        
        # === MARKET RANKS (based on OFR as proxy) ===
        sorted_by_rating = sorted(
            all_runner_features, 
            key=lambda x: x['ofr'] if x['ofr'] is not None else -999,
            reverse=True
        )
        
        for rank, features in enumerate(sorted_by_rating, 1):
            features['odds_rank'] = rank
            features['market_rank'] = rank
        
        # === DRAW BIAS FEATURES ===
        # Get race context from first runner (all have same race)
        if all_runner_features:
            first_runner = all_runner_features[0]
            race_context = {
                'course': first_runner.get('race_id', '').split('_')[0] if first_runner.get('race_id') else None,
                'distance_f': first_runner.get('distance_f'),
                'race_date': None  # Will be determined from race_id if needed
            }
            
            # Compute draw bias for each runner
            for features in all_runner_features:
                # Extract course from race_id if not available
                # race_id format might be like "rac_12345678" or contain course info
                # For now, we'll use compute_draw_bias with available data
                draw = features.get('draw')
                if draw is not None and features.get('distance_f') is not None:
                    # Note: course extraction might need adjustment based on your race_id format
                    # For now, skip draw bias if we can't get course easily
                    # This will be computed during prediction when we have full race context
                    pass
        
        return all_runner_features
    
    def compute_target_variables(self, race_id: str, horse_id: str, 
                                runner_id: int, result: Dict) -> Dict:
        """Compute target variables from race result"""
        if not result:
            return None
        
        position = result.get('position_int')
        if position is None or position >= 900:  # DNF
            return None
        
        return {
            'race_id': race_id,
            'runner_id': runner_id,
            'horse_id': horse_id,
            'position': position,
            'won': 1 if position == 1 else 0,
            'placed': 1 if position <= 3 else 0,
            'top_5': 1 if position <= 5 else 0,
            'beaten_lengths': self._to_float(result.get('ovr_btn')),
            'finishing_time': result.get('time'),
            'prize_money': self._parse_prize(result.get('prize'))
        }
    
    def save_features(self, features: Dict):
        """Save features to ml_features table - Note: New columns need to be added to table first"""
        cursor = self.conn.cursor()
        
        # Try to insert with new columns, fall back to old schema if needed
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO ml_features (
                    race_id, runner_id, horse_id,
                    horse_age, horse_career_runs, horse_career_wins,
                    horse_win_rate, horse_place_rate, horse_avg_position,
                    horse_course_wins, horse_distance_win_rate, horse_going_win_rate,
                    horse_days_since_last, horse_form_last_5_avg, horse_form_improving,
                    horse_consistency, horse_best_rating,
                    horse_best_tsr, horse_avg_tsr_last_5, speed_improving, typical_running_style,
                    trainer_win_rate_14d, trainer_win_rate_90d, trainer_strike_rate,
                    trainer_course_win_rate, trainer_distance_win_rate, trainer_roi,
                    trainer_form_with_horse, trainer_rating,
                    jockey_win_rate_14d, jockey_win_rate_90d, jockey_strike_rate,
                    jockey_course_win_rate, jockey_distance_win_rate, jockey_roi, jockey_rating,
                    combo_win_rate, combo_strike_rate, combo_runs,
                    field_size, race_class, race_class_encoded, distance_f, going_encoded,
                    surface_encoded, prize_money,
                    runner_number, draw, weight_lbs, ofr, rpr, ts, headgear_encoded,
                    rating_vs_avg, weight_vs_avg, age_vs_avg, weight_lbs_rank, age_rank,
                    field_best_rpr, field_worst_rpr, field_avg_rpr, horse_rpr_rank,
                    horse_rpr_vs_best, horse_rpr_vs_worst, field_rpr_spread, top_3_rpr_avg,
                    horse_in_top_quartile, tsr_vs_field_avg, pace_pressure_likely,
                    course_distance_draw_bias, draw_position_normalized, low_draw_advantage, high_draw_advantage,
                    odds_rank, opening_odds, final_odds, odds_movement, market_rank,
                    sire_distance_win_rate, sire_surface_win_rate, dam_produce_win_rate
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                features['race_id'], features['runner_id'], features['horse_id'],
                features['horse_age'], features['horse_career_runs'], features['horse_career_wins'],
                features['horse_win_rate'], features['horse_place_rate'], features['horse_avg_position'],
                features['horse_course_wins'], features['horse_distance_win_rate'], features['horse_going_win_rate'],
                features['horse_days_since_last'], features['horse_form_last_5_avg'], features['horse_form_improving'],
                features['horse_consistency'], features['horse_best_rating'],
                features.get('horse_best_tsr'), features.get('horse_avg_tsr_last_5'), 
                features.get('speed_improving', 0), features.get('typical_running_style', 3),
                features['trainer_win_rate_14d'], features['trainer_win_rate_90d'], features['trainer_strike_rate'],
                features['trainer_course_win_rate'], features['trainer_distance_win_rate'], features['trainer_roi'],
                None, features.get('trainer_rating', 0),  # trainer_form_with_horse not implemented
                features['jockey_win_rate_14d'], features['jockey_win_rate_90d'], features['jockey_strike_rate'],
                features['jockey_course_win_rate'], None, features['jockey_roi'], features.get('jockey_rating', 0),
                features['combo_win_rate'], features['combo_strike_rate'], features['combo_runs'],
                features['field_size'], features['race_class'], features['race_class_encoded'], 
                features['distance_f'], features['going_encoded'], features['surface_encoded'], features['prize_money'],
                features['runner_number'], features['draw'], features['weight_lbs'], 
                features['ofr'], features['rpr'], features['ts'], features['headgear_encoded'],
                features['rating_vs_avg'], features['weight_vs_avg'], features['age_vs_avg'],
                features.get('weight_lbs_rank'), features.get('age_rank'),
                features.get('field_best_rpr'), features.get('field_worst_rpr'), features.get('field_avg_rpr'),
                features.get('horse_rpr_rank'), features.get('horse_rpr_vs_best'), features.get('horse_rpr_vs_worst'),
                features.get('field_rpr_spread'), features.get('top_3_rpr_avg'), features.get('horse_in_top_quartile', 0),
                features.get('tsr_vs_field_avg'), features.get('pace_pressure_likely', 0),
                features.get('course_distance_draw_bias'), features.get('draw_position_normalized'),
                features.get('low_draw_advantage', 0), features.get('high_draw_advantage', 0),
                features['odds_rank'], features['opening_odds'], features['final_odds'], 
                features['odds_movement'], features['market_rank'],
                features['sire_distance_win_rate'], features['sire_surface_win_rate'], features['dam_produce_win_rate']
            ))
        except sqlite3.OperationalError as e:
            # If columns don't exist, log warning and skip (schema needs update)
            logger.warning(f"Error saving features (schema may need update): {e}")
            # Could fall back to old schema here if needed
    
    def save_targets(self, targets: Dict):
        """Save target variables to ml_targets table"""
        if not targets:
            return
        
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO ml_targets (
                race_id, runner_id, horse_id, position, won, placed, top_5,
                beaten_lengths, finishing_time, prize_money, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            targets['race_id'], targets['runner_id'], targets['horse_id'],
            targets['position'], targets['won'], targets['placed'], targets['top_5'],
            targets['beaten_lengths'], targets['finishing_time'], targets['prize_money']
        ))
    
    def process_race(self, race_id: str) -> int:
        """
        Process a single race: compute features and targets for all runners
        Returns number of runners processed
        """
        # Get race context
        race_context = self.get_race_context_features(race_id)
        if not race_context:
            logger.warning(f"No race context for {race_id}")
            return 0
        
        # Get all runners
        runners = self.get_runners_for_race(race_id)
        if not runners:
            logger.warning(f"No runners for race {race_id}")
            return 0
        
        # Compute features for each runner
        all_features = []
        all_targets = []
        
        for runner in runners:
            # Get result (if exists)
            result = self.get_runner_result(race_id, runner['horse_id'])
            
            # Compute features
            features = self.compute_runner_features(runner, race_context, result)
            all_features.append(features)
            
            # Compute targets
            targets = self.compute_target_variables(
                race_id, runner['horse_id'], runner['runner_id'], result
            )
            if targets:
                all_targets.append(targets)
        
        # Compute relative features (modifies in place)
        all_features = self.compute_relative_features(all_features)
        
        # Compute draw bias features now that we have field size and race context
        for features in all_features:
            draw = features.get('draw')
            if draw is not None:
                draw_bias = self.compute_draw_bias(
                    race_context.get('course'),
                    race_context.get('distance_f'),
                    draw,
                    features['field_size'],
                    race_context.get('date')
                )
                features['course_distance_draw_bias'] = draw_bias['course_distance_draw_bias']
                features['draw_position_normalized'] = draw_bias['draw_position_normalized']
                features['low_draw_advantage'] = draw_bias['low_draw_advantage']
                features['high_draw_advantage'] = draw_bias['high_draw_advantage']
        
        # Save to database
        for features in all_features:
            self.save_features(features)
        
        for targets in all_targets:
            self.save_targets(targets)
        
        return len(all_features)
    
    def generate_features_for_all_races(self, limit: Optional[int] = None):
        """
        Main execution: Generate features for all races with results
        """
        logger.info("="*60)
        logger.info("GENERATING ML FEATURES")
        logger.info("="*60)
        
        self.connect()
        
        try:
            # Get races with results
            race_ids = self.get_races_with_results(limit=limit)
            logger.info(f"Found {len(race_ids)} races with results")
            
            if not race_ids:
                logger.warning("No races with results found. Run stats computation first.")
                return
            
            total_runners = 0
            
            for i, race_id in enumerate(race_ids, 1):
                if i % 100 == 0:
                    logger.info(f"  Processed {i}/{len(race_ids)} races...")
                    self.conn.commit()  # Commit every 100 races
                
                runners_processed = self.process_race(race_id)
                total_runners += runners_processed
            
            # Final commit
            self.conn.commit()
            
            logger.info("="*60)
            logger.info("✓ FEATURE GENERATION COMPLETE")
            logger.info(f"  Races processed: {len(race_ids)}")
            logger.info(f"  Runners processed: {total_runners}")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"Error generating features: {e}", exc_info=True)
            self.conn.rollback()
            raise
        finally:
            self.close()


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate ML features')
    parser.add_argument('--limit', type=int, help='Limit number of races (for testing)')
    parser.add_argument('--test', action='store_true', help='Test mode (first 10 races)')
    
    args = parser.parse_args()
    
    limit = args.limit
    if args.test:
        limit = 10
        logger.info("TEST MODE: Processing first 10 races only")
    
    db_path = Path(__file__).parent.parent / "racing_pro.db"
    
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        return
    
    engineer = FeatureEngineer(db_path)
    engineer.generate_features_for_all_races(limit=limit)


if __name__ == "__main__":
    main()

