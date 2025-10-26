# Feature Engineer Integration Guide
## How to integrate new features and remove odds leakage

---

## Overview

This guide explains how to update your feature engineering pipeline to:
1. ❌ Remove 12 odds-based features (data leakage)
2. ✅ Add 27 new fundamental features (speed, BTN, quality, going, weight)

**New modules created**:
- `speed_features.py` - 6 race speed features
- `btn_features.py` - 12 BTN/OVR_BTN features
- `quality_features.py` - 3 race quality features
- `weather_features.py` - 4 going/weather features
- `weight_features.py` - 2 weight-adjusted features

---

## Step 1: Remove Odds Features

### In `feature_engineer_optimized.py` (or your main feature engineer):

Find and **comment out or delete** all odds-related feature generation code.

**Features to remove**:
```python
ODDS_FEATURES_TO_REMOVE = [
    'odds_rank',
    'opening_odds',
    'final_odds',
    'odds_movement',
    'market_rank',
    'odds_implied_prob',
    'odds_is_favorite',
    'odds_favorite_rank',
    'odds_decimal',
    'odds_bookmaker_count',
    'odds_spread',
    'odds_market_stability'
]
```

**Code sections to remove**:
1. Any queries to `runner_market_odds` or `runner_odds` tables
2. Any calculations of odds-derived features
3. Any odds ranking or favorite identification code

---

## Step 2: Import New Feature Modules

Add these imports at the top of your feature engineer:

```python
from ml.speed_features import SpeedFeatureCalculator, parse_race_time, calculate_speed
from ml.btn_features import BTNFeatureCalculator, parse_btn, calculate_field_btn_stats
from ml.quality_features import calculate_all_quality_features
from ml.weather_features import calculate_all_weather_features
from ml.weight_features import calculate_all_weight_features
```

---

## Step 3: Initialize Feature Calculators

In your `__init__` method or at class level:

```python
class FeatureEngineer:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        
        # Initialize new feature calculators
        self.speed_calc = SpeedFeatureCalculator()
        self.btn_calc = BTNFeatureCalculator()
```

---

## Step 4: Integrate Speed Features

In your horse feature generation method (wherever you calculate per-horse features):

```python
def generate_horse_features(self, horse_id, race_id, ...):
    # ... existing feature generation ...
    
    # Get horse's past races with time data
    cursor.execute("""
        SELECT r.time, ra.distance_f, ra.course
        FROM results r
        JOIN races ra ON r.race_id = ra.race_id
        WHERE r.horse_id = ?
        ORDER BY ra.date DESC
        LIMIT 10
    """, (horse_id,))
    
    past_races = [dict(row) for row in cursor.fetchall()]
    
    # Calculate speed features
    speed_features = self.speed_calc.calculate_all_speed_features(
        past_races, 
        current_race_course, 
        current_race_distance_f
    )
    
    # Add to feature dict
    features.update(speed_features)
```

---

## Step 5: Integrate BTN Features

```python
def generate_horse_features(self, horse_id, race_id, ...):
    # ... existing feature generation ...
    
    # Get horse's past races with BTN data
    cursor.execute("""
        SELECT r.btn, r.ovr_btn, r.position, ra.field_size
        FROM results r
        JOIN races ra ON r.race_id = ra.race_id
        WHERE r.horse_id = ?
        ORDER BY ra.date DESC
        LIMIT 10
    """, (horse_id,))
    
    past_races = [dict(row) for row in cursor.fetchall()]
    
    # Calculate BTN features
    btn_features = self.btn_calc.calculate_all_btn_features(
        past_races,
        current_race_field_size
    )
    
    # Add to feature dict
    features.update(btn_features)
```

---

## Step 6: Calculate Field-Level BTN Stats

After generating features for all horses in a race:

```python
def generate_race_features(self, race_id):
    all_horses = []
    
    # Generate features for each horse
    for horse_id in get_horses_in_race(race_id):
        horse_features = generate_horse_features(horse_id, race_id)
        all_horses.append(horse_features)
    
    # Calculate field-level BTN comparisons
    from ml.btn_features import calculate_field_btn_stats
    relative_btn_features = calculate_field_btn_stats(all_horses)
    
    # Update each horse's features with relative BTN metrics
    for horse in all_horses:
        horse_id = horse['horse_id']
        if horse_id in relative_btn_features:
            horse.update(relative_btn_features[horse_id])
```

---

## Step 7: Integrate Quality Features

```python
def generate_horse_features(self, horse_id, race_id, ...):
    # ... existing feature generation ...
    
    # Get similar races for competitiveness
    cursor.execute("""
        SELECT race_id
        FROM races
        WHERE course = ? AND distance_f = ? AND race_class = ?
        LIMIT 20
    """, (current_course, current_distance, current_class))
    
    similar_races = fetch_race_results(cursor.fetchall())
    
    # Calculate quality features
    quality_features = calculate_all_quality_features(
        past_races,
        all_field_horses,
        similar_races,
        all_historical_data_dict
    )
    
    # Add to feature dict
    features.update(quality_features)
```

---

## Step 8: Integrate Weather Features

```python
def generate_horse_features(self, horse_id, race_id, ...):
    # ... existing feature generation ...
    
    # Get race conditions
    cursor.execute("""
        SELECT rail_movements, going, weather
        FROM races
        WHERE race_id = ?
    """, (race_id,))
    
    race_conditions = cursor.fetchone()
    
    # Get horse's past races with going/weather
    cursor.execute("""
        SELECT r.time, ra.distance_f, ra.going, ra.weather
        FROM results r
        JOIN races ra ON r.race_id = ra.race_id
        WHERE r.horse_id = ?
        ORDER BY ra.date DESC
        LIMIT 10
    """, (horse_id,))
    
    past_races_weather = [dict(row) for row in cursor.fetchall()]
    
    # Calculate weather features
    weather_features = calculate_all_weather_features(
        past_races_weather,
        race_conditions['rail_movements'],
        current_draw,
        current_field_size,
        race_conditions['going']
    )
    
    # Add to feature dict
    features.update(weather_features)
```

---

## Step 9: Integrate Weight Features

```python
def generate_horse_features(self, horse_id, race_id, ...):
    # ... existing feature generation ...
    
    # Get horse's past races with weight data
    cursor.execute("""
        SELECT r.weight_lbs, r.rpr
        FROM results r
        WHERE r.horse_id = ?
        ORDER BY r.date DESC
        LIMIT 10
    """, (horse_id,))
    
    past_races_weight = [dict(row) for row in cursor.fetchall()]
    
    # Calculate weight features
    weight_features = calculate_all_weight_features(
        past_races_weight,
        current_rpr,
        current_weight_lbs,
        current_race_type
    )
    
    # Add to feature dict
    features.update(weight_features)
```

---

## Step 10: Update Feature Column List

Make sure your feature column list includes all new features and excludes odds features:

```python
# In train_baseline.py or wherever you define feature columns

# Remove these
REMOVE = [
    'odds_rank', 'opening_odds', 'final_odds', 'odds_movement',
    'market_rank', 'odds_implied_prob', 'odds_is_favorite',
    'odds_favorite_rank', 'odds_decimal', 'odds_bookmaker_count',
    'odds_spread', 'odds_market_stability'
]

# Add these
ADD = [
    # Speed (6)
    'horse_avg_speed_furlongs_per_sec', 'horse_best_speed_career',
    'horse_speed_last_3_avg', 'horse_speed_improving',
    'horse_speed_vs_track_record', 'horse_speed_consistency',
    
    # BTN (8)
    'horse_avg_btn_last_5', 'horse_median_btn_last_5',
    'horse_btn_improving', 'horse_pct_within_3_lengths',
    'horse_btn_vs_field_avg', 'horse_btn_vs_winner_percentile',
    'horse_best_btn_career', 'horse_btn_consistency',
    
    # OVR_BTN (4)
    'horse_avg_ovr_btn_last_5', 'horse_ovr_btn_improving',
    'horse_ovr_btn_vs_field', 'horse_pct_top_half_finishes',
    
    # Quality (3)
    'field_quality_rating', 'race_competitiveness',
    'horse_beaten_by_quality',
    
    # Weather (4)
    'horse_soft_going_speed_ratio', 'horse_weather_performance',
    'rail_position_advantage', 'going_change_adaptation',
    
    # Weight (2)
    'horse_weight_adjusted_rating', 'horse_weight_performance_trend'
]
```

---

## Step 11: Test the Integration

Create a test script:

```python
#!/usr/bin/env python3
"""Test new feature generation"""

import sqlite3
from ml.speed_features import SpeedFeatureCalculator, parse_race_time
from ml.btn_features import BTNFeatureCalculator, parse_btn

# Test parsing functions
assert parse_race_time("1:23.45") == 83.45
assert parse_race_time("45.67") == 45.67
assert parse_btn("2.5") == 2.5
assert parse_btn("nk") == 0.3
assert parse_btn("") == 0.0

print("✓ Parsing functions work")

# Test feature calculators
speed_calc = SpeedFeatureCalculator()
btn_calc = BTNFeatureCalculator()

# Sample data
past_races = [
    {'time': '1:30.00', 'distance_f': 10.0, 'course': 'Ascot'},
    {'time': '1:28.50', 'distance_f': 10.0, 'course': 'Ascot'},
    {'time': '1:29.25', 'distance_f': 10.0, 'course': 'Ascot'},
]

speed_features = speed_calc.calculate_all_speed_features(past_races, 'Ascot', 10.0)
print(f"✓ Speed features generated: {len(speed_features)} features")
print(f"  Sample: {speed_features['horse_avg_speed_furlongs_per_sec']:.4f} f/s")

# BTN test
past_races_btn = [
    {'btn': '2.5', 'ovr_btn': '3.0', 'position': 3, 'field_size': 10},
    {'btn': '1.0', 'ovr_btn': '1.5', 'position': 2, 'field_size': 12},
    {'btn': '0', 'ovr_btn': '0', 'position': 1, 'field_size': 8},
]

btn_features = btn_calc.calculate_all_btn_features(past_races_btn, 10)
print(f"✓ BTN features generated: {len(btn_features)} features")
print(f"  Sample: Avg BTN = {btn_features['horse_avg_btn_last_5']:.2f} lengths")

print("\n✅ All tests passed!")
```

Run it:
```bash
python test_new_features.py
```

---

## Step 12: Regenerate All Features

Once integrated and tested:

```bash
# Option A: Via GUI
# Tab 6 → "Regenerate Features"

# Option B: Via command line
cd Datafetch/ml
python feature_engineer_optimized.py --regenerate-all
```

---

## Step 13: Retrain Model

```bash
# Option A: Via GUI
# Tab 7 → Select "Flat" → "Start Training"

# Option B: Via command line
python train_baseline.py --race-type Flat --test-size 0.2
```

---

## Step 14: Run Diagnostics

```bash
python run_diagnostics.py --race-type Flat
```

**Expected results**:
- ✅ No odds features in top 20
- ✅ Feature importance shows: ratings, speed, BTN, form dominating
- ✅ Data leakage summary: 0 high-risk features

---

## Troubleshooting

### Import Errors
```python
# Make sure ml/ is in Python path
import sys
sys.path.append('/path/to/Datafetch')
```

### Missing Dependencies
```bash
pip install scipy numpy
```

### Database Column Errors
Check that your `results` table has:
- `time` column
- `btn` column
- `ovr_btn` column
- `weight_lbs` column

And `races` table has:
- `weather` column
- `rail_movements` column

### Feature Count Mismatch
After removing 12 and adding 27:
- Old: 91 features
- New: 91 - 12 + 27 = **106 features**

---

## Validation Checklist

Before deploying to production:

- [ ] All odds features removed from feature generation code
- [ ] All 27 new features successfully integrated
- [ ] Test script passes (parse functions, calculators work)
- [ ] Features regenerated for all 271K+ runners
- [ ] Model retrained successfully
- [ ] Diagnostics show 0% odds importance
- [ ] Feature importance dominated by fundamentals
- [ ] Calibration metrics acceptable (ECE < 0.10)
- [ ] A/B test shows new model makes sense
- [ ] 1 week paper trading successful

---

## Quick Reference: File Locations

```
Datafetch/ml/
├── FEATURE_SPECIFICATION.md       # Detailed specs
├── INTEGRATION_GUIDE.md          # This file
├── speed_features.py             # Speed calculator
├── btn_features.py               # BTN/OVR_BTN calculator
├── quality_features.py           # Quality metrics
├── weather_features.py           # Going/weather
├── weight_features.py            # Weight-adjusted
├── feature_engineer_optimized.py # Main engineer (TO MODIFY)
├── train_baseline.py             # Training script
└── run_diagnostics.py            # Diagnostics tool
```

---

## Support

If you encounter issues:

1. Check `feature_generation.log` for errors
2. Run diagnostics to see feature importance
3. Compare old vs new feature distributions
4. Ensure database has all required columns
5. Test on small subset first (1000 races)

---

## Next Steps After Integration

1. **A/B Testing**: Compare old model vs new model predictions
2. **Paper Trading**: Test for 1 week without real money
3. **Performance Monitoring**: Track ROI, strike rate, calibration
4. **Feature Analysis**: Identify which new features are most important
5. **Iteration**: Consider adding Phase 2 features (medical data, form history, etc.)

