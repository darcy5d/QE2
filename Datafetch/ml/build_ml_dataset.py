#!/usr/bin/env python3
"""
Build ML Dataset - Orchestration script
Runs the full pipeline: stats → features → validation

Usage:
    python build_ml_dataset.py [--test]
"""

import logging
import sys
from pathlib import Path
import time

from compute_stats import StatsComputer
from feature_engineer import FeatureEngineer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_results_available(db_path: Path) -> bool:
    """Check if we have results data"""
    import sqlite3
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM results")
    result_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT race_id) FROM results")
    race_count = cursor.fetchone()[0]
    
    conn.close()
    
    logger.info(f"Current data: {result_count:,} results across {race_count:,} races")
    
    return result_count > 0


def validate_stats(db_path: Path):
    """Validate that stats were computed correctly"""
    import sqlite3
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    logger.info("\nValidating statistics...")
    
    # Check horse stats
    cursor.execute("SELECT COUNT(*) FROM horse_career_stats WHERE total_runs > 0")
    horse_count = cursor.fetchone()[0]
    logger.info(f"  ✓ Horse stats: {horse_count:,} horses")
    
    # Check trainer stats
    cursor.execute("SELECT COUNT(*) FROM trainer_stats")
    trainer_count = cursor.fetchone()[0]
    logger.info(f"  ✓ Trainer stats: {trainer_count:,} records")
    
    # Check jockey stats
    cursor.execute("SELECT COUNT(*) FROM jockey_stats")
    jockey_count = cursor.fetchone()[0]
    logger.info(f"  ✓ Jockey stats: {jockey_count:,} records")
    
    # Check combos
    cursor.execute("SELECT COUNT(*) FROM trainer_jockey_combos")
    combo_count = cursor.fetchone()[0]
    logger.info(f"  ✓ Trainer-Jockey combos: {combo_count:,} records")
    
    conn.close()


def validate_features(db_path: Path):
    """Validate that features were generated correctly"""
    import sqlite3
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    logger.info("\nValidating features...")
    
    # Check feature count
    cursor.execute("SELECT COUNT(*) FROM ml_features")
    feature_count = cursor.fetchone()[0]
    logger.info(f"  ✓ Features: {feature_count:,} runners")
    
    # Check target count
    cursor.execute("SELECT COUNT(*) FROM ml_targets")
    target_count = cursor.fetchone()[0]
    logger.info(f"  ✓ Targets: {target_count:,} runners with results")
    
    # Check feature completeness (sample)
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(horse_age) as has_age,
            COUNT(horse_win_rate) as has_win_rate,
            COUNT(trainer_win_rate_90d) as has_trainer_rate,
            COUNT(jockey_win_rate_90d) as has_jockey_rate,
            COUNT(ofr) as has_rating
        FROM ml_features
        LIMIT 1000
    """)
    
    row = cursor.fetchone()
    logger.info(f"  Feature completeness (sample of 1000):")
    logger.info(f"    Age: {row[1]}/1000 ({row[1]/10:.1f}%)")
    logger.info(f"    Horse win rate: {row[2]}/1000 ({row[2]/10:.1f}%)")
    logger.info(f"    Trainer rate: {row[3]}/1000 ({row[3]/10:.1f}%)")
    logger.info(f"    Jockey rate: {row[4]}/1000 ({row[4]/10:.1f}%)")
    logger.info(f"    Rating: {row[5]}/1000 ({row[5]/10:.1f}%)")
    
    # Check a sample race
    cursor.execute("""
        SELECT race_id, COUNT(*) as runner_count
        FROM ml_features
        GROUP BY race_id
        LIMIT 1
    """)
    
    sample = cursor.fetchone()
    if sample:
        logger.info(f"\n  Sample race {sample[0]}: {sample[1]} runners with features")
    
    conn.close()


def main():
    """Main orchestration"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Build ML dataset')
    parser.add_argument('--test', action='store_true', help='Test mode (limited data)')
    parser.add_argument('--skip-stats', action='store_true', help='Skip stats computation')
    parser.add_argument('--skip-features', action='store_true', help='Skip feature generation')
    
    args = parser.parse_args()
    
    db_path = Path(__file__).parent.parent / "racing_pro.db"
    
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        return 1
    
    # Check for results data
    if not check_results_available(db_path):
        logger.error("No results data found. Run fetch_historical_results.py first.")
        return 1
    
    try:
        start_time = time.time()
        
        # Step 1: Compute statistics
        if not args.skip_stats:
            logger.info("\n" + "="*60)
            logger.info("STEP 1: Computing Statistics")
            logger.info("="*60 + "\n")
            
            computer = StatsComputer(db_path)
            computer.compute_all_stats()
            
            validate_stats(db_path)
        else:
            logger.info("Skipping stats computation (--skip-stats)")
        
        # Step 2: Generate features
        if not args.skip_features:
            logger.info("\n" + "="*60)
            logger.info("STEP 2: Generating Features")
            logger.info("="*60 + "\n")
            
            limit = 50 if args.test else None
            if args.test:
                logger.info("TEST MODE: Processing first 50 races only")
            
            engineer = FeatureEngineer(db_path)
            engineer.generate_features_for_all_races(limit=limit)
            
            validate_features(db_path)
        else:
            logger.info("Skipping feature generation (--skip-features)")
        
        elapsed = time.time() - start_time
        
        logger.info("\n" + "="*60)
        logger.info("✓ ML DATASET BUILD COMPLETE")
        logger.info(f"  Time elapsed: {elapsed/60:.1f} minutes")
        logger.info("="*60)
        
        logger.info("\nNext steps:")
        logger.info("  1. Explore data in GUI Data Exploration tab")
        logger.info("  2. Train baseline XGBoost model")
        logger.info("  3. Evaluate performance metrics")
        
        return 0
        
    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Error building dataset: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())


