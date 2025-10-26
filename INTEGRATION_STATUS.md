# Feature Integration Status

## ✅ COMPLETED (Phase 1)

### 1. Feature Modules Created & Tested
- ✅ `speed_features.py` - 6 speed features
- ✅ `btn_features.py` - 12 BTN/OVR_BTN features  
- ✅ `quality_features.py` - 3 race quality features
- ✅ `weather_features.py` - 4 going/weather features
- ✅ `weight_features.py` - 2 weight-adjusted features
- ✅ `test_new_features.py` - All tests passing ✓

### 2. Feature Engineer Integration
- ✅ Added imports for all new feature modules
- ✅ Initialized `SpeedFeatureCalculator` and `BTNFeatureCalculator` in `__init__`
- ✅ Removed `compute_odds_features()` method (commented out)
- ✅ Removed `get_opening_odds()` method (commented out)
- ✅ Added `get_past_races_for_features()` helper method
- ✅ Removed odds feature calls in `compute_runner_features()`
- ✅ Added speed feature calculation (6 features)
- ✅ Added BTN feature calculation (12 features)
- ✅ Added weather feature calculation (4 features)
- ✅ Added weight feature calculation (2 features)
- ✅ Added quality feature placeholders (3 features - calculated at field level)

---

## ⏳ REMAINING (Phase 2)

### 3. Database Schema & SQL Updates

**Current Status**: SQL helper script created, output generated

**What's Needed**:
1. Update `ml_features` table schema to add 27 new columns
2. Update `save_features()` SQL INSERT statement
3. Update `compute_relative_features()` to add field-level BTN stats

**Details**:

#### A. Add Columns to `ml_features` Table

Run this SQL migration:

```sql
-- Speed features (6)
ALTER TABLE ml_features ADD COLUMN horse_avg_speed_furlongs_per_sec REAL;
ALTER TABLE ml_features ADD COLUMN horse_best_speed_career REAL;
ALTER TABLE ml_features ADD COLUMN horse_speed_last_3_avg REAL;
ALTER TABLE ml_features ADD COLUMN horse_speed_improving_new REAL;
ALTER TABLE ml_features ADD COLUMN horse_speed_vs_track_record REAL;
ALTER TABLE ml_features ADD COLUMN horse_speed_consistency REAL;

-- BTN features (12)
ALTER TABLE ml_features ADD COLUMN horse_avg_btn_last_5 REAL;
ALTER TABLE ml_features ADD COLUMN horse_median_btn_last_5 REAL;
ALTER TABLE ml_features ADD COLUMN horse_btn_improving REAL;
ALTER TABLE ml_features ADD COLUMN horse_pct_within_3_lengths REAL;
ALTER TABLE ml_features ADD COLUMN horse_btn_vs_field_avg REAL;
ALTER TABLE ml_features ADD COLUMN horse_btn_vs_winner_percentile REAL;
ALTER TABLE ml_features ADD COLUMN horse_best_btn_career REAL;
ALTER TABLE ml_features ADD COLUMN horse_btn_consistency REAL;
ALTER TABLE ml_features ADD COLUMN horse_avg_ovr_btn_last_5 REAL;
ALTER TABLE ml_features ADD COLUMN horse_ovr_btn_improving REAL;
ALTER TABLE ml_features ADD COLUMN horse_ovr_btn_vs_field REAL;
ALTER TABLE ml_features ADD COLUMN horse_pct_top_half_finishes REAL;

-- Quality features (3)
ALTER TABLE ml_features ADD COLUMN field_quality_rating REAL;
ALTER TABLE ml_features ADD COLUMN race_competitiveness REAL;
ALTER TABLE ml_features ADD COLUMN horse_beaten_by_quality REAL;

-- Weather features (4)
ALTER TABLE ml_features ADD COLUMN horse_soft_going_speed_ratio REAL;
ALTER TABLE ml_features ADD COLUMN horse_weather_performance REAL;
ALTER TABLE ml_features ADD COLUMN rail_position_advantage REAL;
ALTER TABLE ml_features ADD COLUMN going_change_adaptation REAL;

-- Weight features (2)
ALTER TABLE ml_features ADD COLUMN horse_weight_adjusted_rating REAL;
ALTER TABLE ml_features ADD COLUMN horse_weight_performance_trend REAL;
```

#### B. Update `save_features()` Method

The complete SQL has been generated in `ml/sql_update_output.txt`.

**Key changes**:
- **Remove 12 odds columns**: odds_rank, opening_odds, final_odds, odds_movement, market_rank, odds_implied_prob, odds_is_favorite, odds_favorite_rank, odds_decimal, odds_bookmaker_count, odds_spread, odds_market_stability
- **Add 27 new columns**: (see ALTER TABLE statements above)
- **Update column count**: 95 → 110 columns
- **Update placeholders**: 95 → 110 question marks

#### C. Update `compute_relative_features()` 

Add field-level BTN statistics calculation:

```python
# In compute_relative_features() method, after existing field calculations:

# Calculate field-level BTN statistics
from .btn_features import calculate_field_btn_stats
btn_relative = calculate_field_btn_stats(all_features)

# Update each horse's features with relative BTN metrics
for features in all_features:
    horse_id = features.get('horse_id')
    if horse_id in btn_relative:
        features.update(btn_relative[horse_id])
```

---

## 📋 Implementation Steps (Sequential)

### Step 1: Schema Migration
```bash
cd Datafetch
sqlite3 racing_pro.db < ../ml/schema_migration.sql
```

### Step 2: Update save_features() SQL
- Copy SQL from `ml/sql_update_output.txt`
- Replace lines 1250-1324 in `feature_engineer.py`
- Test on 1 race to verify

### Step 3: Update compute_relative_features()
- Add BTN field-level calculation
- Located around line 1115 in `feature_engineer.py`

### Step 4: Test Integration
```bash
cd ml
python -c "
from feature_engineer import FeatureEngineer
from pathlib import Path

fe = FeatureEngineer(Path('../racing_pro.db'))
fe.connect()

# Test on one race
race_ids = fe.conn.execute('SELECT race_id FROM races LIMIT 1').fetchone()
print(f'Testing on race: {race_ids[0]}')

# This will fail if SQL isn't updated yet - that's expected
"
```

### Step 5: Regenerate Features (GUI)
1. Open GUI: `python racecard_gui.py`
2. Go to Tab 6 (ML Features)
3. Click "Regenerate Features"
4. Wait ~10-15 minutes for 295K records

### Step 6: Retrain Model
1. Go to Tab 7 (ML Training)
2. Select "Flat" race type
3. Click "Start Training"
4. Wait ~3-5 minutes

### Step 7: Run Diagnostics
```bash
cd ml
python run_diagnostics.py --race-type Flat
```

**Expected Results**:
- ✅ 0% importance from odds features
- ✅ Top features: speed, BTN, ratings, form
- ✅ No data leakage warnings

---

## 🔧 Quick SQL Update Script

Due to the complexity of the SQL update, here's a complete replacement for the `save_features()` method.

**File**: `Datafetch/ml/feature_engineer.py`  
**Lines**: 1244-1329

See `ml/save_features_replacement.py` for the complete updated method.

---

## 📊 Feature Count Summary

| Category | Old | Remove | Add | New |
|----------|-----|--------|-----|-----|
| **Total Features** | 95 | -12 | +27 | **110** |
| **Odds Features** | 12 | -12 | 0 | **0** |
| **Speed Features** | 4 | 0 | +6 | **10** |
| **BTN Features** | 0 | 0 | +12 | **12** |
| **Quality Features** | 0 | 0 | +3 | **3** |
| **Weather Features** | 0 | 0 | +4 | **4** |
| **Weight Features** | 0 | 0 | +2 | **2** |

---

## 🎯 Success Criteria

After completing Phase 2:

- [ ] Schema migration successful (27 new columns added)
- [ ] save_features() updated (110 columns, 0 odds columns)
- [ ] compute_relative_features() updated (BTN field stats)
- [ ] Test feature generation passes (1 race)
- [ ] Feature regeneration completes (295K records)
- [ ] Model retraining successful
- [ ] Diagnostics show 0% odds importance
- [ ] Top features are fundamentals (speed, BTN, ratings)

---

## 📁 Files Modified/Created

**Created**:
- `ml/speed_features.py`
- `ml/btn_features.py`
- `ml/quality_features.py`
- `ml/weather_features.py`
- `ml/weight_features.py`
- `ml/test_new_features.py` ✓ passing
- `ml/update_save_features_sql.py`
- `ml/sql_update_output.txt`
- `FEATURE_SPECIFICATION.md`
- `INTEGRATION_GUIDE.md`
- `DIAGNOSTICS_README.md`
- `ODDS_LEAKAGE_FIX_SUMMARY.md`
- `INTEGRATION_STATUS.md` (this file)

**Modified**:
- `ml/feature_engineer.py` (partial - needs SQL update)

**Needs Migration**:
- `racing_pro.db` schema (add 27 columns)

---

## ⚡ Next Session Tasks

If continuing in a new session:

1. **Create schema migration SQL file** (`schema_migration.sql`)
2. **Run schema migration** on `racing_pro.db`
3. **Update save_features() SQL** (use generated output)
4. **Update compute_relative_features()** (add BTN field stats)
5. **Test** on 1 sample race
6. **Regenerate** all features via GUI
7. **Retrain** model via GUI
8. **Run diagnostics** to verify

---

## 💡 Notes

- The feature calculation code is complete and tested ✓
- The SQL update is straightforward but verbose (110 columns)
- Schema migration is safe (only adding columns, not modifying existing)
- Regeneration will take ~10-15 min but is fully automated
- After retraining, expect dramatically different feature importance
- Model performance may initially appear worse (adjustment period)
- Paper trade for 1 week before going live with new model

---

## 🚀 Estimated Time to Complete Phase 2

- Schema migration: 2 minutes
- SQL update: 10 minutes  
- compute_relative_features update: 5 minutes
- Testing: 5 minutes
- Feature regeneration: 15 minutes
- Model retraining: 5 minutes
- Diagnostics: 10 minutes

**Total: ~52 minutes** (mostly automated waiting time)

