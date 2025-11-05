#!/usr/bin/env python3
"""
Train Model 2: BTN (Beaten Lengths) Regression
XGBoost regressor predicting continuous BTN values
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


class BTNModelTrainer:
    """Train BTN regression model"""
    
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
    
    def load_data(self, test_size: float = 0.2) -> Tuple:
        """
        Load features and BTN targets, split by date (temporal split)
        
        Returns:
            X_train, X_test, y_train, y_test, train_df, test_df
        """
        logger.info("Loading data from database...")
        
        if self.FEATURE_COLS is None:
            self.FEATURE_COLS = self.get_available_features()
        
        # Load features with BTN target from results
        query = """
            SELECT 
                f.race_id,
                f.runner_id,
                r.date,
                r.type,
                res.position_int as position,
                res.position_int = 1 as won,
                CAST(res.ovr_btn AS REAL) as btn,
                {features}
            FROM ml_features f
            JOIN races r ON f.race_id = r.race_id
            JOIN results res ON f.race_id = res.race_id AND f.horse_id = res.horse_id
            WHERE r.type = ?
            AND res.position_int < 900
            AND res.ovr_btn IS NOT NULL
            ORDER BY r.date, f.race_id, f.runner_id
        """.format(features=', '.join([f'f.{col}' for col in self.FEATURE_COLS]))
        
        df = pd.read_sql_query(query, self.conn, params=(self.race_type,))
        
        logger.info(f"\n✅ Loaded {len(df):,} samples from {df['race_id'].nunique():,} races")
        logger.info(f"Date range: {df['date'].min()} to {df['date'].max()}")
        logger.info(f"Winners: {df['won'].sum():,} ({df['won'].mean()*100:.1f}%)")
        
        # BTN statistics
        logger.info(f"\nBTN target statistics:")
        logger.info(f"  Mean: {df['btn'].mean():.2f} lengths")
        logger.info(f"  Median: {df['btn'].median():.2f} lengths")
        logger.info(f"  Std: {df['btn'].std():.2f} lengths")
        logger.info(f"  Range: {df['btn'].min():.2f} to {df['btn'].max():.2f} lengths")
        
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
        
        # Extract features and BTN targets
        X_train = train_df[self.FEATURE_COLS].copy()
        X_test = test_df[self.FEATURE_COLS].copy()
        y_train = train_df['btn'].copy()
        y_test = test_df['btn'].copy()
        
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
        Train XGBoost REGRESSOR for BTN prediction
        
        Target: BTN (beaten lengths) - continuous value
        0 = winner, higher = further behind
        """
        logger.info("\n" + "="*60)
        logger.info("TRAINING XGBOOST BTN REGRESSION MODEL")
        logger.info("="*60)
        
        # Create DMatrix
        dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=self.FEATURE_COLS)
        dtest = xgb.DMatrix(X_test, label=y_test, feature_names=self.FEATURE_COLS)
        
        # Regression parameters (NOT ranking)
        params = {
            'objective': 'reg:squarederror',  # Regression objective
            'eval_metric': 'rmse',  # Root Mean Squared Error
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
        logger.info(f"  Best RMSE: {best_score:.4f}")
        
        return model
    
    def evaluate(self, model: xgb.Booster, X_test: pd.DataFrame, 
                y_test: pd.Series, test_df: pd.DataFrame) -> Dict:
        """
        Evaluate BTN regression model
        
        Metrics:
        - Regression: RMSE, MAE, R²
        - Ranking: Convert BTN to ranks and check top pick accuracy
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
        
        logger.info(f"  RMSE: {rmse:.4f} lengths")
        logger.info(f"  MAE: {mae:.4f} lengths")
        logger.info(f"  R²: {r2:.4f}")
        
        # === RANKING QUALITY ===
        # Convert predictions to rankings and check accuracy
        logger.info("\n🏆 RANKING QUALITY (from BTN predictions)")
        
        test_df_copy = test_df.copy()
        test_df_copy['predicted_btn'] = y_pred
        test_df_copy['actual_btn'] = y_test
        
        # Rank by predicted BTN (smallest = winner)
        test_df_copy['pred_rank'] = test_df_copy.groupby('race_id')['predicted_btn'].rank(method='first')
        
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
        model_path = output_dir / 'xgboost_flat_btn.json'
        model.save_model(str(model_path))
        logger.info(f"\n✓ Model saved to {model_path}")
        
        # Save feature columns
        features_path = output_dir / 'feature_columns_flat.json'
        with open(features_path, 'w') as f:
            json.dump(self.FEATURE_COLS, f, indent=2)
        logger.info(f"✓ Feature columns saved to {features_path}")
        
        # Save feature importance
        importance_path = output_dir / 'feature_importance_btn.csv'
        metrics['feature_importance'].to_csv(importance_path, index=False)
        logger.info(f"✓ Feature importance saved to {importance_path}")
        
        # Save metrics
        metrics_path = output_dir / 'btn_model_metrics.json'
        metrics_to_save = {
            'rmse': metrics['rmse'],
            'mae': metrics['mae'],
            'r2': metrics['r2'],
            'top_pick_accuracy': metrics['top_pick_accuracy'],
            'top_3_hit_rate': metrics['top_3_hit_rate'],
            'mrr': metrics['mrr'],
            'model_type': 'btn_regression',
            'target': 'beaten_lengths',
            'trained_at': datetime.now().isoformat()
        }
        with open(metrics_path, 'w') as f:
            json.dump(metrics_to_save, f, indent=2)
        logger.info(f"✓ Metrics saved to {metrics_path}")


def main():
    """Run BTN model training"""
    # Paths
    db_path = Path(__file__).parent.parent / 'racing_pro.db'
    output_dir = Path(__file__).parent / 'models'
    
    # Initialize trainer
    trainer = BTNModelTrainer(db_path, race_type='Flat')
    
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
        logger.info("✅ MODEL 2 (BTN REGRESSION) TRAINING COMPLETE")
        logger.info("="*60)
        logger.info(f"RMSE: {metrics['rmse']:.4f} lengths")
        logger.info(f"Top Pick Accuracy: {metrics['top_pick_accuracy']:.1f}%")
        logger.info(f"Model saved to: {output_dir / 'xgboost_flat_btn.json'}")
        
    finally:
        trainer.close()


if __name__ == '__main__':
    main()

