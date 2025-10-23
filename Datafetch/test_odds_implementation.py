#!/usr/bin/env python3
"""
Test script to verify odds and new fields implementation
"""

import sqlite3
from pathlib import Path
import sys

DB_PATH = Path(__file__).parent / "racing_pro.db"


def test_schema():
    """Test that new schema elements exist"""
    print("="*60)
    print("TESTING SCHEMA")
    print("="*60)
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Check for new tables
    print("\nChecking new tables...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('runner_odds', 'runner_market_odds')")
    tables = [row[0] for row in cursor.fetchall()]
    
    for table in ['runner_odds', 'runner_market_odds']:
        if table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  ✓ {table}: {count:,} rows")
        else:
            print(f"  ✗ {table}: NOT FOUND")
            return False
    
    # Check new columns in runners table
    print("\nChecking new runner columns...")
    cursor.execute("PRAGMA table_info(runners)")
    runner_cols = {row[1] for row in cursor.fetchall()}
    
    new_cols = ['age', 'sex_code', 'sire', 'trainer_14d_runs', 'trainer_14d_wins', 'trainer_14d_percent']
    for col in new_cols:
        if col in runner_cols:
            print(f"  ✓ {col}")
        else:
            print(f"  ✗ {col} NOT FOUND")
            return False
    
    # Check new columns in ml_features table
    print("\nChecking new ml_features columns...")
    cursor.execute("PRAGMA table_info(ml_features)")
    feature_cols = {row[1] for row in cursor.fetchall()}
    
    new_feature_cols = [
        'odds_implied_prob', 'odds_is_favorite', 'odds_favorite_rank', 'odds_decimal',
        'horse_sex_encoded', 'horse_is_filly_mare', 'horse_is_gelding',
        'trainer_14d_runs', 'trainer_14d_wins', 'trainer_14d_win_pct', 'trainer_is_hot'
    ]
    for col in new_feature_cols:
        if col in feature_cols:
            print(f"  ✓ {col}")
        else:
            print(f"  ✗ {col} NOT FOUND")
            return False
    
    conn.close()
    return True


def test_data_population():
    """Test that we have data in new fields"""
    print("\n" + "="*60)
    print("TESTING DATA POPULATION")
    print("="*60)
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Check runner_odds table
    print("\nChecking runner_odds table...")
    cursor.execute("""
        SELECT COUNT(*) as total,
               COUNT(DISTINCT runner_id) as unique_runners,
               COUNT(DISTINCT bookmaker) as unique_bookmakers
        FROM runner_odds
    """)
    row = cursor.fetchone()
    print(f"  Total odds records: {row[0]:,}")
    print(f"  Unique runners with odds: {row[1]:,}")
    print(f"  Unique bookmakers: {row[2]:,}")
    
    # Sample some odds data
    cursor.execute("""
        SELECT bookmaker, fractional, decimal
        FROM runner_odds
        LIMIT 5
    """)
    print("\n  Sample odds:")
    for row in cursor.fetchall():
        print(f"    {row[0]}: {row[1]} ({row[2]})")
    
    # Check runner_market_odds table
    print("\nChecking runner_market_odds table...")
    cursor.execute("""
        SELECT COUNT(*) as total,
               AVG(avg_decimal) as avg_odds,
               AVG(bookmaker_count) as avg_bookmakers
        FROM runner_market_odds
    """)
    row = cursor.fetchone()
    print(f"  Runners with market odds: {row[0]:,}")
    print(f"  Average decimal odds: {row[1]:.2f}" if row[1] else "  No data yet")
    print(f"  Average bookmakers per runner: {row[2]:.1f}" if row[2] else "  No data yet")
    
    # Check new runner fields
    print("\nChecking new runner fields...")
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(age) as with_age,
            COUNT(sex_code) as with_sex_code,
            COUNT(trainer_14d_runs) as with_trainer_14d
        FROM runners
    """)
    row = cursor.fetchone()
    total = row[0]
    print(f"  Total runners: {total:,}")
    print(f"  With age: {row[1]:,} ({row[1]/total*100:.1f}%)" if total > 0 else "  No runners")
    print(f"  With sex_code: {row[2]:,} ({row[2]/total*100:.1f}%)" if total > 0 else "  No runners")
    print(f"  With trainer_14d_runs: {row[3]:,} ({row[3]/total*100:.1f}%)" if total > 0 else "  No runners")
    
    # Sample some runner data
    cursor.execute("""
        SELECT age, sex_code, trainer_14d_runs, trainer_14d_wins, trainer_14d_percent
        FROM runners
        WHERE age IS NOT NULL AND trainer_14d_runs IS NOT NULL
        LIMIT 5
    """)
    print("\n  Sample runner demographics & trainer form:")
    for row in cursor.fetchall():
        print(f"    Age: {row[0]}, Sex: {row[1]}, Trainer 14d: {row[2]}/{row[3]} ({row[4]}%)" if row[4] else f"    Age: {row[0]}, Sex: {row[1]}")
    
    conn.close()
    return True


def test_feature_generation():
    """Test that feature generation works with new features"""
    print("\n" + "="*60)
    print("TESTING FEATURE GENERATION")
    print("="*60)
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Get a race with results
    cursor.execute("""
        SELECT DISTINCT r.race_id, r.date
        FROM races r
        JOIN results res ON r.race_id = res.race_id
        WHERE r.is_abandoned = 0
        ORDER BY r.date DESC
        LIMIT 1
    """)
    
    row = cursor.fetchone()
    if not row:
        print("  ⚠ No races with results found for testing")
        conn.close()
        return False
    
    race_id = row[0]
    race_date = row[1]
    print(f"\n  Testing with race: {race_id} ({race_date})")
    
    # Check if this race has runners with new fields
    cursor.execute("""
        SELECT 
            COUNT(*) as total_runners,
            COUNT(age) as with_age,
            COUNT(sex_code) as with_sex,
            COUNT(trainer_14d_runs) as with_trainer_form
        FROM runners
        WHERE race_id = ?
    """, (race_id,))
    
    row = cursor.fetchone()
    print(f"  Runners in race: {row[0]}")
    print(f"    With age: {row[1]}")
    print(f"    With sex_code: {row[2]}")
    print(f"    With trainer form: {row[3]}")
    
    # Check if race has odds data
    cursor.execute("""
        SELECT COUNT(DISTINCT ro.runner_id)
        FROM runner_odds ro
        JOIN runners r ON ro.runner_id = r.runner_id
        WHERE r.race_id = ?
    """, (race_id,))
    
    row = cursor.fetchone()
    print(f"    With odds: {row[0]}")
    
    # Test feature computation
    print("\n  Testing feature computation...")
    try:
        sys.path.append(str(Path(__file__).parent))
        from ml.feature_engineer import FeatureEngineer
        
        engineer = FeatureEngineer(DB_PATH)
        engineer.connect()
        
        # Get race context and runners
        race_context = engineer.get_race_context_features(race_id)
        runners = engineer.get_runners_for_race(race_id)
        
        if not runners:
            print("    ⚠ No runners found")
            engineer.close()
            conn.close()
            return False
        
        print(f"    Processing {len(runners)} runners...")
        
        # Compute features for first runner
        runner = runners[0]
        result = engineer.get_runner_result(race_id, runner['horse_id'])
        features = engineer.compute_runner_features(runner, race_context, result)
        
        # Check new features
        new_features_check = [
            'odds_implied_prob', 'odds_is_favorite', 'odds_decimal',
            'horse_sex_encoded', 'horse_is_filly_mare',
            'trainer_14d_runs', 'trainer_14d_win_pct', 'trainer_is_hot'
        ]
        
        print("\n  New features for first runner:")
        for feat in new_features_check:
            value = features.get(feat)
            print(f"    {feat}: {value}")
        
        engineer.close()
        print("\n  ✓ Feature generation successful!")
        
    except Exception as e:
        print(f"\n  ✗ Feature generation failed: {e}")
        import traceback
        traceback.print_exc()
        conn.close()
        return False
    
    conn.close()
    return True


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("ODDS & NEW FIELDS IMPLEMENTATION TEST")
    print("="*60)
    
    if not DB_PATH.exists():
        print(f"\n✗ Database not found: {DB_PATH}")
        return 1
    
    # Run tests
    tests = [
        ("Schema", test_schema),
        ("Data Population", test_data_population),
        ("Feature Generation", test_feature_generation),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n✓ ALL TESTS PASSED")
        print("\nNext steps:")
        print("  1. Regenerate features for historical data: cd Datafetch/ml && python feature_engineer.py")
        print("  2. Retrain model with new features: python train_baseline.py")
        print("  3. Compare model performance before/after")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())


