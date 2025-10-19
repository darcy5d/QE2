# ML Pipeline Complete Guide

Comprehensive guide to the machine learning pipeline in QE2 - from raw race data to win probability predictions.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Feature Engineering](#feature-engineering)
3. [Training Pipeline](#training-pipeline)
4. [Prediction Generation](#prediction-generation)
5. [Key Innovations](#key-innovations)
6. [Performance Metrics](#performance-metrics)
7. [Code Reference](#code-reference)

---

## Architecture Overview

The ML pipeline transforms raw racing data into actionable win probability predictions through three main stages:

```
Raw Data (races, results) 
    ↓
Feature Engineering (23 features per runner)
    ↓
Model Training (XGBoost rank:pairwise)
    ↓
Predictions (softmax probabilities)
```

### Components

1. **Feature Engineer** (`Datafetch/ml/feature_engineer.py`)
   - Computes 23 race-context features
   - Handles missing data gracefully
   - Saves to `ml_features` table

2. **Baseline Trainer** (`Datafetch/ml/train_baseline.py`)
   - Loads features with temporal split
   - Converts positions to points (target inversion)
   - Trains XGBoost ranking model
   - Evaluates with ranking metrics

3. **Predictor** (`Datafetch/ml/predictor.py`)
   - Generates features for upcoming races
   - Loads trained model
   - Converts ranking scores to probabilities
   - Returns predictions with confidence levels

---

## Feature Engineering

**File**: `Datafetch/ml/feature_engineer.py`

### The 23 Features

Features are grouped into five categories:

#### 1. Basic Horse Features (7 features)
- **RPR** (Racing Post Rating): Official rating of horse ability
- **TSR** (Topspeed Rating): Speed-based rating
- **OFR** (Official Rating): BHA official handicap rating
- **Days Since Last Run**: Recovery time between races
- **Horse Age**: Age in years
- **Weight (lbs)**: Total weight carried
- **Draw Position**: Starting stall number

#### 2. Form Features (1 feature)
- **Form Points**: Calculated from recent finishes
  - Win = 10 points, 2nd = 7, 3rd = 5, 4th = 3, 5th+ = 1
  - Sum of last 5 runs, more recent weighted higher

#### 3. Field Strength Features (8 features)
- **Best RPR in Field**: Highest RPR of any runner
- **Worst RPR in Field**: Lowest RPR of any runner
- **Average RPR in Field**: Mean RPR across all runners
- **RPR Spread**: Difference between best and worst (field competitiveness)
- **Top 3 Avg RPR**: Average of three highest RPRs
- **Horse RPR Rank**: Where this horse ranks (1 = best)
- **Horse RPR vs Best**: Difference from field's best horse
- **Horse RPR vs Worst**: Difference from field's worst horse
- **Horse in Top Quartile**: Binary (1 if in top 25% by RPR)

**Why These Matter**: 
- Winning isn't absolute, it's relative to competition
- A 100 RPR horse in weak field > 110 RPR horse in strong field
- Model learns to evaluate strength in context

#### 4. Relative Ratings Features (4 features)
- **Pace Pressure**: How many front-runners in race
- **Jockey Rating vs Field Avg**: Jockey's win rate relative to field
- **Trainer Rating vs Field Avg**: Trainer's win rate relative to field
- **Weight Rank**: Where horse ranks by weight (1 = lightest)
- **Age Rank**: Where horse ranks by age (1 = youngest)

**Why These Matter**:
- Too many front-runners = fast pace = suits closers
- Top jockeys on average horses still have edge
- Weight distribution affects tactics

#### 5. Draw Bias Features (2 features)
- **Draw Bias**: Historical win rate for this draw position at this course/distance
- **Running Style**: Parsed from form (front-runner, stalker, closer)

**Why These Matter**:
- Some tracks heavily favor low/high draws
- Knowing running style + draw bias = tactical advantage
- Chester low draws win 30%, high draws win 5%

#### 6. Pace Features (1 feature)
- **TSR Trend**: Recent TSR performance trajectory

### Feature Computation Process

```python
# Pseudo-code flow
for each race with results:
    runners = get_runners(race_id)
    
    # Step 1: Basic features (per runner)
    for runner in runners:
        runner.rpr = query_rpr(runner.horse_id, race_id)
        runner.tsr = query_tsr(runner.horse_id, race_id)
        runner.days_since_last = calculate_days_since_last_run(runner.horse_id, race_date)
        runner.form_points = parse_form_string(runner.form)
        # ... other basic features
    
    # Step 2: Field strength features (requires all runners)
    field_rprs = [r.rpr for r in runners if r.rpr is not None]
    best_rpr = max(field_rprs)
    worst_rpr = min(field_rprs)
    avg_rpr = mean(field_rprs)
    
    for runner in runners:
        runner.best_rpr_field = best_rpr
        runner.avg_rpr_field = avg_rpr
        runner.rpr_vs_best = runner.rpr - best_rpr
        runner.rpr_rank = rank(runner.rpr, field_rprs)
        # ... other relative features
    
    # Step 3: Draw bias (requires historical data)
    course_id = race.course_id
    distance = race.distance_f
    for runner in runners:
        runner.draw_bias = historical_win_rate(course_id, distance, runner.draw)
    
    # Step 4: Pace features
    for runner in runners:
        runner.running_style = parse_running_style(runner.form)
        runner.pace_pressure = count_front_runners(runners)
    
    # Step 5: Save to database
    save_features(race_id, runners)
```

### Handling Missing Data

- **Missing RPR/TSR**: Set to `None` (handled by XGBoost)
- **No form string**: Form points = 0
- **No historical draw data**: Draw bias = 0.5 (neutral)
- **First run**: Days since last = 999 (special value)

---

## Training Pipeline

**File**: `Datafetch/ml/train_baseline.py`

### 1. Data Loading

```python
def load_data():
    # Query features + results
    query = """
        SELECT 
            f.*,  -- all 23 features
            r.position as target,
            r.won,
            r.race_id
        FROM ml_features f
        JOIN results r ON f.race_id = r.race_id AND f.horse_id = r.horse_id
        ORDER BY r.date, f.race_id, r.position
    """
    
    df = pd.read_sql(query, conn)
    return df
```

**Key Points**:
- Join features with actual race results
- Order by date (for temporal split)
- Keep race_id for grouping

### 2. Temporal Split

```python
# Split 80/20 by date, not randomly
split_date = df['date'].quantile(0.8)
train_df = df[df['date'] < split_date]
test_df = df[df['date'] >= split_date]
```

**Why Temporal?**
- Prevents data leakage (can't train on future, test on past)
- Simulates real prediction scenario
- More realistic performance estimate

### 3. Target Inversion (Points System)

**Problem**: XGBoost rank:pairwise expects **higher values = better performance**, but position has **1 = winner (best), 10 = last (worst)**.

**Solution**: Convert position to points

```python
# For each race, find max position (field size)
train_df['max_position'] = train_df.groupby('race_id')['target'].transform('max')

# Convert: winner gets max points, last gets 1 point
y_train = train_df['max_position'] - train_df['target'] + 1

# Example: 10-horse race
# Position 1 (winner) → 10 - 1 + 1 = 10 points (highest)
# Position 2 → 10 - 2 + 1 = 9 points
# Position 10 (last) → 10 - 10 + 1 = 1 point (lowest)
```

**Why This Works**:
- Preserves relative ordering
- Winner always has highest value
- Margins preserved (position differences)

### 4. Race Grouping

```python
# Create groups: how many runners per race
train_groups = train_df.groupby('race_id').size().values
test_groups = test_df.groupby('race_id').size().values

# Create DMatrix with groups
dtrain = xgb.DMatrix(X_train, label=y_train)
dtrain.set_group(train_groups)  # CRITICAL!

dtest = xgb.DMatrix(X_test, label=y_test)
dtest.set_group(test_groups)
```

**Why Grouping Matters**:
- Tells XGBoost which horses compete together
- Model learns to rank within groups, not across entire dataset
- Without grouping, would compare horses from different races (nonsense)

### 5. XGBoost Training

```python
params = {
    'objective': 'rank:pairwise',  # Pairwise ranking
    'eval_metric': 'ndcg@3',       # Ranking quality metric
    'max_depth': 8,                # Tree depth
    'learning_rate': 0.05,         # Step size
    'n_estimators': 500,           # Number of trees
    'tree_method': 'hist',         # Fast histogram-based
    'random_state': 42
}

model = xgb.train(
    params,
    dtrain,
    num_boost_round=500,
    evals=[(dtrain, 'train'), (dtest, 'test')],
    early_stopping_rounds=50,
    verbose_eval=50
)
```

**Objective Explained**:
- `rank:pairwise`: For each pair of horses in same race, learns which should rank higher
- Optimizes for correct ordering, not absolute values
- Naturally handles different field sizes

### 6. Evaluation Metrics

```python
def evaluate(model, test_df, test_groups):
    # Get predictions (ranking scores)
    X_test = test_df[feature_columns]
    predictions = model.predict(xgb.DMatrix(X_test))
    
    # For each race, rank horses by predicted scores
    test_df['predicted_score'] = predictions
    
    metrics = {}
    race_results = []
    
    for race_id, race_df in test_df.groupby('race_id'):
        # Sort by predicted score (highest first)
        race_df = race_df.sort_values('predicted_score', ascending=False)
        race_df['predicted_rank'] = range(1, len(race_df) + 1)
        
        # Who actually won?
        actual_winner_idx = race_df['actual_position'].idxmin()
        predicted_rank_of_winner = race_df.loc[actual_winner_idx, 'predicted_rank']
        
        # Metrics
        top_pick_won = (predicted_rank_of_winner == 1)
        top_3_hit = (predicted_rank_of_winner <= 3)
        
        race_results.append({
            'top_pick_won': top_pick_won,
            'top_3_hit': top_3_hit,
            'winner_predicted_rank': predicted_rank_of_winner
        })
    
    # Aggregate metrics
    results_df = pd.DataFrame(race_results)
    metrics['top_pick_win_rate'] = results_df['top_pick_won'].mean()
    metrics['top_3_hit_rate'] = results_df['top_3_hit'].mean()
    metrics['mrr'] = (1 / results_df['winner_predicted_rank']).mean()
    
    return metrics
```

#### Top Pick Win Rate
- % of races where model's #1 pick won
- Target: 30-35% (3× better than random for 10-horse race)

#### Top 3 Hit Rate
- % of races where actual winner was in model's top 3
- Target: 70-75%

#### NDCG@3 (Normalized Discounted Cumulative Gain)
- Measures ranking quality, especially top positions
- Range: 0-1 (higher = better)
- Penalizes mistakes at top more than bottom

#### MRR (Mean Reciprocal Rank)
- Average of 1 / (rank of actual winner)
- Winner at #1 → 1.0, at #2 → 0.5, at #3 → 0.33
- Target: 0.45-0.50

#### Spearman Correlation
- Correlation between predicted ranks and actual positions
- Measures overall ranking agreement
- Target: 0.30-0.40

---

## Prediction Generation

**File**: `Datafetch/ml/predictor.py`

### Workflow

```python
class ModelPredictor:
    def __init__(self, model_path, db_path):
        self.model = xgb.Booster()
        self.model.load_model(model_path)
        self.db = sqlite3.connect(db_path)
    
    def predict_race(self, race_id):
        # 1. Load runners from upcoming race
        runners = self.load_race_runners(race_id)
        
        # 2. Generate features for each runner
        features = self.engineer.compute_race_features(runners)
        
        # 3. Predict ranking scores
        dmatrix = xgb.DMatrix(features)
        scores = self.model.predict(dmatrix)
        
        # 4. Convert scores to probabilities (softmax)
        probabilities = self._scores_to_probabilities(scores)
        
        # 5. Create results dataframe
        results = pd.DataFrame({
            'horse': [r['horse'] for r in runners],
            'score': scores,
            'probability': probabilities
        })
        
        # 6. Sort by probability (highest first)
        results = results.sort_values('probability', ascending=False)
        results['rank'] = range(1, len(results) + 1)
        
        return results
```

### Softmax Conversion

**Why Softmax?**
- Ranking model outputs scores (higher = better)
- Scores are relative, not probabilities
- Softmax converts to valid probabilities that sum to 1.0

```python
def _scores_to_probabilities(self, scores: np.ndarray) -> np.ndarray:
    """
    Convert ranking scores to probabilities using softmax.
    
    Softmax formula: P(i) = exp(score_i) / sum(exp(score_j) for all j)
    
    Properties:
    - All probabilities between 0 and 1
    - Sum of probabilities = 1.0 (guaranteed)
    - Larger score differences → more confident probabilities
    """
    # Subtract max for numerical stability (prevents overflow)
    exp_scores = np.exp(scores - np.max(scores))
    probabilities = exp_scores / exp_scores.sum()
    
    return probabilities
```

**Example**:
```python
# Ranking scores from model
scores = [2.5, 1.8, 1.2, 0.9, 0.5, 0.2, -0.1, -0.4, -0.7, -1.0]

# After softmax
probabilities = [0.285, 0.182, 0.147, 0.101, 0.083, 0.069, 0.052, 0.038, 0.028, 0.016]

# Sum = 1.000 ✓
```

### Confidence Levels

```python
def _check_value_bet(self, predicted_prob, rpr, best_rpr_field):
    """Assign confidence level based on probability and field strength"""
    
    if predicted_prob > 0.20:
        return "Strong Pick"  # Clear favorite
    elif predicted_prob > 0.15:
        return "Good Chance"  # Solid contender
    elif predicted_prob > 0.10:
        return "Decent"       # Around field average
    else:
        return "Longshot"     # Outsider
```

---

## Key Innovations

### 1. Ranking vs Classification

**Old Approach (Binary Classification)**:
```python
# Train separate model for each horse
model.predict_proba(horse_features) → [0.27, 0.73]  # [lose, win]
```

**Problems**:
- Each prediction independent
- No knowledge horses compete together
- Can predict 9 horses at 27% win probability
- Probabilities don't sum to 100%

**New Approach (Ranking)**:
```python
# Train model to rank horses within races
model.predict(race_features) → ranking_scores
softmax(scores) → probabilities that sum to 100%
```

**Benefits**:
- Understands relative competition
- Proper probability distribution
- Better reflects race dynamics

### 2. Race Grouping

**Critical Code**:
```python
dtrain.set_group(train_groups)
```

This one line makes the ranking model work. Without it:
- XGBoost treats all horses as one big dataset
- Compares horses from different races (nonsense)
- No concept of "within-race" ranking

With it:
- XGBoost learns to rank within groups
- Each race is independent ranking problem
- Model learns relative performance

### 3. Points System (Target Inversion)

**Problem**: Positions are inverted (1 = best, 10 = worst)

**Solution**: Convert to points where higher = better
```python
points = max_position - position + 1
```

**Preserves Information**:
- Relative ordering maintained
- Margins preserved (2nd vs 3rd vs 4th)
- Compatible with ranking objective

### 4. Softmax Probabilities

**Why Not Manual Normalization?**

Old approach:
```python
# Manual normalization (wrong for ranking)
normalized = raw_probs / sum(raw_probs)
```

New approach:
```python
# Softmax (correct for ranking scores)
probabilities = exp(scores) / sum(exp(scores))
```

**Softmax Benefits**:
- Mathematically correct for ranking scores
- Amplifies score differences
- Automatic confidence calibration
- No manual tuning needed

---

## Performance Metrics

### Expected Performance (Test Set)

| Metric | Target | Interpretation |
|--------|--------|----------------|
| Top Pick Win Rate | 30-35% | Model's #1 pick wins 1 in 3 races |
| Top 3 Hit Rate | 70-75% | Winner in top 3 picks 70% of time |
| NDCG@3 | 0.60-0.65 | Good ranking quality |
| MRR | 0.45-0.50 | Winner typically in top 2-3 |
| Spearman | 0.30-0.40 | Moderate rank correlation |

### Feature Importance (Typical)

Top 10 features by gain:

1. **RPR** (28.5%) - Dominant feature
2. **RPR vs Best** (12.3%) - Relative strength
3. **Average RPR Field** (8.7%) - Field quality
4. **TSR** (7.2%) - Speed rating
5. **Days Since Last** (6.8%) - Freshness
6. **Horse Age** (5.4%) - Experience/decline
7. **Draw Bias** (4.9%) - Track advantage
8. **Jockey Rating vs Field** (4.2%) - Pilot skill
9. **Form Points** (3.8%) - Recent performance
10. **Pace Pressure** (3.1%) - Race dynamics

**Insights**:
- RPR features dominate (49% of importance)
- Relative features crucial (vs best, field avg)
- Race context matters (draw, pace, field quality)

---

## Code Reference

### Main Files

```
Datafetch/ml/
├── feature_engineer.py      # Feature computation
├── train_baseline.py         # Model training
├── predictor.py              # Predictions
├── build_ml_dataset.py       # Data preparation (legacy)
├── form_parser.py            # Parse form strings
└── models/
    ├── xgboost_baseline.json    # Trained model
    ├── feature_columns.json     # Feature list
    └── feature_importance.csv   # Feature importance scores
```

### Key Classes

#### FeatureEngineer
```python
class FeatureEngineer:
    def generate_features_for_all_races(self):
        """Main entry point - processes all races"""
        
    def compute_runner_features(self, runner, race):
        """Basic features per runner"""
        
    def compute_relative_features(self, race_id, runners):
        """Field strength features"""
        
    def compute_draw_bias(self, course_id, distance, draw):
        """Historical draw advantage"""
        
    def compute_pace_features(self, runner, race):
        """Pace and running style"""
```

#### BaselineTrainer
```python
class BaselineTrainer:
    def load_data(self):
        """Load features + results"""
        
    def train_xgboost(self, train_df, test_df):
        """Train ranking model"""
        
    def evaluate(self, model, test_df):
        """Calculate metrics"""
        
    def run_full_pipeline(self):
        """Complete training workflow"""
```

#### ModelPredictor
```python
class ModelPredictor:
    def predict_race(self, race_id):
        """Generate predictions for one race"""
        
    def _scores_to_probabilities(self, scores):
        """Softmax conversion"""
        
    def _check_value_bet(self, prob, rpr, best_rpr):
        """Confidence levels"""
```

---

## Troubleshooting

### Model Training Issues

**"No features found"**
- Run feature generation first (Tab 6 in GUI)
- Check ml_features table has rows: `SELECT COUNT(*) FROM ml_features;`

**"Training takes forever"**
- Normal for first run (~3-5 minutes for 390k features)
- Reduce n_estimators if testing: `params['n_estimators'] = 100`

**"Poor metrics (Top Pick < 20%)"**
- Need more training data (aim for 30k+ races)
- Check feature quality (many NULL RPR values?)
- Verify temporal split is working (not training on future)

### Prediction Issues

**"Model not found"**
- Train model first (Tab 7 in GUI)
- Check file exists: `Datafetch/ml/models/xgboost_baseline.json`

**"Feature generation failed"**
- Some runners missing RPR/TSR (set to NULL, XGBoost handles)
- Check upcoming race has required data

**"All probabilities similar"**
- Weak field (all horses similar quality)
- Missing key features (RPR not available)
- Model needs retraining with more data

### Debug Commands

```bash
# Check features
cd Datafetch
python -c "import sqlite3; conn = sqlite3.connect('racing_pro.db'); print('Features:', conn.execute('SELECT COUNT(*) FROM ml_features').fetchone()[0])"

# Check model file
ls -lh ml/models/xgboost_baseline.json

# Run training manually
cd Datafetch
python -m ml.train_baseline

# Test prediction
cd Datafetch
python -m ml.predictor --race_id rac_12345678
```

---

## Further Reading

- **[Target Inversion Fix](TARGET_INVERSION_FIX.md)** - Detailed explanation of points system
- **[Ranking Model Implementation](RANKING_MODEL_IMPLEMENTATION.md)** - Migration from binary to ranking
- **[Probability Normalization Fix](PROBABILITY_NORMALIZATION_FIX.md)** - Original problem that led to ranking model

---

**Built with XGBoost and domain expertise 🏇**

