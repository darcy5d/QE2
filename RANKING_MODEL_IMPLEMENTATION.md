# Ranking Model Implementation Summary

**Date**: October 19, 2025  
**Status**: ✅ Implementation Complete - Ready for Feature Regeneration and Training

## Overview

Successfully migrated from **binary classification** to **pairwise ranking** model with comprehensive race-context features. The model now understands that horses compete **within races**, not in isolation.

---

## Phase 1: Enhanced Feature Engineering ✅

### New Features Added (23 total)

#### 1. Pace & Speed Features
- `horse_best_tsr`: Best Time Speed Rating from career
- `horse_avg_tsr_last_5`: Average TSR from last 5 runs
- `speed_improving`: Boolean if TSR trending upward
- `typical_running_style`: 1=leader, 2=prominent, 3=midfield, 4=held up (parsed from race comments)

#### 2. Field Strength Features
- `field_best_rpr`: Highest RPR in race
- `field_worst_rpr`: Lowest RPR in race
- `field_avg_rpr`: Average RPR of field
- `field_rpr_spread`: Range (competitiveness indicator)
- `horse_rpr_rank`: Horse's RPR rank in field
- `horse_rpr_vs_best`: Difference from best horse
- `horse_rpr_vs_worst`: Difference from worst horse
- `top_3_rpr_avg`: Average RPR of top 3 rated horses
- `horse_in_top_quartile`: Boolean if horse in top 25% by rating
- `tsr_vs_field_avg`: Horse's TSR vs field average
- `pace_pressure_likely`: Count of front-runners in field

#### 3. Draw Bias Features
- `course_distance_draw_bias`: Historical win rate by draw at this course/distance
- `draw_position_normalized`: Draw position / field size (0-1 scale)
- `low_draw_advantage`: Boolean if draw ≤ 5 on courses favoring low draws
- `high_draw_advantage`: Boolean if draw ≥ field_size - 5 on courses favoring high draws

#### 4. Additional Relative Rankings
- `weight_lbs_rank`: Weight rank in field
- `age_rank`: Age rank in field
- `jockey_rating`: Jockey win rate vs field average
- `trainer_rating`: Trainer form vs field average

### Implementation Details

**File**: `Datafetch/ml/feature_engineer.py`

**New Methods Added**:
1. `compute_pace_features()` - Extracts TSR and running style from race comments
2. `compute_draw_bias()` - Calculates historical draw performance at course/distance
3. `_parse_running_style()` - Keyword analysis of race comments
4. Enhanced `compute_relative_features()` - Computes all field-relative metrics

**Database Schema**: 
- Migration script: `Datafetch/ml/migrate_ml_features_schema.py`
- ✅ Successfully added 23 new columns to `ml_features` table
- Total columns: 83 (was 60)

---

## Phase 2: XGBoost Ranking Model ✅

### Critical Changes

#### Before (Binary Classification)
```python
'objective': 'binary:logistic'  # Each horse independent
# Outputs: probability for each horse (sum can exceed 100%)
# No awareness of race context
```

#### After (Pairwise Ranking)
```python
'objective': 'rank:pairwise'    # Learns pairwise comparisons
'eval_metric': 'ndcg@3'         # Ranking quality metric

# KEY: Race grouping
train_groups = train_df.groupby('race_id').size().values
dtrain.set_group(train_groups)  # Tells model which horses compete together

# Outputs: ranking scores (converted to probabilities via softmax)
# Full awareness of race context
```

### Training Pipeline Updates

**File**: `Datafetch/ml/train_baseline.py`

1. **Data Loading**: Now loads position (not just binary won) and groups by race_id
2. **Model Training**: Uses `xgb.train()` with DMatrix groups instead of XGBClassifier
3. **Evaluation**: Completely new ranking-specific metrics

**New Model Parameters**:
```python
{
    'objective': 'rank:pairwise',
    'eval_metric': 'ndcg@3',
    'max_depth': 8,              # Deeper for race interactions
    'learning_rate': 0.03,       # Lower for ranking stability
    'n_estimators': 300,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'tree_method': 'hist'
}
```

### New Evaluation Metrics

**Racing-Specific**:
- **Top Pick Win Rate**: % of races where highest-scored horse wins
- **Top 3 Hit Rate**: % of races where winner is in predicted top 3
- **Spearman Correlation**: Correlation between predicted and actual ranks

**Ranking Quality**:
- **NDCG@K** (K=1,3,5): Normalized Discounted Cumulative Gain
- **Mean Reciprocal Rank (MRR)**: Average of 1/rank for actual winners

**Position Distribution**: Shows where predicted winners actually finish

---

## Phase 3: Prediction Pipeline ✅

### Predictor Updates

**File**: `Datafetch/ml/predictor.py`

#### Before (Manual Normalization)
```python
raw_probabilities = model.predict(dmatrix)
# Manual normalization needed
weights = np.power(raw_probs, 2.0)
probabilities = weights / weights.sum()
```

#### After (Softmax from Ranking Scores)
```python
ranking_scores = model.predict(dmatrix)
# Softmax naturally sums to 1.0
exp_scores = np.exp(scores - np.max(scores))
probabilities = exp_scores / exp_scores.sum()
```

**Key Insight**: Ranking model outputs are already relative within a race. Softmax is the mathematically correct conversion to probabilities. No manual normalization needed!

### Updated Thresholds

Since probabilities are now properly distributed:
- **⭐ Strong Pick**: >20% (was >25%)
- **✓ Good Chance**: >12% (was >15%)

In a 13-horse race, average = 7.7%, so these thresholds are above-average indicators.

---

## What This Fixes

### The Original Problem

**Before**: 9 out of 13 horses with 27%+ win probability (sum ~300%)
```
Race with 13 horses:
- Horse A: 35.2% ✗ (impossible!)
- Horse B: 34.3% ✗
- Horse C: 34.6% ✗
... 6 more horses >27% ...
Total: ~300% ✗
```

**After**: Realistic probability distribution (sum = 100%)
```
Race with 13 horses:
- Top horse: ~18-22% ✓
- Contenders: ~12-15% each ✓
- Mid-pack: ~6-10% each ✓
- Outsiders: ~3-5% each ✓
Total: 100% ✓
```

### Why Binary Classification Failed

1. **Independent Predictions**: Model evaluated each horse in isolation
2. **No Race Context**: Didn't know horses were competing together
3. **Class Imbalance**: Only ~7-10% of horses win (severe imbalance)
4. **No Field Strength**: Couldn't distinguish weak fields vs. competitive races

### How Ranking Model Succeeds

1. **Pairwise Learning**: Learns "Horse A beats Horse B in THIS race"
2. **Race Grouping**: Model knows which horses compete together
3. **Relative Scoring**: Outputs are already relative within race
4. **Field-Aware Features**: Knows if it's a weak field (clear favorite) or competitive (tight probabilities)

---

## Expected Improvements

### Prediction Quality

| Metric | Binary (Old) | Ranking (Target) |
|--------|--------------|------------------|
| Top Pick Win Rate | ~25% | >30% |
| Top 3 Hit Rate | ~65% | >70% |
| NDCG@3 | N/A | >0.65 |
| Probabilities | Invalid (sum >100%) | Valid (sum=100%) |
| Field Awareness | None | Full |

### Real-World Benefits

**Competitive Class 3 Handicap**:
- **Before**: Confusing - 9 horses rated as favorites
- **After**: Clear hierarchy with 2-3 contenders at top

**Weak Maiden Race**:
- **Before**: Similar spread to competitive races
- **After**: Clear 35% favorite, rest <10% (reflects reality)

**Draw Bias Detection**:
- **Before**: Not considered
- **After**: Low draws at Chester get advantage boost

**Pace Analysis**:
- **Before**: Ignored
- **After**: Race with 5 front-runners → closers get advantage

---

## Next Steps

### 1. Regenerate Features
```bash
cd /Users/darcy5d/Desktop/DD_AI_models/QE2/Datafetch/ml
python build_ml_dataset.py
```
This will populate all 23 new feature columns with data.

**Expected Time**: ~10-20 minutes for full dataset

### 2. Train Ranking Model
```bash
python train_baseline.py --output-dir models
```

This will:
- Load features with race grouping
- Train with `rank:pairwise` objective
- Evaluate with ranking metrics
- Save model to `models/xgboost_baseline.json`

**Expected Time**: ~5-10 minutes depending on data size

### 3. Test Predictions

Restart GUI and generate predictions for upcoming races. Verify:
- ✓ Probabilities sum to ~100% per race
- ✓ Clear favorites in weak fields
- ✓ Tighter distributions in competitive races
- ✓ Field strength features working
- ✓ Draw bias applied correctly
- ✓ Pace pressure accounted for

---

## Technical Notes

### Race Grouping Mechanics

XGBoost's ranking objective needs to know which samples belong to the same group:

```python
# Example: 3 races with different field sizes
race_groups = [10, 12, 8]  # 10 horses, 12 horses, 8 horses

# Model learns:
# - Compare horses 0-9 (race 1)
# - Compare horses 10-21 (race 2)
# - Compare horses 22-29 (race 3)
# But NEVER compare horse from race 1 vs race 2
```

This is why temporal ordering (ORDER BY date, race_id, position) is critical!

### Softmax vs. Manual Normalization

**Softmax** (used now):
```python
P(horse_i) = exp(score_i) / sum(exp(scores))
```
- Mathematically principled
- Preserves relative scores
- Standard for converting logits to probabilities

**Manual Normalization** (old approach):
```python
P(horse_i) = score_i² / sum(scores²)
```
- Ad-hoc fix for independent predictions
- Required tuning exponent
- Not theoretically justified

### Feature Importance Changes

Expect to see NEW important features:
- `field_avg_rpr` - Field strength matters!
- `horse_rpr_vs_best` - Relative position crucial
- `pace_pressure_likely` - Running style matters
- `course_distance_draw_bias` - Track biases detected

Old important features remain valuable:
- `ofr` (Official Rating)
- `trainer_win_rate_90d`
- `jockey_win_rate_90d`
- `horse_form_last_5_avg`

---

## Files Modified

### Core Implementation
1. **`Datafetch/ml/feature_engineer.py`** - Added 23 new features
2. **`Datafetch/ml/train_baseline.py`** - Ranking objective + new metrics
3. **`Datafetch/ml/predictor.py`** - Softmax instead of normalization

### Database & Migration
4. **`Datafetch/ml/migrate_ml_features_schema.py`** - New (adds columns)

### Documentation
5. **`PROBABILITY_NORMALIZATION_FIX.md`** - Explains original problem
6. **`RANKING_MODEL_IMPLEMENTATION.md`** - This file

---

## Success Criteria

✅ **Implementation Complete**:
- Feature engineering extended
- Database schema migrated
- Training pipeline updated
- Prediction pipeline updated
- All code passes linter

⏳ **Pending**:
- Regenerate features with new pipeline
- Train ranking model on full dataset
- Validate predictions on test races
- Compare to binary baseline

📊 **Target Metrics** (after training):
- Top Pick Win Rate: >30%
- Top 3 Hit Rate: >70%
- NDCG@3: >0.65
- Probabilities: Sum to 100% ✓
- No more 9 horses at 27%+ ✓

---

## Theoretical Foundation

### Why Ranking is Better for Racing

**Horse racing is fundamentally a ranking problem**, not binary classification:

1. **Relative Performance**: What matters is who finishes ahead of whom, not absolute performance
2. **Context-Dependent**: Same horse performs differently depending on opposition quality
3. **Field Effects**: Pace scenario, draw bias, class level all affect relative outcomes
4. **One Winner**: Only one horse can win (unlike multi-label where multiple could be "positive")

### Learning to Rank Approaches

We use **Pairwise Ranking** (`rank:pairwise`):
- Learns from pairs: "In race X, horse A beat horse B"
- Optimizes pairwise preferences
- Generalizes to full ranking

**Alternatives considered**:
- `rank:ndcg`: Directly optimizes NDCG (can be less stable)
- `rank:map`: Mean Average Precision (better for information retrieval)

**Pairwise chosen because**:
- Most stable for training
- Proven effective for racing
- Good balance of accuracy and computational cost

---

## Conclusion

This implementation represents a **fundamental improvement** in how the model understands horse racing:

**Before**: "What's the probability this horse wins?"  
**After**: "Given these horses in THIS race, which will finish ahead?"

The model now has **full race context** through 23 new features and **proper learning objective** through pairwise ranking. Predictions will be **mathematically valid** (sum to 100%) and **contextually aware** (field strength, pace, draw bias).

Next: Regenerate features and train the model to see the improvements in action!

