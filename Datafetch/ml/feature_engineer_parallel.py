#!/usr/bin/env python3
"""
Parallel Feature Engineering Pipeline
Uses multiprocessing to speed up feature generation on multi-core systems
"""

import sqlite3
import logging
import numpy as np
from pathlib import Path
from typing import Optional
from multiprocessing import Pool, cpu_count
from functools import partial

from .feature_engineer import FeatureEngineer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_race_batch(race_ids: list, db_path: Path) -> tuple:
    """
    Process a batch of races in a single worker process
    Returns (num_races_processed, num_runners_processed)
    """
    engineer = FeatureEngineer(db_path)
    engineer.connect()
    
    total_runners = 0
    races_processed = 0
    
    try:
        for race_id in race_ids:
            runners = engineer.process_race(race_id)
            if runners > 0:
                total_runners += runners
                races_processed += 1
        
        # Commit at end of batch
        engineer.conn.commit()
        
    except Exception as e:
        logger.error(f"Error in worker process: {e}")
    finally:
        engineer.close()
    
    return races_processed, total_runners


def generate_features_parallel(db_path: Path, limit: Optional[int] = None, 
                               num_workers: Optional[int] = None):
    """
    Generate features using multiple worker processes
    
    Args:
        db_path: Path to database
        limit: Limit number of races (for testing)
        num_workers: Number of worker processes (default: CPU count - 1)
    """
    logger.info("="*60)
    logger.info("PARALLEL FEATURE GENERATION")
    logger.info("="*60)
    
    # Determine number of workers
    if num_workers is None:
        num_workers = max(1, cpu_count() - 1)  # Leave one core free
    
    logger.info(f"Using {num_workers} worker processes")
    logger.info(f"CPU cores available: {cpu_count()}")
    
    # Get all race IDs
    engineer = FeatureEngineer(db_path)
    engineer.connect()
    race_ids = engineer.get_races_with_results(limit=limit)
    engineer.close()
    
    total_races = len(race_ids)
    logger.info(f"Found {total_races:,} races with results")
    
    if total_races == 0:
        logger.warning("No races to process")
        return
    
    # Split races into batches for workers
    batch_size = max(10, total_races // (num_workers * 4))  # 4 batches per worker
    batches = []
    
    for i in range(0, total_races, batch_size):
        batch = race_ids[i:i + batch_size]
        batches.append(batch)
    
    logger.info(f"Split into {len(batches)} batches of ~{batch_size} races each")
    logger.info(f"Starting parallel processing...")
    
    # Process batches in parallel
    process_func = partial(process_race_batch, db_path=db_path)
    
    total_runners = 0
    completed_races = 0
    
    with Pool(processes=num_workers) as pool:
        # Use imap for progress tracking
        for i, (races_done, runners_done) in enumerate(pool.imap(process_func, batches), 1):
            completed_races += races_done
            total_runners += runners_done
            
            if i % 10 == 0 or i == len(batches):
                progress_pct = (completed_races / total_races) * 100
                logger.info(f"  Progress: {completed_races:,}/{total_races:,} races ({progress_pct:.1f}%) - {total_runners:,} runners")
    
    logger.info("="*60)
    logger.info("✓ PARALLEL FEATURE GENERATION COMPLETE")
    logger.info(f"  Races processed: {completed_races:,}")
    logger.info(f"  Runners processed: {total_runners:,}")
    logger.info(f"  Workers used: {num_workers}")
    logger.info("="*60)


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate ML features in parallel')
    parser.add_argument('--limit', type=int, help='Limit number of races (for testing)')
    parser.add_argument('--test', action='store_true', help='Test mode (first 100 races)')
    parser.add_argument('--workers', type=int, help='Number of worker processes')
    
    args = parser.parse_args()
    
    limit = args.limit
    if args.test:
        limit = 100
        logger.info("TEST MODE: Processing first 100 races only")
    
    db_path = Path(__file__).parent.parent / "racing_pro.db"
    
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        return 1
    
    try:
        import time
        start_time = time.time()
        
        generate_features_parallel(db_path, limit=limit, num_workers=args.workers)
        
        elapsed = time.time() - start_time
        logger.info(f"\n⏱️  Total time: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
        
        return 0
    except Exception as e:
        logger.error(f"Feature generation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

