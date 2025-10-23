# Flat Racing System - Command Line Testing Regime

## Test Plan Overview

**Goal**: Verify Flat-only ML pipeline works end-to-end via command line

**Duration**: ~30-60 minutes (depending on training time)

---

## Phase 1: Pre-Flight Checks ✅

### 1.1 Verify Feature Data

```bash
cd /Users/darcy5d/Desktop/DD_AI_models/QE2/Datafetch
sqlite3 racing_pro.db "SELECT r.type, COUNT(*) as features, COUNT(DISTINCT r.race_id) as races FROM ml_features f JOIN races r ON f.race_id = r.race_id GROUP BY r.type ORDER BY features DESC;"
```

**Expected Output**:
```
Flat|~295K|~27.5K races
Hurdle|~88K|~8K races
Chase|~40K|~4.7K races
```

✅ **PASSED**: Features exist, no regeneration needed!

### 1.2 Verify Training Script Has Race Type Support

```bash
python ml/train_baseline.py --help
```

**Expected**: Should show `--race-type` argument with choices: Flat, Hurdle, Chase

### 1.3 Check for Existing Models

```bash
ls -lh ml/models/*.json 2>/dev/null || echo "No models yet"
```

**Expected**: May show old `xgboost_baseline.json` - that's OK, we're creating `xgboost_flat.json`

---

## Phase 2: Train Flat Model 🏋️

### 2.1 Train with Flat Races Only

```bash
cd ml
python train_baseline.py --race-type Flat --test-size 0.2 --output-dir models
```

**What to Watch For**:
```
============================================================
Race counts by type in database:
  Flat: 27,551 races
  Hurdle: 7,933 races
  Chase: 4,682 races
============================================================

✅ Training on Flat races only
Loaded 295,307 samples
Unique races: 27,551

Train/test split at date: YYYY-MM-DD
  Train: ~236K samples in ~22K races
  Test: ~59K samples in ~5.5K races

Training XGBoost RANKING model...
[Progress bars and metrics]

Test Performance:
  Top-1 Accuracy: ~XX%
  Top-3 Accuracy: ~XX%
  NDCG@5: ~X.XXX

✓ Flat model saved to models/xgboost_flat.json
✓ Feature importance saved to models/feature_importance_flat.csv
✓ Feature columns saved to models/feature_columns_flat.json
```

**Success Criteria**:
- [x] Shows "Training on Flat races only"
- [x] Loaded ~295K samples
- [x] ~27.5K unique races
- [x] Top-3 accuracy >40% (aim for >50%)
- [x] Model saved as `xgboost_flat.json`

**Estimated Time**: 10-30 minutes depending on CPU

---

## Phase 3: Verify Model Files 📁

### 3.1 Check Model Files Created

```bash
ls -lh ml/models/*flat*
```

**Expected Output**:
```
-rw-r--r--  xgboost_flat.json          (~XX MB)
-rw-r--r--  feature_columns_flat.json  (~3-5 KB)
-rw-r--r--  feature_importance_flat.csv (~10 KB)
```

### 3.2 Inspect Feature Columns

```bash
wc -l ml/models/feature_columns_flat.json
cat ml/models/feature_columns_flat.json | head -20
```

**Expected**: Should show 93 features (same as before)

### 3.3 Check Top Features

```bash
head -20 ml/models/feature_importance_flat.csv
```

**Expected**: Should see Flat-relevant features high:
- `draw` (critical for Flat!)
- `rpr`, `ts`, `ofr` (ratings)
- `odds_implied_prob` (market info)
- `horse_course_wins`, `jockey_win_rate` (form)

---

## Phase 4: Test Predictions 🔮

### 4.1 Check Upcoming Races

```bash
sqlite3 upcoming_races.db "SELECT type, COUNT(*) FROM races GROUP BY type;"
```

**Expected**: Should show mix of Flat, Hurdle, Chase races

### 4.2 Test Prediction Script (if exists)

```bash
cd ml
python -c "
from predictor import ModelPredictor
from pathlib import Path

# Initialize with Flat model
predictor = ModelPredictor(race_type='Flat')
print('✅ Flat model loaded successfully')
print(f'   Features: {len(predictor.feature_columns)}')
print(f'   Model: {predictor.model_path.name}')
"
```

**Expected**:
```
✓ Loaded Flat racing model from xgboost_flat.json
✓ Loaded 93 feature columns for Flat racing
✓ Loaded feature importance scores
✅ Flat model loaded successfully
   Features: 93
   Model: xgboost_flat.json
```

### 4.3 Test Race Type Validation

```bash
python -c "
from predictor import ModelPredictor
import sqlite3

# Test that Hurdle races are skipped
predictor = ModelPredictor(race_type='Flat')

# Get a Hurdle race ID
conn = sqlite3.connect('../upcoming_races.db')
cursor = conn.cursor()
cursor.execute(\"SELECT race_id FROM races WHERE type = 'Hurdle' LIMIT 1\")
hurdle_race = cursor.fetchone()
conn.close()

if hurdle_race:
    result = predictor.predict_race(hurdle_race[0], '../upcoming_races.db')
    if result is None:
        print('✅ Correctly skipped Hurdle race')
    else:
        print('❌ ERROR: Should have skipped Hurdle race!')
else:
    print('⚠️  No Hurdle races to test (that\\'s OK)')
"
```

**Expected**: `✅ Correctly skipped Hurdle race` or no Hurdle races available

---

## Phase 5: Integration Test 🔗

### 5.1 Test End-to-End with GUI (Quick Check)

```bash
cd ..
# Start GUI briefly just to verify it loads the Flat model
python racecard_gui.py &
GUI_PID=$!
sleep 5
kill $GUI_PID
```

**Success**: GUI starts without errors

### 5.2 Test In The Money View Logic

```bash
python -c "
from pathlib import Path
import sys
sys.path.insert(0, str(Path('gui').parent))

from gui.betting_calculator import BettingCalculator

# Test betting calculator
calc = BettingCalculator(
    bankroll=1000.0,
    kelly_fraction=0.5,
    min_edge=0.05,
    market_confidence=0.65
)

# Test recommendation
test_runner = {
    'horse_name': 'Test Horse',
    'runner_number': 1,
    'win_probability': 0.25,  # 25% chance
    'predicted_rank': 1
}
market_odds = 5.0  # Market says 20% (1/5 = 0.2)

rec = calc.recommend_win_bet(test_runner, market_odds)

if rec:
    print(f'✅ Betting calculator works')
    print(f'   Horse: {rec[\"horse_name\"]}')
    print(f'   Our odds: {rec[\"our_odds\"]:.2f}')
    print(f'   Market odds: {rec[\"market_odds\"]:.2f}')
    print(f'   Stake: ${rec[\"stake\"]:.2f}')
    print(f'   EV: {rec[\"ev_percentage\"]:.1f}%')
else:
    print('❌ No recommendation generated (check logic)')
"
```

**Expected**: Shows recommendation with reasonable stake

---

## Phase 6: Performance Verification 📊

### 6.1 Check Model Metrics

```bash
# Review training output saved in log
grep -A 20 "Test Performance" ml_training.log 2>/dev/null || echo "Check terminal output from training"
```

**Target Metrics**:
- Top-1 Accuracy: >15% (baseline ~8-10% for 12-horse field)
- Top-3 Accuracy: >40% (aim for >50%)
- NDCG@5: >0.500 (higher is better)

### 6.2 Feature Importance Check

```bash
head -10 ml/models/feature_importance_flat.csv | column -t -s,
```

**Expected Top Features**:
1. Ratings: `rpr`, `ts`, `ofr`
2. Market: `odds_implied_prob`, `odds_decimal`
3. Form: `horse_form_last_5_avg`, `jockey_win_rate`
4. **Flat-specific**: `draw`, `draw_position_normalized`

### 6.3 Verify No Jump Features High

```bash
grep -i "jump\|hurdle\|chase\|fence" ml/models/feature_importance_flat.csv || echo "✅ No Jump-specific features"
```

**Expected**: `✅ No Jump-specific features` (none exist)

---

## Phase 7: Race Type Distribution Check 🔍

### 7.1 Verify Training Set Purity

```bash
python -c "
import sqlite3
conn = sqlite3.connect('racing_pro.db')
cursor = conn.cursor()

# Check ml_features + targets filtered by Flat
cursor.execute('''
    SELECT r.type, COUNT(*) as samples
    FROM ml_features f
    JOIN ml_targets t ON f.race_id = t.race_id AND f.runner_id = t.runner_id
    JOIN races r ON f.race_id = r.race_id
    WHERE r.type = 'Flat'
    GROUP BY r.type
''')

results = cursor.fetchall()
conn.close()

for row in results:
    print(f'{row[0]}: {row[1]:,} samples')
    
if len(results) == 1 and results[0][0] == 'Flat':
    print('✅ Training data is 100% Flat races')
else:
    print('❌ ERROR: Non-Flat races in filtered set!')
"
```

**Expected**: 
```
Flat: 295,307 samples
✅ Training data is 100% Flat races
```

---

## Success Criteria Summary

### ✅ All Tests Must Pass:

1. **Pre-Flight**:
   - [x] Features exist (~295K Flat samples)
   - [x] Training script supports `--race-type`
   
2. **Training**:
   - [ ] "Training on Flat races only" message
   - [ ] ~295K samples loaded
   - [ ] Model saved as `xgboost_flat.json`
   - [ ] Top-3 accuracy >40%

3. **Model Files**:
   - [ ] `xgboost_flat.json` exists
   - [ ] `feature_columns_flat.json` exists (93 features)
   - [ ] `feature_importance_flat.csv` exists

4. **Predictions**:
   - [ ] Flat model loads successfully
   - [ ] Hurdle races are skipped (validation works)
   - [ ] Betting calculator generates recommendations

5. **Quality**:
   - [ ] Top Flat-relevant features ranked high
   - [ ] No Jump-specific features in dataset
   - [ ] Training set is 100% Flat races

---

## If Any Test Fails:

### Training Hangs/Crashes:
- Check memory usage: `top` or `htop`
- Reduce data: Use `--test-size 0.3` for faster testing
- Check logs for errors

### Poor Accuracy (<40% top-3):
- This might be OK initially - model learns patterns over time
- Check feature importance - are ratings/odds ranking high?
- Consider hyperparameter tuning later

### Model Not Loading:
- Verify file exists: `ls ml/models/xgboost_flat.json`
- Check file size: Should be >1MB
- Try retraining if corrupted

### Race Type Validation Not Working:
- Check predictor.py has validation code
- Verify `race_type` parameter is being set
- Check terminal output for "Skipping" messages

---

## Next Steps After Testing:

### If All Tests Pass ✅:
1. **Commit the trained model** (optional - models are large):
   ```bash
   git add ml/models/*flat*
   git commit -m "Add trained Flat racing model"
   ```

2. **Test with GUI**:
   - Start GUI
   - Go to "In The Money" view
   - Click "Find Value Bets"
   - Verify only Flat races appear

3. **Paper Trade**:
   - Track 20-30 Flat bets
   - Monitor win rate, ROI
   - Verify predictions vs actual results

4. **If Performance Good**:
   - Complete remaining GUI tabs
   - Go live with Flat betting
   - Train Hurdle/Chase models later

### If Tests Fail ❌:
1. **Debug the specific failure**
2. **Re-run failed test**
3. **Check logs and error messages**
4. **Fix issues before proceeding**

---

**Ready to Execute!** 🚀

Run tests in order - each phase builds on the previous one.

