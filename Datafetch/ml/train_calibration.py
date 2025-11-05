#!/usr/bin/env python3
"""
Train Calibration Parameters
Learn temperature scaling to improve probability calibration
"""

import numpy as np
import pandas as pd
from pathlib import Path
import json
from typing import Dict, Tuple
from scipy.optimize import minimize


class CalibrationTrainer:
    """Train calibration parameters using temperature scaling"""
    
    def __init__(self, db_path: str, model_path: str, feature_cols_path: str, race_type: str = 'Flat'):
        """
        Initialize calibration trainer
        
        Args:
            db_path: Path to racing_pro.db
            model_path: Path to trained model
            feature_cols_path: Path to feature columns JSON
            race_type: Race type ('Flat', 'Hurdle', 'Chase')
        """
        self.db_path = Path(db_path)
        self.model_path = Path(model_path)
        self.feature_cols_path = Path(feature_cols_path)
        self.race_type = race_type
        self.model = None
        self.feature_columns = None
        self.calibration_params = None
        
    def load_model_and_features(self):
        """Load trained model and feature columns"""
        import xgboost as xgb
        
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        
        if not self.feature_cols_path.exists():
            raise FileNotFoundError(f"Feature columns not found: {self.feature_cols_path}")
        
        self.model = xgb.Booster()
        self.model.load_model(str(self.model_path))
        
        with open(self.feature_cols_path, 'r') as f:
            self.feature_columns = json.load(f)
        
        print(f"✓ Loaded model and {len(self.feature_columns)} feature columns")
    
    def load_validation_data(self, test_size: float = 0.2, val_split: float = 0.5) -> Tuple:
        """
        Load validation set (second half of test set)
        
        Args:
            test_size: Size of overall test set
            val_split: Proportion of test set to use for calibration validation
        
        Returns:
            X_val, val_df, y_won, ranking_scores
        """
        import sqlite3
        
        print("\nLoading validation data for calibration...")
        conn = sqlite3.connect(str(self.db_path))
        
        # Load all data
        query = """
            SELECT 
                f.race_id,
                f.runner_id,
                r.date,
                t.position,
                t.won,
                {}
            FROM ml_features f
            JOIN ml_targets t ON f.race_id = t.race_id AND f.runner_id = t.runner_id
            JOIN races r ON f.race_id = r.race_id
            WHERE r.type = ?
            ORDER BY r.date, f.race_id, t.position
        """.format(', '.join([f'f."{col}"' for col in self.feature_columns]))
        
        df = pd.read_sql_query(query, conn, params=(self.race_type,))
        conn.close()
        
        # Split into train and test
        split_idx = int(len(df) * (1 - test_size))
        test_df = df.iloc[split_idx:].copy()
        
        # Split test into calibration training and validation
        cal_split_idx = int(len(test_df) * val_split)
        val_df = test_df.iloc[cal_split_idx:].copy()
        
        print(f"✓ Loaded {len(val_df):,} validation samples from {val_df['race_id'].nunique():,} races")
        print(f"  Date range: {val_df['date'].min()} to {val_df['date'].max()}")
        
        # Extract features and outcomes
        X_val = val_df[self.feature_columns].copy()
        y_won = val_df['won'].copy()
        
        # Convert to numeric and handle missing values
        for col in X_val.columns:
            X_val[col] = pd.to_numeric(X_val[col], errors='coerce')
            median_val = X_val[col].median()
            if pd.isna(median_val):
                median_val = 0
            X_val[col] = X_val[col].fillna(median_val)
        
        # Get raw ranking scores
        import xgboost as xgb
        dmatrix = xgb.DMatrix(X_val, feature_names=self.feature_columns)
        ranking_scores = self.model.predict(dmatrix)
        
        return X_val, val_df, y_won, ranking_scores
    
    def softmax(self, scores: np.ndarray, temperature: float = 1.0) -> np.ndarray:
        """
        Apply softmax with temperature scaling
        
        Args:
            scores: Raw ranking scores
            temperature: Temperature parameter (> 1 = less confident, < 1 = more confident)
        
        Returns:
            Probabilities
        """
        scaled_scores = scores / temperature
        exp_scores = np.exp(scaled_scores - np.max(scaled_scores))
        return exp_scores / exp_scores.sum()
    
    def compute_nll_loss(self, temperature: float, scores_by_race: list, labels_by_race: list) -> float:
        """
        Compute negative log likelihood loss for given temperature
        
        Args:
            temperature: Temperature parameter to evaluate
            scores_by_race: List of score arrays (one per race)
            labels_by_race: List of label arrays (one per race)
        
        Returns:
            Negative log likelihood
        """
        total_nll = 0.0
        epsilon = 1e-15
        
        for scores, labels in zip(scores_by_race, labels_by_race):
            # Apply temperature-scaled softmax
            probs = self.softmax(scores, temperature)
            
            # Clip probabilities for numerical stability
            probs = np.clip(probs, epsilon, 1 - epsilon)
            
            # Compute NLL for this race
            nll = -np.sum(labels * np.log(probs))
            total_nll += nll
        
        return total_nll
    
    def train_temperature_scaling(self, ranking_scores: np.ndarray, y_won: np.ndarray, 
                                  val_df: pd.DataFrame) -> float:
        """
        Learn optimal temperature parameter
        
        Args:
            ranking_scores: Raw ranking scores from model
            y_won: Binary win labels
            val_df: Validation dataframe with race_id
        
        Returns:
            Optimal temperature
        """
        print("\n" + "="*80)
        print("TRAINING TEMPERATURE SCALING")
        print("="*80)
        
        # Group scores and labels by race
        val_df_copy = val_df.copy()
        val_df_copy['score'] = ranking_scores
        val_df_copy['won'] = y_won
        
        scores_by_race = []
        labels_by_race = []
        
        for race_id, group in val_df_copy.groupby('race_id'):
            scores_by_race.append(group['score'].values)
            labels_by_race.append(group['won'].values)
        
        print(f"\nOptimizing temperature on {len(scores_by_race)} races...")
        
        # Define objective function
        def objective(T):
            return self.compute_nll_loss(T[0], scores_by_race, labels_by_race)
        
        # Optimize temperature (start from 1.0)
        result = minimize(
            objective,
            x0=[1.0],
            method='L-BFGS-B',
            bounds=[(0.1, 10.0)],  # Temperature must be positive
            options={'disp': False}
        )
        
        optimal_temperature = result.x[0]
        
        print(f"\n✓ Optimal temperature: {optimal_temperature:.4f}")
        print(f"  Initial NLL (T=1.0): {objective([1.0]):.4f}")
        print(f"  Optimized NLL (T={optimal_temperature:.4f}): {result.fun:.4f}")
        print(f"  Improvement: {((objective([1.0]) - result.fun) / objective([1.0]) * 100):.2f}%")
        
        # Interpretation
        if optimal_temperature > 1.5:
            print("\n  Interpretation: Model is OVERCONFIDENT - scaling down predictions")
        elif optimal_temperature < 0.7:
            print("\n  Interpretation: Model is UNDERCONFIDENT - scaling up predictions")
        else:
            print("\n  Interpretation: Model calibration is reasonable")
        
        return optimal_temperature
    
    def evaluate_calibration(self, ranking_scores: np.ndarray, y_won: np.ndarray, 
                            val_df: pd.DataFrame, temperature: float):
        """
        Evaluate calibration before and after temperature scaling
        
        Args:
            ranking_scores: Raw ranking scores
            y_won: Binary win labels
            val_df: Validation dataframe with race_id
            temperature: Learned temperature
        """
        print("\n" + "="*80)
        print("CALIBRATION EVALUATION")
        print("="*80)
        
        # Generate probabilities before and after calibration
        val_df_copy = val_df.copy()
        val_df_copy['score'] = ranking_scores
        val_df_copy['won'] = y_won
        
        def apply_softmax_per_race(group, temp=1.0):
            scores = group['score'].values
            probs = self.softmax(scores, temp)
            return pd.Series(probs, index=group.index)
        
        probs_before = val_df_copy.groupby('race_id', group_keys=False).apply(
            lambda g: apply_softmax_per_race(g, temp=1.0)
        ).values
        
        probs_after = val_df_copy.groupby('race_id', group_keys=False).apply(
            lambda g: apply_softmax_per_race(g, temp=temperature)
        ).values
        
        # Compute metrics
        def compute_ece(y_true, y_pred, n_bins=10):
            bins = np.linspace(0, 1, n_bins + 1)
            bin_indices = np.digitize(y_pred, bins[:-1]) - 1
            bin_indices = np.clip(bin_indices, 0, n_bins - 1)
            
            ece = 0.0
            for i in range(n_bins):
                mask = bin_indices == i
                if mask.sum() > 0:
                    bin_acc = y_true[mask].mean()
                    bin_conf = y_pred[mask].mean()
                    bin_weight = mask.sum() / len(y_true)
                    ece += bin_weight * np.abs(bin_acc - bin_conf)
            return ece
        
        def compute_brier(y_true, y_pred):
            return np.mean((y_true - y_pred) ** 2)
        
        ece_before = compute_ece(y_won.values, probs_before)
        ece_after = compute_ece(y_won.values, probs_after)
        
        brier_before = compute_brier(y_won.values, probs_before)
        brier_after = compute_brier(y_won.values, probs_after)
        
        print("\nBefore Calibration (T=1.0):")
        print(f"  ECE: {ece_before:.6f}")
        print(f"  Brier Score: {brier_before:.6f}")
        
        print(f"\nAfter Calibration (T={temperature:.4f}):")
        print(f"  ECE: {ece_after:.6f}")
        print(f"  Brier Score: {brier_after:.6f}")
        
        print("\nImprovement:")
        ece_improvement = (ece_before - ece_after) / ece_before * 100
        brier_improvement = (brier_before - brier_after) / brier_before * 100
        
        print(f"  ECE: {ece_improvement:+.2f}%")
        print(f"  Brier Score: {brier_improvement:+.2f}%")
        
        if ece_improvement > 5:
            print("\n✓ Temperature scaling significantly improves calibration")
        elif ece_improvement > 0:
            print("\n✓ Temperature scaling slightly improves calibration")
        else:
            print("\n⚠️  Temperature scaling does not improve calibration")
    
    def save_calibration_params(self, temperature: float, output_path: str = None):
        """
        Save calibration parameters to JSON
        
        Args:
            temperature: Learned temperature parameter
            output_path: Path to save parameters
        """
        race_type_lower = self.race_type.lower()
        
        if output_path:
            output_path = Path(output_path)
        else:
            output_path = self.model_path.parent / f'calibration_params_{race_type_lower}.json'
        
        params = {
            'method': 'temperature_scaling',
            'temperature': float(temperature),
            'race_type': self.race_type,
            'model': self.model_path.name,
            'trained_on': pd.Timestamp.now().isoformat()
        }
        
        with open(output_path, 'w') as f:
            json.dump(params, f, indent=2)
        
        print(f"\n✓ Saved calibration parameters to {output_path}")
        
        self.calibration_params = params
    
    def run_full_training(self, test_size: float = 0.2, val_split: float = 0.5):
        """Run complete calibration training pipeline"""
        print("="*80)
        print("CALIBRATION TRAINING")
        print(f"Model: {self.model_path.name}")
        print(f"Race Type: {self.race_type}")
        print("="*80)
        
        # Load model and features
        self.load_model_and_features()
        
        # Load validation data
        X_val, val_df, y_won, ranking_scores = self.load_validation_data(
            test_size=test_size, val_split=val_split
        )
        
        # Train temperature scaling
        temperature = self.train_temperature_scaling(ranking_scores, y_won, val_df)
        
        # Evaluate calibration
        self.evaluate_calibration(ranking_scores, y_won, val_df, temperature)
        
        # Save parameters
        self.save_calibration_params(temperature)
        
        print("\n" + "="*80)
        print("✓ CALIBRATION TRAINING COMPLETE")
        print("="*80)
        print(f"\nTo use calibrated predictions, the predictor will automatically")
        print(f"load the calibration parameters from:")
        print(f"  {self.model_path.parent / f'calibration_params_{self.race_type.lower()}.json'}")
        
        return temperature


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Train calibration parameters')
    parser.add_argument('--db', type=str, default='../racing_pro.db',
                       help='Path to racing_pro.db')
    parser.add_argument('--model', type=str, default='models/xgboost_flat.json',
                       help='Path to trained model')
    parser.add_argument('--features', type=str, default='models/feature_columns_flat.json',
                       help='Path to feature columns JSON')
    parser.add_argument('--race-type', type=str, default='Flat',
                       choices=['Flat', 'Hurdle', 'Chase'],
                       help='Race type')
    parser.add_argument('--test-size', type=float, default=0.2,
                       help='Test set size')
    parser.add_argument('--val-split', type=float, default=0.5,
                       help='Proportion of test set to use for calibration validation')
    
    args = parser.parse_args()
    
    # Resolve paths
    script_dir = Path(__file__).parent
    db_path = script_dir / args.db
    model_path = script_dir / args.model
    features_path = script_dir / args.features
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return 1
    
    if not model_path.exists():
        print(f"❌ Model not found: {model_path}")
        return 1
    
    if not features_path.exists():
        print(f"❌ Feature columns not found: {features_path}")
        return 1
    
    # Run training
    trainer = CalibrationTrainer(
        str(db_path), str(model_path), str(features_path), 
        race_type=args.race_type
    )
    
    try:
        trainer.run_full_training(test_size=args.test_size, val_split=args.val_split)
        return 0
    except Exception as e:
        print(f"❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

