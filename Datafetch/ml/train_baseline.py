#!/usr/bin/env python3
"""
Train Baseline ML Models
XGBoost classifier for winner prediction
"""

import sqlite3
import numpy as np
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime
from typing import Tuple, Dict, List
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BaselineTrainer:
    """Train and evaluate baseline models"""
    
    # Feature columns to use (will be populated from ml_features table)
    def __init__(self, db_path: Path, race_type: str = 'Flat'):
        self.db_path = db_path
        self.race_type = race_type
        self.conn = None
        self.model = None
        self.feature_importance = None
        self.FEATURE_COLS = None  # Will be loaded dynamically
        
    def connect(self):
        """Connect to database"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        
    def close(self):
        """Close connection"""
        if self.conn:
            self.conn.close()
    
    def get_available_features(self) -> List[str]:
        """
        Dynamically get available feature columns from ml_features table.
        Excludes ID columns, dates, and text columns.
        """
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(ml_features)")
        columns = cursor.fetchall()
        
        # Skip these columns
        skip_cols = ['feature_id', 'race_id', 'runner_id', 'horse_id', 'created_at', 'race_class']
        
        feature_cols = []
        for col in columns:
            col_name = col['name']
            col_type = col['type']
            # Include numeric columns only
            if col_name not in skip_cols and col_type in ['REAL', 'INTEGER']:
                feature_cols.append(col_name)
        
        logger.info(f"Found {len(feature_cols)} feature columns in database")
        return feature_cols
    
    def load_data(self, test_size: float = 0.2) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.DataFrame, pd.DataFrame]:
        """
        Load features and targets, split by date (temporal split)
        For ranking model: also return race_id for grouping
        
        Returns:
            X_train, X_test, y_train, y_test, train_df, test_df
        """
        logger.info("Loading data from database...")
        
        # Get available features dynamically
        if self.FEATURE_COLS is None:
            self.FEATURE_COLS = self.get_available_features()
        
        # Show race type breakdown before filtering
        logger.info("\n" + "="*60)
        logger.info("Race counts by type in database:")
        cursor = self.conn.cursor()
        cursor.execute("SELECT type, COUNT(*) as count FROM races GROUP BY type ORDER BY count DESC")
        all_counts = cursor.fetchall()
        for row in all_counts:
            logger.info(f"  {row['type']}: {row['count']:,} races")
        logger.info("="*60 + "\n")
        
        # Load features and targets joined together
        # For ranking: use position instead of binary won (lower position = better)
        # FILTER BY RACE TYPE (Flat only for focused training)
        query = """
            SELECT 
                f.race_id,
                f.runner_id,
                r.date,
                r.type,
                t.position as target,
                t.won,
                {}
            FROM ml_features f
            JOIN ml_targets t ON f.race_id = t.race_id AND f.runner_id = t.runner_id
            JOIN races r ON f.race_id = r.race_id
            WHERE r.type = ?
            ORDER BY r.date, f.race_id, t.position
        """.format(', '.join([f'f."{col}"' for col in self.FEATURE_COLS]))
        
        df = pd.read_sql_query(query, self.conn, params=(self.race_type,))
        
        logger.info(f"\n✅ Training on {self.race_type} races only")
        logger.info(f"Loaded {len(df):,} samples")
        logger.info(f"Date range: {df['date'].min()} to {df['date'].max()}")
        logger.info(f"Winners: {df['won'].sum():,} ({df['won'].mean()*100:.1f}%)")
        logger.info(f"Unique races: {df['race_id'].nunique():,}")
        
        # Temporal split (earlier dates for training, later for test)
        split_idx = int(len(df) * (1 - test_size))
        train_df = df.iloc[:split_idx]
        test_df = df.iloc[split_idx:]
        
        split_date = train_df['date'].max()
        logger.info(f"\nTrain/test split at date: {split_date}")
        logger.info(f"  Train: {len(train_df):,} samples in {train_df['race_id'].nunique():,} races")
        logger.info(f"    Date range: {train_df['date'].min()} to {train_df['date'].max()}")
        logger.info(f"  Test: {len(test_df):,} samples in {test_df['race_id'].nunique():,} races")
        logger.info(f"    Date range: {test_df['date'].min()} to {test_df['date'].max()}")
        
        # Extract features and targets
        X_train = train_df[self.FEATURE_COLS].copy()
        X_test = test_df[self.FEATURE_COLS].copy()
        
        # CRITICAL: Convert position to points for ranking objective
        # Ranking models expect HIGHER values = BETTER performance
        # Position 1 (winner) should have highest value, not lowest!
        # Points system: In each race, winner gets max_position points, last gets 1 point
        logger.info("\nConverting positions to points (higher = better)...")
        train_df['max_position'] = train_df.groupby('race_id')['target'].transform('max')
        test_df['max_position'] = test_df.groupby('race_id')['target'].transform('max')
        
        y_train = train_df['max_position'] - train_df['target'] + 1
        y_test = test_df['max_position'] - test_df['target'] + 1
        
        # Cap at 31 for XGBoost NDCG compatibility (required in some versions)
        y_train = y_train.clip(upper=31)
        y_test = y_test.clip(upper=31)
        
        # Example: 10-horse race
        #   Position 1 (winner): 10 - 1 + 1 = 10 points (highest)
        #   Position 5: 10 - 5 + 1 = 6 points
        #   Position 10 (last): 10 - 10 + 1 = 1 point (lowest)
        
        logger.info(f"  Position → Points conversion:")
        logger.info(f"  Winner (pos 1) → {y_train.max():.0f} points (max)")
        logger.info(f"  Last place → {y_train.min():.0f} point (min)")
        logger.info(f"  Mean points: {y_train.mean():.1f}")
        
        # Convert all features to numeric (coerce errors to NaN)
        logger.info("Converting features to numeric types...")
        for col in X_train.columns:
            X_train[col] = pd.to_numeric(X_train[col], errors='coerce')
            X_test[col] = pd.to_numeric(X_test[col], errors='coerce')
        
        # Handle missing values (fill with median for numeric)
        logger.info("Imputing missing values with median...")
        for col in X_train.columns:
            median_val = X_train[col].median()
            if pd.isna(median_val):
                median_val = 0  # If all values are NaN, use 0
            X_train[col] = X_train[col].fillna(median_val)
            X_test[col] = X_test[col].fillna(median_val)
        
        logger.info(f"\nFeature matrix shape: {X_train.shape}")
        logger.info(f"Features: {len(self.FEATURE_COLS)}")
        
        return X_train, X_test, y_train, y_test, train_df, test_df
    
    def train_xgboost(self, X_train: pd.DataFrame, y_train: pd.Series, 
                     train_df: pd.DataFrame,
                     X_val: pd.DataFrame = None, y_val: pd.Series = None,
                     test_df: pd.DataFrame = None) -> 'xgboost.Booster':
        """
        Train XGBoost RANKING model
        Critical change: uses rank:pairwise objective with race grouping
        """
        try:
            import xgboost as xgb
        except ImportError:
            logger.error("XGBoost not installed. Run: pip install xgboost")
            raise
        
        logger.info("\n" + "="*60)
        logger.info("TRAINING XGBOOST RANKING MODEL")
        logger.info("="*60)
        
        # === RACE GROUPING (CRITICAL FOR RANKING) ===
        # Group samples by race_id so model knows which horses compete together
        logger.info("\nPreparing race groups...")
        train_groups = train_df.groupby('race_id').size().values
        logger.info(f"  Training races: {len(train_groups)}")
        logger.info(f"  Avg runners per race: {train_groups.mean():.1f}")
        logger.info(f"  Min/Max runners: {train_groups.min()}/{train_groups.max()}")
        
        # Create DMatrix with group information
        dtrain = xgb.DMatrix(X_train, label=y_train)
        dtrain.set_group(train_groups)  # THIS IS THE KEY: tells model which samples are in same race
        
        # Validation set (if provided)
        if X_val is not None and y_val is not None and test_df is not None:
            test_groups = test_df.groupby('race_id').size().values
            dtest = xgb.DMatrix(X_val, label=y_val)
            dtest.set_group(test_groups)
            eval_list = [(dtrain, 'train'), (dtest, 'eval')]
            logger.info(f"  Test races: {len(test_groups)}")
        else:
            eval_list = [(dtrain, 'train')]
            dtest = None
        
        # === RANKING PARAMETERS ===
        params = {
            'objective': 'rank:pairwise',  # Pairwise ranking loss - learns which horse beats which
            'eval_metric': 'ndcg@3',       # Normalized Discounted Cumulative Gain for top 3
            'ndcg_exp_gain': False,        # Use linear DCG for large fields (>31 runners)
            'max_depth': 8,                 # Deeper trees for complex race interactions
            'learning_rate': 0.03,          # Lower learning rate for ranking
            'n_estimators': 300,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'tree_method': 'hist',          # Fast histogram-based method
            'random_state': 42,
            'nthread': -1
        }
        
        logger.info("\nModel parameters:")
        for key, val in params.items():
            logger.info(f"  {key}: {val}")
        
        # === TRAIN MODEL ===
        logger.info("\nTraining...")
        num_rounds = params.pop('n_estimators')
        
        model = xgb.train(
            params,
            dtrain,
            num_boost_round=num_rounds,
            evals=eval_list,
            early_stopping_rounds=20 if dtest else None,
            verbose_eval=50  # Print every 50 rounds
        )
        
        self.model = model
        
        # === FEATURE IMPORTANCE ===
        importance_dict = model.get_score(importance_type='gain')
        if importance_dict:
            self.feature_importance = pd.DataFrame({
                'feature': list(importance_dict.keys()),
                'importance': list(importance_dict.values())
            }).sort_values('importance', ascending=False)
            
            logger.info("\n" + "="*60)
            logger.info("TOP 15 MOST IMPORTANT FEATURES")
            logger.info("="*60)
            for i, row in self.feature_importance.head(15).iterrows():
                logger.info(f"  {i+1:2d}. {row['feature']:<35s} {row['importance']:>10.2f}")
        else:
            logger.warning("No feature importance scores available")
            self.feature_importance = pd.DataFrame()
        
        return model
    
    def evaluate(self, model, X_test: pd.DataFrame, y_test: pd.Series, 
                test_df: pd.DataFrame) -> Dict:
        """
        Evaluate RANKING model performance
        Uses ranking-specific metrics (NDCG, MRR, Spearman)
        """
        import xgboost as xgb
        from scipy.stats import spearmanr
        
        logger.info("\n" + "="*60)
        logger.info("RANKING MODEL EVALUATION")
        logger.info("="*60)
        
        # === PREDICT RANKING SCORES ===
        dtest = xgb.DMatrix(X_test)
        ranking_scores = model.predict(dtest)
        
        # Add scores to test dataframe
        test_df = test_df.copy()
        test_df['ranking_score'] = ranking_scores
        test_df['actual_position'] = test_df['target'].values  # Use original position, not points!
        
        # === RACING-SPECIFIC METRICS ===
        logger.info("\n🏇 RACING METRICS")
        
        # Top pick accuracy (highest score in each race = prediction winner)
        def get_race_metrics(race_df):
            # Sort by ranking score (higher = better)
            race_df = race_df.sort_values('ranking_score', ascending=False)
            race_df['pred_rank'] = range(1, len(race_df) + 1)
            
            # Top pick = predicted winner
            top_pick_wins = race_df.iloc[0]['actual_position'] == 1
            
            # Top 3 hit rate = is actual winner in predicted top 3?
            actual_winner = race_df[race_df['actual_position'] == 1]
            top_3_hit = len(actual_winner[actual_winner['pred_rank'] <= 3]) > 0 if len(actual_winner) > 0 else False
            
            # Spearman correlation between predicted and actual ranks
            spearman_corr = spearmanr(race_df['pred_rank'], race_df['actual_position'])[0] if len(race_df) > 2 else 0
            
            return {
                'top_pick_wins': top_pick_wins,
                'top_3_hit': top_3_hit,
                'spearman': spearman_corr
            }
        
        race_results = test_df.groupby('race_id').apply(get_race_metrics)
        
        top_pick_accuracy = sum(r['top_pick_wins'] for r in race_results) / len(race_results)
        top_3_hit_rate = sum(r['top_3_hit'] for r in race_results) / len(race_results)
        avg_spearman = np.mean([r['spearman'] for r in race_results if not np.isnan(r['spearman'])])
        
        logger.info(f"  Top Pick Win Rate: {top_pick_accuracy:.4f} ({top_pick_accuracy*100:.1f}%)")
        logger.info(f"  Top 3 Hit Rate: {top_3_hit_rate:.4f} ({top_3_hit_rate*100:.1f}%)")
        logger.info(f"  Avg Spearman Correlation: {avg_spearman:.4f}")
        
        # === RANKING QUALITY METRICS ===
        logger.info("\n📊 RANKING QUALITY METRICS")
        
        # Mean Reciprocal Rank (MRR) - average of 1/rank for actual winners
        def get_mrr(race_df):
            race_df = race_df.sort_values('ranking_score', ascending=False)
            race_df['pred_rank'] = range(1, len(race_df) + 1)
            winner = race_df[race_df['actual_position'] == 1]
            if len(winner) > 0:
                return 1.0 / winner.iloc[0]['pred_rank']
            return 0
        
        mrr = test_df.groupby('race_id').apply(get_mrr).mean()
        logger.info(f"  Mean Reciprocal Rank (MRR): {mrr:.4f}")
        
        # NDCG@K for different K values
        def dcg_at_k(race_df, k):
            """Discounted Cumulative Gain at K"""
            race_df = race_df.sort_values('ranking_score', ascending=False).head(k)
            # Relevance = 1 if winner, 0 otherwise
            race_df['relevance'] = (race_df['actual_position'] == 1).astype(int)
            dcg = sum(race_df['relevance'] / np.log2(np.arange(2, len(race_df) + 2)))
            return dcg
        
        def ndcg_at_k(race_df, k):
            """Normalized DCG at K"""
            actual_dcg = dcg_at_k(race_df, k)
            # Ideal DCG (winner at position 1)
            ideal_dcg = 1.0  # log2(2) = 1
            return actual_dcg / ideal_dcg if ideal_dcg > 0 else 0
        
        for k in [1, 3, 5]:
            ndcg_k = test_df.groupby('race_id').apply(lambda df: ndcg_at_k(df, k)).mean()
            logger.info(f"  NDCG@{k}: {ndcg_k:.4f}")
        
        # === POSITION DISTRIBUTION ===
        logger.info("\n📈 PREDICTED WINNER POSITION DISTRIBUTION")
        test_df_sorted = test_df.sort_values(['race_id', 'ranking_score'], ascending=[True, False])
        test_df_sorted['pred_rank'] = test_df_sorted.groupby('race_id').cumcount() + 1
        predicted_winners = test_df_sorted[test_df_sorted['pred_rank'] == 1]
        
        pos_dist = predicted_winners['actual_position'].value_counts().sort_index()
        for pos, count in pos_dist.head(10).items():
            pct = count / len(predicted_winners) * 100
            logger.info(f"  Position {int(pos)}: {count:4d} races ({pct:5.1f}%)")
        
        # === SUMMARY ===
        metrics = {
            'top_pick_accuracy': top_pick_accuracy,
            'top_3_hit_rate': top_3_hit_rate,
            'mean_reciprocal_rank': mrr,
            'avg_spearman': avg_spearman,
            'ndcg@1': test_df.groupby('race_id').apply(lambda df: ndcg_at_k(df, 1)).mean(),
            'ndcg@3': test_df.groupby('race_id').apply(lambda df: ndcg_at_k(df, 3)).mean(),
            'ndcg@5': test_df.groupby('race_id').apply(lambda df: ndcg_at_k(df, 5)).mean(),
            'num_test_races': len(race_results)
        }
        
        return metrics
    
    def save_model(self, output_dir: Path):
        """Save trained model and metadata with race type suffix"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate race-type-specific filenames
        race_type_lower = self.race_type.lower()
        
        # Save model
        model_path = output_dir / f'xgboost_{race_type_lower}.json'
        self.model.save_model(str(model_path))
        logger.info(f"\n✓ {self.race_type} model saved to {model_path}")
        
        # Save feature importance
        importance_path = output_dir / f'feature_importance_{race_type_lower}.csv'
        self.feature_importance.to_csv(importance_path, index=False)
        logger.info(f"✓ Feature importance saved to {importance_path}")
        
        # Save feature list
        features_path = output_dir / f'feature_columns_{race_type_lower}.json'
        with open(features_path, 'w') as f:
            json.dump(self.FEATURE_COLS, f, indent=2)
        logger.info(f"✓ Feature columns saved to {features_path}")
    
    def run_full_pipeline(self, test_size: float = 0.2, save_dir: Path = None):
        """Run complete training and evaluation pipeline"""
        logger.info("="*60)
        logger.info("RANKING MODEL TRAINING PIPELINE")
        logger.info("="*60)
        
        self.connect()
        
        try:
            # Load data
            X_train, X_test, y_train, y_test, train_df, test_df = self.load_data(test_size)
            
            # Train model (pass train_df and test_df for race grouping)
            model = self.train_xgboost(
                X_train, y_train, train_df,
                X_val=X_test, y_val=y_test, test_df=test_df
            )
            
            # Evaluate
            metrics = self.evaluate(model, X_test, y_test, test_df)
            
            # Save
            if save_dir:
                self.save_model(save_dir)
            
            logger.info("\n" + "="*60)
            logger.info("✓ TRAINING COMPLETE")
            logger.info("="*60)
            logger.info(f"\nKey metrics:")
            logger.info(f"  Top Pick Accuracy: {metrics['top_pick_accuracy']:.1%}")
            logger.info(f"  Top 3 Hit Rate: {metrics['top_3_hit_rate']:.1%}")
            logger.info(f"  NDCG@3: {metrics['ndcg@3']:.4f}")
            logger.info(f"  Mean Reciprocal Rank: {metrics['mean_reciprocal_rank']:.4f}")
            
            return model, metrics
            
        except Exception as e:
            logger.error(f"Error in training pipeline: {e}", exc_info=True)
            raise
        finally:
            self.close()


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Train baseline ML model')
    parser.add_argument('--test-size', type=float, default=0.2, 
                       help='Test set size (default: 0.2)')
    parser.add_argument('--output-dir', type=str, default='models',
                       help='Output directory for models')
    parser.add_argument('--race-type', type=str, default='Flat',
                       choices=['Flat', 'Hurdle', 'Chase'],
                       help='Race type to train on (default: Flat)')
    
    args = parser.parse_args()
    
    db_path = Path(__file__).parent.parent / "racing_pro.db"
    
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        return 1
    
    output_dir = Path(__file__).parent / args.output_dir
    
    logger.info(f"Training model for {args.race_type} racing")
    trainer = BaselineTrainer(db_path, race_type=args.race_type)
    
    try:
        model, metrics = trainer.run_full_pipeline(
            test_size=args.test_size,
            save_dir=output_dir
        )
        return 0
    except Exception as e:
        logger.error(f"Training failed: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

