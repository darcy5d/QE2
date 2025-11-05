#!/usr/bin/env python3
"""
Test New Feature Modules
Validates that all new feature calculators work correctly
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from ml.speed_features import SpeedFeatureCalculator, parse_race_time, calculate_speed
from ml.btn_features import BTNFeatureCalculator, parse_btn
from ml.quality_features import QualityFeatureCalculator
from ml.weather_features import WeatherFeatureCalculator, parse_rail_movements
from ml.weight_features import WeightFeatureCalculator


def test_parsing_functions():
    """Test all parsing functions"""
    print("\n" + "="*60)
    print("TESTING PARSING FUNCTIONS")
    print("="*60)
    
    # Test time parsing
    assert parse_race_time("1:23.45") == 83.45, "Failed: MM:SS.ms format"
    assert parse_race_time("45.67") == 45.67, "Failed: SS.ms format"
    assert parse_race_time("2:15") == 135.0, "Failed: MM:SS format"
    assert parse_race_time("invalid") is None, "Failed: invalid input"
    print("✓ Time parsing works")
    
    # Test BTN parsing
    assert parse_btn("2.5") == 2.5, "Failed: numeric BTN"
    assert parse_btn("nk") == 0.3, "Failed: neck"
    assert parse_btn("hd") == 0.2, "Failed: head"
    assert parse_btn("shd") == 0.1, "Failed: short head"
    assert parse_btn("dist") == 30.0, "Failed: distance"
    assert parse_btn("") == 0.0, "Failed: winner (empty)"
    assert parse_btn(None) == 0.0, "Failed: winner (None)"
    print("✓ BTN parsing works")
    
    # Test rail movements parsing
    assert parse_rail_movements("+3 yards") == 3.0, "Failed: positive rail"
    assert parse_rail_movements("-2m") == -2.0, "Failed: negative rail"
    assert parse_rail_movements("0") == 0.0, "Failed: no movement"
    print("✓ Rail movements parsing works")


def test_speed_features():
    """Test speed feature calculator"""
    print("\n" + "="*60)
    print("TESTING SPEED FEATURES")
    print("="*60)
    
    calc = SpeedFeatureCalculator()
    
    # Sample past races
    past_races = [
        {'time': '1:30.00', 'distance_f': 10.0, 'course': 'Ascot'},
        {'time': '1:28.50', 'distance_f': 10.0, 'course': 'Ascot'},
        {'time': '1:29.25', 'distance_f': 10.0, 'course': 'Ascot'},
        {'time': '1:31.00', 'distance_f': 10.0, 'course': 'York'},
        {'time': '1:27.80', 'distance_f': 10.0, 'course': 'Ascot'},
    ]
    
    features = calc.calculate_all_speed_features(past_races, 'Ascot', 10.0)
    
    # Check all features are present
    expected_features = [
        'horse_avg_speed_furlongs_per_sec',
        'horse_best_speed_career',
        'horse_speed_last_3_avg',
        'horse_speed_improving',
        'horse_speed_vs_track_record',
        'horse_speed_consistency'
    ]
    
    for feature in expected_features:
        assert feature in features, f"Missing feature: {feature}"
    
    print(f"✓ Generated {len(features)} speed features")
    print(f"  Avg speed: {features['horse_avg_speed_furlongs_per_sec']:.4f} f/s")
    print(f"  Best speed: {features['horse_best_speed_career']:.4f} f/s")
    print(f"  Speed improving: {features['horse_speed_improving']:.6f}")


def test_btn_features():
    """Test BTN feature calculator"""
    print("\n" + "="*60)
    print("TESTING BTN FEATURES")
    print("="*60)
    
    calc = BTNFeatureCalculator()
    
    # Sample past races
    past_races = [
        {'btn': '0', 'ovr_btn': '0', 'position': 1, 'field_size': 10},
        {'btn': '2.5', 'ovr_btn': '3.0', 'position': 3, 'field_size': 10},
        {'btn': '1.0', 'ovr_btn': '1.5', 'position': 2, 'field_size': 12},
        {'btn': 'nk', 'ovr_btn': '0.5', 'position': 2, 'field_size': 8},
        {'btn': '3.5', 'ovr_btn': '5.0', 'position': 4, 'field_size': 9},
    ]
    
    features = calc.calculate_all_btn_features(past_races, 10)
    
    # Check all features are present
    expected_features = [
        'horse_avg_btn_last_5',
        'horse_median_btn_last_5',
        'horse_btn_improving',
        'horse_pct_within_3_lengths',
        'horse_btn_vs_field_avg',
        'horse_btn_vs_winner_percentile',
        'horse_best_btn_career',
        'horse_btn_consistency',
        'horse_avg_ovr_btn_last_5',
        'horse_ovr_btn_improving',
        'horse_ovr_btn_vs_field',
        'horse_pct_top_half_finishes'
    ]
    
    for feature in expected_features:
        assert feature in features, f"Missing feature: {feature}"
    
    print(f"✓ Generated {len(features)} BTN features")
    print(f"  Avg BTN: {features['horse_avg_btn_last_5']:.2f} lengths")
    print(f"  Best BTN: {features['horse_best_btn_career']:.2f} lengths")
    print(f"  % within 3L: {features['horse_pct_within_3_lengths']:.1%}")


def test_weather_features():
    """Test weather feature calculator"""
    print("\n" + "="*60)
    print("TESTING WEATHER FEATURES")
    print("="*60)
    
    calc = WeatherFeatureCalculator()
    
    # Sample past races
    past_races = [
        {'going': 'Good', 'weather': 'Fine', 'time': '1:30.00', 'distance_f': 10.0, 'position': 1},
        {'going': 'Soft', 'weather': 'Rain', 'time': '1:35.00', 'distance_f': 10.0, 'position': 2},
        {'going': 'Good to Firm', 'weather': 'Sunny', 'time': '1:28.00', 'distance_f': 10.0, 'position': 1},
        {'going': 'Heavy', 'weather': 'Showers', 'time': '1:40.00', 'distance_f': 10.0, 'position': 3},
    ]
    
    soft_going_ratio = calc.calculate_soft_going_speed_ratio(past_races)
    weather_perf = calc.calculate_weather_performance(past_races)
    rail_adv = calc.calculate_rail_position_advantage("+3 yards", 2, 10)
    going_adapt = calc.calculate_going_change_adaptation(past_races, 'Good')
    
    print(f"✓ Generated 4 weather features")
    print(f"  Soft going ratio: {soft_going_ratio:.2f}")
    print(f"  Weather performance: {weather_perf:.2f}")
    print(f"  Rail advantage: {rail_adv:.2f}")
    print(f"  Going adaptation: {going_adapt:.2f}")


def test_weight_features():
    """Test weight feature calculator"""
    print("\n" + "="*60)
    print("TESTING WEIGHT FEATURES")
    print("="*60)
    
    calc = WeightFeatureCalculator()
    
    # Test weight adjustment
    adjusted_rating = calc.calculate_weight_adjusted_rating(100, 130, 126)
    assert adjusted_rating == 104, "Weight adjustment failed"
    print(f"✓ Weight adjusted rating: 100 @ 130lbs -> {adjusted_rating}")
    
    # Sample past races
    past_races = [
        {'weight_lbs': 126, 'rpr': 100},
        {'weight_lbs': 128, 'rpr': 98},
        {'weight_lbs': 130, 'rpr': 96},
        {'weight_lbs': 125, 'rpr': 102},
        {'weight_lbs': 127, 'rpr': 99},
    ]
    
    trend = calc.calculate_weight_performance_trend(past_races)
    print(f"✓ Weight performance trend: {trend:.3f}")
    
    if trend < 0:
        print("  → Horse struggles with weight")
    elif trend > 0:
        print("  → Horse handles weight well")
    else:
        print("  → No clear weight trend")


def run_all_tests():
    """Run all test suites"""
    print("="*60)
    print("NEW FEATURE MODULES TEST SUITE")
    print("="*60)
    
    try:
        test_parsing_functions()
        test_speed_features()
        test_btn_features()
        test_weather_features()
        test_weight_features()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nFeature modules are ready for integration.")
        print("Next step: Follow INTEGRATION_GUIDE.md")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())

