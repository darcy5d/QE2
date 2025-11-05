#!/usr/bin/env python3
"""
Compare All 4 Models Side-by-Side
Evaluate ranking accuracy, probability discrimination, and calibration
"""

import sqlite3
import numpy as np
import pandas as pd
from pathlib import Path
import logging
import json
from typing import Dict, List, Tuple
import xgboost as xgb
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
from sklearn.metrics import log_loss, brier_score_loss

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModelComparison:
    """Compare multiple model approaches"""
    
    def __init__(self, db_path: str, models_dir: str, race_type: str = 'Flat'):
        self.db_path = Path(db_path)
        self.models_dir = Path(models_dir)
        self.race_type = race_type
        self.feature_columns = None
        self.models = {}
        self.test_data = None
        
    def load_feature_columns(self):
        """Load feature column names"""
        features_path = self.models_dir / 'feature_columns_flat.json'
        with open(features_path, 'r') as f:
            self.feature_columns = json.load(f)
        logger.info(f"✓ Loaded {len(self.feature_columns)} feature columns")
    
    def load_models(self):
        """Load all available models"""
        model_files = {
            'baseline': 'xgboost_flat.json',
            'btn': 'xgboost_flat_btn.json',
            'speed_abs': 'xgboost_flat_speed_abs.json',
            'speed_rel': 'xgboost_flat_speed_rel.json'
        }
        
        for name, filename in model_files.items():
            model_path = self.models_dir / filename
            if model_path.exists():
                model = xgb.Booster()
                model.load_model(str(model_path))
                self.models[name] = {'model': model, 'type': name}
                logger.info(f"✓ Loaded model: {name}")
            else:
                logger.warning(f"⚠ Model not found: {name} ({model_path})")
        
        # Load temperature config if available
        temp_config_path = self.models_dir / 'temperature_config.json'
        if temp_config_path.exists():
            with open(temp_config_path, 'r') as f:
                temp_config = json.load(f)
                self.models['temperature'] = {
                    'model': self.models['baseline']['model'],  # Same model, different temp
                    'type': 'temperature',
                    'temperature': temp_config['temperature']
                }
                logger.info(f"✓ Loaded temperature config: T={temp_config['temperature']}")
    
    def load_test_data(self, test_size: float = 0.2):
        """Load test data for evaluation"""
        logger.info("Loading test data...")
        
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        
        # Load features and targets
        # Alias r.distance_f to avoid collision with f.distance_f
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
                CAST(res.ovr_btn AS REAL) as btn,
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
        
        # Temporal split - take last 20% as test
        split_idx = int(len(df) * (1 - test_size))
        test_df = df.iloc[split_idx:].copy()
        
        logger.info(f"✓ Loaded {len(test_df):,} test samples from {test_df['race_id'].nunique():,} races")
        logger.info(f"  Date range: {test_df['date'].min()} to {test_df['date'].max()}")
        
        # Handle missing values
        # Only process columns that actually exist in the dataframe
        feature_cols_to_process = [col for col in self.feature_columns if col in test_df.columns]
        for col in feature_cols_to_process:
            test_df[col] = pd.to_numeric(test_df[col], errors='coerce')
            median_val = test_df[col].median()
            if pd.isna(median_val):
                median_val = 0
            test_df[col] = test_df[col].fillna(median_val)
        
        self.test_data = test_df
    
    def _parse_time_to_seconds(self, time_str: str) -> float:
        """Convert time string to seconds"""
        if not time_str or pd.isna(time_str):
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
    
    def generate_predictions(self, model_name: str) -> np.ndarray:
        """
        Generate win probabilities for a model
        
        Returns:
            Array of win probabilities
        """
        model_config = self.models[model_name]
        model = model_config['model']
        model_type = model_config['type']
        
        # Get raw predictions
        # Only use feature columns that exist in test data
        available_features = [col for col in self.feature_columns if col in self.test_data.columns]
        X = self.test_data[available_features]
        dmatrix = xgb.DMatrix(X, feature_names=available_features)
        raw_scores = model.predict(dmatrix)
        
        # Convert to probabilities based on model type
        test_df_copy = self.test_data.copy()
        test_df_copy['raw_score'] = raw_scores
        
        def convert_to_probabilities(group, model_type, temperature=1.0):
            """Convert raw scores to probabilities per race"""
            scores = group['raw_score'].values
            
            if model_type == 'baseline':
                # Standard softmax (ranking model)
                exp_scores = np.exp(scores - np.max(scores))
                probabilities = exp_scores / exp_scores.sum()
            
            elif model_type == 'temperature':
                # Softmax with temperature scaling
                temp = temperature
                scaled_scores = scores / temp
                exp_scores = np.exp(scaled_scores - np.max(scaled_scores))
                probabilities = exp_scores / exp_scores.sum()
            
            elif model_type == 'btn':
                # Smaller BTN = better (apply softmax to negative)
                exp_scores = np.exp(-scores - np.min(-scores))
                probabilities = exp_scores / exp_scores.sum()
            
            elif model_type == 'speed_abs':
                # Higher speed = better
                exp_scores = np.exp(scores - np.max(scores))
                probabilities = exp_scores / exp_scores.sum()
            
            elif model_type == 'speed_rel':
                # Closer to 0 = better (apply softmax to negative absolute value)
                # Actually, higher deficit (closer to 0) = better
                exp_scores = np.exp(scores - np.max(scores))
                probabilities = exp_scores / exp_scores.sum()
            
            return pd.Series(probabilities, index=group.index)
        
        temperature = model_config.get('temperature', 1.0)
        probabilities = test_df_copy.groupby('race_id', group_keys=False).apply(
            lambda g: convert_to_probabilities(g, model_type, temperature)
        ).values
        
        return probabilities
    
    def compute_metrics(self, probabilities: np.ndarray) -> Dict:
        """Compute evaluation metrics for predictions"""
        y_true = self.test_data['won'].values
        test_df_copy = self.test_data.copy()
        test_df_copy['prob'] = probabilities
        
        # === PROBABILITY METRICS ===
        prob_clipped = np.clip(probabilities, 1e-10, 1 - 1e-10)
        nll = log_loss(y_true, prob_clipped)
        brier = brier_score_loss(y_true, probabilities)
        
        # === RANKING METRICS ===
        test_df_copy['pred_rank'] = test_df_copy.groupby('race_id')['prob'].rank(
            method='first', ascending=False
        )
        
        # Top pick accuracy
        top_picks = test_df_copy[test_df_copy['pred_rank'] == 1]
        top_pick_accuracy = (top_picks['won'].sum() / len(top_picks)) * 100 if len(top_picks) > 0 else 0
        
        # Top 3 hit rate
        actual_winners = test_df_copy[test_df_copy['position'] == 1]
        actual_winners['in_top_3'] = actual_winners['pred_rank'] <= 3
        top_3_hit_rate = (actual_winners['in_top_3'].sum() / len(actual_winners)) * 100
        
        # MRR
        mrr = (1.0 / actual_winners['pred_rank']).mean()
        
        # === PROBABILITY SPREAD ===
        prob_spread = {
            'min': float(np.min(probabilities)),
            'max': float(np.max(probabilities)),
            'mean': float(np.mean(probabilities)),
            'std': float(np.std(probabilities)),
            'q25': float(np.percentile(probabilities, 25)),
            'q75': float(np.percentile(probabilities, 75))
        }
        
        # === CALIBRATION ERROR ===
        n_bins = 10
        bin_edges = np.linspace(0, 1, n_bins + 1)
        bin_indices = np.digitize(probabilities, bin_edges[:-1]) - 1
        bin_indices = np.clip(bin_indices, 0, n_bins - 1)
        
        calibration_error = 0.0
        for i in range(n_bins):
            mask = bin_indices == i
            if np.sum(mask) > 0:
                bin_mean_pred = np.mean(probabilities[mask])
                bin_mean_true = np.mean(y_true[mask])
                bin_weight = np.sum(mask) / len(y_true)
                calibration_error += bin_weight * abs(bin_mean_pred - bin_mean_true)
        
        return {
            'nll': nll,
            'brier': brier,
            'calibration_error': calibration_error,
            'top_pick_accuracy': top_pick_accuracy,
            'top_3_hit_rate': top_3_hit_rate,
            'mrr': mrr,
            'prob_spread': prob_spread
        }
    
    def evaluate_all_models(self) -> Dict:
        """Evaluate all models and return comparison table"""
        logger.info("\n" + "="*60)
        logger.info("EVALUATING ALL MODELS")
        logger.info("="*60)
        
        results = {}
        for model_name in self.models.keys():
            logger.info(f"\nEvaluating {model_name}...")
            probabilities = self.generate_predictions(model_name)
            metrics = self.compute_metrics(probabilities)
            results[model_name] = {
                'probabilities': probabilities,
                'metrics': metrics
            }
            logger.info(f"  Top Pick: {metrics['top_pick_accuracy']:.1f}%")
            logger.info(f"  Prob range: {metrics['prob_spread']['min']:.1%} to {metrics['prob_spread']['max']:.1%}")
        
        return results
    
    def print_comparison_table(self, results: Dict):
        """Print formatted comparison table"""
        logger.info("\n" + "="*80)
        logger.info("MODEL COMPARISON RESULTS")
        logger.info("="*80)
        
        # Header
        print(f"\n{'Model':<15} | {'Top Pick':<9} | {'Top 3':<8} | {'MRR':<6} | {'Prob Spread':<15} | {'Calib Err':<10} | {'NLL':<6}")
        print("-" * 95)
        
        # Rows
        for model_name, data in results.items():
            metrics = data['metrics']
            spread = metrics['prob_spread']
            prob_range = f"{spread['min']:.1%}-{spread['max']:.1%}"
            
            print(f"{model_name:<15} | "
                  f"{metrics['top_pick_accuracy']:>8.1f}% | "
                  f"{metrics['top_3_hit_rate']:>7.1f}% | "
                  f"{metrics['mrr']:>6.4f} | "
                  f"{prob_range:>15} | "
                  f"{metrics['calibration_error']:>10.4f} | "
                  f"{metrics['nll']:>6.4f}")
        
        print()
        
        # Best per metric
        best_top_pick = max(results.items(), key=lambda x: x[1]['metrics']['top_pick_accuracy'])
        best_calibration = min(results.items(), key=lambda x: x[1]['metrics']['calibration_error'])
        best_discrimination = max(results.items(), key=lambda x: x[1]['metrics']['prob_spread']['std'])
        
        logger.info("\n📊 BEST PERFORMERS:")
        logger.info(f"  Best Top Pick Accuracy: {best_top_pick[0]} ({best_top_pick[1]['metrics']['top_pick_accuracy']:.1f}%)")
        logger.info(f"  Best Calibration: {best_calibration[0]} (error: {best_calibration[1]['metrics']['calibration_error']:.4f})")
        logger.info(f"  Best Discrimination: {best_discrimination[0]} (std: {best_discrimination[1]['metrics']['prob_spread']['std']:.4f})")
    
    def plot_probability_distributions(self, results: Dict, output_path: str):
        """Plot probability distributions for all models"""
        logger.info("\nGenerating probability distribution plot...")
        
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        axes = axes.flatten()
        
        for idx, (model_name, data) in enumerate(results.items()):
            probabilities = data['probabilities']
            ax = axes[idx]
            
            ax.hist(probabilities, bins=50, alpha=0.7, edgecolor='black')
            ax.set_title(f'{model_name.upper()}\nRange: {probabilities.min():.1%} to {probabilities.max():.1%}')
            ax.set_xlabel('Win Probability')
            ax.set_ylabel('Frequency')
            ax.grid(alpha=0.3)
            
            # Add statistics
            stats_text = f'Mean: {probabilities.mean():.1%}\nStd: {probabilities.std():.4f}'
            ax.text(0.95, 0.95, stats_text, transform=ax.transAxes,
                   verticalalignment='top', horizontalalignment='right',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        # Hide unused subplots
        for idx in range(len(results), len(axes)):
            axes[idx].axis('off')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        logger.info(f"✓ Saved probability distributions to {output_path}")
        plt.close()
    
    def plot_calibration_curves(self, results: Dict, output_path: str):
        """Plot calibration curves for all models"""
        logger.info("\nGenerating calibration curves...")
        
        fig, ax = plt.subplots(figsize=(10, 10))
        
        y_true = self.test_data['won'].values
        n_bins = 10
        
        for model_name, data in results.items():
            probabilities = data['probabilities']
            
            # Compute calibration curve
            bin_edges = np.linspace(0, 1, n_bins + 1)
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
            bin_indices = np.digitize(probabilities, bin_edges[:-1]) - 1
            bin_indices = np.clip(bin_indices, 0, n_bins - 1)
            
            bin_means_pred = []
            bin_means_true = []
            
            for i in range(n_bins):
                mask = bin_indices == i
                if np.sum(mask) > 0:
                    bin_means_pred.append(np.mean(probabilities[mask]))
                    bin_means_true.append(np.mean(y_true[mask]))
                else:
                    bin_means_pred.append(bin_centers[i])
                    bin_means_true.append(bin_centers[i])
            
            ax.plot(bin_means_pred, bin_means_true, 'o-', label=model_name, linewidth=2)
        
        # Perfect calibration line
        ax.plot([0, 1], [0, 1], 'k--', label='Perfect Calibration', linewidth=2)
        
        ax.set_xlabel('Predicted Probability', fontsize=12)
        ax.set_ylabel('Actual Win Rate', fontsize=12)
        ax.set_title('Calibration Curves - All Models', fontsize=14)
        ax.legend()
        ax.grid(alpha=0.3)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        logger.info(f"✓ Saved calibration curves to {output_path}")
        plt.close()
    
    def save_comparison_report(self, results: Dict, output_path: str):
        """Save comparison metrics to CSV"""
        rows = []
        for model_name, data in results.items():
            metrics = data['metrics']
            spread = metrics['prob_spread']
            
            rows.append({
                'model': model_name,
                'top_pick_accuracy': metrics['top_pick_accuracy'],
                'top_3_hit_rate': metrics['top_3_hit_rate'],
                'mrr': metrics['mrr'],
                'nll': metrics['nll'],
                'brier': metrics['brier'],
                'calibration_error': metrics['calibration_error'],
                'prob_min': spread['min'],
                'prob_max': spread['max'],
                'prob_mean': spread['mean'],
                'prob_std': spread['std'],
                'prob_q25': spread['q25'],
                'prob_q75': spread['q75']
            })
        
        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)
        logger.info(f"✓ Saved comparison report to {output_path}")


def main():
    """Run model comparison"""
    # Paths
    db_path = 'Datafetch/racing_pro.db'
    models_dir = 'Datafetch/ml/models'
    
    # Initialize comparison
    comparison = ModelComparison(db_path, models_dir, race_type='Flat')
    
    # Load everything
    comparison.load_feature_columns()
    comparison.load_models()
    comparison.load_test_data(test_size=0.2)
    
    # Evaluate all models
    results = comparison.evaluate_all_models()
    
    # Print comparison table
    comparison.print_comparison_table(results)
    
    # Generate visualizations
    comparison.plot_probability_distributions(results, f'{models_dir}/probability_distributions.png')
    comparison.plot_calibration_curves(results, f'{models_dir}/calibration_curves.png')
    
    # Save report
    comparison.save_comparison_report(results, f'{models_dir}/model_comparison_report.csv')
    
    logger.info("\n" + "="*80)
    logger.info("✅ MODEL COMPARISON COMPLETE")
    logger.info("="*80)
    logger.info(f"Results saved to: {models_dir}/")


if __name__ == '__main__':
    main()

