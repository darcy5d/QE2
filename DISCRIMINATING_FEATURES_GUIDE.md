# Discriminating Features Implementation Guide

## Overview

This guide covers the implementation of 18 new discriminating features designed to fix the model's flat probability issue. After removing odds-based features, the model produced probabilities clustered at 8-9% for all horses, indicating poor discrimination. These new features provide strong signals for ranking horses.

---

## What Was Added

### Feature Summary (18 total features)

1. **Market Position** (1 feature)
   - Categorical odds anchor (0-4 tiers)
   - Provides baseline without full data leakage

2. **Class Movement** (4 features)
   - Average recent class
   - Class change vs recent
   - Dropping in class flag
   - Rising in class flag

3. **Course Specialists** (5 features)
   - Runs at course
   - Wins at course
   - Course win rate
   - Course place rate
   - Specialist flag

4. **Distance Optimization** (4 features)
   - Best distance
   - Distance from optimal
   - Runs at distance
   - Win rate at distance

5. **Trainer Hot Streaks** (4 features)
   - Wins in last 14 days
   - Runs in last 14 days
   - Recent win rate
   - Hot trainer flag

---

## Feature Count

- **Before**: 110 features (odds removed)
- **After**: 128 features (+18 discriminating features)
- **Note**: Schema shows 129 columns because `trainer_is_hot` already existed

---

## How to Use (GUI Workflow)

### Step 1: Verify Schema Migration

Schema migration was automatically executed during implementation. To verify:

```bash
cd /Users/darcy5d/Desktop/DD_AI_models/QE2/Datafetch
sqlite3 racing_pro.db "SELECT COUNT(*) FROM pragma_table_info('ml_features');"
```

**Expected**: 129 columns

### Step 2: Regenerate Features

1. **Launch GUI**:
   ```bash
   cd /Users/darcy5d/Desktop/DD_AI_models/QE2/Datafetch
   python racecard_gui.py
   ```

2. **Navigate to Tab 6** - "ML Features"

3. **Click "Regenerate Features"**

4. **Select Options**:
   - Race Type: **Flat**
   - Batch Size: **1000** (recommended)
   
5. **Click "Start Regeneration"**

6. **Monitor Progress**:
   - Watch progress bar (295K records)
   - Check terminal output for errors
   - **Expected time**: 15-20 minutes

7. **Look for**:
   - `Processing race XXX/43354...`
   - `Processed YYYY runners`
   - `Feature regeneration complete!`

### Step 3: Retrain Model

1. **Navigate to Tab 7** - "Model Training"

2. **Select Configuration**:
   - Model Type: **XGBoost Ranking**
   - Race Type: **Flat**
   - Test Split: **20%** (default)

3. **Click "Start Training"**

4. **Monitor Training**:
   - Watch training metrics appear
   - **Expected time**: 3-5 minutes
   - Check for convergence

5. **Review Results**:
   - NDCG@3 (higher is better)
   - Training/validation curves
   - Feature importance

### Step 4: Verify Feature Importance

After training completes, check feature importance in the results panel:

**Good signs**:
- ✓ No odds features in top 20
- ✓ `course_specialist` in top 10
- ✓ `dropping_in_class` highly ranked
- ✓ `distance_from_optimal` has importance
- ✓ `trainer_is_hot` present
- ✓ Diverse feature set (no single feature >25%)

**Bad signs**:
- ✗ `market_position_tier` dominates (>30%)
- ✗ All top features are from one category
- ✗ Many features with 0% importance

### Step 5: Verify Probability Spread

1. **Navigate to Tab 8** - "Predictions"

2. **Generate Predictions**:
   - Click "Get Upcoming Races"
   - Wait for fetch to complete
   - Click "Generate Predictions"

3. **Check Win Probabilities**:

**Before (flat model)**:
```
Horse A: 8.2%
Horse B: 9.1%
Horse C: 8.7%
Horse D: 8.5%
Horse E: 8.9%
```

**After (good discrimination)**:
```
Horse A: 24.5%  ← Strong favorite
Horse B: 16.2%  ← Co-favorite
Horse C: 12.8%  
Horse D: 8.1%   
Horse E: 5.3%   ← Outsider
```

**Target**: Spread from ~5% (outsiders) to ~25% (strong favorites)

### Step 6: Test Predictions

1. **Navigate to Tab 9** - "In The Money"

2. **Set Conservative Settings**:
   - Bankroll: $100 (test amount)
   - Kelly Fraction: **1/2 Kelly**
   - Minimum Edge: **8%**
   - Market Blend: **0% (Pure Model)**

3. **Select Date**: Choose upcoming race day

4. **Click "Find Value Bets"**

5. **Review Recommendations**:
   - Check if model suggests bets
   - Verify probability spread makes sense
   - Look for value in class droppers, course specialists

---

## Expected Improvements

### Before (Flat Probabilities)
- All horses: 8-9% win probability
- No clear favorites or outsiders
- Poor value detection
- Betting on everything or nothing

### After (Good Discrimination)
- Strong favorites: 20-30% win probability
- Mid-range: 10-15%
- Outsiders: 3-8%
- Clear ranking separation
- Better value detection

### Key Metrics to Watch

1. **Probability Spread**:
   - Standard deviation of win probs
   - Target: >0.06 (was ~0.005)

2. **Feature Importance**:
   - Top 10 features diverse
   - No single feature >25%
   - Class/course/distance visible

3. **Real-World Testing**:
   - Paper trade 50 predictions
   - Track hit rates by probability tier
   - Expect favorites to win ~25% (not 8%)

---

## Troubleshooting

### Issue: Feature Regeneration Fails

**Symptoms**:
- Errors in terminal during regeneration
- Progress stops
- `TypeError` or `NoneType` errors

**Solutions**:
1. Check terminal output for specific error
2. Verify database schema (129 columns)
3. Check `feature_generation_optimized.log`
4. Report specific error for debugging

### Issue: Probabilities Still Flat

**Symptoms**:
- All horses still 8-9% after retraining
- No discrimination improvement

**Possible causes**:
1. **Features not regenerated**: Re-run Step 2
2. **Old model loaded**: Check model path in Tab 7
3. **Market position dominates**: Check feature importance
4. **Insufficient training**: Increase max_depth or n_estimators

**Fixes**:
- Delete old model: `rm Datafetch/ml/models/xgboost_flat.json`
- Regenerate features from scratch
- Retrain with fresh model

### Issue: Market Position Too Important

**Symptoms**:
- `market_position_tier` >30% importance
- Other features ignored
- Model essentially copying odds

**Fix**:
Remove market position and retrain with only fundamental features:
```python
# In feature_engineer.py, comment out:
# market_position_tier = calculate_market_position(...)
```

### Issue: Low Coverage for New Features

**Symptoms**:
- Many NULL values in new columns
- Features have 0% importance
- Check with:

```sql
SELECT 
    COUNT(*) as total,
    COUNT(course_specialist) as has_course_specialist,
    COUNT(class_last_3_avg) as has_class_avg
FROM ml_features;
```

**Expected**: >80% coverage for class/course features

---

## Data Coverage (Verified)

✓ **Class data**: 100% coverage  
✓ **Course data**: 238 unique courses, avg 182 races  
✓ **Distance data**: 100% coverage  
✓ **Trainer data**: 100% coverage, 3,478 trainers  

All features should have excellent coverage.

---

## Success Criteria

✅ **Feature generation completes without errors**  
✅ **Model trains successfully on 128 features**  
✅ **Probability spread improves (5-30% range)**  
✅ **Feature importance is diverse (no single feature >25%)**  
✅ **Class/course/distance features appear in top 20**  
✅ **Paper trading shows realistic hit rates by tier**

---

## Next Steps After Implementation

1. **Generate predictions for upcoming races**
2. **Paper trade 50 bets** (no real money)
3. **Track results by probability tier**:
   - 20-30% predictions should win ~25% of time
   - 10-15% predictions should win ~12% of time
   - 5-10% predictions should win ~7% of time
4. **Iterate on features** if discrimination insufficient
5. **Adjust Kelly settings** once confident

---

## Files Modified

### New Files Created:
- `Datafetch/ml/market_position_features.py`
- `Datafetch/ml/class_features.py`
- `Datafetch/ml/course_specialist_features.py`
- `Datafetch/ml/distance_features.py`
- `Datafetch/ml/trainer_hotstreak_features.py`
- `Datafetch/ml/schema_migration_add_discriminating_features.sql`
- `Datafetch/ml/test_discriminating_features.py`
- `DISCRIMINATING_FEATURES_GUIDE.md` (this file)

### Files Modified:
- `Datafetch/ml/feature_engineer.py` (imports, compute_runner_features, save_features)
- `Datafetch/ml/FEATURE_SPECIFICATION.md` (added documentation for 18 features)
- `racing_pro.db` (schema updated: 110 → 128 features)

---

## Support

If you encounter issues:

1. Check terminal output for specific errors
2. Review `feature_generation_optimized.log`
3. Run test script: `python Datafetch/ml/test_discriminating_features.py`
4. Verify schema: SQL query for column count
5. Report error with context

---

## Estimated Timeline

- **Feature regeneration**: 15-20 minutes
- **Model training**: 3-5 minutes
- **Testing predictions**: 5-10 minutes
- **Total**: ~30 minutes end-to-end

**Note**: First regeneration may take longer as database writes initial data.

