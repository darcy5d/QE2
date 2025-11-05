#!/usr/bin/env python3
"""
Optimize Temperature Scaling for Model 1
Find optimal temperature parameter to sharpen probability distributions
"""

import sqlite3
import numpy as np
import pandas as pd
from pathlib import Path
import logging
import json
from typing import Tuple, Dict
import xgboost as xgb
from sklearn.metrics import log_loss, brier_score_loss

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TemperatureOptimizer:
    """Optimize temperature scaling for existing ranking model"""
    
    def __init__(self, db_path: str, model_path: str, feature_cols_path: str, race_type: str = 'Flat'):
        self.db_path = Path(db_path)
        self.model_path = Path(model_path)
        self.feature_cols_path = Path(feature_cols_path)
        self.race_type = race_type
        self.model = None
        self.feature_columns = None
        self.optimal_temperature = 1.0
        
    def load_model_and_features(self):
        """Load trained model and feature columns"""
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        
        if not self.feature_cols_path.exists():
            raise FileNotFoundError(f"Feature columns not found: {self.feature_cols_path}")
        
        self.model = xgb.Booster()
        self.model.load_model(str(self.model_path))
        
        with open(self.feature_cols_path, 'r') as f:
            self.feature_columns = json.load(f)
        
        logger.info(f"✓ Loaded model from {self.model_path}")
        logger.info(f"✓ Loaded {len(self.feature_columns)} feature columns")
    
    def load_data(self, train_size: float = 0.6, val_size: float = 0.2) -> Tuple:
        """
        Load data and split into train/val/test (60/20/20)
        We only need val/test for temperature optimization
        
        Returns:
            X_val, val_df, y_val, X_test, test_df, y_test
        """
        logger.info("Loading data from database...")
        
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        
        # Load features and targets
        query = """
            SELECT 
                f.race_id,
                f.runner_id,
                r.date,
                r.type,
                res.position_int as target,
                res.position_int = 1 as won,
                {features}
            FROM ml_features f
            JOIN races r ON f.race_id = r.race_id
            JOIN results res ON f.race_id = res.race_id AND f.horse_id = res.horse_id
            WHERE r.type = ?
            AND res.position_int < 900
            ORDER BY r.date, f.race_id, f.runner_id
        """.format(features=', '.join([f'f.{col}' for col in self.feature_columns]))
        
        df = pd.read_sql_query(query, conn, params=(self.race_type,))
        conn.close()
        
        logger.info(f"Loaded {len(df):,} samples from {df['race_id'].nunique():,} races")
        logger.info(f"Date range: {df['date'].min()} to {df['date'].max()}")
        
        # Temporal split (earlier dates for training, later for val/test)
        n_total = len(df)
        train_idx = int(n_total * train_size)
        val_idx = int(n_total * (train_size + val_size))
        
        # We only need val and test for temperature optimization
        val_df = df.iloc[train_idx:val_idx].copy()
        test_df = df.iloc[val_idx:].copy()
        
        logger.info(f"\nData split:")
        logger.info(f"  Validation: {len(val_df):,} samples in {val_df['race_id'].nunique():,} races")
        logger.info(f"    Date range: {val_df['date'].min()} to {val_df['date'].max()}")
        logger.info(f"  Test: {len(test_df):,} samples in {test_df['race_id'].nunique():,} races")
        logger.info(f"    Date range: {test_df['date'].min()} to {test_df['date'].max()}")
        
        # Extract features and targets
        X_val = val_df[self.feature_columns].copy()
        X_test = test_df[self.feature_columns].copy()
        y_val = val_df['won'].values
        y_test = test_df['won'].values
        
        # Handle missing values
        for col in self.feature_columns:
            X_val[col] = pd.to_numeric(X_val[col], errors='coerce')
            X_test[col] = pd.to_numeric(X_test[col], errors='coerce')
            median_val = X_val[col].median()
            if pd.isna(median_val):
                median_val = 0
            X_val[col] = X_val[col].fillna(median_val)
            X_test[col] = X_test[col].fillna(median_val)
        
        return X_val, val_df, y_val, X_test, test_df, y_test
    
    def generate_raw_scores(self, X: pd.DataFrame) -> np.ndarray:
        """Generate raw ranking scores from model"""
        dmatrix = xgb.DMatrix(X, feature_names=self.feature_columns)
        scores = self.model.predict(dmatrix)
        return scores
    
    def apply_softmax_per_race(self, scores: np.ndarray, race_ids: pd.Series, 
                               temperature: float = 1.0) -> np.ndarray:
        """
        Apply softmax with temperature scaling per race
        
        Args:
            scores: Raw ranking scores
            race_ids: Race identifier for grouping
            temperature: Temperature parameter (< 1 = sharper, > 1 = flatter)
        
        Returns:
            Array of win probabilities
        """
        # Create temporary dataframe for grouping
        temp_df = pd.DataFrame({
            'race_id': race_ids,
            'score': scores
        })
        
        def softmax_group(group):
            """Apply softmax to one race with temperature"""
            scores = group['score'].values / temperature  # Scale by temperature
            exp_scores = np.exp(scores - np.max(scores))  # Numerical stability
            probabilities = exp_scores / exp_scores.sum()
            return pd.Series(probabilities, index=group.index)
        
        probabilities = temp_df.groupby('race_id', group_keys=False).apply(softmax_group).values
        return probabilities
    
    def compute_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
        """
        Compute evaluation metrics for probability predictions
        
        Args:
            y_true: Binary labels (1 = won, 0 = lost)
            y_pred: Predicted win probabilities
            
        Returns:
            Dictionary with NLL, Brier score, and calibration error
        """
        # Clip probabilities to avoid log(0)
        y_pred_clipped = np.clip(y_pred, 1e-10, 1 - 1e-10)
        
        # Negative Log-Likelihood (lower = better)
        nll = log_loss(y_true, y_pred_clipped)
        
        # Brier Score (lower = better)
        brier = brier_score_loss(y_true, y_pred)
        
        # Calibration Error (10 bins)
        n_bins = 10
        bin_edges = np.linspace(0, 1, n_bins + 1)
        bin_indices = np.digitize(y_pred, bin_edges[:-1]) - 1
        bin_indices = np.clip(bin_indices, 0, n_bins - 1)
        
        calibration_error = 0.0
        for i in range(n_bins):
            mask = bin_indices == i
            if np.sum(mask) > 0:
                bin_mean_pred = np.mean(y_pred[mask])
                bin_mean_true = np.mean(y_true[mask])
                bin_weight = np.sum(mask) / len(y_true)
                calibration_error += bin_weight * abs(bin_mean_pred - bin_mean_true)
        
        return {
            'nll': nll,
            'brier': brier,
            'calibration_error': calibration_error
        }
    
    def compute_probability_spread(self, probabilities: np.ndarray) -> Dict:
        """Compute statistics on probability distribution"""
        return {
            'min': float(np.min(probabilities)),
            'max': float(np.max(probabilities)),
            'mean': float(np.mean(probabilities)),
            'std': float(np.std(probabilities)),
            'median': float(np.median(probabilities)),
            'q25': float(np.percentile(probabilities, 25)),
            'q75': float(np.percentile(probabilities, 75))
        }
    
    def optimize_temperature(self, X_val: pd.DataFrame, val_df: pd.DataFrame, 
                           y_val: np.ndarray) -> float:
        """
        Search for optimal temperature on validation set
        
        Args:
            X_val: Validation features
            val_df: Validation dataframe (for race_id)
            y_val: Validation labels
            
        Returns:
            Optimal temperature value
        """
        logger.info("\n" + "="*60)
        logger.info("TEMPERATURE OPTIMIZATION")
        logger.info("="*60)
        
        # Generate raw scores once
        logger.info("\nGenerating raw model scores...")
        raw_scores = self.generate_raw_scores(X_val)
        logger.info(f"  Raw score range: {raw_scores.min():.2f} to {raw_scores.max():.2f}")
        logger.info(f"  Raw score std dev: {raw_scores.std():.2f}")
        
        # Temperature candidates (focus on sharpening: < 1.0)
        temperature_candidates = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        
        logger.info(f"\nTesting {len(temperature_candidates)} temperature values...")
        
        results = []
        for temp in temperature_candidates:
            # Apply softmax with this temperature
            probabilities = self.apply_softmax_per_race(
                raw_scores, val_df['race_id'], temperature=temp
            )
            
            # Compute metrics
            metrics = self.compute_metrics(y_val, probabilities)
            spread = self.compute_probability_spread(probabilities)
            
            results.append({
                'temperature': temp,
                'nll': metrics['nll'],
                'brier': metrics['brier'],
                'calibration_error': metrics['calibration_error'],
                'prob_min': spread['min'],
                'prob_max': spread['max'],
                'prob_std': spread['std']
            })
            
            logger.info(f"\n  Temperature = {temp:.1f}")
            logger.info(f"    NLL: {metrics['nll']:.4f}")
            logger.info(f"    Brier: {metrics['brier']:.4f}")
            logger.info(f"    Calibration Error: {metrics['calibration_error']:.4f}")
            logger.info(f"    Prob range: {spread['min']:.1%} to {spread['max']:.1%}")
            logger.info(f"    Prob std dev: {spread['std']:.4f}")
        
        # Select best temperature (minimize combined metric)
        # Weight: 60% NLL + 40% calibration error
        logger.info("\n" + "="*60)
        logger.info("SELECTING BEST TEMPERATURE")
        logger.info("="*60)
        
        best_temp = None
        best_score = float('inf')
        
        for result in results:
            combined_score = 0.6 * result['nll'] + 0.4 * result['calibration_error']
            if combined_score < best_score:
                best_score = combined_score
                best_temp = result['temperature']
        
        logger.info(f"\n✓ Optimal temperature: {best_temp}")
        logger.info(f"  Combined score: {best_score:.4f}")
        
        # Show comparison
        baseline = [r for r in results if r['temperature'] == 1.0][0]
        optimal = [r for r in results if r['temperature'] == best_temp][0]
        
        logger.info(f"\nBaseline (T=1.0) vs Optimal (T={best_temp}):")
        logger.info(f"  NLL: {baseline['nll']:.4f} → {optimal['nll']:.4f} ({(optimal['nll']-baseline['nll'])/baseline['nll']*100:+.1f}%)")
        logger.info(f"  Calibration Error: {baseline['calibration_error']:.4f} → {optimal['calibration_error']:.4f} ({(optimal['calibration_error']-baseline['calibration_error'])/baseline['calibration_error']*100:+.1f}%)")
        logger.info(f"  Prob std dev: {baseline['prob_std']:.4f} → {optimal['prob_std']:.4f} ({(optimal['prob_std']-baseline['prob_std'])/baseline['prob_std']*100:+.1f}%)")
        logger.info(f"  Prob range: {baseline['prob_min']:.1%}-{baseline['prob_max']:.1%} → {optimal['prob_min']:.1%}-{optimal['prob_max']:.1%}")
        
        return best_temp, results
    
    def evaluate_on_test(self, X_test: pd.DataFrame, test_df: pd.DataFrame, 
                        y_test: np.ndarray, temperature: float) -> Dict:
        """Evaluate model with optimal temperature on test set"""
        logger.info("\n" + "="*60)
        logger.info("TEST SET EVALUATION")
        logger.info("="*60)
        
        # Generate scores
        raw_scores = self.generate_raw_scores(X_test)
        
        # Apply optimal temperature
        probabilities = self.apply_softmax_per_race(
            raw_scores, test_df['race_id'], temperature=temperature
        )
        
        # Compute metrics
        metrics = self.compute_metrics(y_test, probabilities)
        spread = self.compute_probability_spread(probabilities)
        
        logger.info(f"\nTest set results with T={temperature}:")
        logger.info(f"  NLL: {metrics['nll']:.4f}")
        logger.info(f"  Brier Score: {metrics['brier']:.4f}")
        logger.info(f"  Calibration Error: {metrics['calibration_error']:.4f}")
        logger.info(f"  Probability range: {spread['min']:.1%} to {spread['max']:.1%}")
        logger.info(f"  Probability std dev: {spread['std']:.4f}")
        
        return {
            'metrics': metrics,
            'spread': spread,
            'temperature': temperature
        }
    
    def save_config(self, temperature: float, validation_results: list, 
                   test_results: Dict, output_path: str):
        """Save optimal temperature configuration"""
        config = {
            'temperature': temperature,
            'validation_results': validation_results,
            'test_metrics': test_results['metrics'],
            'test_spread': test_results['spread'],
            'model_path': str(self.model_path),
            'feature_columns_path': str(self.feature_cols_path),
            'race_type': self.race_type
        }
        
        output_file = Path(output_path)
        with open(output_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"\n✓ Saved temperature config to {output_file}")


def main():
    """Run temperature optimization"""
    # Paths
    db_path = 'Datafetch/racing_pro.db'
    model_path = 'Datafetch/ml/models/xgboost_flat.json'
    feature_cols_path = 'Datafetch/ml/models/feature_columns_flat.json'
    output_path = 'Datafetch/ml/models/temperature_config.json'
    
    # Initialize optimizer
    optimizer = TemperatureOptimizer(db_path, model_path, feature_cols_path, race_type='Flat')
    
    # Load model
    optimizer.load_model_and_features()
    
    # Load data (60/20/20 split)
    X_val, val_df, y_val, X_test, test_df, y_test = optimizer.load_data()
    
    # Optimize temperature on validation set
    optimal_temp, val_results = optimizer.optimize_temperature(X_val, val_df, y_val)
    
    # Evaluate on test set
    test_results = optimizer.evaluate_on_test(X_test, test_df, y_test, optimal_temp)
    
    # Save configuration
    optimizer.save_config(optimal_temp, val_results, test_results, output_path)
    
    logger.info("\n" + "="*60)
    logger.info("✅ TEMPERATURE OPTIMIZATION COMPLETE")
    logger.info("="*60)
    logger.info(f"Optimal temperature: {optimal_temp}")
    logger.info(f"Config saved to: {output_path}")


if __name__ == '__main__':
    main()

