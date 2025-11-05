#!/usr/bin/env python3
"""
Test probability distributions on upcoming/unresolved races
This tests whether models produce "flat" probabilities on truly unseen data
"""

import sqlite3
import pandas as pd
import numpy as np
import xgboost as xgb
import json
import logging
from pathlib import Path
from typing import Dict, Tuple
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class UpcomingRacesTester:
    def __init__(self, db_path: Path = None, models_dir: Path = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / 'racing_pro.db'
        if models_dir is None:
            models_dir = Path(__file__).parent / 'models'
        self.db_path = Path(db_path)
        self.models_dir = Path(models_dir)
        self.models = {}
        self.feature_columns = []
        self.temperature = 1.0
        
    def load_models(self):
        """Load all models and feature columns"""
        # Load feature columns
        feature_path = self.models_dir / "feature_columns_flat.json"
        with open(feature_path) as f:
            self.feature_columns = json.load(f)
        logger.info(f"✓ Loaded {len(self.feature_columns)} feature columns")
        
        # Load baseline ranking model
        baseline_path = self.models_dir / "xgboost_flat.json"
        if baseline_path.exists():
            baseline_model = xgb.Booster()
            baseline_model.load_model(str(baseline_path))
            self.models['baseline'] = {'model': baseline_model, 'type': 'ranking'}
            logger.info("✓ Loaded baseline model")
        
        # Load BTN model
        btn_path = self.models_dir / "xgboost_flat_btn.json"
        if btn_path.exists():
            btn_model = xgb.Booster()
            btn_model.load_model(str(btn_path))
            self.models['btn'] = {'model': btn_model, 'type': 'btn'}
            logger.info("✓ Loaded BTN model")
        
        # Load absolute speed model
        speed_abs_path = self.models_dir / "xgboost_flat_speed_abs.json"
        if speed_abs_path.exists():
            speed_abs_model = xgb.Booster()
            speed_abs_model.load_model(str(speed_abs_path))
            self.models['speed_abs'] = {'model': speed_abs_model, 'type': 'speed_abs'}
            logger.info("✓ Loaded speed_abs model")
        
        # Load relative speed model
        speed_rel_path = self.models_dir / "xgboost_flat_speed_rel.json"
        if speed_rel_path.exists():
            speed_rel_model = xgb.Booster()
            speed_rel_model.load_model(str(speed_rel_path))
            self.models['speed_rel'] = {'model': speed_rel_model, 'type': 'speed_rel'}
            logger.info("✓ Loaded speed_rel model")
        
        # Load temperature
        temp_path = self.models_dir / "optimal_temperature.json"
        if temp_path.exists():
            with open(temp_path) as f:
                temp_config = json.load(f)
                self.temperature = temp_config.get('optimal_temperature', 1.0)
        logger.info(f"✓ Temperature: {self.temperature}")
    
    def load_upcoming_races(self) -> pd.DataFrame:
        """Load most recent races (validation set - unseen by models during training)"""
        logger.info("Loading validation set (most recent races not used in training)...")
        
        conn = sqlite3.connect(str(self.db_path))
        
        # Get all races with features and results, then take validation split (last 20%)
        query = """
            SELECT 
                f.race_id,
                f.runner_id,
                r.date,
                r.course,
                r.off_time as race_time,
                r.distance_f as race_distance,
                res.position_int as actual_position,
                res.position_int = 1 as won,
                {features}
            FROM ml_features f
            JOIN races r ON f.race_id = r.race_id
            JOIN results res ON f.race_id = res.race_id AND f.horse_id = res.horse_id
            WHERE r.type = 'Flat'
            AND res.position_int < 900
            ORDER BY r.date, f.race_id, f.runner_id
        """.format(features=', '.join([f'f.{col}' for col in self.feature_columns]))
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Take validation split (last 20% chronologically)
        total_races = df['race_id'].nunique()
        unique_races = df[['race_id', 'date']].drop_duplicates().sort_values('date')
        val_split_idx = int(len(unique_races) * 0.8)
        val_race_ids = unique_races.iloc[val_split_idx:]['race_id'].values
        
        df = df[df['race_id'].isin(val_race_ids)].copy()
        
        logger.info(f"✓ Loaded {len(df)} runners from {df['race_id'].nunique()} validation races")
        logger.info(f"  Date range: {df['date'].min()} to {df['date'].max()}")
        logger.info(f"  (These races were not used for training)")
        
        # Handle missing values and convert all feature columns to numeric
        feature_cols_to_process = [col for col in self.feature_columns if col in df.columns]
        for col in feature_cols_to_process:
            # Convert to numeric regardless of current dtype
            df[col] = pd.to_numeric(df[col], errors='coerce')
            median_val = df[col].median()
            if pd.isna(median_val):
                median_val = 0
            df[col] = df[col].fillna(median_val)
        
        return df
    
    def predict_probabilities(self, model_name: str, df: pd.DataFrame) -> pd.DataFrame:
        """Generate predictions for a specific model"""
        model_config = self.models[model_name]
        model = model_config['model']
        model_type = model_config['type']
        
        # Get predictions
        available_features = [col for col in self.feature_columns if col in df.columns]
        X = df[available_features]
        dmatrix = xgb.DMatrix(X, feature_names=available_features)
        raw_scores = model.predict(dmatrix)
        
        # Convert to probabilities based on model type
        df_copy = df.copy()
        df_copy['raw_score'] = raw_scores
        
        # Group by race and convert to probabilities
        def scores_to_probs(scores):
            scores = scores.values
            
            if model_type == 'ranking':
                # Standard softmax with temperature
                scores_temp = scores / self.temperature
                exp_scores = np.exp(scores_temp - np.max(scores_temp))
                probs = exp_scores / exp_scores.sum()
            elif model_type == 'btn':
                # Negative BTN -> higher is better (smaller BTN)
                exp_scores = np.exp(-scores)
                probs = exp_scores / exp_scores.sum()
            elif model_type in ['speed_abs', 'speed_rel']:
                # Higher speed is better
                exp_scores = np.exp(scores - np.max(scores))
                probs = exp_scores / exp_scores.sum()
            else:
                raise ValueError(f"Unknown model type: {model_type}")
            
            return probs
        
        df_copy['probability'] = df_copy.groupby('race_id')['raw_score'].transform(scores_to_probs)
        
        return df_copy[['race_id', 'runner_id', 'date', 'course', 'race_time', 'probability']]
    
    def analyze_distributions(self, predictions: Dict[str, pd.DataFrame]):
        """Analyze and compare probability distributions"""
        logger.info("\n" + "="*80)
        logger.info("PROBABILITY DISTRIBUTION ANALYSIS - VALIDATION SET")
        logger.info("(Most recent races not used in training)")
        logger.info("="*80)
        
        stats = []
        
        for model_name, pred_df in predictions.items():
            probs = pred_df['probability'].values
            
            # Calculate statistics
            stat = {
                'model': model_name,
                'mean': np.mean(probs),
                'std': np.std(probs),
                'min': np.min(probs),
                'max': np.max(probs),
                'q25': np.percentile(probs, 25),
                'q50': np.percentile(probs, 50),
                'q75': np.percentile(probs, 75),
                'q95': np.percentile(probs, 95),
                'cv': np.std(probs) / np.mean(probs),  # Coefficient of variation
            }
            stats.append(stat)
            
            logger.info(f"\n{model_name.upper()}:")
            logger.info(f"  Mean: {stat['mean']:.4f}")
            logger.info(f"  Std Dev: {stat['std']:.4f}")
            logger.info(f"  CV (Std/Mean): {stat['cv']:.4f} {'⚠️ LOW DISCRIMINATION' if stat['cv'] < 0.3 else '✓ Good'}")
            logger.info(f"  Range: {stat['min']:.4f} to {stat['max']:.4f}")
            logger.info(f"  25th-75th percentile: {stat['q25']:.4f} to {stat['q75']:.4f}")
            logger.info(f"  95th percentile: {stat['q95']:.4f}")
        
        return pd.DataFrame(stats)
    
    def visualize_distributions(self, predictions: Dict[str, pd.DataFrame], output_path: Path):
        """Create visualization comparing distributions"""
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        fig.suptitle('Probability Distributions on Validation Set\n(Most Recent Races - Unseen During Training)', 
                     fontsize=16, fontweight='bold')
        
        axes = axes.flatten()
        
        for idx, (model_name, pred_df) in enumerate(predictions.items()):
            ax = axes[idx]
            probs = pred_df['probability'].values
            
            # Histogram
            ax.hist(probs, bins=50, alpha=0.7, edgecolor='black')
            
            # Add statistics
            mean_val = np.mean(probs)
            std_val = np.std(probs)
            cv_val = std_val / mean_val
            
            ax.axvline(mean_val, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_val:.3f}')
            ax.set_title(f'{model_name.upper()}\nStd: {std_val:.4f}, CV: {cv_val:.3f}', 
                        fontweight='bold')
            ax.set_xlabel('Win Probability')
            ax.set_ylabel('Frequency')
            ax.legend()
            ax.grid(alpha=0.3)
        
        # Hide extra subplot
        axes[5].axis('off')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        logger.info(f"\n✓ Saved visualization to {output_path}")
    
    def print_example_races(self, predictions: Dict[str, pd.DataFrame], num_races: int = 3):
        """Print example predictions for a few races"""
        logger.info("\n" + "="*80)
        logger.info(f"EXAMPLE PREDICTIONS (First {num_races} races)")
        logger.info("="*80)
        
        # Get first N races
        first_race_ids = predictions['baseline']['race_id'].unique()[:num_races]
        
        for race_idx, race_id in enumerate(first_race_ids, 1):
            logger.info(f"\n{'='*60}")
            
            # Get race info
            first_model = list(predictions.keys())[0]
            race_info = predictions[first_model][predictions[first_model]['race_id'] == race_id].iloc[0]
            logger.info(f"RACE {race_idx}: {race_info['course']} - {race_info['date']} {race_info['race_time']}")
            logger.info(f"{'='*60}")
            
            # Create comparison table
            comparison_data = []
            
            for model_name, pred_df in predictions.items():
                race_preds = pred_df[pred_df['race_id'] == race_id].copy()
                race_preds = race_preds.sort_values('probability', ascending=False)
                
                # Get top 3
                top_3 = race_preds.head(3)['probability'].values
                comparison_data.append({
                    'Model': model_name,
                    '1st': f"{top_3[0]*100:.1f}%" if len(top_3) > 0 else "N/A",
                    '2nd': f"{top_3[1]*100:.1f}%" if len(top_3) > 1 else "N/A",
                    '3rd': f"{top_3[2]*100:.1f}%" if len(top_3) > 2 else "N/A",
                    'Range': f"{race_preds['probability'].min()*100:.1f}%-{race_preds['probability'].max()*100:.1f}%"
                })
            
            comp_df = pd.DataFrame(comparison_data)
            logger.info("\n" + comp_df.to_string(index=False))


def main():
    tester = UpcomingRacesTester()
    
    # Load models
    tester.load_models()
    
    # Load upcoming races
    df = tester.load_upcoming_races()
    
    if len(df) == 0:
        logger.warning("No upcoming races found!")
        return
    
    # Generate predictions for all models
    predictions = {}
    for model_name in tester.models.keys():
        logger.info(f"\nGenerating predictions for {model_name}...")
        predictions[model_name] = tester.predict_probabilities(model_name, df)
    
    # Analyze distributions
    stats_df = tester.analyze_distributions(predictions)
    
    # Save statistics
    output_path = tester.models_dir / "upcoming_races_probability_stats.csv"
    stats_df.to_csv(output_path, index=False)
    logger.info(f"\n✓ Saved statistics to {output_path}")
    
    # Visualize
    viz_path = tester.models_dir / "upcoming_races_distributions.png"
    tester.visualize_distributions(predictions, viz_path)
    
    # Show example races
    tester.print_example_races(predictions, num_races=3)
    
    # Final recommendation
    logger.info("\n" + "="*80)
    logger.info("🎯 RECOMMENDATION")
    logger.info("="*80)
    
    # Find model with highest CV (coefficient of variation = discrimination)
    best_discrimination = stats_df.loc[stats_df['cv'].idxmax()]
    
    logger.info(f"\nBest discrimination on upcoming races: {best_discrimination['model'].upper()}")
    logger.info(f"  Coefficient of Variation: {best_discrimination['cv']:.4f}")
    logger.info(f"  Standard Deviation: {best_discrimination['std']:.4f}")
    logger.info(f"\nA higher CV means more discriminating probabilities (less 'flat')")
    logger.info(f"A CV < 0.3 typically indicates overly flat probabilities")


if __name__ == "__main__":
    main()

