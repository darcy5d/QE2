#!/usr/bin/env python3
"""
Calibration Diagnostics
Analyzes how well predicted probabilities match actual outcomes
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, Tuple
import json


class CalibrationAnalyzer:
    """Analyze model calibration quality"""
    
    def __init__(self, db_path: str, model_path: str, feature_cols_path: str, race_type: str = 'Flat'):
        """
        Initialize calibration analyzer
        
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
    
    def load_test_data(self, test_size: float = 0.2) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
        """
        Load test set using same temporal split as training
        
        Returns:
            X_test, test_df (with race_id), y_won (binary outcomes)
        """
        import sqlite3
        
        print("\nLoading test data...")
        conn = sqlite3.connect(str(self.db_path))
        
        # Load features and targets with temporal ordering
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
        
        # Temporal split
        split_idx = int(len(df) * (1 - test_size))
        test_df = df.iloc[split_idx:].copy()
        
        print(f"✓ Loaded {len(test_df):,} test samples from {test_df['race_id'].nunique():,} races")
        print(f"  Date range: {test_df['date'].min()} to {test_df['date'].max()}")
        
        # Extract features and outcomes
        X_test = test_df[self.feature_columns].copy()
        y_won = test_df['won'].copy()
        
        # Convert to numeric and handle missing values
        for col in X_test.columns:
            X_test[col] = pd.to_numeric(X_test[col], errors='coerce')
            median_val = X_test[col].median()
            if pd.isna(median_val):
                median_val = 0
            X_test[col] = X_test[col].fillna(median_val)
        
        return X_test, test_df, y_won
    
    def generate_predictions(self, X_test: pd.DataFrame, test_df: pd.DataFrame) -> np.ndarray:
        """
        Generate predictions using ranking model + softmax
        
        Args:
            X_test: Feature matrix
            test_df: Test dataframe with race_id for grouping
        
        Returns:
            Array of win probabilities
        """
        import xgboost as xgb
        
        print("\nGenerating predictions...")
        
        # Get ranking scores
        dmatrix = xgb.DMatrix(X_test, feature_names=self.feature_columns)
        ranking_scores = self.model.predict(dmatrix)
        
        # Convert to probabilities using softmax per race
        test_df_copy = test_df.copy()
        test_df_copy['ranking_score'] = ranking_scores
        
        def softmax_group(group):
            scores = group['ranking_score'].values
            exp_scores = np.exp(scores - np.max(scores))  # Numerical stability
            probabilities = exp_scores / exp_scores.sum()
            return pd.Series(probabilities, index=group.index)
        
        probabilities = test_df_copy.groupby('race_id', group_keys=False).apply(softmax_group).values
        
        print(f"✓ Generated predictions for {len(probabilities):,} runners")
        print(f"  Mean predicted probability: {probabilities.mean():.4f}")
        print(f"  Std predicted probability: {probabilities.std():.4f}")
        
        return probabilities
    
    def compute_calibration_curve(self, y_true: np.ndarray, y_pred: np.ndarray, 
                                  n_bins: int = 10) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Compute calibration curve
        
        Args:
            y_true: Binary outcomes (1 = won, 0 = lost)
            y_pred: Predicted probabilities
            n_bins: Number of bins
        
        Returns:
            prob_true, prob_pred, counts
        """
        # Create bins
        bins = np.linspace(0, 1, n_bins + 1)
        bin_indices = np.digitize(y_pred, bins[:-1]) - 1
        bin_indices = np.clip(bin_indices, 0, n_bins - 1)
        
        prob_true = np.zeros(n_bins)
        prob_pred = np.zeros(n_bins)
        counts = np.zeros(n_bins)
        
        for i in range(n_bins):
            mask = bin_indices == i
            if mask.sum() > 0:
                prob_true[i] = y_true[mask].mean()
                prob_pred[i] = y_pred[mask].mean()
                counts[i] = mask.sum()
        
        return prob_true, prob_pred, counts
    
    def compute_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
        """
        Compute calibration metrics
        
        Args:
            y_true: Binary outcomes
            y_pred: Predicted probabilities
        
        Returns:
            Dictionary of metrics
        """
        # Brier score (lower is better)
        brier_score = np.mean((y_true - y_pred) ** 2)
        
        # Log loss (lower is better)
        epsilon = 1e-15
        y_pred_clipped = np.clip(y_pred, epsilon, 1 - epsilon)
        log_loss = -np.mean(y_true * np.log(y_pred_clipped) + 
                           (1 - y_true) * np.log(1 - y_pred_clipped))
        
        # Expected Calibration Error (ECE)
        prob_true, prob_pred, counts = self.compute_calibration_curve(y_true, y_pred, n_bins=10)
        weights = counts / counts.sum()
        ece = np.sum(weights * np.abs(prob_true - prob_pred))
        
        # Maximum Calibration Error (MCE)
        mce = np.max(np.abs(prob_true - prob_pred))
        
        return {
            'brier_score': brier_score,
            'log_loss': log_loss,
            'ece': ece,
            'mce': mce
        }
    
    def plot_calibration_curve(self, y_true: np.ndarray, y_pred: np.ndarray, 
                               output_path: str = None, n_bins: int = 10):
        """
        Plot calibration curve
        
        Args:
            y_true: Binary outcomes
            y_pred: Predicted probabilities
            output_path: Path to save plot
            n_bins: Number of bins
        """
        prob_true, prob_pred, counts = self.compute_calibration_curve(y_true, y_pred, n_bins)
        
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Plot 1: Calibration curve
        ax1.plot([0, 1], [0, 1], 'k--', linewidth=2, label='Perfect Calibration')
        
        # Plot line connecting bins
        valid_bins = counts > 0
        ax1.plot(prob_pred[valid_bins], prob_true[valid_bins], 
                'o-', linewidth=2, markersize=8, color='#4ecdc4', label='Model Calibration')
        
        # Add bin sizes as annotations
        for i in range(n_bins):
            if counts[i] > 0:
                ax1.annotate(f'{int(counts[i])}', 
                           xy=(prob_pred[i], prob_true[i]),
                           xytext=(5, 5), textcoords='offset points',
                           fontsize=8, alpha=0.7)
        
        ax1.set_xlabel('Predicted Probability', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Actual Win Rate', fontsize=12, fontweight='bold')
        ax1.set_title('Calibration Curve', fontsize=14, fontweight='bold')
        ax1.legend(loc='upper left', fontsize=10)
        ax1.grid(alpha=0.3)
        ax1.set_xlim([-0.05, 1.05])
        ax1.set_ylim([-0.05, 1.05])
        
        # Plot 2: Histogram of predictions
        ax2.hist(y_pred, bins=30, color='#4ecdc4', alpha=0.7, edgecolor='black')
        ax2.axvline(y_pred.mean(), color='red', linestyle='--', linewidth=2, 
                   label=f'Mean: {y_pred.mean():.4f}')
        ax2.set_xlabel('Predicted Probability', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Count', fontsize=12, fontweight='bold')
        ax2.set_title('Distribution of Predicted Probabilities', fontsize=14, fontweight='bold')
        ax2.legend(fontsize=10)
        ax2.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        
        # Save plot
        if output_path:
            output_path = Path(output_path)
        else:
            output_path = self.model_path.parent / 'calibration_curve.png'
        
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"✓ Saved calibration curve to {output_path}")
        
        plt.close()
    
    def plot_reliability_diagram(self, y_true: np.ndarray, y_pred: np.ndarray, 
                                 test_df: pd.DataFrame, output_path: str = None):
        """
        Plot reliability diagram with confidence intervals
        
        Args:
            y_true: Binary outcomes
            y_pred: Predicted probabilities
            test_df: Test dataframe with race_id
            output_path: Path to save plot
        """
        # Group predictions by predicted rank within each race
        test_df_copy = test_df.copy()
        test_df_copy['pred_prob'] = y_pred
        test_df_copy['actual_won'] = y_true
        
        # Assign predicted rank within each race
        test_df_copy['pred_rank'] = test_df_copy.groupby('race_id')['pred_prob'].rank(ascending=False, method='first')
        
        # Analyze by predicted rank
        rank_analysis = []
        for rank in range(1, 11):  # Top 10 predicted positions
            mask = test_df_copy['pred_rank'] == rank
            if mask.sum() > 0:
                actual_win_rate = test_df_copy[mask]['actual_won'].mean()
                predicted_prob = test_df_copy[mask]['pred_prob'].mean()
                count = mask.sum()
                rank_analysis.append({
                    'rank': rank,
                    'predicted_prob': predicted_prob,
                    'actual_win_rate': actual_win_rate,
                    'count': count
                })
        
        rank_df = pd.DataFrame(rank_analysis)
        
        # Create plot
        fig, ax = plt.subplots(figsize=(10, 7))
        
        # Plot bars
        x = rank_df['rank']
        width = 0.35
        
        ax.bar(x - width/2, rank_df['predicted_prob'], width, 
              label='Predicted Probability', color='#4ecdc4', alpha=0.8)
        ax.bar(x + width/2, rank_df['actual_win_rate'], width, 
              label='Actual Win Rate', color='#ff6b6b', alpha=0.8)
        
        # Add perfect calibration line
        ax.plot(x, rank_df['predicted_prob'], 'k--', alpha=0.5, label='Perfect Calibration')
        
        # Add count annotations
        for _, row in rank_df.iterrows():
            ax.text(row['rank'], max(row['predicted_prob'], row['actual_win_rate']) + 0.01,
                   f"n={int(row['count'])}", ha='center', fontsize=8, alpha=0.7)
        
        ax.set_xlabel('Predicted Rank', fontsize=12, fontweight='bold')
        ax.set_ylabel('Probability / Win Rate', fontsize=12, fontweight='bold')
        ax.set_title('Reliability by Predicted Rank', fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(axis='y', alpha=0.3)
        ax.set_xticks(x)
        
        plt.tight_layout()
        
        # Save plot
        if output_path:
            output_path = Path(output_path)
        else:
            output_path = self.model_path.parent / 'reliability_diagram.png'
        
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"✓ Saved reliability diagram to {output_path}")
        
        plt.close()
    
    def print_metrics(self, metrics: Dict):
        """Print calibration metrics"""
        print("\n" + "="*80)
        print("CALIBRATION METRICS")
        print("="*80)
        
        print(f"\nBrier Score: {metrics['brier_score']:.6f}")
        print("  (Lower is better; perfect = 0.0)")
        
        print(f"\nLog Loss: {metrics['log_loss']:.6f}")
        print("  (Lower is better; perfect = 0.0)")
        
        print(f"\nExpected Calibration Error (ECE): {metrics['ece']:.6f}")
        print("  (Lower is better; perfect = 0.0)")
        print("  Interpretation:")
        if metrics['ece'] < 0.01:
            print("  ✓✓ Excellent calibration")
        elif metrics['ece'] < 0.05:
            print("  ✓ Good calibration")
        elif metrics['ece'] < 0.10:
            print("  ⚠️  Moderate miscalibration - consider calibration training")
        else:
            print("  ❌ Poor calibration - calibration training recommended")
        
        print(f"\nMaximum Calibration Error (MCE): {metrics['mce']:.6f}")
        print("  (Worst bin error; lower is better)")
    
    def save_report(self, metrics: Dict, output_path: str = None):
        """Save calibration report"""
        if output_path:
            output_path = Path(output_path)
        else:
            output_path = self.model_path.parent / 'calibration_report.txt'
        
        with open(output_path, 'w') as f:
            f.write("="*80 + "\n")
            f.write("CALIBRATION DIAGNOSTICS REPORT\n")
            f.write("="*80 + "\n")
            f.write(f"\nModel: {self.model_path.name}\n")
            f.write(f"Race Type: {self.race_type}\n")
            f.write(f"\nMetrics:\n")
            f.write(f"  Brier Score: {metrics['brier_score']:.6f}\n")
            f.write(f"  Log Loss: {metrics['log_loss']:.6f}\n")
            f.write(f"  Expected Calibration Error (ECE): {metrics['ece']:.6f}\n")
            f.write(f"  Maximum Calibration Error (MCE): {metrics['mce']:.6f}\n")
            
            if metrics['ece'] < 0.01:
                f.write("\n✓ Calibration Status: Excellent\n")
            elif metrics['ece'] < 0.05:
                f.write("\n✓ Calibration Status: Good\n")
            elif metrics['ece'] < 0.10:
                f.write("\n⚠️  Calibration Status: Moderate - consider calibration training\n")
            else:
                f.write("\n❌ Calibration Status: Poor - calibration training recommended\n")
        
        print(f"\n✓ Saved calibration report to {output_path}")
    
    def run_full_analysis(self, test_size: float = 0.2, n_bins: int = 10):
        """Run complete calibration analysis"""
        print("="*80)
        print("CALIBRATION DIAGNOSTICS")
        print(f"Model: {self.model_path.name}")
        print(f"Race Type: {self.race_type}")
        print("="*80)
        
        # Load model and features
        self.load_model_and_features()
        
        # Load test data
        X_test, test_df, y_won = self.load_test_data(test_size=test_size)
        
        # Generate predictions
        y_pred = self.generate_predictions(X_test, test_df)
        
        # Compute metrics
        metrics = self.compute_metrics(y_won.values, y_pred)
        
        # Print metrics
        self.print_metrics(metrics)
        
        # Plot calibration curve
        self.plot_calibration_curve(y_won.values, y_pred, n_bins=n_bins)
        
        # Plot reliability diagram
        self.plot_reliability_diagram(y_won.values, y_pred, test_df)
        
        # Save report
        self.save_report(metrics)
        
        print("\n" + "="*80)
        print("✓ CALIBRATION DIAGNOSTICS COMPLETE")
        print("="*80)
        
        return metrics, y_won.values, y_pred, test_df


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze model calibration')
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
                       help='Test set size for calibration analysis')
    parser.add_argument('--bins', type=int, default=10,
                       help='Number of bins for calibration curve')
    
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
    
    # Run analysis
    analyzer = CalibrationAnalyzer(
        str(db_path), str(model_path), str(features_path), 
        race_type=args.race_type
    )
    
    try:
        analyzer.run_full_analysis(test_size=args.test_size, n_bins=args.bins)
        return 0
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

