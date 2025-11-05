#!/usr/bin/env python3
"""
Test Discriminating Features
Validates that new features calculate correctly and provide good coverage
"""

import sys
import sqlite3
from pathlib import Path
from typing import Dict, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.market_position_features import calculate_market_position
from ml.class_features import calculate_class_features, parse_race_class
from ml.course_specialist_features import calculate_course_specialist_features
from ml.distance_features import calculate_distance_features
from ml.trainer_hotstreak_features import calculate_trainer_hotstreak


def test_market_position():
    """Test market position feature"""
    print("\n=== Testing Market Position Feature ===")
    
    test_cases = [
        (2.5, 0, "Strong Favorite"),
        (4.0, 1, "Co-Favorite"),
        (7.5, 2, "Mid-range"),
        (15.0, 3, "Outsider"),
        (25.0, 4, "Longshot"),
        (None, 2, "Missing odds")
    ]
    
    for odds, expected, label in test_cases:
        result = calculate_market_position(odds)
        status = "✓" if result == expected else "✗"
        print(f"{status} {label}: odds={odds} → tier={result} (expected={expected})")


def test_class_features():
    """Test class features"""
    print("\n=== Testing Class Features ===")
    
    # Test class parsing
    print("\nClass Parsing:")
    test_classes = ["Class 5", "5", "Class 2", "2", "", None]
    for class_str in test_classes:
        parsed = parse_race_class(class_str)
        print(f"  '{class_str}' → {parsed}")
    
    # Test class movement (dropping = going to easier class)
    print("\nClass Movement:")
    past_races = [
        {'class': 'Class 5'},
        {'class': 'Class 5'},
        {'class': 'Class 6'}
    ]
    
    # Test 1: Dropping in class (5 avg → 6 today = easier)
    result = calculate_class_features(past_races, 'Class 6')
    print(f"  Recent: C5,C5,C6 → Today: C6")
    print(f"    Avg: {result['class_last_3_avg']:.2f}")
    print(f"    Change: {result['class_change']:.2f}")
    print(f"    Dropping: {result['dropping_in_class']} (expected: 1)")
    print(f"    Rising: {result['rising_in_class']} (expected: 0)")
    
    # Test 2: Rising in class (5 avg → 3 today = harder)
    result = calculate_class_features(past_races, 'Class 3')
    print(f"  Recent: C5,C5,C6 → Today: C3")
    print(f"    Avg: {result['class_last_3_avg']:.2f}")
    print(f"    Change: {result['class_change']:.2f}")
    print(f"    Dropping: {result['dropping_in_class']} (expected: 0)")
    print(f"    Rising: {result['rising_in_class']} (expected: 1)")


def test_course_specialist():
    """Test course specialist features"""
    print("\n=== Testing Course Specialist Features ===")
    
    # Simulate past races at Wolverhampton
    past_races = [
        {'course': 'Wolverhampton', 'position': '1'},
        {'course': 'Wolverhampton', 'position': '1'},
        {'course': 'Wolverhampton', 'position': '3'},
        {'course': 'Wolverhampton', 'position': '2'},
        {'course': 'Newbury', 'position': '5'},
        {'course': 'Newbury', 'position': '8'}
    ]
    
    # Test at Wolverhampton (specialist)
    result = calculate_course_specialist_features(past_races, 'Wolverhampton')
    print(f"  Course: Wolverhampton")
    print(f"    Runs: {result['course_runs']} (expected: 4)")
    print(f"    Wins: {result['course_wins']} (expected: 2)")
    print(f"    Win rate: {result['course_win_rate']:.2%}")
    print(f"    Place rate: {result['course_place_rate']:.2%}")
    print(f"    Is specialist: {result['course_specialist']} (expected: 1)")
    
    # Test at Newbury (not specialist)
    result = calculate_course_specialist_features(past_races, 'Newbury')
    print(f"  Course: Newbury")
    print(f"    Runs: {result['course_runs']} (expected: 2)")
    print(f"    Wins: {result['course_wins']} (expected: 0)")
    print(f"    Win rate: {result['course_win_rate']:.2%}")
    print(f"    Is specialist: {result['course_specialist']} (expected: 0)")


def test_distance_features():
    """Test distance optimization features"""
    print("\n=== Testing Distance Features ===")
    
    # Horse best at 8f (1 mile)
    past_races = [
        {'distance_f': '8.0', 'position': '1'},
        {'distance_f': '8.0', 'position': '2'},
        {'distance_f': '8.5', 'position': '3'},
        {'distance_f': '10.0', 'position': '7'},
        {'distance_f': '6.0', 'position': '9'}
    ]
    
    # Test at optimal distance
    result = calculate_distance_features(past_races, 8.0)
    print(f"  Best distance: {result['best_distance_f']}f (expected: ~8f)")
    print(f"  Racing at 8f:")
    print(f"    Distance from optimal: {result['distance_from_optimal']}")
    print(f"    Runs at distance: {result['runs_at_distance']}")
    print(f"    Win rate: {result['win_rate_at_distance']:.2%}")
    
    # Test at wrong distance
    result = calculate_distance_features(past_races, 12.0)
    print(f"  Racing at 12f:")
    print(f"    Distance from optimal: {result['distance_from_optimal']:.1f}f (expected: ~4f)")
    print(f"    Runs at distance: {result['runs_at_distance']} (expected: 0)")


def test_trainer_hotstreak():
    """Test trainer hot streak features"""
    print("\n=== Testing Trainer Hot Streak Features ===")
    
    # Note: This requires actual database connection
    db_path = Path(__file__).parent.parent / 'racing_pro.db'
    
    if not db_path.exists():
        print("  ⚠ Database not found, skipping live test")
        print("  Testing function signature only...")
        result = calculate_trainer_hotstreak(None, None, None)
        print(f"    Null inputs return: {result}")
        return
    
    conn = sqlite3.connect(db_path)
    
    # Get a sample trainer with recent activity
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT r.trainer_id
        FROM results r
        JOIN races ra ON r.race_id = ra.race_id
        WHERE r.trainer_id IS NOT NULL
          AND ra.date >= '2024-10-01'
        LIMIT 1
    """)
    
    sample_trainer = cursor.fetchone()
    
    if sample_trainer:
        trainer_id = sample_trainer[0]
        race_date = '2024-10-26'
        
        result = calculate_trainer_hotstreak(trainer_id, race_date, conn)
        print(f"  Sample trainer: {trainer_id}")
        print(f"    Wins (last 14d): {result['trainer_wins_last_14d']}")
        print(f"    Runs (last 14d): {result['trainer_runs_last_14d']}")
        print(f"    Win rate: {result['trainer_win_rate_recent']:.2%}")
        print(f"    Is hot: {result['trainer_is_hot']}")
    else:
        print("  ⚠ No recent trainer data found")
    
    conn.close()


def check_feature_coverage():
    """Check data coverage for new features"""
    print("\n=== Checking Feature Coverage ===")
    
    db_path = Path(__file__).parent.parent / 'racing_pro.db'
    
    if not db_path.exists():
        print("  ⚠ Database not found, skipping coverage check")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if new columns exist
    cursor.execute("PRAGMA table_info(ml_features)")
    columns = [col[1] for col in cursor.fetchall()]
    
    new_columns = [
        'market_position_tier', 'class_last_3_avg', 'class_change',
        'dropping_in_class', 'rising_in_class', 'course_runs',
        'course_wins', 'course_win_rate', 'course_place_rate',
        'course_specialist', 'best_distance_f', 'distance_from_optimal',
        'runs_at_distance', 'win_rate_at_distance', 'trainer_wins_last_14d',
        'trainer_runs_last_14d', 'trainer_win_rate_recent', 'trainer_is_hot'
    ]
    
    print(f"\n  New columns in schema:")
    for col in new_columns:
        status = "✓" if col in columns else "✗ MISSING"
        print(f"    {status} {col}")
    
    # Total column count
    print(f"\n  Total columns: {len(columns)} (expected: 128)")
    
    conn.close()


def main():
    """Run all tests"""
    print("=" * 60)
    print("DISCRIMINATING FEATURES TEST SUITE")
    print("=" * 60)
    
    test_market_position()
    test_class_features()
    test_course_specialist()
    test_distance_features()
    test_trainer_hotstreak()
    check_feature_coverage()
    
    print("\n" + "=" * 60)
    print("TESTS COMPLETE")
    print("=" * 60)
    print("\nNext Steps:")
    print("1. Review output above for any unexpected results")
    print("2. Run feature regeneration via GUI (Tab 6)")
    print("3. Check regeneration log for errors")
    print("4. Retrain model (Tab 7)")
    print("5. Verify probability spread improves (Tab 8)")


if __name__ == '__main__':
    main()

