#!/usr/bin/env python3
"""
Train Model 4: Relative Speed Regression
XGBoost regressor predicting speed deficit from winner (0=winner, negative=slower)
"""

import sqlite3
import numpy as np
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime
from typing import Tuple, Dict, List
import json
import xgboost as xgb

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RelativeSpeedModelTrainer:
    """Train relative speed regression model"""
    
    def __init__(self, db_path: Path, race_type: str = 'Flat'):
        self.db_path = db_path
        self.race_type = race_type
        self.conn = None
        self.model = None
        self.FEATURE_COLS = None
        
    def connect(self):
        """Connect to database"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        
    def close(self):
        """Close connection"""
        if self.conn:
            self.conn.close()
    
    def get_available_features(self) -> List[str]:
        """Get available feature columns from ml_features table"""
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(ml_features)")
        columns = cursor.fetchall()
        
        skip_cols = ['feature_id', 'race_id', 'runner_id', 'horse_id', 'created_at', 'race_class']
        
        feature_cols = []
        for col in columns:
            col_name = col['name']
            col_type = col['type']
            if col_name not in skip_cols and col_type in ['REAL', 'INTEGER']:
                feature_cols.append(col_name)
        
        logger.info(f"Found {len(feature_cols)} feature columns in database")
        return feature_cols
    
    def _parse_time_to_seconds(self, time_str: str) -> float:
        """Convert 'minutes:seconds.centiseconds' to total seconds"""
        if not time_str:
            return None
        try:
            parts = str(time_str).split(':')
            if len(parts) != 2:
                return None
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        except (ValueError, TypeError, AttributeError):
            return None
    
    def load_data(self, test_size: float = 0.2) -> Tuple:
        """
        Load features and compute speed deficit target
        Speed deficit = horse_speed - winner_speed (0 for winner, negative for others)
        
        Returns:
            X_train, X_test, y_train, y_test, train_df, test_df
        """
        logger.info("Loading data from database...")
        
        if self.FEATURE_COLS is None:
            self.FEATURE_COLS = self.get_available_features()
        
        # Load features with time and distance
        # Alias r.distance_f as race_distance_f to avoid collision with f.distance_f
        query = """
            SELECT 
                f.race_id,
                f.runner_id,
                r.date,
                r.type,
                r.distance_f as race_distance_f,
                res.position_int as position,
                res.position_int = 1 as won,
                res.time,
                {features}
            FROM ml_features f
            JOIN races r ON f.race_id = r.race_id
            JOIN results res ON f.race_id = res.race_id AND f.horse_id = res.horse_id
            WHERE r.type = ?
            AND res.position_int < 900
            AND res.time IS NOT NULL
            AND r.distance_f IS NOT NULL
            ORDER BY r.date, f.race_id, f.runner_id
        """.format(features=', '.join([f'f.{col}' for col in self.FEATURE_COLS]))
        
        df = pd.read_sql_query(query, self.conn, params=(self.race_type,))
        
        logger.info(f"\n✅ Loaded {len(df):,} samples from {df['race_id'].nunique():,} races")
        logger.info(f"Date range: {df['date'].min()} to {df['date'].max()}")
        
        # Compute speed
        logger.info("\nComputing speed and speed deficit targets...")
        df['time_seconds'] = df['time'].apply(self._parse_time_to_seconds)
        # Convert to numeric
        df['race_distance_f'] = pd.to_numeric(df['race_distance_f'], errors='coerce')
        df['time_seconds'] = pd.to_numeric(df['time_seconds'], errors='coerce')
        df['speed'] = df['race_distance_f'] / df['time_seconds']
        
        # Remove rows with invalid speed
        initial_count = len(df)
        df = df.dropna(subset=['speed'])
        df = df[df['speed'] > 0]
        removed_count = initial_count - len(df)
        if removed_count > 0:
            logger.info(f"  Removed {removed_count} rows with invalid speed")
        
        # Compute speed_deficit per race (horse_speed - winner_speed)
        def compute_deficit(group):
            """Compute speed deficit within a race"""
            winner_speed = group[group['position'] == 1]['speed'].values
            if len(winner_speed) == 0:
                # No winner found, skip this race
                return None
            winner_speed = winner_speed[0]
            group['speed_deficit'] = group['speed'] - winner_speed
            return group
        
        df = df.groupby('race_id', group_keys=False).apply(compute_deficit)
        df = df.dropna(subset=['speed_deficit'])
        
        logger.info(f"  Final dataset: {len(df):,} samples")
        
        # Speed deficit statistics
        logger.info(f"\nSpeed deficit target statistics:")
        logger.info(f"  Mean: {df['speed_deficit'].mean():.6f} f/s")
        logger.info(f"  Median: {df['speed_deficit'].median():.6f} f/s")
        logger.info(f"  Std: {df['speed_deficit'].std():.6f} f/s")
        logger.info(f"  Range: {df['speed_deficit'].min():.6f} to {df['speed_deficit'].max():.6f} f/s")
        logger.info(f"  Winners (deficit=0): {(df['speed_deficit'] == 0).sum():,}")
        
        # Temporal split
        split_idx = int(len(df) * (1 - test_size))
        train_df = df.iloc[:split_idx].copy()
        test_df = df.iloc[split_idx:].copy()
        
        split_date = train_df['date'].max()
        logger.info(f"\nTrain/test split at date: {split_date}")
        logger.info(f"  Train: {len(train_df):,} samples in {train_df['race_id'].nunique():,} races")
        logger.info(f"    Date range: {train_df['date'].min()} to {train_df['date'].max()}")
        logger.info(f"  Test: {len(test_df):,} samples in {test_df['race_id'].nunique():,} races")
        logger.info(f"    Date range: {test_df['date'].min()} to {test_df['date'].max()}")
        
        # Extract features and speed_deficit targets
        X_train = train_df[self.FEATURE_COLS].copy()
        X_test = test_df[self.FEATURE_COLS].copy()
        y_train = train_df['speed_deficit'].copy()
        y_test = test_df['speed_deficit'].copy()
        
        # Handle missing values
        logger.info("\nHandling missing values...")
        for col in self.FEATURE_COLS:
            X_train[col] = pd.to_numeric(X_train[col], errors='coerce')
            X_test[col] = pd.to_numeric(X_test[col], errors='coerce')
            median_val = X_train[col].median()
            if pd.isna(median_val):
                median_val = 0
            X_train[col] = X_train[col].fillna(median_val)
            X_test[col] = X_test[col].fillna(median_val)
        
        return X_train, X_test, y_train, y_test, train_df, test_df
    
    def train_xgboost_regressor(self, X_train: pd.DataFrame, y_train: pd.Series,
                                X_test: pd.DataFrame, y_test: pd.Series) -> xgb.Booster:
        """
        Train XGBoost REGRESSOR for speed deficit prediction
        
        Target: Speed deficit (horse_speed - winner_speed)
        0 = winner, negative = slower
        """
        logger.info("\n" + "="*60)
        logger.info("TRAINING XGBOOST RELATIVE SPEED REGRESSION MODEL")
        logger.info("="*60)
        
        # Create DMatrix
        dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=self.FEATURE_COLS)
        dtest = xgb.DMatrix(X_test, label=y_test, feature_names=self.FEATURE_COLS)
        
        # Regression parameters
        params = {
            'objective': 'reg:squarederror',
            'eval_metric': 'rmse',
            'max_depth': 6,
            'learning_rate': 0.1,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'min_child_weight': 1,
            'gamma': 0,
            'reg_alpha': 0,
            'reg_lambda': 1,
            'seed': 42,
            'tree_method': 'hist',
            'device': 'cpu'
        }
        
        logger.info("\nModel parameters:")
        for k, v in params.items():
            logger.info(f"  {k}: {v}")
        
        # Train with early stopping
        evals = [(dtrain, 'train'), (dtest, 'test')]
        evals_result = {}
        
        logger.info("\nTraining model...")
        model = xgb.train(
            params,
            dtrain,
            num_boost_round=500,
            evals=evals,
            early_stopping_rounds=50,
            verbose_eval=50,
            evals_result=evals_result
        )
        
        best_iteration = model.best_iteration
        best_score = model.best_score
        
        logger.info(f"\n✓ Training complete!")
        logger.info(f"  Best iteration: {best_iteration}")
        logger.info(f"  Best RMSE: {best_score:.6f}")
        
        return model
    
    def evaluate(self, model: xgb.Booster, X_test: pd.DataFrame, 
                y_test: pd.Series, test_df: pd.DataFrame) -> Dict:
        """
        Evaluate relative speed regression model
        
        Metrics:
        - Regression: RMSE, MAE, R²
        - Ranking: Convert deficit to ranks and check top pick accuracy
        """
        logger.info("\n" + "="*60)
        logger.info("MODEL EVALUATION")
        logger.info("="*60)
        
        # Generate predictions
        dtest = xgb.DMatrix(X_test, feature_names=self.FEATURE_COLS)
        y_pred = model.predict(dtest)
        
        # === REGRESSION METRICS ===
        logger.info("\n📊 REGRESSION METRICS")
        
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
        
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        logger.info(f"  RMSE: {rmse:.6f} f/s")
        logger.info(f"  MAE: {mae:.6f} f/s")
        logger.info(f"  R²: {r2:.4f}")
        
        # === RANKING QUALITY ===
        logger.info("\n🏆 RANKING QUALITY (from speed deficit predictions)")
        
        test_df_copy = test_df.copy()
        test_df_copy['predicted_deficit'] = y_pred
        test_df_copy['actual_deficit'] = y_test
        
        # Rank by predicted deficit (closest to 0 = winner)
        # We rank by absolute value, then prefer values closest to 0
        test_df_copy['pred_rank'] = test_df_copy.groupby('race_id')['predicted_deficit'].rank(
            method='first', ascending=False
        )
        
        # Check if actual winners are predicted as winners
        actual_winners = test_df_copy[test_df_copy['position'] == 1]
        top_picks = test_df_copy[test_df_copy['pred_rank'] == 1]
        
        top_pick_accuracy = (top_picks['won'].sum() / len(top_picks)) * 100
        logger.info(f"  Top Pick Win Rate: {top_pick_accuracy:.1f}%")
        
        # Top 3 accuracy
        test_df_copy['in_top_3'] = test_df_copy['pred_rank'] <= 3
        actual_winners_df = test_df_copy[test_df_copy['position'] == 1]
        top_3_hit_rate = (actual_winners_df['in_top_3'].sum() / len(actual_winners_df)) * 100
        logger.info(f"  Top 3 Hit Rate: {top_3_hit_rate:.1f}%")
        
        # Mean Reciprocal Rank
        mrr = (1.0 / actual_winners_df['pred_rank']).mean()
        logger.info(f"  Mean Reciprocal Rank: {mrr:.4f}")
        
        # === FEATURE IMPORTANCE ===
        logger.info("\n📈 TOP 15 MOST IMPORTANT FEATURES")
        
        importance_dict = model.get_score(importance_type='gain')
        importance_df = pd.DataFrame([
            {'feature': k, 'importance': v}
            for k, v in importance_dict.items()
        ]).sort_values('importance', ascending=False)
        
        for idx, row in importance_df.head(15).iterrows():
            logger.info(f"  {row['feature']}: {row['importance']:.1f}")
        
        return {
            'rmse': rmse,
            'mae': mae,
            'r2': r2,
            'top_pick_accuracy': top_pick_accuracy,
            'top_3_hit_rate': top_3_hit_rate,
            'mrr': mrr,
            'feature_importance': importance_df
        }
    
    def save_model(self, model: xgb.Booster, metrics: Dict, output_dir: Path):
        """Save model and metadata"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save model
        model_path = output_dir / 'xgboost_flat_speed_rel.json'
        model.save_model(str(model_path))
        logger.info(f"\n✓ Model saved to {model_path}")
        
        # Save feature columns (reuse existing)
        features_path = output_dir / 'feature_columns_flat.json'
        with open(features_path, 'w') as f:
            json.dump(self.FEATURE_COLS, f, indent=2)
        logger.info(f"✓ Feature columns saved to {features_path}")
        
        # Save feature importance
        importance_path = output_dir / 'feature_importance_speed_rel.csv'
        metrics['feature_importance'].to_csv(importance_path, index=False)
        logger.info(f"✓ Feature importance saved to {importance_path}")
        
        # Save metrics
        metrics_path = output_dir / 'speed_rel_model_metrics.json'
        metrics_to_save = {
            'rmse': metrics['rmse'],
            'mae': metrics['mae'],
            'r2': metrics['r2'],
            'top_pick_accuracy': metrics['top_pick_accuracy'],
            'top_3_hit_rate': metrics['top_3_hit_rate'],
            'mrr': metrics['mrr'],
            'model_type': 'speed_relative_regression',
            'target': 'speed_deficit_from_winner',
            'trained_at': datetime.now().isoformat()
        }
        with open(metrics_path, 'w') as f:
            json.dump(metrics_to_save, f, indent=2)
        logger.info(f"✓ Metrics saved to {metrics_path}")


def main():
    """Run relative speed model training"""
    # Paths
    db_path = Path(__file__).parent.parent / 'racing_pro.db'
    output_dir = Path(__file__).parent / 'models'
    
    # Initialize trainer
    trainer = RelativeSpeedModelTrainer(db_path, race_type='Flat')
    
    try:
        # Connect and load data
        trainer.connect()
        X_train, X_test, y_train, y_test, train_df, test_df = trainer.load_data(test_size=0.2)
        
        # Train model
        model = trainer.train_xgboost_regressor(X_train, y_train, X_test, y_test)
        
        # Evaluate
        metrics = trainer.evaluate(model, X_test, y_test, test_df)
        
        # Save
        trainer.save_model(model, metrics, output_dir)
        
        logger.info("\n" + "="*60)
        logger.info("✅ MODEL 4 (RELATIVE SPEED REGRESSION) TRAINING COMPLETE")
        logger.info("="*60)
        logger.info(f"RMSE: {metrics['rmse']:.6f} f/s")
        logger.info(f"Top Pick Accuracy: {metrics['top_pick_accuracy']:.1f}%")
        logger.info(f"Model saved to: {output_dir / 'xgboost_flat_speed_rel.json'}")
        
    finally:
        trainer.close()


if __name__ == '__main__':
    main()

