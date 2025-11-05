#!/usr/bin/env python3
"""
Check if flat probabilities correlate with missing data rates
"""

import sqlite3
import pandas as pd
import numpy as np
import xgboost as xgb
import json
import logging
from pathlib import Path
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    db_path = Path("Datafetch/racing_pro.db")
    models_dir = Path("Datafetch/ml/models")
    
    # Load feature columns and model
    with open(models_dir / "feature_columns_flat.json") as f:
        feature_columns = json.load(f)
    
    # Load baseline model
    baseline_model = xgb.Booster()
    baseline_model.load_model(str(models_dir / "xgboost_flat.json"))
    
    # Load test data
    conn = sqlite3.connect(str(db_path))
    
    query = """
        SELECT 
            f.race_id,
            f.runner_id,
            r.date,
            r.course,
            res.position_int as position,
            {features}
        FROM ml_features f
        JOIN races r ON f.race_id = r.race_id
        JOIN results res ON f.race_id = res.race_id AND f.horse_id = res.horse_id
        WHERE r.type = 'Flat'
        AND res.position_int < 900
        ORDER BY r.date, f.race_id, f.runner_id
    """.format(features=', '.join([f'f.{col}' for col in feature_columns]))
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Take test set (last 20%)
    split_idx = int(len(df) * 0.8)
    test_df = df.iloc[split_idx:].copy()
    
    logger.info(f"Analyzing {len(test_df):,} test samples from {test_df['race_id'].nunique():,} races")
    
    # Calculate missing rate per sample
    test_features = test_df[feature_columns].copy()
    for col in test_features.columns:
        test_features[col] = pd.to_numeric(test_features[col], errors='coerce')
    
    test_df['missing_rate'] = test_features.isnull().sum(axis=1) / len(feature_columns) * 100
    
    # Fill missing values (as models do)
    for col in feature_columns:
        if col not in test_features.columns:
            continue
        median_val = test_features[col].median()
        if pd.isna(median_val):
            median_val = 0
        test_features[col] = test_features[col].fillna(median_val)
    
    # Get predictions
    dmatrix = xgb.DMatrix(test_features, feature_names=feature_columns)
    raw_scores = baseline_model.predict(dmatrix)
    test_df['raw_score'] = raw_scores
    
    # Convert to probabilities per race
    def scores_to_probs(scores):
        scores = scores.values
        exp_scores = np.exp(scores - np.max(scores))
        return exp_scores / exp_scores.sum()
    
    test_df['probability'] = test_df.groupby('race_id')['raw_score'].transform(scores_to_probs)
    
    # Calculate "flatness" per race
    # Flatness = 1 - std(probabilities) / max_possible_std
    # A race with all equal probabilities has flatness = 1
    # A race with one horse at 100% has flatness = 0
    
    race_stats = test_df.groupby('race_id').agg({
        'probability': ['std', 'min', 'max', lambda x: x.max() - x.min()],
        'missing_rate': 'mean',
        'runner_id': 'count',
        'date': 'first',
        'course': 'first'
    })
    
    race_stats.columns = ['prob_std', 'prob_min', 'prob_max', 'prob_range', 'missing_rate', 'num_runners', 'date', 'course']
    
    # Calculate expected std for uniform distribution
    race_stats['uniform_prob'] = 1 / race_stats['num_runners']
    race_stats['uniform_std'] = np.sqrt(race_stats['uniform_prob'] * (1 - race_stats['uniform_prob']) / race_stats['num_runners'])
    
    # Flatness score: how close to uniform distribution
    # 0 = highly discriminating, 1 = completely flat
    race_stats['flatness'] = 1 - (race_stats['prob_std'] / race_stats['uniform_std']).clip(upper=10)
    
    logger.info("\n" + "="*80)
    logger.info("CORRELATION: MISSING DATA vs FLAT PROBABILITIES")
    logger.info("="*80)
    
    # Correlation
    correlation = race_stats['missing_rate'].corr(race_stats['flatness'])
    logger.info(f"\nPearson correlation: {correlation:.4f}")
    
    if abs(correlation) > 0.3:
        logger.info(f"🚨 STRONG correlation! Missing data {'CAUSES' if correlation > 0 else 'prevents'} flat probabilities!")
    elif abs(correlation) > 0.1:
        logger.info(f"⚠️  Moderate correlation. Missing data {'tends to cause' if correlation > 0 else 'tends to prevent'} flat probabilities.")
    else:
        logger.info(f"✓ Weak correlation. Missing data doesn't strongly affect probability flatness.")
    
    # Show flat races
    logger.info("\n🔍 FLATTEST RACES (most uniform probabilities):")
    logger.info("-" * 80)
    flattest = race_stats.nlargest(15, 'flatness')
    for race_id, row in flattest.iterrows():
        logger.info(f"{race_id} ({row['date']}, {row['course']}) | {row['num_runners']:.0f} runners | Prob range: {row['prob_min']:.3f}-{row['prob_max']:.3f} | Missing: {row['missing_rate']:.1f}%")
    
    # Show discriminating races
    logger.info("\n🎯 MOST DISCRIMINATING RACES:")
    logger.info("-" * 80)
    discriminating = race_stats.nsmallest(15, 'flatness')
    for race_id, row in discriminating.iterrows():
        logger.info(f"{race_id} ({row['date']}, {row['course']}) | {row['num_runners']:.0f} runners | Prob range: {row['prob_min']:.3f}-{row['prob_max']:.3f} | Missing: {row['missing_rate']:.1f}%")
    
    # Binned analysis
    logger.info("\n📊 MISSING DATA BINS vs FLATNESS:")
    logger.info("-" * 80)
    
    race_stats['missing_bin'] = pd.cut(race_stats['missing_rate'], bins=[0, 10, 15, 20, 25, 100], 
                                        labels=['0-10%', '10-15%', '15-20%', '20-25%', '>25%'])
    
    bin_stats = race_stats.groupby('missing_bin').agg({
        'flatness': ['mean', 'std', 'count'],
        'prob_std': 'mean',
        'prob_range': 'mean'
    })
    
    logger.info(bin_stats.to_string())
    
    # Visualization
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Scatter plot
    ax = axes[0]
    ax.scatter(race_stats['missing_rate'], race_stats['flatness'], alpha=0.3, s=10)
    ax.set_xlabel('Missing Data Rate (%)')
    ax.set_ylabel('Flatness Score (0=discriminating, 1=flat)')
    ax.set_title(f'Missing Data vs Probability Flatness\n(Correlation: {correlation:.3f})')
    ax.grid(alpha=0.3)
    
    # Add trend line
    z = np.polyfit(race_stats['missing_rate'], race_stats['flatness'], 1)
    p = np.poly1d(z)
    x_line = np.linspace(race_stats['missing_rate'].min(), race_stats['missing_rate'].max(), 100)
    ax.plot(x_line, p(x_line), "r--", alpha=0.8, linewidth=2, label=f'Trend: y={z[0]:.4f}x+{z[1]:.4f}')
    ax.legend()
    
    # Box plot by bins
    ax = axes[1]
    race_stats.boxplot(column='flatness', by='missing_bin', ax=ax)
    ax.set_xlabel('Missing Data Rate')
    ax.set_ylabel('Flatness Score')
    ax.set_title('Flatness Distribution by Missing Data Rate')
    plt.suptitle('')  # Remove default title
    
    plt.tight_layout()
    output_path = models_dir / "missing_data_vs_flatness.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    logger.info(f"\n✓ Saved visualization to {output_path}")
    
    # Key insights
    logger.info("\n" + "="*80)
    logger.info("🎯 KEY INSIGHTS")
    logger.info("="*80)
    
    high_missing = race_stats[race_stats['missing_rate'] > 20]
    low_missing = race_stats[race_stats['missing_rate'] < 12]
    
    logger.info(f"\nRaces with >20% missing data:")
    logger.info(f"  Count: {len(high_missing)}")
    logger.info(f"  Average flatness: {high_missing['flatness'].mean():.3f}")
    logger.info(f"  Average prob std: {high_missing['prob_std'].mean():.4f}")
    
    logger.info(f"\nRaces with <12% missing data:")
    logger.info(f"  Count: {len(low_missing)}")
    logger.info(f"  Average flatness: {low_missing['flatness'].mean():.3f}")
    logger.info(f"  Average prob std: {low_missing['prob_std'].mean():.4f}")
    
    if high_missing['flatness'].mean() > low_missing['flatness'].mean():
        diff = high_missing['flatness'].mean() - low_missing['flatness'].mean()
        logger.info(f"\n🚨 HIGH missing data races are {diff:.3f} points FLATTER on average!")
        logger.info("   YOUR THESIS IS CORRECT - missing data causes flat probabilities!")
    else:
        logger.info(f"\n✓ Missing data doesn't significantly increase flatness")


if __name__ == "__main__":
    main()

