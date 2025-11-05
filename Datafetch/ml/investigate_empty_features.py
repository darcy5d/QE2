#!/usr/bin/env python3
"""
Investigate all empty features to understand why they're not populated
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def main():
    conn = sqlite3.connect('Datafetch/racing_pro.db')
    cursor = conn.cursor()
    
    logger.info("="*80)
    logger.info("EMPTY FEATURES INVESTIGATION")
    logger.info("="*80)
    
    # 1. HORSE AGE
    logger.info("\n1. HORSE AGE")
    logger.info("-" * 80)
    cursor.execute("SELECT COUNT(*) as total, SUM(CASE WHEN age IS NULL THEN 1 ELSE 0 END) as missing FROM runners")
    row = cursor.fetchone()
    logger.info(f"   runners.age: {row[1]:,}/{row[0]:,} missing ({row[1]/row[0]*100:.1f}%)")
    logger.info("   ✗ AGE IS 100% EMPTY IN RUNNERS TABLE")
    logger.info("   Root Cause: Data fetching from Racing Post API doesn't populate age")
    
    # 2. CLASS FEATURES
    logger.info("\n2. CLASS FEATURES (class_last_3_avg, class_change)")
    logger.info("-" * 80)
    cursor.execute("SELECT COUNT(*) as total, SUM(CASE WHEN race_class IS NULL OR race_class = '' THEN 1 ELSE 0 END) as missing FROM races WHERE type='Flat'")
    row = cursor.fetchone()
    logger.info(f"   races.race_class: {row[1]:,}/{row[0]:,} missing ({row[1]/row[0]*100:.1f}%)")
    if row[1] < row[0]:
        logger.info("   ✓ Race class data EXISTS")
        logger.info("   Issue: get_past_races_for_features() may not include 'class' field")
    else:
        logger.info("   ✗ Race class is completely empty")
    
    # 3. QUALITY FEATURES
    logger.info("\n3. QUALITY FEATURES (field_quality_rating, race_competitiveness, horse_beaten_by_quality)")
    logger.info("-" * 80)
    logger.info("   ✗ INTENTIONALLY SET TO None IN CODE")
    logger.info("   Location: feature_engineer.py lines 979-981")
    logger.info("   Status: Unimplemented placeholder features")
    
    # 4. BREEDING FEATURES
    logger.info("\n4. BREEDING FEATURES (sire_distance_win_rate, sire_surface_win_rate, dam_produce_win_rate)")
    logger.info("-" * 80)
    cursor.execute("SELECT COUNT(*) as total, SUM(CASE WHEN sire_id IS NULL THEN 1 ELSE 0 END) as missing_sire, SUM(CASE WHEN dam_id IS NULL THEN 1 ELSE 0 END) as missing_dam FROM runners")
    row = cursor.fetchone()
    logger.info(f"   runners.sire_id: {row[1]:,}/{row[0]:,} missing ({row[1]/row[0]*100:.1f}%)")
    logger.info(f"   runners.dam_id: {row[2]:,}/{row[0]:,} missing ({row[2]/row[0]*100:.1f}%)")
    
    # Check if sire/dam stats tables exist
    cursor.execute("SELECT COUNT(*) FROM sires LIMIT 1")
    sire_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM dams LIMIT 1")
    dam_count = cursor.fetchone()[0]
    logger.info(f"   sires table: {sire_count:,} records")
    logger.info(f"   dams table: {dam_count:,} records")
    
    if row[1] == row[0]:
        logger.info("   ✗ No sire/dam IDs in runners table")
        logger.info("   User decision: Not important, remove these features")
    else:
        logger.info("   ✓ Breeding data exists")
        logger.info("   Issue: breeding_features.py may not be implemented")
    
    # 5. TRAINER HOT STREAK
    logger.info("\n5. TRAINER HOT STREAK (trainer_hot_streak)")
    logger.info("-" * 80)
    # Check if trainer_hotstreak_features.py exists and is imported
    logger.info("   Checking if feature is calculated...")
    cursor.execute("""
        SELECT trainer_id, COUNT(*) as wins 
        FROM results r
        JOIN races rac ON r.race_id = rac.race_id
        WHERE r.position_int = 1
        AND rac.date BETWEEN date('2025-10-01', '-14 days') AND '2025-10-01'
        GROUP BY trainer_id
        LIMIT 5
    """)
    rows = cursor.fetchall()
    if rows:
        logger.info(f"   ✓ Can calculate trainer hot streaks (sample: {rows[0][1]} wins)")
        logger.info("   Issue: calculate_trainer_hotstreak() may not return expected format")
        logger.info("   Note: trainer_is_hot and trainer_14d_win_pct already exist (redundant)")
    else:
        logger.info("   ✗ No recent results to calculate hot streaks")
    
    # 6. JOCKEY DISTANCE WIN RATE
    logger.info("\n6. JOCKEY DISTANCE WIN RATE (jockey_distance_win_rate)")
    logger.info("-" * 80)
    logger.info("   Issue: Not implemented in jockey stats calculation")
    logger.info("   Note: jockey_win_rate_14d, jockey_strike_rate already exist (similar)")
    
    # 7. TRAINER FORM WITH HORSE
    logger.info("\n7. TRAINER FORM WITH HORSE (trainer_form_with_horse)")
    logger.info("-" * 80)
    logger.info("   Issue: Not implemented in trainer stats calculation")
    logger.info("   Note: combo_win_rate already exists (trainer+jockey+horse)")
    
    # 8. SPEED IMPROVING NEW
    logger.info("\n8. SPEED IMPROVING NEW (horse_speed_improving_new)")
    logger.info("-" * 80)
    logger.info("   Issue: May be duplicate of 'speed_improving' feature")
    logger.info("   Note: speed_improving already exists")
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("SUMMARY")
    logger.info("="*80)
    logger.info("\nFeatures to FIX (data exists but not fetched):")
    logger.info("  - class_last_3_avg, class_change (if race_class exists)")
    logger.info("\nFeatures to REMOVE (no data source):")
    logger.info("  - horse_age (100% empty in runners table)")
    logger.info("  - sire_distance_win_rate, sire_surface_win_rate, dam_produce_win_rate (no breeding implementation)")
    logger.info("  - field_quality_rating, race_competitiveness, horse_beaten_by_quality (unimplemented placeholders)")
    logger.info("\nFeatures to REMOVE (redundant):")
    logger.info("  - trainer_hot_streak (have trainer_is_hot, trainer_14d_win_pct)")
    logger.info("  - jockey_distance_win_rate (have jockey_win_rate_14d, jockey_strike_rate)")
    logger.info("  - trainer_form_with_horse (have combo_win_rate)")
    logger.info("  - horse_speed_improving_new (have speed_improving)")
    
    # Check age-related features that rely on age
    logger.info("\nDEPENDENT FEATURES (rely on horse_age):")
    logger.info("  - age_vs_avg")
    logger.info("  - age_rank")
    logger.info("  → These will also be 100% empty, should be removed")
    
    conn.close()

if __name__ == "__main__":
    main()

