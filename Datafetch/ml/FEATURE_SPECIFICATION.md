# Feature Engineering Specification v2.0
## Racing Fundamentals Model (No Odds Leakage)

---

## Overview

This specification defines all features for the new model that eliminates data leakage from odds-based features. The model will rely purely on racing fundamentals: horse ability, recent form, speed metrics, beaten distances, and contextual factors.

**Key Principle**: All features must be available BEFORE the race starts and BEFORE odds are published.

---

## Feature Categories

Total features: **128 features** (110 base + 18 discriminating features)

1. **Horse Form & Performance**: 17 features (unchanged)
2. **Trainer Stats**: 12 features (unchanged)
3. **Jockey Stats**: 7 features (unchanged)
4. **Combination Stats**: 3 features (unchanged)
5. **Race Context**: 8 features (unchanged)
6. **Physical Attributes**: 7 features (unchanged)
7. **Ratings & Rankings**: 15 features (unchanged)
8. **Speed & Pace**: 8 features (**6 new**)
9. **Draw Analysis**: 6 features (unchanged)
10. **Pedigree**: 3 features (unchanged)
11. **BTN (Beaten By) Features**: 8 features (**NEW**)
12. **OVR_BTN Features**: 4 features (**NEW**)
13. **Race Quality**: 3 features (**NEW**)
14. **Going/Weather**: 4 features (**NEW**)
15. **Weight-Adjusted**: 2 features (**NEW**)
16. **Market Position**: 1 feature (**NEW** - strategic odds anchor)
17. **Class Movement**: 4 features (**NEW** - class changes)
18. **Course Specialists**: 5 features (**NEW** - track suitability)
19. **Distance Optimization**: 4 features (**NEW** - trip suitability)
20. **Trainer Hot Streaks**: 4 features (**NEW** - recent form)

---

## 🚫 Features to REMOVE (12 odds-based features)

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

**Rationale**: These features cause 36%+ model importance and create circular logic where the model learns to follow the market instead of beating it.

---

## ✅ NEW FEATURES - Detailed Specifications

### 1. Race Speed Features (6 new features)

**Data Source**: `results.time` + `races.distance_f`

#### 1.1 `horse_avg_speed_furlongs_per_sec`
**Calculation**:
```python
# For each past race:
time_seconds = parse_race_time(results.time)  # "1:23.45" -> 83.45 seconds
distance_furlongs = races.distance_f          # e.g., 10.0
speed = distance_furlongs / time_seconds       # furlongs/second

# Average over last 5 races
horse_avg_speed_furlongs_per_sec = mean(speeds_last_5)
```

**Time Parsing Logic**:
```python
def parse_race_time(time_str):
    """
    Parse race time formats:
    - "1:23.45" -> 83.45 seconds
    - "23.45" -> 23.45 seconds  
    - "2:15" -> 135.0 seconds
    """
    if ':' in time_str:
        parts = time_str.split(':')
        minutes = int(parts[0])
        seconds = float(parts[1])
        return minutes * 60 + seconds
    else:
        return float(time_str)
```

**Handling Missing Data**:
- If < 3 past races with time data: Use field average
- If no field data: Use 0.12 (typical flat racing speed ~7-8f/min)

---

#### 1.2 `horse_best_speed_career`
**Calculation**:
```python
# Best (maximum) speed ever recorded for this horse
horse_best_speed_career = max(all_career_speeds)
```

**Use Case**: Identifies horses with peak performance capability, even if recent form is poor.

---

#### 1.3 `horse_speed_last_3_avg`
**Calculation**:
```python
# Average speed over last 3 races (more recent than last 5)
horse_speed_last_3_avg = mean(speeds_last_3)
```

**Use Case**: Recent speed indicator, more responsive to form changes.

---

#### 1.4 `horse_speed_improving`
**Calculation**:
```python
# Linear regression slope of last 5 speeds
# Positive = improving, negative = declining
from scipy.stats import linregress

speeds = [speed_5_races_ago, ..., speed_last_race]
races_ago = [5, 4, 3, 2, 1]

slope, intercept, r_value, p_value, std_err = linregress(races_ago, speeds)

horse_speed_improving = slope  # Positive = getting faster
```

**Normalization**: Divide by mean speed to get percentage improvement per race.

---

#### 1.5 `horse_speed_vs_track_record`
**Calculation**:
```python
# Compare horse's best speed at this course/distance to track record
track_record_speed = max(all_historical_speeds_at_course_distance)
horse_best_at_course_distance = max(horse_speeds_at_course_distance)

if track_record_speed > 0:
    horse_speed_vs_track_record = horse_best_at_course_distance / track_record_speed
else:
    horse_speed_vs_track_record = 0
```

**Range**: 0.0 to 1.0+ (1.0 = matched track record, 0.9 = 90% of record, 1.1 = broke record)

---

#### 1.6 `horse_speed_consistency`
**Calculation**:
```python
# Standard deviation of last 5 speeds
# Lower = more consistent, higher = erratic
horse_speed_consistency = std(speeds_last_5) / mean(speeds_last_5)
```

**Coefficient of variation**: Normalized by mean for comparability across speed ranges.

---

### 2. BTN (Beaten By) Features (8 new features)

**Data Source**: `results.btn` (distance beaten by winner in lengths)

**BTN Format Examples**:
- "2.5" = beaten by 2.5 lengths
- "nk" = neck (0.3 lengths)
- "hd" = head (0.2 lengths)
- "shd" = short head (0.1 lengths)
- "dist" = distance (30+ lengths)
- "" or NULL = won the race (0 lengths)

**BTN Parsing Logic**:
```python
def parse_btn(btn_str):
    """Convert BTN string to numeric lengths"""
    if btn_str is None or btn_str == '':
        return 0.0  # Won the race
    
    btn_str = str(btn_str).lower().strip()
    
    # Handle special cases
    conversions = {
        'nk': 0.3,
        'neck': 0.3,
        'hd': 0.2,
        'head': 0.2,
        'shd': 0.1,
        'short-head': 0.1,
        'sht-hd': 0.1,
        'dist': 30.0,
        'distance': 30.0
    }
    
    if btn_str in conversions:
        return conversions[btn_str]
    
    # Try to parse as float
    try:
        return float(btn_str)
    except:
        return None  # Invalid data
```

---

#### 2.1 `horse_avg_btn_last_5`
**Calculation**:
```python
# Average distance beaten over last 5 races
btns = [parse_btn(btn) for btn in last_5_races if parse_btn(btn) is not None]
horse_avg_btn_last_5 = mean(btns) if len(btns) >= 3 else None
```

**Interpretation**: Lower is better (closer to winner).

---

#### 2.2 `horse_median_btn_last_5`
**Calculation**:
```python
# Median BTN (more robust to outliers like "dist")
horse_median_btn_last_5 = median(btns_last_5)
```

**Use Case**: Better than mean when horse has occasional very poor runs.

---

#### 2.3 `horse_btn_improving`
**Calculation**:
```python
# Linear regression slope of last 5 BTNs
# Negative slope = improving (getting closer to winners)
slope, _, _, _, _ = linregress([5, 4, 3, 2, 1], btns_last_5)

horse_btn_improving = -slope  # Negate so positive = improving
```

---

#### 2.4 `horse_pct_within_3_lengths`
**Calculation**:
```python
# Percentage of races where horse finished within 3 lengths of winner
within_3L = sum(1 for btn in career_btns if btn <= 3.0)
total_races = len(career_btns)

horse_pct_within_3_lengths = within_3L / total_races if total_races > 0 else 0
```

**Range**: 0.0 to 1.0 (higher = frequently competitive)

---

#### 2.5 `horse_btn_vs_field_avg`
**Calculation**:
```python
# How does this horse's average BTN compare to field average?
field_avg_btn = mean([horse_avg_btn_last_5 for all horses in race])
horse_btn_vs_field_avg = field_avg_btn - horse_avg_btn_last_5
```

**Interpretation**: Positive = horse better than field average (beaten by less).

---

#### 2.6 `horse_btn_vs_winner_percentile`
**Calculation**:
```python
# Rank in field by average BTN (lower BTN = better rank)
field_btns_sorted = sorted([horse_avg_btn_last_5 for all horses])
rank = field_btns_sorted.index(this_horse_avg_btn) + 1
field_size = len(field_btns_sorted)

horse_btn_vs_winner_percentile = rank / field_size
```

**Range**: 0.0 to 1.0 (lower = closer to winners historically)

---

#### 2.7 `horse_best_btn_career`
**Calculation**:
```python
# Closest finish to winner (minimum BTN) in career
horse_best_btn_career = min(career_btns)
```

**Use Case**: Identifies horses that have shown ability to finish very close.

---

#### 2.8 `horse_btn_consistency`
**Calculation**:
```python
# Coefficient of variation of BTN
horse_btn_consistency = std(btns_last_5) / mean(btns_last_5)
```

**Interpretation**: Lower = consistent finishes, higher = erratic.

---

### 3. OVR_BTN (Overall Beaten) Features (4 new features)

**Data Source**: `results.ovr_btn` (cumulative distance behind, accounting for all horses ahead)

**Example**:
- Winner (1st): ovr_btn = 0
- 2nd place (beaten 2L): ovr_btn = 2L
- 3rd place (beaten 1L by 2nd): ovr_btn = 3L (2 + 1)
- 4th place (beaten 0.5L by 3rd): ovr_btn = 3.5L (2 + 1 + 0.5)

**OVR_BTN gives better positioning information than BTN alone.**

---

#### 3.1 `horse_avg_ovr_btn_last_5`
**Calculation**:
```python
# Average cumulative distance beaten
ovr_btns = [parse_btn(ovr_btn) for ovr_btn in last_5_races]
horse_avg_ovr_btn_last_5 = mean(ovr_btns)
```

---

#### 3.2 `horse_ovr_btn_improving`
**Calculation**:
```python
# Trend in OVR_BTN (negative slope = improving)
slope, _, _, _, _ = linregress([5, 4, 3, 2, 1], ovr_btns_last_5)
horse_ovr_btn_improving = -slope
```

---

#### 3.3 `horse_ovr_btn_vs_field`
**Calculation**:
```python
# Relative OVR_BTN vs field
field_avg_ovr_btn = mean([horse_avg_ovr_btn_last_5 for all horses])
horse_ovr_btn_vs_field = field_avg_ovr_btn - horse_avg_ovr_btn_last_5
```

**Positive = better than field average.**

---

#### 3.4 `horse_pct_top_half_finishes`
**Calculation**:
```python
# Percentage of races where horse finished in top half of field
# Use OVR_BTN to determine positioning

top_half_finishes = 0
for race in career_races:
    # Get all OVR_BTNs in that race
    race_ovr_btns_sorted = sorted(race_ovr_btns)
    median_ovr_btn = median(race_ovr_btns_sorted)
    
    if horse_ovr_btn <= median_ovr_btn:
        top_half_finishes += 1

horse_pct_top_half_finishes = top_half_finishes / total_races
```

---

### 4. Race Quality & Competitiveness (3 new features)

#### 4.1 `race_competitiveness`
**Calculation**:
```python
# Average BTN across all finishers in today's race historical data
# Lower = tighter finishes historically at this course/distance/class

similar_races = get_races(same_course, same_distance, similar_class)
avg_btns_per_race = [mean(race_btns) for race in similar_races]

race_competitiveness = 1 / mean(avg_btns_per_race) if mean > 0 else 0
```

**Higher value = more competitive races historically.**

---

#### 4.2 `field_quality_rating`
**Calculation**:
```python
# Weighted average of field's past performance
field_rprs = [horse.horse_best_rating for horse in field]
field_recent_form = [horse.horse_form_last_5_avg for horse in field]

# Weight by recency and consistency
field_quality_rating = mean(field_rprs) * mean(field_recent_form)
```

---

#### 4.3 `horse_beaten_by_quality`
**Calculation**:
```python
# Average RPR of horses that beat this horse in past races
beaten_by_horses = []
for past_race in last_5_races:
    horses_ahead = get_horses_with_better_position(past_race)
    for h in horses_ahead:
        beaten_by_horses.append(h.rpr)

horse_beaten_by_quality = mean(beaten_by_horses) if len(beaten_by_horses) > 0 else 0
```

**Use Case**: If consistently beaten by high-rated horses, that's less concerning than being beaten by weak horses.

---

### 5. Going/Weather Interactions (4 new features)

#### 5.1 `horse_soft_going_speed_ratio`
**Calculation**:
```python
# Speed on soft/heavy going vs good/firm going
soft_speeds = [speed for race in career if going in ['Soft', 'Heavy', 'Yielding']]
firm_speeds = [speed for race in career if going in ['Good', 'Good to Firm', 'Firm']]

if len(firm_speeds) >= 2 and len(soft_speeds) >= 2:
    horse_soft_going_speed_ratio = mean(soft_speeds) / mean(firm_speeds)
else:
    horse_soft_going_speed_ratio = 1.0  # Neutral assumption
```

**Range**: <1.0 = prefers firm, >1.0 = prefers soft.

---

#### 5.2 `horse_weather_performance`
**Calculation**:
```python
# Win rate in wet weather vs dry
wet_races = [race for race in career if weather in ['Rain', 'Showers', 'Drizzle']]
dry_races = [race for race in career if weather in ['Fine', 'Sunny', 'Cloudy', 'Overcast']]

wet_win_rate = sum(1 for r in wet_races if r.position == 1) / len(wet_races)
dry_win_rate = sum(1 for r in dry_races if r.position == 1) / len(dry_races)

horse_weather_performance = wet_win_rate / dry_win_rate if dry_win_rate > 0 else 1.0
```

---

#### 5.3 `rail_position_advantage`
**Calculation**:
```python
# Impact of rail movements on draw advantage
# Positive rail movement = inside rail favored
# Negative = outside favored

rail_movement = parse_rail_movements(races.rail_movements)  # e.g., +3 yards
draw_normalized = (draw - 1) / (field_size - 1)  # 0 to 1

if rail_movement > 0:
    # Inside draw advantaged
    rail_position_advantage = (1 - draw_normalized) * abs(rail_movement)
elif rail_movement < 0:
    # Outside draw advantaged
    rail_position_advantage = draw_normalized * abs(rail_movement)
else:
    rail_position_advantage = 0
```

---

#### 5.4 `going_change_adaptation`
**Calculation**:
```python
# How well does horse adapt when going changes from last run?
last_going = horse.last_race.going
today_going = today_race.going

going_change_magnitude = abs(going_scale[today_going] - going_scale[last_going])

# Scale: Firm=1, Good to Firm=2, Good=3, Good to Soft=4, Soft=5, Heavy=6

# Look at historical performance when going changed similarly
similar_changes = [race for race in career 
                   if abs(going_scale[race.going] - going_scale[race.prev_going]) >= going_change_magnitude]

adaptation_win_rate = sum(1 for r in similar_changes if r.position <= 3) / len(similar_changes)

going_change_adaptation = adaptation_win_rate if len(similar_changes) >= 3 else 0.5
```

---

### 6. Weight-Adjusted Performance (2 new features)

#### 6.1 `horse_weight_adjusted_rating`
**Calculation**:
```python
# Adjust RPR for weight carried
# Rule of thumb: 1 lb = ~1 point of rating in Flat racing

standard_weight = 126  # lbs (typical flat racing weight)
actual_weight = results.weight_lbs

weight_difference = actual_weight - standard_weight

# Adjust rating (carrying more weight = tougher, so increase effective rating)
horse_weight_adjusted_rating = horse.rpr + (weight_difference * 1.0)
```

---

#### 6.2 `horse_weight_performance_trend`
**Calculation**:
```python
# How does performance change as weight increases?
weights = [race.weight_lbs for race in last_10_races]
rprs = [race.rpr for race in last_10_races]

slope, _, _, _, _ = linregress(weights, rprs)

horse_weight_performance_trend = slope
```

**Negative slope = struggles with weight, positive = handles weight well.**

---

### 7. Discriminating Features - Market Position (1 feature)

**Purpose**: Provide categorical odds anchor without full data leakage

#### 7.1 `market_position_tier`

**Type**: Integer (0-4)  
**Purpose**: Convert continuous odds to discrete market position

**Calculation**:
```python
if odds < 3.0:
    tier = 0  # Strong Favorite
elif odds < 5.0:
    tier = 1  # Co-Favorite
elif odds < 10.0:
    tier = 2  # Mid-range
elif odds < 20.0:
    tier = 3  # Outsider
else:
    tier = 4  # Longshot
```

**Rationale**: 
- Categorical representation reduces data leakage vs continuous odds
- Provides baseline ranking anchor for model
- Model can adjust from this baseline using fundamental features
- Less information than raw odds (5 categories vs infinite precision)

---

### 8. Discriminating Features - Class Movement (4 features)

**Purpose**: Detect horses moving between class levels (huge signal in racing)

#### 8.1 `class_last_3_avg`

**Type**: Float  
**Purpose**: Average class level over last 3 races  
**Range**: 1.0 (highest) to 7.0 (lowest)

**Calculation**: Average of parsed class from last 3 races

#### 8.2 `class_change`

**Type**: Float  
**Purpose**: Difference from recent average to today's class  
**Range**: -6.0 to +6.0

**Calculation**: `current_class - class_last_3_avg`

**Interpretation**:
- Positive = Dropping in class (easier race) = GOOD
- Negative = Rising in class (harder race) = BAD
- Note: Class 1 is best, Class 7 is worst

#### 8.3 `dropping_in_class`

**Type**: Binary (0/1)  
**Purpose**: Flag significant drop in class  
**Calculation**: 1 if `class_change > 0.5`, else 0

**Example**: Class 3→5 or Class 4→6 (easier competition)

#### 8.4 `rising_in_class`

**Type**: Binary (0/1)  
**Purpose**: Flag significant rise in class  
**Calculation**: 1 if `class_change < -0.5`, else 0

**Example**: Class 5→3 or Class 6→4 (harder competition)

---

### 9. Discriminating Features - Course Specialists (5 features)

**Purpose**: Identify horses that excel at specific tracks

#### 9.1 `course_runs`

**Type**: Integer  
**Purpose**: Number of previous runs at this specific course  
**Range**: 0 to ~50

#### 9.2 `course_wins`

**Type**: Integer  
**Purpose**: Wins at this course  
**Range**: 0 to ~20

#### 9.3 `course_win_rate`

**Type**: Float  
**Purpose**: Win rate at this course  
**Range**: 0.0 to 1.0  
**Calculation**: `course_wins / course_runs` (min 2 runs for rate)

#### 9.4 `course_place_rate`

**Type**: Float  
**Purpose**: Top 3 finish rate at this course  
**Range**: 0.0 to 1.0

#### 9.5 `course_specialist`

**Type**: Binary (0/1)  
**Purpose**: Flag proven track specialists  
**Calculation**: 1 if `course_runs >= 3 AND course_win_rate >= 0.3`, else 0

**Rationale**: Some horses perform 20-30% better at certain tracks due to track shape, surface, or familiarity

---

### 10. Discriminating Features - Distance Optimization (4 features)

**Purpose**: Identify if horse is racing at optimal trip

#### 10.1 `best_distance_f`

**Type**: Float  
**Purpose**: Distance (furlongs) where horse has best average position  
**Range**: 5.0 to 20.0  
**Calculation**: Find distance with lowest avg finishing position (min 2 runs)

#### 10.2 `distance_from_optimal`

**Type**: Float  
**Purpose**: Absolute difference from best distance  
**Range**: 0.0 (optimal) to 15.0 (very wrong trip)

**Calculation**: `abs(current_distance - best_distance_f)`

**Interpretation**:
- 0.0-1.0 = Optimal range
- 1.0-3.0 = Acceptable
- 3.0+ = Wrong trip (major disadvantage)

#### 10.3 `runs_at_distance`

**Type**: Integer  
**Purpose**: Experience at this distance (±0.5f)  
**Range**: 0 to ~30

#### 10.4 `win_rate_at_distance`

**Type**: Float  
**Purpose**: Win rate at this distance range  
**Range**: 0.0 to 1.0

**Rationale**: Horses bred for sprints struggle at 12f+, stayers struggle at 5-6f

---

### 11. Discriminating Features - Trainer Hot Streaks (4 features)

**Purpose**: Capture trainer's recent form cycle

#### 11.1 `trainer_wins_last_14d`

**Type**: Integer  
**Purpose**: Wins in last 14 days  
**Range**: 0 to ~20

**Calculation**: Count wins from results table where date is within 14 days before race

#### 11.2 `trainer_runs_last_14d`

**Type**: Integer  
**Purpose**: Total runners in last 14 days  
**Range**: 0 to ~100

#### 11.3 `trainer_win_rate_recent`

**Type**: Float  
**Purpose**: Recent strike rate  
**Range**: 0.0 to 1.0  
**Calculation**: `trainer_wins_last_14d / trainer_runs_last_14d`

#### 11.4 `trainer_is_hot`

**Type**: Binary (0/1)  
**Purpose**: Flag trainers in excellent recent form  
**Calculation**: 1 if `win_rate_recent >= 0.15 AND wins >= 3`, else 0

**Rationale**: 
- Trainers cycle through hot/cold periods
- Hot trainer = horses peaking together = 15-20% better results
- Captures momentum better than long-term averages

---

## Feature Generation Priority

### Phase 1: Remove Odds Features
- Quick win: Immediately eliminate data leakage
- Expected: ~24-48 hour implementation

### Phase 2: Add Speed Features
- High impact: 6 features based on time/distance
- Expected: Model will start preferring fast horses

### Phase 3: Add BTN Features
- Medium-high impact: 8 features on finish proximity
- Expected: Better understanding of competitiveness

### Phase 4: Add Remaining Features
- OVR_BTN, quality, going/weather, weight-adjusted
- Expected: Incremental improvements

---

## Testing Strategy

1. **Unit Tests**: Test parsing functions (time, BTN, going)
2. **Integration Tests**: Generate features for 100 sample races
3. **Distribution Checks**: Ensure feature ranges are reasonable
4. **Correlation Analysis**: Check for multicollinearity
5. **A/B Testing**: Compare old model vs new model predictions

---

## Performance Expectations

### Before (With Odds Leakage):
- Top feature: `odds_decimal` (26%)
- Model learns to: Follow favorites
- Long-term edge: None (following efficient market)

### After (Fundamental Features):
- Top feature: Expected `horse_rpr_rank` or `horse_avg_speed`
- Model learns to: Identify horses with strong fundamentals
- Long-term edge: Possible (identifying market inefficiencies)

---

## Implementation Files

1. **`speed_features.py`**: Race speed calculations
2. **`btn_features.py`**: BTN/OVR_BTN calculations
3. **`quality_features.py`**: Race quality metrics
4. **`weather_features.py`**: Going/weather interactions
5. **`weight_features.py`**: Weight-adjusted performance
6. **`feature_engineer_v2.py`**: Main feature engineering pipeline

---

## Migration Path

```bash
# 1. Create new feature engineer
python feature_engineer_v2.py --validate-only

# 2. Generate features for small test set (1000 races)
python feature_engineer_v2.py --test-mode --limit 1000

# 3. Compare feature distributions
python compare_feature_distributions.py

# 4. Generate full feature set
python feature_engineer_v2.py --full

# 5. Retrain model
python train_baseline.py --race-type Flat

# 6. Run diagnostics
python run_diagnostics.py --race-type Flat

# 7. A/B test on upcoming races
python compare_models.py --old models/xgboost_flat.json --new models/xgboost_flat_v2.json
```

---

## Success Criteria

✅ **Feature Importance**: No odds features in top 20
✅ **Data Leakage**: 0% importance from market data
✅ **Top Features**: Racing fundamentals (speed, ratings, BTN, form)
✅ **Model Performance**: Maintains or improves test set metrics
✅ **Calibration**: ECE < 0.10
✅ **Real-world Testing**: 1 week paper trading without major issues

