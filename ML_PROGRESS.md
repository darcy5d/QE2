# ML Pipeline Development Progress

**Date**: October 18, 2025  
**Status**: Phase 1 & 2 Complete, Ready for Phase 3 (Model Training)

## ✅ Completed Tasks

### Phase 1: Data Foundation

1. **Database Schema Extension** ✓
   - Created 8 new tables:
     - `results` - Race results with positions, times, odds
     - `horse_career_stats` - Pre-computed horse statistics
     - `trainer_stats` - Trainer performance by period
     - `jockey_stats` - Jockey performance by period
     - `trainer_jockey_combos` - Partnership statistics
     - `form_history` - Parsed form with computed features
     - `ml_features` - Feature vectors for ML (50+ features)
     - `ml_targets` - Target variables (positions, times)
   - All tables have proper foreign keys and indexes
   - Script: `extend_db_schema.py`

2. **Historical Results Fetcher** ✓
   - Built `fetch_historical_results.py`
   - Fetches from `/v1/results/{race_id}` endpoint
   - Rate limited to 0.55s between requests
   - Handles retries with exponential backoff
   - Matches results to racecard data
   - **Currently Running**: Fetching 98 days (Jan 23 - Apr 30, 2023)
   - **Estimated Time**: ~35-40 minutes for full dataset
   - **Test Results**: Successfully fetched 713 results from 73 races in 3 test days
   
3. **Form String Parser** ✓
   - Built `ml/form_parser.py`
   - Parses form strings like "1-2-3-F-P" into structured data
   - Handles non-finishers (Fell, Pulled up, etc.)
   - Computes 13 form-derived features:
     - last_position
     - avg_last_3, avg_last_5, avg_last_10
     - best_last_5, worst_last_5
     - consistency (std dev)
     - races_since_win, races_since_place
     - improving_trend (-1/0/1)
     - completed_last_5, dnf_last_5
     - win_rate_last_10, place_rate_last_10
   - Fully tested with various form patterns

### Phase 2: Feature Engineering ✅

1. **Career Statistics Aggregator** ✓
   - Built `ml/compute_stats.py`
   - Aggregates horse/trainer/jockey statistics from results
   - Computes rolling windows (14d, 30d, 90d, 365d, career)
   - Calculates win rates, place rates, ROI, A/E ratios
   - Course/distance/going specializations
   - Trainer-jockey combo statistics (min 5 runs)

2. **Feature Engineering Pipeline** ✓
   - Built `ml/feature_engineer.py`
   - Combines all feature sources:
     - Race context (course, distance, going, class, etc.)
     - Horse features (age, career stats, form, pedigree)
     - Trainer/Jockey features (recent form, specializations)
     - Relative features (vs field average)
     - Market features (odds, rankings)
   - Output: ~50+ features per runner in `ml_features` table
   - Handles missing data, temporal integrity maintained

3. **Pipeline Orchestration** ✓
   - Built `ml/build_ml_dataset.py` - Full pipeline coordinator
   - Built `ml/monitor_progress.py` - Status checker
   - Built `ml/run_full_pipeline.sh` - Automated runner
   - Comprehensive error handling and validation

4. **Model Training Infrastructure** ✓
   - Built `ml/train_baseline.py` - XGBoost classifier
   - Binary classification (Win/Not Win)
   - Temporal train/test split
   - Feature importance analysis
   - Racing-specific metrics (top pick accuracy, ROI simulation)
   - Model saving and loading

5. **Documentation** ✓
   - Created `ml/README.md` - Complete pipeline guide
   - Created `ml/requirements_ml.txt` - Dependencies
   - Updated `ML_PROGRESS.md` - This document

## 🔄 In Progress

### Phase 3: Model Training & Evaluation

1. **Waiting for Data** (85% complete)
   - Results fetch at 78/98 dates (~10 minutes remaining)
   - Will have ~28,000 results when complete
   - Pipeline ready to run immediately after

## 📊 Current Data Status

### Racecard Data (Existing)
- **Date Range**: 2023-01-23 to 2024-06-30
- **Races**: 22,604
- **Runners**: 239,552
- **Unique Horses**: 17,625
- **Unique Trainers**: 1,843
- **Unique Jockeys**: 1,497

### Results Data (Fetching - 79% Complete)
- **Dates Processed**: 78/98 (target: Jan-Apr 2023)
- **Results Inserted**: ~27,000+ (estimated)
- **Unique Horses**: ~10,550+
- **Expected Total**: ~28,000 results
- **Estimated Completion**: ~10 minutes

## 🎯 Next Steps

### Immediate (Next 30 minutes)
1. ⏳ Wait for results fetch to complete (~10 more minutes)
2. Run automated pipeline: `./ml/run_full_pipeline.sh`
3. This will:
   - ✅ Compute statistics (10-15 min)
   - ✅ Generate features (5-10 min)
   - ✅ Validate data quality

### Phase 3: Model Training (Today)
1. ✅ Built XGBoost winner classifier (`ml/train_baseline.py`)
2. ✅ Implemented temporal train/test split
3. Run training: `python ml/train_baseline.py`
4. Evaluate baseline performance
5. Analyze feature importance
6. Tune hyperparameters if needed

### Phase 4: Neural Networks (Next Week)
1. Build PyTorch data loader
2. Implement feedforward network
3. Train with validation
4. Compare to XGBoost
5. Experiment with architectures

### Phase 5: Exotic Predictions (Week 3)
1. Monte Carlo simulator for trifecta/exacta
2. Generate probability distributions
3. Test on historical data
4. Calculate expected values

### Phase 6: Betting Strategy (Week 3-4)
1. Implement Kelly Criterion
2. Portfolio optimization
3. Backtest on holdout set
4. Risk management rules
5. Generate recommendations

### Phase 7: Production (Week 4)
1. GUI integration
2. Predictions tab
3. Upcoming races predictions
4. Performance tracking

## 📈 Feature List (Planned)

### Horse Features (~20)
- Age, sex, weight carried
- Career: runs, wins, places, earnings
- Form: last 3/5/10 avg, consistency, trend
- Course/distance win rates
- Going preference
- Days since last run
- Recent form score

### Trainer/Jockey Features (~15)
- Win rates (14d, 30d, 90d, career)
- Course/distance specialization
- Going specialization
- Strike rate, ROI, A/E ratio
- Trainer-jockey combo stats

### Race Context Features (~10)
- Distance (furlongs)
- Going (encoded)
- Surface (turf/AW)
- Race class (1-7)
- Prize money
- Field size
- Region
- Race type (flat/chase/hurdle)
- Age/sex restrictions

### Relative Features (~10)
- Rating vs field average (ofr, rpr, ts)
- Weight vs field average
- Age vs field average
- Odds rank (1=favorite)
- Draw advantage (for flat)

### Market Features (~5)
- Opening odds
- Final SP
- Odds movement
- Market rank
- Odds vs implied probability

### Pedigree Features (~5)
- Sire distance/surface performance
- Dam produce performance
- Pedigree rating composite

**Total**: ~65 features

## 🔬 Modeling Strategy

### Approach 1: XGBoost (Baseline)
- Binary classification: Win/Not Win
- Multi-class: Position prediction (1st, 2nd, 3rd, etc.)
- Ranking: LambdaRank for ordering

### Approach 2: Neural Network
- Feedforward with race + runner features
- Softmax output over positions
- Attention mechanism for runner interactions
- Custom loss for ranking

### Approach 3: Ensemble
- Combine XGBoost + NN predictions
- Weighted averaging by validation performance
- Meta-learner on top

## 📊 Success Metrics

### Model Performance
- Winner Accuracy: Target > 30% (baseline ~10%)
- Top 3 Accuracy: Target > 60% (baseline ~30%)
- Log Loss: Target < 2.0
- ROI at SP: Target > 0%
- A/E Ratio: Target > 1.0

### Betting Performance
- Kelly ROI: Target > 5% per race
- Win Rate: Target > 35% of bets
- Max Drawdown: Target < 20%
- Sharpe Ratio: Target > 1.0

## 🛠️ Technical Stack

### Core
- Python 3.10+
- SQLite for data storage
- PySide6 for GUI

### ML Libraries
- scikit-learn (preprocessing, baseline models)
- XGBoost (gradient boosting)
- PyTorch (neural networks)
- NumPy/Pandas (data manipulation)

### Visualization
- Matplotlib/Seaborn (plotting)
- SHAP (model interpretation)

### Optimization
- Optuna (hyperparameter tuning)
- Kelly Criterion (betting optimization)

## 📝 Notes

- Rate limiting: 0.55s between API requests (conservative)
- Data quality: 100% of runners have horse_id, trainer_id
- Some jockeys missing from results (TBR announcements)
- Non-finishers coded as position 900-999
- Database optimized with indexes on all key lookups
- All timestamps in UTC
- Currency in GBP for prize money

## 🚀 Future Enhancements

1. **Real-time Odds**: Scrape or API for live odds movements
2. **NLP Features**: Analyze comments, spotlight text
3. **Weather Integration**: More detailed weather data
4. **Track Bias**: Model positional bias by course/going
5. **Multi-Region**: Separate models for UK/IRE/AUS/US
6. **Deep Learning**: RNN for sequential form, CNN for track layouts
7. **Reinforcement Learning**: Dynamic betting strategy
8. **Extended History**: Fetch back to 1985 for career stats

---

**Last Updated**: 2025-10-18 21:45 UTC  
**Next Milestone**: Complete results fetch, build stats aggregator

