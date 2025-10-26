# Data Exploration & Speed-Based Target Evaluation Plan

## Overview

Inspired by the Medium article showing that **predicting speed gave better results than predicting time**, this plan explores whether switching from a **ranking objective** to a **regression objective** (predicting speed/time) could fix the flat probability issue.

**Key insight from article**: "By predicting speed, we got better time predictions than directly predicting time" - because the distribution was cleaner.

---

## Phase 1: Explore Current Data & Target Distributions (2-3 hours)

### 1.1 Understand Current Ranking Target

**Goal**: See what the model is actually trying to learn

```python
# File: Datafetch/ml/explore_ranking_target.py

import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

def analyze_current_target():
    """Analyze the distribution of the ranking target"""
    
    conn = sqlite3.connect('racing_pro.db')
    
    # Get position distribution
    query = """
        SELECT 
            r.position,
            COUNT(*) as count,
            ra.field_size
        FROM results r
        JOIN races ra ON r.race_id = ra.race_id
        WHERE ra.type = 'Flat'
          AND r.position IS NOT NULL
          AND r.position != ''
        GROUP BY r.position
        ORDER BY CAST(r.position AS INTEGER)
    """
    
    positions = pd.read_sql_query(query, conn)
    
    # Plot position distribution
    plt.figure(figsize=(12, 6))
    plt.bar(positions['position'].astype(int), positions['count'])
    plt.xlabel('Position')
    plt.ylabel('Count')
    plt.title('Distribution of Finishing Positions (Flat Racing)')
    plt.savefig('ml/diagnostics/position_distribution.png')
    plt.close()
    
    print("Position distribution saved")
    
    # Get win rate by field size
    query = """
        SELECT 
            ra.field_size,
            COUNT(*) as total_runners,
            SUM(CASE WHEN r.position = '1' THEN 1 ELSE 0 END) as wins,
            ROUND(100.0 * SUM(CASE WHEN r.position = '1' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_pct
        FROM results r
        JOIN races ra ON r.race_id = ra.race_id
        WHERE ra.type = 'Flat'
        GROUP BY ra.field_size
        ORDER BY CAST(ra.field_size AS INTEGER)
    """
    
    field_sizes = pd.read_sql_query(query, conn)
    print("\nWin rate by field size:")
    print(field_sizes)
    
    # This shows what a uniform model would predict
    # If field_size = 10, uniform = 10% per horse
    # Your model giving 8-9% to all suggests it's close to uniform
    
    conn.close()
```

**Expected insight**: If your model is giving 8-9% to all horses in 10-horse races, it's essentially predicting uniform probabilities - it hasn't learned meaningful ranking.

### 1.2 Explore Finish Time Distribution (Like Article)

**Goal**: See if time/speed has cleaner distribution than positions

```python
# File: Datafetch/ml/explore_finish_times.py

def analyze_finish_times():
    """Analyze finish time distribution (replicating article's analysis)"""
    
    conn = sqlite3.connect('racing_pro.db')
    
    # Get finish times for winners
    query = """
        SELECT 
            ra.race_id,
            ra.type,
            ra.distance_f,
            r.time as finish_time,
            ra.going,
            ra.course
        FROM results r
        JOIN races ra ON r.race_id = ra.race_id
        WHERE ra.type = 'Flat'
          AND r.position = '1'
          AND r.time IS NOT NULL
          AND r.time != ''
        ORDER BY ra.date DESC
        LIMIT 50000
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Parse time to seconds
    def parse_time_to_seconds(time_str):
        """Convert time string like '1:23.45' to seconds"""
        try:
            if ':' in str(time_str):
                parts = str(time_str).split(':')
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            else:
                return float(time_str)
        except:
            return None
    
    df['finish_time_seconds'] = df['finish_time'].apply(parse_time_to_seconds)
    df = df.dropna(subset=['finish_time_seconds'])
    
    # Plot 1: Finish time distribution (like article)
    plt.figure(figsize=(12, 6))
    plt.hist(df['finish_time_seconds'], bins=50, edgecolor='black')
    plt.xlabel('Finish Time (seconds)')
    plt.ylabel('Count')
    plt.title('Distribution of Winning Times (Flat Racing)')
    plt.savefig('ml/diagnostics/finish_time_distribution.png')
    plt.close()
    
    print(f"Finish time distribution saved (n={len(df)})")
    print(f"Min: {df['finish_time_seconds'].min():.1f}s")
    print(f"Max: {df['finish_time_seconds'].max():.1f}s")
    print(f"Mean: {df['finish_time_seconds'].mean():.1f}s")
    print(f"Std: {df['finish_time_seconds'].std():.1f}s")
    
    # Plot 2: Speed distribution (KEY INSIGHT FROM ARTICLE)
    # Speed = distance / time (m/s)
    # Convert furlongs to meters (1f = 201.168m)
    df['distance_m'] = df['distance_f'].astype(float) * 201.168
    df['speed_mps'] = df['distance_m'] / df['finish_time_seconds']
    
    plt.figure(figsize=(12, 6))
    plt.hist(df['speed_mps'].dropna(), bins=50, edgecolor='black')
    plt.xlabel('Speed (meters per second)')
    plt.ylabel('Count')
    plt.title('Distribution of Winning Speeds (Flat Racing)')
    plt.savefig('ml/diagnostics/speed_distribution.png')
    plt.close()
    
    print(f"\nSpeed distribution saved")
    print(f"Min: {df['speed_mps'].min():.2f} m/s")
    print(f"Max: {df['speed_mps'].max():.2f} m/s")
    print(f"Mean: {df['speed_mps'].mean():.2f} m/s")
    print(f"Std: {df['speed_mps'].std():.2f} m/s")
    
    # Plot 3: Speed by distance (should show cleaner clusters)
    plt.figure(figsize=(14, 6))
    plt.scatter(df['distance_f'].astype(float), df['speed_mps'], alpha=0.3)
    plt.xlabel('Distance (furlongs)')
    plt.ylabel('Speed (m/s)')
    plt.title('Speed vs Distance (Flat Racing)')
    plt.savefig('ml/diagnostics/speed_vs_distance.png')
    plt.close()
    
    # Compare distributions
    print("\n=== DISTRIBUTION COMPARISON ===")
    print(f"Finish Time CV (coefficient of variation): {df['finish_time_seconds'].std() / df['finish_time_seconds'].mean():.3f}")
    print(f"Speed CV: {df['speed_mps'].std() / df['speed_mps'].mean():.3f}")
    print("\nLower CV = cleaner distribution = easier to fit")
    
    return df
```

**Expected insight**: Speed should have lower coefficient of variation (CV) than time, indicating a cleaner, more learnable distribution.

### 1.3 Explore BTN (Beaten By) Distribution

**Goal**: Check if `ovr_btn` (like article used) has distribution issues

```python
# File: Datafetch/ml/explore_btn_distribution.py

def analyze_btn_distribution():
    """Check BTN distribution (article said this was problematic)"""
    
    conn = sqlite3.connect('racing_pro.db')
    
    query = """
        SELECT 
            r.ovr_btn,
            r.btn,
            r.position
        FROM results r
        JOIN races ra ON r.race_id = ra.race_id
        WHERE ra.type = 'Flat'
          AND r.ovr_btn IS NOT NULL
        LIMIT 100000
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Parse BTN to float
    def parse_btn(btn_str):
        try:
            return float(btn_str)
        except:
            return None
    
    df['ovr_btn_float'] = df['ovr_btn'].apply(parse_btn)
    df = df.dropna(subset=['ovr_btn_float'])
    
    # Plot BTN distribution
    plt.figure(figsize=(12, 6))
    plt.hist(df['ovr_btn_float'], bins=100, edgecolor='black')
    plt.xlabel('OVR_BTN (lengths behind winner)')
    plt.ylabel('Count')
    plt.title('Distribution of OVR_BTN (Flat Racing)')
    plt.axvline(x=0, color='red', linestyle='--', label='Winner (0)')
    plt.legend()
    plt.savefig('ml/diagnostics/ovr_btn_distribution.png')
    plt.close()
    
    print("BTN distribution saved")
    print(f"Winners (ovr_btn=0): {(df['ovr_btn_float'] == 0).sum()}")
    print(f"Non-winners: {(df['ovr_btn_float'] > 0).sum()}")
    print(f"Percentage at 0: {100 * (df['ovr_btn_float'] == 0).sum() / len(df):.2f}%")
    
    # This should show heavy skew toward 0 (like article)
    # Model will be biased to predict 0
```

**Expected insight**: Like the article, BTN should be heavily skewed toward 0 (winners), making it a poor target.

### 1.4 Explore Current Model Predictions

**Goal**: Understand what your ranking model is actually outputting

```python
# File: Datafetch/ml/explore_current_predictions.py

def analyze_current_model_predictions():
    """Load recent predictions and analyze distribution"""
    
    conn = sqlite3.connect('upcoming_races.db')
    
    query = """
        SELECT 
            race_id,
            horse_name,
            win_probability,
            place_probability
        FROM predictions
        ORDER BY created_at DESC
        LIMIT 1000
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Plot win probability distribution
    plt.figure(figsize=(12, 6))
    plt.hist(df['win_probability'], bins=50, edgecolor='black')
    plt.xlabel('Win Probability')
    plt.ylabel('Count')
    plt.title('Current Model Win Probability Distribution')
    plt.axvline(x=df['win_probability'].mean(), color='red', 
                linestyle='--', label=f'Mean: {df["win_probability"].mean():.3f}')
    plt.legend()
    plt.savefig('ml/diagnostics/current_predictions_distribution.png')
    plt.close()
    
    print("Current predictions distribution saved")
    print(f"Mean: {df['win_probability'].mean():.3f}")
    print(f"Std: {df['win_probability'].std():.3f}")
    print(f"Min: {df['win_probability'].min():.3f}")
    print(f"Max: {df['win_probability'].max():.3f}")
    
    # Group by race and check variance
    race_variance = df.groupby('race_id')['win_probability'].std()
    print(f"\nAverage within-race std: {race_variance.mean():.4f}")
    print("(Low std = flat predictions)")
```

**Expected insight**: Should confirm 8-9% predictions with very low standard deviation.

---

## Phase 2: Design Speed-Based Alternative (2-3 hours)

### 2.1 Two-Model Architecture (Inspired by Article)

**Model 1: Race Pace Predictor** (race-level features)
- **Target**: Expected winning time or speed
- **Features**: Distance, going, course, field quality, weather
- **Output**: Baseline race speed/time

**Model 2: Horse Speed Deviation** (horse-level features)  
- **Target**: Horse's speed relative to race baseline
- **Features**: Horse form, trainer, jockey, class, course specialist, etc.
- **Output**: Speed adjustment (+/- from baseline)

**Final Prediction**:
```python
horse_predicted_speed = race_baseline_speed + horse_speed_adjustment
horse_win_probability = convert_speed_to_probability(horse_predicted_speed, all_horses)
```

### 2.2 Create Speed Prediction Module

```python
# File: Datafetch/ml/speed_predictor.py

import xgboost as xgb
import numpy as np
from typing import Dict, List, Tuple

class SpeedBasedPredictor:
    """
    Two-model approach for predicting race outcomes via speed
    
    Model 1: Predicts race pace (expected winning speed)
    Model 2: Predicts each horse's deviation from race pace
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.race_pace_model = None  # XGBoost Regressor
        self.horse_deviation_model = None  # XGBoost Regressor
        
    def prepare_race_pace_features(self, race: Dict) -> np.ndarray:
        """
        Extract race-level features for pace prediction
        
        Features:
        - distance_f
        - going_encoded (soft, good, firm, etc.)
        - surface_encoded
        - course_encoded (or course average speed)
        - field_avg_rating (quality)
        - weather_encoded
        - prize_money (proxy for quality)
        """
        features = [
            race['distance_f'],
            race['going_encoded'],
            race['surface_encoded'],
            race['course_avg_speed'],  # Historical avg speed at course
            race['field_avg_rpr'],
            race['weather_encoded'],
            race['prize_money']
        ]
        return np.array(features)
    
    def prepare_horse_deviation_features(self, 
                                         runner: Dict, 
                                         race: Dict,
                                         race_pace: float) -> np.ndarray:
        """
        Extract horse-level features for speed deviation prediction
        
        Features: Use your existing 128 features!
        - All horse form features
        - Trainer/jockey features
        - Class movement features
        - Course specialist features
        - Distance optimization features
        - Plus: expected_race_pace as additional feature
        """
        # Use your existing feature_engineer!
        features = self.feature_engineer.compute_runner_features(
            runner, race, result=None
        )
        
        # Add race pace as feature
        features['expected_race_pace'] = race_pace
        
        return features
    
    def train_race_pace_model(self, training_data: pd.DataFrame):
        """
        Train Model 1: Race Pace Prediction
        
        Target: winning_speed = distance_m / winning_time_seconds
        """
        X = training_data[self.race_pace_features]
        y = training_data['winning_speed']  # m/s
        
        self.race_pace_model = xgb.XGBRegressor(
            objective='reg:squarederror',
            n_estimators=500,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8
        )
        
        self.race_pace_model.fit(X, y)
        
        # Evaluate
        y_pred = self.race_pace_model.predict(X)
        mae = np.mean(np.abs(y - y_pred))
        print(f"Race Pace Model MAE: {mae:.3f} m/s")
        
        return mae
    
    def train_horse_deviation_model(self, training_data: pd.DataFrame):
        """
        Train Model 2: Horse Speed Deviation
        
        Target: horse_speed_deviation = horse_actual_speed - winning_speed
        
        Winner: deviation = 0 (or slightly negative if they won easily)
        2nd place: deviation = -0.5 m/s (slower than winner)
        10th place: deviation = -2.0 m/s (much slower)
        """
        X = training_data[self.horse_features]
        y = training_data['speed_deviation']  # horse_speed - winning_speed
        
        self.horse_deviation_model = xgb.XGBRegressor(
            objective='reg:squarederror',
            n_estimators=1000,
            max_depth=8,
            learning_rate=0.03,
            subsample=0.8,
            colsample_bytree=0.8
        )
        
        self.horse_deviation_model.fit(X, y)
        
        # Evaluate
        y_pred = self.horse_deviation_model.predict(X)
        mae = np.mean(np.abs(y - y_pred))
        print(f"Horse Deviation Model MAE: {mae:.3f} m/s")
        
        return mae
    
    def predict_race(self, race: Dict, runners: List[Dict]) -> Dict:
        """
        Predict race outcome using two-model approach
        
        Returns: Dict with win probabilities for each horse
        """
        # Step 1: Predict race pace
        race_features = self.prepare_race_pace_features(race)
        race_pace = self.race_pace_model.predict([race_features])[0]
        
        # Step 2: Predict each horse's deviation
        predictions = []
        for runner in runners:
            horse_features = self.prepare_horse_deviation_features(
                runner, race, race_pace
            )
            speed_deviation = self.horse_deviation_model.predict([horse_features])[0]
            predicted_speed = race_pace + speed_deviation
            
            predictions.append({
                'horse_id': runner['horse_id'],
                'horse_name': runner['horse_name'],
                'predicted_speed': predicted_speed,
                'race_pace': race_pace,
                'deviation': speed_deviation
            })
        
        # Step 3: Convert speeds to probabilities
        # Fastest horse = highest probability
        speeds = np.array([p['predicted_speed'] for p in predictions])
        
        # Method 1: Softmax on speeds
        # Higher speed = higher probability
        probabilities = self._speeds_to_probabilities(speeds)
        
        for i, pred in enumerate(predictions):
            pred['win_probability'] = probabilities[i]
        
        return predictions
    
    def _speeds_to_probabilities(self, speeds: np.ndarray) -> np.ndarray:
        """
        Convert predicted speeds to win probabilities
        
        Using softmax: higher speed = higher probability
        """
        # Normalize speeds to 0-1 range
        speeds_normalized = (speeds - speeds.min()) / (speeds.max() - speeds.min() + 1e-8)
        
        # Apply softmax with temperature
        temperature = 2.0  # Controls how flat/sharp probabilities are
        exp_speeds = np.exp(speeds_normalized / temperature)
        probabilities = exp_speeds / exp_speeds.sum()
        
        return probabilities
```

### 2.3 Prepare Training Data for Speed Models

```python
# File: Datafetch/ml/prepare_speed_training_data.py

def prepare_speed_targets():
    """
    Create training targets for both models
    
    Model 1 target: winning_speed (race-level)
    Model 2 target: horse_speed_deviation (horse-level)
    """
    conn = sqlite3.connect('racing_pro.db')
    
    # Get all race results with times
    query = """
        SELECT 
            r.race_id,
            r.horse_id,
            r.position,
            r.time as horse_time,
            r.ovr_btn,
            ra.distance_f,
            (SELECT time FROM results 
             WHERE race_id = r.race_id AND position = '1' 
             LIMIT 1) as winning_time
        FROM results r
        JOIN races ra ON r.race_id = ra.race_id
        WHERE ra.type = 'Flat'
          AND r.time IS NOT NULL
          AND ra.distance_f IS NOT NULL
        ORDER BY ra.date
    """
    
    df = pd.read_sql_query(query, conn)
    
    # Parse times to seconds
    df['horse_time_sec'] = df['horse_time'].apply(parse_time_to_seconds)
    df['winning_time_sec'] = df['winning_time'].apply(parse_time_to_seconds)
    df['distance_m'] = df['distance_f'].astype(float) * 201.168
    
    # Calculate speeds
    df['horse_speed'] = df['distance_m'] / df['horse_time_sec']  # m/s
    df['winning_speed'] = df['distance_m'] / df['winning_time_sec']  # m/s
    
    # Calculate deviation (Model 2 target)
    df['speed_deviation'] = df['horse_speed'] - df['winning_speed']
    
    # For winners: deviation should be 0
    # For 2nd place: deviation should be negative (slower)
    
    print(f"Training data prepared: {len(df)} records")
    print(f"Speed deviation mean: {df['speed_deviation'].mean():.3f} m/s")
    print(f"Speed deviation std: {df['speed_deviation'].std():.3f} m/s")
    
    # Save to new table
    df.to_sql('speed_training_targets', conn, if_exists='replace', index=False)
    conn.close()
    
    return df
```

---

## Phase 3: Compare Approaches (1-2 hours)

### 3.1 Create Comparison Framework

```python
# File: Datafetch/ml/compare_approaches.py

class ModelComparison:
    """Compare ranking vs speed-based approaches"""
    
    def compare_distributions(self):
        """
        Compare target distributions
        
        1. Current: Positions (discrete, 1-20)
        2. Alternative: Speed deviation (continuous, gaussian-like)
        """
        # Load data
        positions = self.get_position_distribution()
        speed_devs = self.get_speed_deviation_distribution()
        
        # Calculate metrics
        print("=== DISTRIBUTION COMPARISON ===")
        print(f"Positions - Unique values: {len(positions.unique())}")
        print(f"Speed deviations - Unique values: {len(speed_devs.unique())}")
        
        print(f"\nPositions - Skewness: {positions.skew():.3f}")
        print(f"Speed deviations - Skewness: {speed_devs.skew():.3f}")
        
        print(f"\nPositions - Kurtosis: {positions.kurtosis():.3f}")
        print(f"Speed deviations - Kurtosis: {speed_devs.kurtosis():.3f}")
        
        # Plot side-by-side
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        ax1.hist(positions, bins=20, edgecolor='black')
        ax1.set_title('Current Target: Positions')
        ax1.set_xlabel('Position')
        
        ax2.hist(speed_devs, bins=50, edgecolor='black')
        ax2.set_title('Alternative Target: Speed Deviation')
        ax2.set_xlabel('Speed Deviation (m/s)')
        
        plt.tight_layout()
        plt.savefig('ml/diagnostics/target_comparison.png')
        
    def compare_predictions(self):
        """
        Compare probability spreads from both approaches
        
        Expected:
        - Ranking: 8-9% for all (flat)
        - Speed: 5-30% range (good spread)
        """
        pass
```

### 3.2 Decision Matrix

Create a decision matrix to choose approach:

| Criterion | Ranking Approach | Speed Approach | Winner |
|-----------|------------------|----------------|---------|
| **Target Distribution** | Discrete positions, uneven | Continuous speed, gaussian-like | Speed |
| **Current Performance** | Flat probabilities (8-9%) | Unknown (needs testing) | TBD |
| **Complexity** | Single model | Two models | Ranking |
| **Feature Usage** | All 128 features | Can use same 128 features | Tie |
| **Interpretability** | Direct probabilities | Speed → probabilities | Ranking |
| **Flexibility** | Position only | Can predict times, speeds, positions | Speed |
| **Training Data** | Positions (always available) | Times (may have gaps) | Ranking |

---

## Phase 4: Implementation Decision (30 min)

### Option A: Try Speed Approach (Recommended if coverage good)

**If time data coverage >80%**:
1. Implement two-model speed predictor
2. Train on historical data
3. Compare probability spreads
4. If better → switch to speed approach
5. If worse → stick with ranking + discriminating features

**Pros**:
- Article shows this works well
- Cleaner target distribution
- More interpretable (speed is physical)
- Can still use all 128 features

**Cons**:
- Requires time data (check coverage first!)
- Two models to maintain
- More complex pipeline

### Option B: Stick with Ranking + Discriminating Features

**If time data coverage <80% or speed approach fails**:
1. Regenerate features with 128 features
2. Retrain ranking model
3. Hope discriminating features fix flat probabilities

**Pros**:
- Uses existing infrastructure
- Proven for some datasets
- All data available (positions always recorded)

**Cons**:
- Target distribution may still be problematic
- Flat probabilities might persist
- Article suggests ranking on complex targets is hard

### Option C: Hybrid Approach

Use speed predictions to **enhance features** for ranking model:

```python
# Add predicted speed as feature to ranking model
features['predicted_race_pace'] = race_pace_model.predict(race)
features['predicted_speed_deviation'] = deviation_model.predict(horse)

# Then use ranking model with these added features
```

---

## Phase 5: Execution Plan

### Step 1: Data Coverage Check (30 min)

```bash
cd /Users/darcy5d/Desktop/DD_AI_models/QE2/Datafetch

# Create diagnostics directory
mkdir -p ml/diagnostics

# Run exploration scripts
python ml/explore_ranking_target.py
python ml/explore_finish_times.py
python ml/explore_btn_distribution.py
python ml/explore_current_predictions.py
```

**Decision point**: If time data coverage >80%, proceed with speed approach.

### Step 2: Implement Speed Predictor (4-6 hours)

If proceeding with speed approach:
1. Create `speed_predictor.py`
2. Prepare training data with speed targets
3. Train race pace model (Model 1)
4. Train horse deviation model (Model 2)
5. Integrate with prediction pipeline

### Step 3: Compare Results (1 hour)

```python
# Generate predictions with both approaches
ranking_predictions = ranking_model.predict(test_races)
speed_predictions = speed_model.predict(test_races)

# Compare probability spreads
print("Ranking approach std:", ranking_predictions.std())
print("Speed approach std:", speed_predictions.std())

# Compare with actual results
ranking_accuracy = evaluate_model(ranking_predictions, actual_results)
speed_accuracy = evaluate_model(speed_predictions, actual_results)
```

### Step 4: Choose Winner (30 min)

Based on:
- Probability spread (wider = better)
- Calibration (predicted 25% should win 25% of time)
- Feature importance (diverse = better)
- Interpretability
- Ease of maintenance

---

## Success Criteria

### For Speed Approach to Win:

✅ Time data coverage >80%  
✅ Speed distribution cleaner than position distribution (lower CV)  
✅ Model 1 (race pace) achieves MAE <2s for flat races  
✅ Model 2 (deviation) achieves MAE <0.5 m/s  
✅ Final probabilities spread 5-30% (not 8-9%)  
✅ Calibration curve shows good fit  
✅ Feature importance diverse  

### For Ranking Approach to Win:

✅ Time data coverage <80%  
✅ Discriminating features fix flat probabilities  
✅ Probabilities spread 5-30% after retraining  
✅ Simpler to maintain  

---

## Files to Create

### Exploration Scripts (Phase 1):
- `Datafetch/ml/explore_ranking_target.py`
- `Datafetch/ml/explore_finish_times.py`
- `Datafetch/ml/explore_btn_distribution.py`
- `Datafetch/ml/explore_current_predictions.py`

### Speed Approach (Phase 2):
- `Datafetch/ml/speed_predictor.py`
- `Datafetch/ml/prepare_speed_training_data.py`
- `Datafetch/ml/train_speed_models.py`

### Comparison (Phase 3):
- `Datafetch/ml/compare_approaches.py`

### Integration (Phase 4):
- Update `Datafetch/ml/predictor.py` to support both approaches
- Update GUI to show which approach is being used

---

## Estimated Timeline

- **Phase 1 (Exploration)**: 2-3 hours
- **Phase 2 (Speed implementation)**: 4-6 hours  
- **Phase 3 (Comparison)**: 1-2 hours
- **Phase 4 (Decision)**: 30 min
- **Phase 5 (Integration)**: 2-3 hours

**Total**: 10-15 hours (vs 20 min to just regenerate features)

**Worth it?** If it fixes flat probabilities, absolutely yes!

---

## Recommendation

Based on the Medium article's strong results:

1. **Start with Phase 1** (exploration) - 2-3 hours
2. **Check time data coverage** - if >80%, proceed with speed approach
3. **If speed looks promising**, implement Phase 2
4. **Compare with current ranking approach**
5. **Choose winner based on results**

The article's author spent 3 years on their model with the wrong target, then fixed it in weeks by changing to speed prediction. Your flat probabilities suggest you might have a similar issue - **the problem might not be features, it might be the target/objective**.

**Next action**: Run Phase 1 exploration scripts to understand your data distributions before deciding.

