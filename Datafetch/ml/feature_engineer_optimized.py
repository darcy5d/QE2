#!/usr/bin/env python3
"""
Optimized Feature Engineering - Compute in parallel, write in batches
Avoids SQLite write lock contention
"""

import sqlite3
import logging
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict
from multiprocessing import Pool, cpu_count
from functools import partial
import time

from .feature_engineer import FeatureEngineer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def compute_race_features(race_id: str, db_path: Path) -> tuple:
    """
    Compute features for a race (NO DATABASE WRITES)
    Returns (race_id, features_list, targets_list)
    """
    engineer = FeatureEngineer(db_path)
    engineer.connect()
    
    try:
        # Get race context
        race_context = engineer.get_race_context_features(race_id)
        if not race_context:
            engineer.close()
            return race_id, [], []
        
        # Get all runners
        runners = engineer.get_runners_for_race(race_id)
        if not runners:
            engineer.close()
            return race_id, [], []
        
        # Compute features for each runner (in memory only)
        all_features = []
        all_targets = []
        
        for runner in runners:
            result = engineer.get_runner_result(race_id, runner['horse_id'])
            try:
                features = engineer.compute_runner_features(runner, race_context, result)
                all_features.append(features)
            except TypeError as e:
                if "'<=' not supported between instances of 'dict' and 'int'" in str(e):
                    # DIAGNOSTIC: Log the exact values causing the error
                    import json
                    logger.error(f"DIAGNOSTIC for {race_id}:")
                    logger.error(f"  race_context keys: {list(race_context.keys())}")
                    for k, v in race_context.items():
                        logger.error(f"    {k}: {type(v).__name__} = {repr(v)[:100]}")
                    logger.error(f"  runner keys: {list(runner.keys())}")
                    logger.error(f"  Full error: {e}")
                    import traceback
                    logger.error(f"  Traceback:\n{traceback.format_exc()}")
                raise
            
            # Compute targets (with distance for speed calculation)
            distance_f = race_context.get('distance_f') if race_context else None
            targets = engineer.compute_target_variables(
                race_id, runner['horse_id'], runner['runner_id'], result, distance_f
            )
            if targets:
                all_targets.append(targets)
        
        # Post-process: Compute speed_deficit (Model 4 target)
        if all_targets:
            winner_speed = None
            for target in all_targets:
                if target.get('position') == 1 and target.get('speed') is not None:
                    winner_speed = target['speed']
                    break
            
            if winner_speed is not None:
                for target in all_targets:
                    if target.get('speed') is not None:
                        target['speed_deficit'] = target['speed'] - winner_speed
                    else:
                        target['speed_deficit'] = None
        
        # Compute relative features
        all_features = engineer.compute_relative_features(all_features)
        
        # Compute draw bias
        for features in all_features:
            draw = features.get('draw')
            if draw is not None:
                draw_bias = engineer.compute_draw_bias(
                    race_context.get('course'),
                    race_context.get('distance_f'),
                    draw,
                    features['field_size'],
                    race_context.get('date')
                )
                features['course_distance_draw_bias'] = draw_bias['course_distance_draw_bias']
                features['draw_position_normalized'] = draw_bias['draw_position_normalized']
                features['low_draw_advantage'] = draw_bias['low_draw_advantage']
                features['high_draw_advantage'] = draw_bias['high_draw_advantage']
        
        engineer.close()
        return race_id, all_features, all_targets
        
    except Exception as e:
        import traceback
        logger.error(f"EXCEPTION for {race_id}:")
        logger.error(f"  Type: {type(e).__name__}")
        logger.error(f"  Message: {repr(e)}")
        logger.error(f"  Traceback:\n{traceback.format_exc()}")
        engineer.close()
        return race_id, [], []


def write_features_batch(features_batch: List[Dict], targets_batch: List[Dict], db_path: Path):
    """
    Write a batch of features to database (single-threaded)
    """
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    
    engineer = FeatureEngineer(db_path)
    engineer.conn = conn
    
    for features in features_batch:
        engineer.save_features(features)
    
    for targets in targets_batch:
        engineer.save_targets(targets)
    
    conn.commit()
    conn.close()


def generate_features_optimized(db_path: Path, limit: Optional[int] = None, 
                                num_workers: Optional[int] = None):
    """
    Optimized feature generation:
    1. Compute features in parallel (CPU intensive)
    2. Write to database in batches (single-threaded, I/O intensive)
    """
    logger.info("="*60)
    logger.info("OPTIMIZED PARALLEL FEATURE GENERATION")
    logger.info("="*60)
    
    # Determine number of workers
    if num_workers is None:
        num_workers = max(1, cpu_count() - 1)
    
    logger.info(f"Using {num_workers} worker processes for computation")
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
        return {'races_processed': 0, 'runners_processed': 0, 'workers': 0}
    
    logger.info("Strategy: Compute in parallel, write in batches")
    logger.info("Starting feature computation...")
    
    # Compute features in parallel
    compute_func = partial(compute_race_features, db_path=db_path)
    
    all_features = []
    all_targets = []
    races_computed = 0
    total_runners = 0
    
    write_batch_size = 100  # Write every 100 races
    
    with Pool(processes=num_workers) as pool:
        # Use imap for progress tracking
        for race_id, features_list, targets_list in pool.imap(compute_func, race_ids, chunksize=5):
            if features_list:
                all_features.extend(features_list)
                all_targets.extend(targets_list)
                races_computed += 1
                total_runners += len(features_list)
                
                # Write in batches to avoid memory issues
                if len(all_features) >= write_batch_size * 10:  # ~1000 runners
                    logger.info(f"  Computed: {races_computed:,}/{total_races:,} races ({races_computed/total_races*100:.1f}%) - Writing batch...")
                    write_features_batch(all_features, all_targets, db_path)
                    all_features = []
                    all_targets = []
                elif races_computed % 100 == 0:
                    progress_pct = (races_computed / total_races) * 100
                    logger.info(f"  Computed: {races_computed:,}/{total_races:,} races ({progress_pct:.1f}%) - {total_runners:,} runners")
    
    # Write remaining features
    if all_features:
        logger.info(f"Writing final batch ({len(all_features)} features)...")
        write_features_batch(all_features, all_targets, db_path)
    
    logger.info("="*60)
    logger.info("✓ OPTIMIZED FEATURE GENERATION COMPLETE")
    logger.info(f"  Races processed: {races_computed:,}")
    logger.info(f"  Runners processed: {total_runners:,}")
    logger.info(f"  Workers used: {num_workers}")
    logger.info("="*60)
    
    # Return results for GUI integration
    return {
        'races_processed': races_computed,
        'runners_processed': total_runners,
        'workers': num_workers
    }


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate ML features (optimized for SQLite)')
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
        start_time = time.time()
        
        generate_features_optimized(db_path, limit=limit, num_workers=args.workers)
        
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

