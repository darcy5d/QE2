#!/usr/bin/env python3
"""
ML Predictor - Generate predictions for upcoming races
Uses trained XGBoost model to predict win probabilities
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import sqlite3
import sys

# Add parent directory to path to import feature_engineer
sys.path.append(str(Path(__file__).parent.parent))

from ml.feature_engineer import FeatureEngineer


def dict_factory(cursor, row):
    """
    Convert sqlite3 query results to dictionaries
    
    This allows using .get() method which sqlite3.Row doesn't support.
    """
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


class ModelPredictor:
    """Generate predictions for upcoming races using trained ML model"""
    
    def __init__(self, model_path: str = None, racing_db_path: str = None, race_type: str = 'Flat'):
        """
        Initialize predictor with trained model
        
        Args:
            model_path: Path to trained model JSON file (optional, auto-generates from race_type if not provided)
            racing_db_path: Path to racing_pro.db with historical data
            race_type: Type of races to predict ('Flat', 'Hurdle', 'Chase')
        """
        self.race_type = race_type
        self.model_dir = Path(__file__).parent / "models"
        
        # Auto-generate model path based on race type if not provided
        if model_path:
            self.model_path = Path(model_path)
        else:
            race_type_lower = race_type.lower()
            self.model_path = self.model_dir / f"xgboost_{race_type_lower}.json"
        
        # Database paths
        if racing_db_path:
            self.racing_db_path = Path(racing_db_path)
        else:
            self.racing_db_path = Path(__file__).parent.parent / "racing_pro.db"
        
        self.model = None
        self.feature_columns = None
        self.feature_importance = None
        self.feature_engineer = None
        self._upcoming_db_connected = False
        
        self._load_model()
        self._load_feature_metadata()
        # Note: feature_engineer will be initialized in predict_race with upcoming_db_path
    
    def _load_model(self):
        """Load trained XGBoost model"""
        try:
            import xgboost as xgb
            
            if not self.model_path.exists():
                raise FileNotFoundError(
                    f"Model not found: {self.model_path}\n"
                    f"Train a {self.race_type} model first using: "
                    f"python train_baseline.py --race-type {self.race_type}"
                )
            
            self.model = xgb.Booster()
            self.model.load_model(str(self.model_path))
            print(f"✓ Loaded {self.race_type} racing model from {self.model_path.name}")
        except Exception as e:
            raise RuntimeError(f"Failed to load model: {e}")
    
    def _load_feature_metadata(self):
        """Load feature columns and importance scores for specific race type"""
        race_type_lower = self.race_type.lower()
        
        # Load race-type-specific feature columns
        feature_cols_path = self.model_dir / f"feature_columns_{race_type_lower}.json"
        if feature_cols_path.exists():
            with open(feature_cols_path, 'r') as f:
                self.feature_columns = json.load(f)
            print(f"✓ Loaded {len(self.feature_columns)} feature columns for {self.race_type} racing")
        else:
            raise FileNotFoundError(
                f"Feature columns file not found: {feature_cols_path}\n"
                f"Train a {self.race_type} model first."
            )
        
        # Load race-type-specific feature importance
        importance_path = self.model_dir / f"feature_importance_{race_type_lower}.csv"
        if importance_path.exists():
            importance_df = pd.read_csv(importance_path)
            self.feature_importance = dict(zip(importance_df['feature'], importance_df['importance']))
            print(f"✓ Loaded feature importance scores")
        else:
            print("⚠ Feature importance file not found, will use default importance")
            self.feature_importance = {col: 1.0/len(self.feature_columns) for col in self.feature_columns}
    
    def _init_feature_engineer(self, upcoming_db_path: str = None):
        """Initialize feature engineer for generating features"""
        self.feature_engineer = FeatureEngineer(
            db_path=str(self.racing_db_path),
            upcoming_db_path=upcoming_db_path
        )
        self.feature_engineer.connect()
    
    def predict_race(self, race_id: str, upcoming_db_path: str) -> Dict:
        """
        Generate predictions for all runners in a race
        
        Args:
            race_id: Race ID from upcoming_races.db
            upcoming_db_path: Path to upcoming_races.db
            
        Returns:
            Dictionary with race info and predictions for each runner
        """
        # Initialize or update feature engineer with upcoming database connection
        if not self.feature_engineer or not self._upcoming_db_connected:
            if self.feature_engineer:
                self.feature_engineer.close()
            self._init_feature_engineer(upcoming_db_path)
            self._upcoming_db_connected = True
            print(f"✓ Feature engineer connected to upcoming database: {upcoming_db_path}")
        
        # Get race details and runners from upcoming_races.db
        race_data = self._get_race_data(race_id, upcoming_db_path)
        if not race_data:
            return None
        
        # Validate race type matches model
        race_type = race_data['race_info'].get('type', 'Unknown')
        if race_type != self.race_type:
            print(f"⚠️  Skipping {race_type} race (model trained for {self.race_type} only)")
            return None
        
        print(f"\n🏇 Processing race: {race_data['race_info'].get('course')} {race_data['race_info'].get('time')}")
        print(f"   Total runners in race: {len(race_data['runners'])}")
        
        # PASS 1: Collect available RPR/TS values to calculate field statistics
        available_rprs = []
        available_tss = []
        
        for runner in race_data['runners']:
            rpr = self._safe_convert(runner.get('rpr'))
            ts = self._safe_convert(runner.get('ts'))
            
            if rpr is not None:
                available_rprs.append(rpr)
            if ts is not None:
                available_tss.append(ts)
        
        # Calculate field statistics for smart defaults
        field_stats = {
            'median_rpr': np.median(available_rprs) if len(available_rprs) >= 3 else None,
            'avg_rpr': np.mean(available_rprs) if len(available_rprs) >= 1 else None,
            'median_ts': np.median(available_tss) if len(available_tss) >= 3 else None,
            'avg_ts': np.mean(available_tss) if len(available_tss) >= 1 else None,
            'count_rpr': len(available_rprs),
            'count_ts': len(available_tss)
        }
        
        print(f"   Runners with RPR: {field_stats['count_rpr']}/{len(race_data['runners'])}")
        print(f"   Runners with TS: {field_stats['count_ts']}/{len(race_data['runners'])}")
        if field_stats['median_rpr']:
            print(f"   Field median RPR: {field_stats['median_rpr']:.1f}")
        
        # Compute field-level odds statistics for smart defaults
        field_odds_avg = self._compute_field_odds_stats(race_data['runners'])
        if field_odds_avg['count'] > 0:
            print(f"   Runners with odds: {field_odds_avg['count']}/{len(race_data['runners'])}")
        
        # PASS 2: Generate features for each runner (with smart defaults)
        features_list = []
        runner_info = []
        
        for runner in race_data['runners']:
            # Generate features using FeatureEngineer (now with field stats and odds stats)
            features = self._generate_runner_features(
                race_data['race_info'],
                runner,
                field_stats,
                field_odds_avg
            )
            
            if features:
                features_list.append(features)
                runner_info.append(runner)
        
        print(f"   Successfully generated features for: {len(features_list)}/{len(race_data['runners'])} runners")
        
        # Diagnostic: Check odds feature population
        odds_count = sum(1 for f in features_list if f.get('odds_decimal') is not None and f.get('odds_decimal') > 0)
        if odds_count > 0:
            print(f"   ✓ Odds features populated: {odds_count}/{len(features_list)} runners ({odds_count*100/len(features_list):.1f}%)")
        else:
            print(f"   ⚠️  No odds data available for this race (using defaults)")
        
        if not features_list:
            print(f"   ❌ No features generated for any runner!")
            return None
        
        # Compute relative features (field size, rating_vs_avg, etc.)
        features_list = self.feature_engineer.compute_relative_features(features_list)
        
        # Create feature matrix
        X = self._prepare_feature_matrix(features_list)
        
        # Make predictions with RANKING model
        import xgboost as xgb
        dmatrix = xgb.DMatrix(X, feature_names=self.feature_columns)
        ranking_scores = self.model.predict(dmatrix)
        
        # Convert ranking scores to probabilities using softmax
        # Ranking model outputs relative scores (higher = better)
        # Softmax naturally ensures probabilities sum to 1.0
        probabilities = self._scores_to_probabilities(ranking_scores)
        
        # Calculate ranks and confidence
        ranks = self._calculate_ranks(probabilities)
        confidence = self._calculate_confidence(probabilities)
        
        # Get top contributing features for each runner
        contributions = [
            self._get_feature_contributions(features_list[i], probabilities[i])
            for i in range(len(runner_info))
        ]
        
        # Compile results
        predictions = []
        for i, runner in enumerate(runner_info):
            predictions.append({
                'runner_number': runner.get('number'),
                'horse_name': runner.get('horse_name'),
                'trainer': runner.get('trainer_name'),
                'jockey': runner.get('jockey_name'),
                'win_probability': float(probabilities[i]),
                'predicted_rank': int(ranks[i]),
                'confidence': confidence,
                'top_features': contributions[i],
                'value_indicator': self._check_value_bet(probabilities[i], runner.get('ofr')),
                'market_odds': runner.get('market_odds'),  # Market win odds
                'market_prob': runner.get('market_prob'),  # Market implied probability
                'runner_id': runner.get('runner_id')  # For fetching additional data later
            })
        
        return {
            'race_info': race_data['race_info'],
            'predictions': sorted(predictions, key=lambda x: x['predicted_rank'])
        }
    
    def _get_race_data(self, race_id: str, upcoming_db_path: str) -> Optional[Dict]:
        """Fetch race and runner data from upcoming_races.db"""
        conn = sqlite3.connect(upcoming_db_path)
        conn.row_factory = dict_factory  # Changed from sqlite3.Row to support .get()
        cursor = conn.cursor()
        
        # Get race info
        cursor.execute("""
            SELECT race_id, course, date, off_time as time, distance, distance_f, going, 
                   surface, type, race_class, race_name, prize, age_band, pattern, region
            FROM races
            WHERE race_id = ?
        """, (race_id,))
        
        race_row = cursor.fetchone()
        if not race_row:
            conn.close()
            return None
        
        race_info = dict(race_row)
        
        # Convert numeric fields from TEXT to proper types
        if race_info.get('distance_f'):
            try:
                race_info['distance_f'] = float(race_info['distance_f'])
            except (ValueError, TypeError):
                race_info['distance_f'] = None
        
        # Get runners with market odds
        cursor.execute("""
            SELECT r.runner_id, r.number, r.draw, r.lbs, r.ofr, r.rpr, r.ts,
                   r.headgear, r.form,
                   h.horse_id, h.name as horse_name, h.age,
                   t.trainer_id, t.name as trainer_name,
                   j.jockey_id, j.name as jockey_name,
                   mo.avg_decimal as market_odds,
                   mo.implied_probability as market_prob
            FROM runners r
            LEFT JOIN horses h ON r.horse_id = h.horse_id
            LEFT JOIN trainers t ON r.trainer_id = t.trainer_id
            LEFT JOIN jockeys j ON r.jockey_id = j.jockey_id
            LEFT JOIN runner_market_odds mo ON r.runner_id = mo.runner_id
            WHERE r.race_id = ?
            ORDER BY r.number
        """, (race_id,))
        
        runners = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {
            'race_info': race_info,
            'runners': runners
        }
    
    def _compute_field_odds_stats(self, runners: List[Dict]) -> Dict:
        """
        Compute field-level odds statistics for smart defaults
        
        When a runner doesn't have odds, use field average instead of 0/None
        This is better than defaulting to 0 which breaks the model
        
        Args:
            runners: List of runner dictionaries with runner_id
            
        Returns:
            Dictionary with average odds statistics
        """
        if not self.feature_engineer or not self.feature_engineer.upcoming_conn:
            return {'count': 0}
        
        # Query all odds for this race's runners
        runner_ids = [r['runner_id'] for r in runners if r.get('runner_id')]
        if not runner_ids:
            return {'count': 0}
        
        placeholders = ','.join('?' * len(runner_ids))
        conn = self.feature_engineer.upcoming_conn
        cursor = conn.cursor()
        
        cursor.execute(f'''
            SELECT avg_decimal, implied_probability, favorite_rank, bookmaker_count
            FROM runner_market_odds
            WHERE runner_id IN ({placeholders})
        ''', runner_ids)
        
        rows = cursor.fetchall()
        
        if not rows:
            return {'count': 0}
        
        # Compute averages
        decimals = [r['avg_decimal'] for r in rows if r.get('avg_decimal')]
        probs = [r['implied_probability'] for r in rows if r.get('implied_probability')]
        ranks = [r['favorite_rank'] for r in rows if r.get('favorite_rank')]
        bk_counts = [r['bookmaker_count'] for r in rows if r.get('bookmaker_count')]
        
        return {
            'count': len(rows),
            'avg_decimal': np.mean(decimals) if decimals else None,
            'avg_implied_prob': np.mean(probs) if probs else None,
            'avg_rank': np.mean(ranks) if ranks else 8,  # Default to middle rank
            'avg_bookmaker_count': int(np.mean(bk_counts)) if bk_counts else 0,
            'avg_spread': 2.0  # Reasonable default spread
        }
    
    def _safe_convert(self, value) -> Optional[float]:
        """Convert value to float, return None for '-' or invalid values"""
        if value is None or value == '-' or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _get_smart_default(self, field_stats: Dict, race_class: str, feature_name: str) -> float:
        """
        Get smart default for missing feature value
        
        Priority:
        1. Field median (if available and enough samples)
        2. Field average (if available)
        3. Race class default
        4. Global default
        
        Args:
            field_stats: Dictionary with field statistics
            race_class: Race class string (e.g., "Class 3", "Group 1")
            feature_name: 'rpr' or 'ts'
            
        Returns:
            Smart default value
        """
        # Priority 1: Field median (if we have enough samples)
        if feature_name == 'rpr':
            if field_stats.get('median_rpr') is not None and field_stats.get('count_rpr', 0) >= 3:
                return field_stats['median_rpr']
            if field_stats.get('avg_rpr') is not None and field_stats.get('count_rpr', 0) >= 1:
                return field_stats['avg_rpr']
        elif feature_name == 'ts':
            if field_stats.get('median_ts') is not None and field_stats.get('count_ts', 0) >= 3:
                return field_stats['median_ts']
            if field_stats.get('avg_ts') is not None and field_stats.get('count_ts', 0) >= 1:
                return field_stats['avg_ts']
        
        # Priority 2: Race class defaults
        class_defaults = {
            'rpr': {
                'Group 1': 115, 'Group 2': 115, 'Group 3': 110,
                'Listed': 110,
                'Class 1': 105, 'Class 2': 100, 'Class 3': 95,
                'Class 4': 85, 'Class 5': 75, 'Class 6': 65, 'Class 7': 65
            },
            'ts': {
                'Group 1': 90, 'Group 2': 90, 'Group 3': 85,
                'Listed': 85,
                'Class 1': 80, 'Class 2': 75, 'Class 3': 70,
                'Class 4': 65, 'Class 5': 60, 'Class 6': 55, 'Class 7': 55
            }
        }
        
        if race_class:
            # Try exact match
            if race_class in class_defaults.get(feature_name, {}):
                return class_defaults[feature_name][race_class]
            # Try partial match (e.g., "Class 3" contains "Class 3")
            for key in class_defaults.get(feature_name, {}).keys():
                if key in race_class or race_class in key:
                    return class_defaults[feature_name][key]
        
        # Priority 3: Global defaults
        return 90 if feature_name == 'rpr' else 70
    
    def _generate_runner_features(self, race_info: Dict, runner: Dict, field_stats: Dict = None, field_odds_avg: Dict = None) -> Optional[Dict]:
        """Generate ML features for a runner using FeatureEngineer"""
        from datetime import datetime
        
        # Debug logging
        runner_num = runner.get('number', '?')
        horse_name = runner.get('horse_name', 'Unknown')
        rpr_raw = runner.get('rpr')
        ts_raw = runner.get('ts')
        
        print(f"     Runner {runner_num}: {horse_name}")
        print(f"       Raw RPR: {rpr_raw}, Raw TS: {ts_raw}")
        
        # Use today's date to ensure we only use historical data
        race_date = datetime.now().strftime('%Y-%m-%d')
        race_id = race_info['race_id']
        
        # Initialize field_stats and field_odds_avg if not provided
        if field_stats is None:
            field_stats = {}
        if field_odds_avg is None:
            field_odds_avg = {'count': 0}
        
        try:
            # Encode categorical features (matching FeatureEngineer logic)
            going_map = {
                'heavy': 1, 'soft': 2, 'good to soft': 3, 'good': 4, 
                'good to firm': 5, 'firm': 6, 'hard': 7, 'standard': 4, 'slow': 3
            }
            surface_map = {'turf': 1, 'aw': 2, 'tapeta': 2, 'polytrack': 2, 'dirt': 3}
            
            going_str = str(race_info.get('going') or 'good').lower()
            going_encoded = going_map.get(going_str, 4)
            
            surface_str = str(race_info.get('surface') or 'turf').lower()
            surface_encoded = surface_map.get(surface_str, 1)
            
            # Extract class number from race_class string (e.g., "Class 3" -> 3)
            race_class_num = None
            if race_info.get('race_class'):
                import re
                match = re.search(r'\d+', str(race_info['race_class']))
                if match:
                    race_class_num = int(match.group())
            
            # Parse prize money
            prize_money = 0.0
            if race_info.get('prize'):
                try:
                    prize_str = str(race_info['prize']).replace('£', '').replace('€', '').replace(',', '').strip()
                    prize_money = float(prize_str)
                except:
                    pass
            
            # Convert distance_f to float (defensive check)
            distance_f_val = race_info.get('distance_f')
            if distance_f_val is not None:
                try:
                    distance_f_val = float(distance_f_val)
                except (ValueError, TypeError):
                    distance_f_val = None
            
            # Build race context
            race_context = {
                'race_id': race_id,
                'course': race_info.get('course'),
                'distance_f': distance_f_val,
                'going': race_info.get('going'),
                'going_encoded': going_encoded,
                'surface': race_info.get('surface'),
                'surface_encoded': surface_encoded,
                'race_type': race_info.get('type'),
                'race_class': race_info.get('race_class'),
                'race_class_encoded': race_class_num,
                'prize': race_info.get('prize'),
                'prize_money': prize_money,
                'age_band': race_info.get('age_band'),
                'pattern': race_info.get('pattern'),
                'date': race_date,
                'region': race_info.get('region')
            }
            
            # Build runner dict compatible with FeatureEngineer
            # Convert numeric fields to proper types (handle '-' placeholders)
            # Apply SMART DEFAULTS for missing RPR/TS
            
            rpr = self._safe_convert(runner.get('rpr'))
            ts = self._safe_convert(runner.get('ts'))
            
            # Apply smart defaults if RPR/TS is missing
            race_class_str = race_info.get('race_class')
            
            if rpr is None:
                rpr = self._get_smart_default(field_stats, race_class_str, 'rpr')
                print(f"       ⚠️  Missing RPR - using smart default: {rpr:.1f}")
            
            if ts is None:
                ts = self._get_smart_default(field_stats, race_class_str, 'ts')
                print(f"       ⚠️  Missing TS - using smart default: {ts:.1f}")
            
            print(f"       Final RPR: {rpr:.1f}, Final TS: {ts:.1f}")
            
            runner_data = {
                'runner_id': runner.get('runner_id', 0),
                'horse_id': runner.get('horse_id'),
                'trainer_id': runner.get('trainer_id'),
                'jockey_id': runner.get('jockey_id'),
                'number': runner.get('number'),
                'draw': runner.get('draw'),
                'age': runner.get('age'),
                'lbs': self._safe_convert(runner.get('lbs')),
                'weight_lbs_combined': self._safe_convert(runner.get('lbs')),  # FeatureEngineer looks for this key
                'ofr': self._safe_convert(runner.get('ofr')),
                'rpr': rpr,  # Now with smart defaults
                'ts': ts,    # Now with smart defaults
                'headgear': runner.get('headgear'),
                'form': runner.get('form')
            }
            
            # Generate features (this will compute all ML features)
            # result is None for upcoming races (no historical result yet)
            features = self.feature_engineer.compute_runner_features(
                runner_data, race_context, result=None, field_odds_avg=field_odds_avg
            )
            
            return features
            
        except Exception as e:
            import traceback
            print(f"Error generating features for runner {runner.get('horse_name')}: {e}")
            print(f"Runner data: ofr={runner.get('ofr')}, rpr={runner.get('rpr')}, ts={runner.get('ts')}, lbs={runner.get('lbs')}")
            print(f"Traceback: {traceback.format_exc()}")
            return None
    
    def _prepare_feature_matrix(self, features_list: List[Dict]) -> np.ndarray:
        """Convert feature dictionaries to numpy array matching model's expected features"""
        X = np.zeros((len(features_list), len(self.feature_columns)))
        
        for i, features in enumerate(features_list):
            for j, col in enumerate(self.feature_columns):
                value = features.get(col, 0)
                # Handle None values
                if value is None:
                    value = 0
                # Convert to float
                try:
                    X[i, j] = float(value)
                except (ValueError, TypeError):
                    X[i, j] = 0
        
        return X
    
    def _scores_to_probabilities(self, scores: np.ndarray) -> np.ndarray:
        """
        Convert ranking scores to probabilities using softmax
        
        Ranking model outputs relative scores (higher = better).
        Softmax converts these to valid probabilities that sum to 1.0.
        
        This is the mathematically correct way to get probabilities from
        a ranking model - no manual normalization needed!
        
        Args:
            scores: Ranking scores from model (higher = better)
            
        Returns:
            Probabilities that sum to 1.0
        """
        # Softmax: exp(score) / sum(exp(scores))
        # Subtract max for numerical stability (prevents overflow)
        exp_scores = np.exp(scores - np.max(scores))
        probabilities = exp_scores / exp_scores.sum()
        
        return probabilities
    
    def _calculate_ranks(self, probabilities: np.ndarray) -> np.ndarray:
        """Calculate predicted ranks from probabilities (1 = highest prob)"""
        # argsort twice: first gets sorting indices, second gets ranks
        # Example: probs=[0.05, 0.204, 0.115] -> ranks=[3, 1, 2]
        return np.argsort(np.argsort(-probabilities)) + 1
    
    def _calculate_confidence(self, probabilities: np.ndarray) -> str:
        """
        Calculate overall confidence level for predictions
        High confidence = clear favorite (top prob >> others)
        Low confidence = many similar probabilities
        """
        sorted_probs = np.sort(probabilities)[::-1]
        
        if len(sorted_probs) < 2:
            return "Medium"
        
        # Difference between top and second
        gap = sorted_probs[0] - sorted_probs[1]
        
        if gap > 0.15:
            return "High"
        elif gap > 0.08:
            return "Medium"
        else:
            return "Low"
    
    def _get_feature_contributions(self, features: Dict, probability: float, top_n: int = 3) -> List[Dict]:
        """
        Get top N features contributing to prediction
        Uses feature importance * feature value as contribution score
        """
        contributions = []
        
        for feature, value in features.items():
            if feature in self.feature_importance and feature in self.feature_columns:
                # Skip if value is None or 0
                if value is None or value == 0:
                    continue
                
                # Convert value to float, skip if conversion fails (e.g., '-' placeholders)
                try:
                    float_value = float(value)
                except (ValueError, TypeError):
                    continue
                
                if float_value == 0:
                    continue
                
                importance = self.feature_importance[feature]
                # Contribution = importance * normalized value
                contribution = importance * float_value
                contributions.append({
                    'feature': feature,
                    'value': float_value,
                    'contribution': contribution
                })
        
        # Sort by absolute contribution
        contributions.sort(key=lambda x: abs(x['contribution']), reverse=True)
        
        return contributions[:top_n]
    
    def _check_value_bet(self, predicted_prob: float, ofr: Optional[float]) -> Optional[str]:
        """
        Check if this is a value bet based on predicted probability
        
        Args:
            predicted_prob: Model's predicted win probability (normalized within race)
            ofr: Official rating or odds (if available)
            
        Returns:
            "Value Bet!" if predicted prob significantly exceeds implied prob from odds
        """
        # Thresholds adjusted for normalized probabilities
        # In a typical race with 10-15 runners, average probability is 7-10%
        # Strong picks should be significantly above average
        if predicted_prob > 0.20:  # >20% = very strong favorite
            return "⭐ Strong Pick"
        elif predicted_prob > 0.12:  # >12% = above average confidence
            return "✓ Good Chance"
        else:
            return None
    
    def close(self):
        """Close database connections"""
        if self.feature_engineer:
            self.feature_engineer.close()

