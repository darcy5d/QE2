# Odds & New Fields Implementation - COMPLETE ✓

**Implementation Date:** October 20, 2025

## Overview

Successfully implemented the ranking model enhancement plan to add **odds as standalone features** plus demographic and trainer form data. This gives the model both market wisdom (odds) AND performance ratings (RPR/TS) for more powerful predictions.

## Philosophy

**OLD thinking**: Use odds to fill gaps when RPR/TS missing  
**NEW thinking**: Odds are **independent features** with unique predictive power

- **RPR/TS**: Historical performance ratings
- **Odds**: Real-time market consensus (incorporates form, trainer confidence, stable whispers, money flows, etc.)
- **Together**: More powerful than either alone!

## Implementation Summary

### ✅ 1. Database Schema Extensions

**New Tables Created:**
- `runner_odds` - Individual bookmaker odds (245,525 records migrated)
  - Columns: runner_id, bookmaker, fractional, decimal, ew_places, ew_denom, updated
- `runner_market_odds` - Aggregated market odds (9,821 runners with odds)
  - Columns: runner_id, avg_decimal, median_decimal, min/max_decimal, bookmaker_count, implied_probability, is_favorite, favorite_rank

**New Columns in `runners` Table:**
- Demographics: age, sex, sex_code, dob
- Breeding: sire, sire_id, dam, dam_id, damsire, damsire_id
- Additional: region, breeder, colour, trainer_location
- Trainer form: trainer_14d_runs, trainer_14d_wins, trainer_14d_percent

**New Columns in `ml_features` Table:**
- **Odds features (7):**
  - odds_implied_prob
  - odds_is_favorite
  - odds_favorite_rank
  - odds_decimal
  - odds_bookmaker_count
  - odds_spread
  - odds_market_stability

- **Demographic features (3):**
  - horse_sex_encoded
  - horse_is_filly_mare
  - horse_is_gelding

- **Trainer form features (4):**
  - trainer_14d_runs
  - trainer_14d_wins
  - trainer_14d_win_pct
  - trainer_is_hot

**Total New Features: 14** (plus age already existed)

### ✅ 2. Data Migration

**File:** `Datafetch/migrate_odds_schema.py`

- Migrated 245,525 historical odds records from JSON format to normalized schema
- Computed market aggregates for 9,821 runners
- Identified and marked 928 favorites across races
- Average 25 bookmakers per runner

### ✅ 3. Data Fetching Updates

**File:** `Datafetch/gui/upcoming_fetcher.py`

**Enhancements:**
- Updated schema to include odds tables and new runner fields
- Added `save_runner_odds()` function to process bookmaker odds
- Added `update_favorite_status()` function to rank favorites by odds
- Updated runner insertion to extract all new API fields
- Automatically parses trainer_14_days stats from API
- Handles trainer percentage format (removes % symbol)

**Key Features:**
- Extracts age, sex, sex_code, dob from runners
- Captures sire, dam, damsire information
- Stores trainer 14-day form (runs, wins, percentage)
- Processes and normalizes odds from multiple bookmakers
- Computes market statistics (avg, median, min, max, spread, stability)
- Identifies favorites and ranks all runners by odds

### ✅ 4. Feature Engineering Updates

**File:** `Datafetch/ml/feature_engineer.py`

**New Methods Added:**

1. **`compute_odds_features(runner_id)`**
   - Queries runner_market_odds table
   - Returns 7 odds-based features
   - Handles missing data gracefully
   - Computes spread and market stability

2. **`compute_demographic_features(runner_data)`**
   - Encodes horse sex (C/F/G/H/M → 1-5)
   - Creates binary indicators for fillies/mares and geldings
   - Returns 3 demographic features

3. **`compute_trainer_form_features(runner_data)`**
   - Extracts trainer 14-day stats
   - Identifies "hot" trainers (>25% win rate, 4+ runs)
   - Returns 4 trainer form features

**Integration:**
- All new methods integrated into `compute_runner_features()`
- Updated `get_runners_for_race()` to fetch new fields
- Updated `save_features()` to save all new feature columns
- Features computed for both training (historical) and prediction (upcoming)

### ✅ 5. Model Training

**File:** `Datafetch/ml/train_baseline.py`

**Updates:**
- Model automatically discovers features via `get_available_features()`
- Dynamically includes all 14 new features
- No manual feature list maintenance required
- Works seamlessly with ranking objective

### ✅ 6. Testing & Verification

**File:** `Datafetch/test_odds_implementation.py`

**Test Results:**
- ✓ Schema: All tables and columns created successfully
- ✓ Data Population: 245,525 odds records, 9,821 market summaries
- ✓ Feature Generation: All new features compute correctly

## Current Data Status

### Historical Data (Already in DB)
- ✅ **Odds data**: 245,525 records from 928 races, 9,821 runners
  - Average 25 bookmakers per runner
  - Favorites identified and ranked
  - Market statistics computed

### Upcoming Data (Will be populated on next fetch)
- ✅ Schema ready for: age, sex, trainer form
- ✅ Odds processing active
- ✅ All new fields will be extracted from API

## Feature Count Evolution

**Before:** 77 features  
**After:** 92 features (77 + 15 new)

### New Features Breakdown:
1. **Odds Features (7):**
   - odds_implied_prob - Market's win probability
   - odds_is_favorite - Binary: is this the favorite?
   - odds_favorite_rank - 1=fav, 2=2nd fav, etc.
   - odds_decimal - Average decimal odds
   - odds_bookmaker_count - Market liquidity
   - odds_spread - Price disagreement between bookmakers
   - odds_market_stability - Consensus level (min/max ratio)

2. **Demographics (4):**
   - horse_age - Age of horse
   - horse_sex_encoded - Encoded sex value (1-5)
   - horse_is_filly_mare - Binary indicator
   - horse_is_gelding - Binary indicator

3. **Trainer Form (4):**
   - trainer_14d_runs - Recent activity
   - trainer_14d_wins - Recent success
   - trainer_14d_win_pct - Recent win percentage
   - trainer_is_hot - >25% win rate with 4+ runs

## Real-World Examples

### Scenario A: Favorite with form to match
```
Horse A: RPR=98, Odds=2.5 (40%), Age=4, Trainer hot → Strong pick ✓
```

### Scenario B: Market darling but questionable form
```
Horse B: RPR=82, Odds=3.0 (33%), Age=6, Gelding → Model learns skepticism
```

### Scenario C: Australian race (no RPR available)
```
Horse C: RPR=None, Odds=4.0 (25%), Age=3, Filly, Trainer=15% → Still has features!
```

## Expected Performance Improvement

**Baseline:** 26% top pick accuracy (current)

**Expected with new features:**
- +Odds: 28-30% accuracy (market is strong signal!)
- +Demographics: +1-2% (age/sex patterns)
- +Trainer form: +0.5-1% (hot trainers)

**Target:** 30-32% top pick accuracy

## Next Steps

### 1. Regenerate Features for Historical Data
```bash
cd Datafetch/ml
python feature_engineer.py
```
This will compute the new features for all historical races with results.

### 2. Retrain Model with 92 Features
```bash
python train_baseline.py
```
This will train a new model with all 92 features (including the 15 new ones).

### 3. Compare Performance
- Old model: 77 features, 26% accuracy
- New model: 92 features, target 30-32% accuracy
- Analyze feature importance to see which new features matter most

### 4. Test on Upcoming Races
Use the GUI to:
1. Fetch upcoming races (will populate new fields)
2. Generate predictions with new model
3. Compare against actual results

### 5. Monitor & Iterate
- Track which new features have highest importance
- Consider additional derived features from odds (e.g., odds movement)
- Monitor for any data quality issues

## Files Created/Modified

### New Files:
1. `Datafetch/extend_odds_schema.py` - Initial schema extension
2. `Datafetch/migrate_odds_schema.py` - Migrate historical odds data
3. `Datafetch/test_odds_implementation.py` - Comprehensive testing

### Modified Files:
1. `Datafetch/gui/upcoming_fetcher.py` - Extract new API fields, process odds
2. `Datafetch/ml/feature_engineer.py` - Compute new features
3. `Datafetch/ml/train_baseline.py` - Dynamic feature discovery (no changes needed)

### Database Tables:
- Modified: `runners`, `ml_features`
- New: `runner_odds`, `runner_market_odds`
- Archived: `runner_odds_old` (original JSON format)

## Technical Notes

### Odds Processing Pipeline
1. API returns odds array with bookmaker objects
2. `save_runner_odds()` stores individual bookmaker odds
3. Market aggregates computed (avg, median, min, max)
4. `update_favorite_status()` ranks runners within each race
5. Feature engineer queries market_odds for ML features

### Data Quality
- Handles missing odds gracefully (returns None/defaults)
- Trainer percentage parsed with % symbol removal
- Type conversions with error handling
- Age/sex coalesced from runners or horses table

### Performance Considerations
- Indexed runner_odds on runner_id
- Indexed runner_market_odds on runner_id
- Market odds pre-computed for fast feature extraction
- Favorites computed once per race

## Benefits of This Approach

### 1. Odds as Complementary Features ✅
Model learns patterns like:
- RPR 95 + Odds 5.0 = "Strong form, market agrees"
- RPR 95 + Odds 15.0 = "Strong form, market doubts" (injury concerns?)
- RPR 70 + Odds 3.0 = "Weak form, market confident" (insider info?)

### 2. Better for ALL Races ✅
- **UK races with RPR**: Get BOTH signals → better predictions
- **International races without RPR**: Get odds signal → some differentiation
- **Mixed data races**: Model learns to weight each signal appropriately

### 3. Robust Feature Engineering ✅
- Market consensus (avg odds)
- Market confidence (spread, stability)
- Position in betting (favorite rank)
- Demographics (age/sex patterns)
- Trainer momentum (hot trainers)

## Success Metrics

✅ **Schema Complete** - All tables and columns created  
✅ **Data Migrated** - 245,525 odds records normalized  
✅ **Code Updated** - All fetching, engineering, and training code ready  
✅ **Tests Passing** - All validation tests pass  
⏳ **Model Retraining** - Ready to retrain with new features  
⏳ **Performance Validation** - Awaiting comparison results

## Conclusion

The odds and new fields implementation is **complete and tested**. The system is now ready to:

1. ✅ Fetch upcoming races with all new fields
2. ✅ Process and normalize odds data automatically
3. ✅ Compute 15 new ML features
4. ✅ Train models with 92 total features
5. ⏳ Achieve 30-32% top pick accuracy (to be validated)

**The model now has both form assessment (RPR/TS) AND market wisdom (odds) working together!** 🎯


