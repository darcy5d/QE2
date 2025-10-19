# Target Inversion Fix - Points System

**Date**: October 19, 2025  
**Status**: ✅ Fixed

## The Problem

The ranking model was predicting **backwards** because the target variable was upside down!

### What Went Wrong

**XGBoost's `rank:pairwise` expects**: HIGHER values = BETTER performance

**What we gave it**: Position (1, 2, 3, 4...)
- Position 1 = Winner
- Position 10 = Last place

**What the model learned**: "Position 10 is better than Position 1!" 😱

### The Evidence

```
Results from first training:
- Spearman Correlation: -0.2866 (NEGATIVE = backwards!)
- Top Pick Win Rate: 5.6% (should be >30%)
- Predicted winners actually finished in positions 4-7 most often
```

The model was literally predicting the OPPOSITE of what we wanted!

---

## The Solution: Points System

Convert positions to points where **higher = better**:

```python
# In each race, convert position to points
max_position = race.groupby('race_id')['position'].max()
points = max_position - position + 1

# Examples:
# 10-horse race:
#   Position 1 (winner) → 10 - 1 + 1 = 10 points ✓
#   Position 5          → 10 - 5 + 1 = 6 points
#   Position 10 (last)  → 10 - 10 + 1 = 1 point ✓

# 8-horse race:
#   Position 1 (winner) → 8 - 1 + 1 = 8 points ✓
#   Position 8 (last)   → 8 - 8 + 1 = 1 point ✓
```

### Why This Works

1. **Higher points = Better finish** (what ranking models expect)
2. **Race-specific**: Points scale with field size automatically
3. **Preserves relative differences**: Winner-to-second gap same as second-to-third
4. **Intuitive**: Like Formula 1 points (winner gets most points)

---

## Implementation

### Changes Made

**File**: `Datafetch/ml/train_baseline.py`

**Before** (lines 117-120):
```python
X_train = train_df[self.FEATURE_COLS].copy()
X_test = test_df[self.FEATURE_COLS].copy()
y_train = train_df['target']  # Position - WRONG!
y_test = test_df['target']
```

**After** (lines 117-139):
```python
X_train = train_df[self.FEATURE_COLS].copy()
X_test = test_df[self.FEATURE_COLS].copy()

# CRITICAL: Convert position to points for ranking objective
logger.info("\nConverting positions to points (higher = better)...")
train_df['max_position'] = train_df.groupby('race_id')['target'].transform('max')
test_df['max_position'] = test_df.groupby('race_id')['target'].transform('max')

y_train = train_df['max_position'] - train_df['target'] + 1
y_test = test_df['max_position'] - test_df['target'] + 1

# Shows conversion stats
logger.info(f"  Winner (pos 1) → {y_train.max():.0f} points (max)")
logger.info(f"  Last place → {y_train.min():.0f} point (min)")
```

**Also Fixed** (line 274):
```python
# Use original positions for evaluation display, not points!
test_df['actual_position'] = test_df['target'].values
```

---

## Expected Results After Fix

### Metrics Should Improve To:

| Metric | Before Fix | After Fix (Target) |
|--------|-----------|-------------------|
| Top Pick Win Rate | 5.6% | >30% |
| Top 3 Hit Rate | 20.1% | >70% |
| NDCG@3 | 0.1369 | >0.65 |
| Spearman Correlation | **-0.2866** | **+0.3 to +0.5** (POSITIVE!) |

### Position Distribution

**Before**: Model predicted positions 4-7 as winners most often  
**After**: Model should predict position 1 (actual winners) most often

---

## Why This Is a Common Mistake

### The Confusion

In horse racing:
- "Position 1" is **BEST** (winner)
- Lower positions are **BETTER**

In machine learning rankings:
- Higher scores/values are **BETTER**
- Model maximizes the target value

### The Solution Pattern

**Any time you use ranking objectives**:
- ✅ If lower = better (positions, times): **INVERT the target**
- ✅ If higher = better (points, scores): **Use as-is**

---

## Testing the Fix

### Run Training Again

```bash
cd /Users/darcy5d/Desktop/DD_AI_models/QE2
# In GUI: ML Training tab → Train Model
```

### Look For These Changes:

1. **New log message**:
```
Converting positions to points (higher = better)...
  Winner (pos 1) → 26 points (max)
  Last place → 1 point (min)
  Mean points: 4.5
```

2. **Positive Spearman**: Should be >0.3 (not negative!)

3. **Better metrics**:
```
Top Pick Win Rate: >25% (was 5.6%)
Top 3 Hit Rate: >60% (was 20%)
```

4. **Position distribution**:
```
Position 1: >20% (was 5.6%)
Position 4-7: <10% each (was 11%+)
```

---

## Alternative Approaches Considered

### Option 1: Negative Position (Simpler)
```python
y_train = -train_df['target']  # -1 for winner, -10 for last
```
- ✅ Simpler code
- ❌ Less intuitive (negative numbers)
- ❌ Doesn't scale with field size

### Option 2: Max Position Minus Current (Selected!)
```python
y_train = max_pos - train_df['target'] + 1
```
- ✅ Always positive (1 to field_size)
- ✅ Scales with field size automatically
- ✅ Intuitive (like points in sports)
- ✅ Preserves relative differences

### Option 3: Reciprocal
```python
y_train = 1 / train_df['target']  # 1.0 for winner, 0.1 for 10th
```
- ✅ Higher = better
- ❌ Non-linear scaling (winner-to-2nd gap > 2nd-to-3rd)
- ❌ Problematic for large fields

---

## Lessons Learned

### 1. Always Check Direction!
When using ranking objectives, verify:
- Is the Spearman correlation **positive**?
- Are predictions aligned with actual outcomes?
- Does the position distribution make sense?

### 2. Validate Early
Even if training completes successfully, metrics can reveal issues:
- Negative correlation = **backwards model**
- Very low accuracy = **something fundamentally wrong**

### 3. Document Transformations
Always document target transformations:
```python
# CRITICAL: Higher = better for ranking
y_train = transform(position)  # Clear comment!
```

---

## Quick Reference

### Ranking Model Target Requirements

| Your Data | Ranking Target | Transformation |
|-----------|---------------|----------------|
| Position (1=best) | Higher=better | `max_pos - pos + 1` |
| Time (lower=better) | Higher=better | `max_time - time` or `1/time` |
| Score (higher=best) | Higher=better | Use as-is ✓ |
| Loss (lower=better) | Higher=better | `max_loss - loss` or `-loss` |

### Debug Checklist

When ranking model performs poorly:
- [ ] Check Spearman correlation (should be **positive**)
- [ ] Verify position distribution (winners should be predicted as pos 1)
- [ ] Confirm target direction (higher = better?)
- [ ] Validate race grouping (horses in same race grouped together?)
- [ ] Check for data leakage (using future information?)

---

## Summary

✅ **Fixed**: Target variable now correctly represents higher = better  
✅ **Method**: Points system scales with field size  
✅ **Expected**: Spearman >0.3, Top Pick >25%, much better ranking  
✅ **Retrain**: Ready to train with corrected target

This is a **textbook ranking pitfall** - the confusion between "position 1 is best" (lower is better) vs "higher values are better" (ranking objective expectation). The points system elegantly solves this!

