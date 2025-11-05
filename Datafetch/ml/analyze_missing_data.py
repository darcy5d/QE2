#!/usr/bin/env python3
"""
Analyze missing data patterns in our features
Check if flat probabilities correlate with high missing data rates
"""

import sqlite3
import pandas as pd
import numpy as np
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    db_path = Path("Datafetch/racing_pro.db")
    models_dir = Path("Datafetch/ml/models")
    
    # Load feature columns
    with open(models_dir / "feature_columns_flat.json") as f:
        feature_columns = json.load(f)
    
    logger.info(f"Analyzing {len(feature_columns)} features")
    
    # Load data
    conn = sqlite3.connect(str(db_path))
    
    query = """
        SELECT 
            f.race_id,
            f.runner_id,
            r.date,
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
    
    logger.info(f"\nLoaded {len(df):,} rows from {df['race_id'].nunique():,} races")
    logger.info(f"Date range: {df['date'].min()} to {df['date'].max()}")
    
    # Split into train/test temporally
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()
    
    logger.info(f"\nTrain: {len(train_df):,} rows, {train_df['race_id'].nunique():,} races")
    logger.info(f"  Date range: {train_df['date'].min()} to {train_df['date'].max()}")
    logger.info(f"Test: {len(test_df):,} rows, {test_df['race_id'].nunique():,} races")
    logger.info(f"  Date range: {test_df['date'].min()} to {test_df['date'].max()}")
    
    # Analyze missing data for each feature
    logger.info("\n" + "="*80)
    logger.info("MISSING DATA ANALYSIS")
    logger.info("="*80)
    
    missing_stats = []
    
    for col in feature_columns:
        if col not in df.columns:
            continue
            
        # Count nulls before conversion
        null_count_train = train_df[col].isnull().sum()
        null_count_test = test_df[col].isnull().sum()
        
        # Convert to numeric and check what becomes NaN
        train_numeric = pd.to_numeric(train_df[col], errors='coerce')
        test_numeric = pd.to_numeric(test_df[col], errors='coerce')
        
        nan_count_train = train_numeric.isnull().sum()
        nan_count_test = test_numeric.isnull().sum()
        
        pct_missing_train = (nan_count_train / len(train_df)) * 100
        pct_missing_test = (nan_count_test / len(test_df)) * 100
        
        missing_stats.append({
            'feature': col,
            'train_missing_pct': pct_missing_train,
            'test_missing_pct': pct_missing_test,
            'difference': pct_missing_test - pct_missing_train,
            'train_null': null_count_train,
            'train_nan_after_convert': nan_count_train - null_count_train
        })
    
    stats_df = pd.DataFrame(missing_stats)
    stats_df = stats_df.sort_values('test_missing_pct', ascending=False)
    
    # Show worst offenders
    logger.info("\n🚨 TOP 20 FEATURES WITH HIGHEST MISSING DATA IN TEST SET:")
    logger.info("-" * 80)
    for _, row in stats_df.head(20).iterrows():
        logger.info(f"{row['feature']:40s} | Train: {row['train_missing_pct']:5.1f}% | Test: {row['test_missing_pct']:5.1f}% | Δ: {row['difference']:+5.1f}%")
    
    # Check if missing data increased from train to test
    logger.info("\n⚠️  FEATURES WITH SIGNIFICANTLY MORE MISSING DATA IN TEST:")
    logger.info("-" * 80)
    increased = stats_df[stats_df['difference'] > 5].sort_values('difference', ascending=False)
    if len(increased) > 0:
        for _, row in increased.iterrows():
            logger.info(f"{row['feature']:40s} | Train: {row['train_missing_pct']:5.1f}% | Test: {row['test_missing_pct']:5.1f}% | Δ: {row['difference']:+5.1f}%")
    else:
        logger.info("✓ No features with significantly increased missing data")
    
    # Overall stats
    logger.info("\n📊 OVERALL MISSING DATA STATISTICS:")
    logger.info("-" * 80)
    logger.info(f"Average missing % in TRAIN: {stats_df['train_missing_pct'].mean():.2f}%")
    logger.info(f"Average missing % in TEST:  {stats_df['test_missing_pct'].mean():.2f}%")
    logger.info(f"Features with >50% missing in TRAIN: {(stats_df['train_missing_pct'] > 50).sum()}")
    logger.info(f"Features with >50% missing in TEST:  {(stats_df['test_missing_pct'] > 50).sum()}")
    logger.info(f"Features with >80% missing in TRAIN: {(stats_df['train_missing_pct'] > 80).sum()}")
    logger.info(f"Features with >80% missing in TEST:  {(stats_df['test_missing_pct'] > 80).sum()}")
    
    # Check non-null but non-numeric (these become NaN after conversion)
    logger.info("\n🔍 FEATURES WITH NON-NUMERIC VALUES (converted to NaN):")
    logger.info("-" * 80)
    non_numeric = stats_df[stats_df['train_nan_after_convert'] > 0].sort_values('train_nan_after_convert', ascending=False)
    if len(non_numeric) > 0:
        for _, row in non_numeric.head(10).iterrows():
            logger.info(f"{row['feature']:40s} | {row['train_nan_after_convert']:,} non-numeric values")
    else:
        logger.info("✓ All non-null values are numeric")
    
    # Save report
    output_path = Path("Datafetch/ml/models/missing_data_analysis.csv")
    stats_df.to_csv(output_path, index=False)
    logger.info(f"\n✓ Saved detailed report to {output_path}")
    
    # Analyze per-race missing data rates
    logger.info("\n" + "="*80)
    logger.info("PER-RACE MISSING DATA ANALYSIS")
    logger.info("="*80)
    
    # Calculate missing rate per row
    test_features = test_df[feature_columns].copy()
    for col in test_features.columns:
        test_features[col] = pd.to_numeric(test_features[col], errors='coerce')
    
    test_df['missing_rate'] = test_features.isnull().sum(axis=1) / len(feature_columns) * 100
    
    # Group by race and calculate average missing rate
    race_missing = test_df.groupby('race_id').agg({
        'missing_rate': 'mean',
        'runner_id': 'count'
    }).rename(columns={'runner_id': 'num_runners'})
    
    logger.info(f"\nMissing data per race in TEST set:")
    logger.info(f"  Average: {race_missing['missing_rate'].mean():.2f}% of features missing per race")
    logger.info(f"  Median: {race_missing['missing_rate'].median():.2f}%")
    logger.info(f"  Min: {race_missing['missing_rate'].min():.2f}%")
    logger.info(f"  Max: {race_missing['missing_rate'].max():.2f}%")
    logger.info(f"  Std: {race_missing['missing_rate'].std():.2f}%")
    
    # Show races with highest missing data
    logger.info("\n🚨 RACES WITH HIGHEST MISSING DATA RATES:")
    logger.info("-" * 80)
    worst_races = race_missing.nlargest(10, 'missing_rate')
    for race_id, row in worst_races.iterrows():
        race_date = test_df[test_df['race_id'] == race_id]['date'].iloc[0]
        logger.info(f"{race_id} ({race_date}) | {row['num_runners']} runners | {row['missing_rate']:.1f}% missing")
    
    # Check correlation between missing data and flat probabilities
    # A race has "flat" probabilities if all horses have similar probabilities
    # We'll use the missing rate as a proxy for now
    
    logger.info("\n" + "="*80)
    logger.info("🎯 KEY INSIGHTS")
    logger.info("="*80)
    
    high_missing_pct = (stats_df['test_missing_pct'] > 50).sum() / len(stats_df) * 100
    logger.info(f"• {high_missing_pct:.1f}% of features have >50% missing data in test set")
    
    if stats_df['difference'].mean() > 2:
        logger.info(f"• ⚠️  Test set has {stats_df['difference'].mean():.1f}% MORE missing data than train set on average")
        logger.info("  This could explain worse generalization!")
    else:
        logger.info(f"• ✓ Test set has similar missing data rates to train set")
    
    if race_missing['missing_rate'].std() > 10:
        logger.info(f"• ⚠️  High variance in missing data across races (std: {race_missing['missing_rate'].std():.1f}%)")
        logger.info("  Some races have much more missing data than others!")


if __name__ == "__main__":
    main()

