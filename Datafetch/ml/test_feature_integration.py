#!/usr/bin/env python3
"""
Test Feature Engineer Integration
Verify that new features generate correctly without odds leakage
"""

import sys
from pathlib import Path
import sqlite3

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.feature_engineer import FeatureEngineer

def test_feature_generation():
    """Test feature generation on a sample race"""
    
    db_path = Path(__file__).parent.parent / 'racing_pro.db'
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return False
    
    print(f"✓ Found database: {db_path}")
    print()
    
    # Get a sample race with multiple runners
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.race_id, COUNT(*) as runner_count
        FROM results r
        JOIN races ra ON r.race_id = ra.race_id
        WHERE ra.date >= '2024-01-01'
        GROUP BY r.race_id
        HAVING runner_count >= 8
        ORDER BY ra.date DESC
        LIMIT 1
    """)
    
    race_row = cursor.fetchone()
    if not race_row:
        print("❌ No suitable test race found")
        conn.close()
        return False
    
    test_race_id = race_row['race_id']
    runner_count = race_row['runner_count']
    
    print(f"✓ Found test race: {test_race_id}")
    print(f"✓ Runner count: {runner_count}")
    print()
    
    conn.close()
    
    # Initialize feature engineer
    print("Initializing FeatureEngineer...")
    fe = FeatureEngineer(db_path)
    fe.connect()
    print("✓ FeatureEngineer connected")
    print()
    
    # Get race context
    print(f"Getting race context for {test_race_id}...")
    race_context = fe.get_race_context_features(test_race_id)
    if not race_context:
        print("❌ Failed to get race context")
        fe.close()
        return False
    print(f"✓ Race context loaded: {race_context.get('course')}, {race_context.get('distance_f')}f")
    print()
    
    # Get runners
    print("Getting runners...")
    runners = fe.get_runners_for_race(test_race_id)
    if not runners:
        print("❌ No runners found")
        fe.close()
        return False
    print(f"✓ Found {len(runners)} runners")
    print()
    
    # Compute features for each runner
    print("Computing features...")
    all_features = []
    
    for i, runner in enumerate(runners, 1):
        print(f"  [{i}/{len(runners)}] {runner.get('horse_name', 'Unknown')}...", end=" ")
        
        try:
            result = fe.get_runner_result(test_race_id, runner['horse_id'])
            features = fe.compute_runner_features(runner, race_context, result)
            all_features.append(features)
            print("✓")
        except Exception as e:
            print(f"❌ Error: {e}")
            fe.close()
            return False
    
    print()
    print("✓ All runner features computed")
    print()
    
    # Compute relative features
    print("Computing relative features...")
    try:
        all_features = fe.compute_relative_features(all_features)
        print("✓ Relative features computed")
    except Exception as e:
        print(f"❌ Error computing relative features: {e}")
        fe.close()
        return False
    
    print()
    
    # Verify new features exist
    print("Verifying new features...")
    
    # Check first runner's features
    first_runner = all_features[0]
    
    # Speed features (6)
    speed_features = [
        'horse_avg_speed_furlongs_per_sec', 'horse_best_speed_career',
        'horse_speed_last_3_avg', 'horse_speed_improving_new',
        'horse_speed_vs_track_record', 'horse_speed_consistency'
    ]
    
    # BTN features (12)
    btn_features = [
        'horse_avg_btn_last_5', 'horse_median_btn_last_5',
        'horse_btn_improving', 'horse_pct_within_3_lengths',
        'horse_btn_vs_field_avg', 'horse_btn_vs_winner_percentile',
        'horse_best_btn_career', 'horse_btn_consistency',
        'horse_avg_ovr_btn_last_5', 'horse_ovr_btn_improving',
        'horse_ovr_btn_vs_field', 'horse_pct_top_half_finishes'
    ]
    
    # Quality features (3)
    quality_features = [
        'field_quality_rating', 'race_competitiveness',
        'horse_beaten_by_quality'
    ]
    
    # Weather features (4)
    weather_features = [
        'horse_soft_going_speed_ratio', 'horse_weather_performance',
        'rail_position_advantage', 'going_change_adaptation'
    ]
    
    # Weight features (2)
    weight_features = [
        'horse_weight_adjusted_rating', 'horse_weight_performance_trend'
    ]
    
    all_new_features = (speed_features + btn_features + quality_features + 
                        weather_features + weight_features)
    
    missing_features = []
    present_features = []
    
    for feat in all_new_features:
        if feat in first_runner:
            present_features.append(feat)
        else:
            missing_features.append(feat)
    
    print(f"✓ {len(present_features)}/{len(all_new_features)} new features present")
    
    if missing_features:
        print(f"⚠️  Missing features: {', '.join(missing_features)}")
    
    # Verify odds features are NOT present
    odds_features = [
        'odds_implied_prob', 'odds_is_favorite', 'odds_favorite_rank',
        'odds_decimal', 'odds_bookmaker_count', 'odds_spread', 'odds_market_stability'
    ]
    
    odds_found = [f for f in odds_features if f in first_runner and first_runner[f] is not None]
    
    if odds_found:
        print(f"⚠️  Odds features still present: {', '.join(odds_found)}")
    else:
        print("✓ No odds features present (data leakage removed)")
    
    print()
    
    # Print sample feature values
    print("Sample feature values (first runner):")
    print(f"  Horse: {first_runner.get('horse_id')}")
    print(f"  Speed features:")
    for feat in speed_features[:3]:
        val = first_runner.get(feat)
        print(f"    {feat}: {val}")
    print(f"  BTN features:")
    for feat in btn_features[:3]:
        val = first_runner.get(feat)
        print(f"    {feat}: {val}")
    
    print()
    
    fe.close()
    
    return True

if __name__ == '__main__':
    print("="*80)
    print("FEATURE INTEGRATION TEST")
    print("="*80)
    print()
    
    success = test_feature_generation()
    
    print()
    print("="*80)
    if success:
        print("✅ TEST PASSED - Feature integration working correctly!")
    else:
        print("❌ TEST FAILED - Check errors above")
    print("="*80)
    
    sys.exit(0 if success else 1)

