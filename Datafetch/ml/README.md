# ML Pipeline for Horse Racing Predictions

Complete machine learning pipeline for predicting race outcomes using historical racing data.

## 📁 Directory Structure

```
ml/
├── __init__.py                 # Package initialization
├── form_parser.py             # Parse form strings into features
├── compute_stats.py           # Aggregate career statistics
├── feature_engineer.py        # Generate ML-ready features
├── train_baseline.py          # Train XGBoost baseline model
├── build_ml_dataset.py        # Orchestration script
├── monitor_progress.py        # Check pipeline status
├── run_full_pipeline.sh       # Automated pipeline runner
├── requirements_ml.txt        # ML dependencies
└── README.md                  # This file
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r ml/requirements_ml.txt
```

### 2. Fetch Historical Results

```bash
python fetch_historical_results.py --start-date 2023-01-23 --end-date 2023-04-30
```

### 3. Run Full Pipeline (Automated)

```bash
./ml/run_full_pipeline.sh
```

This will automatically:
- Wait for fetch to complete
- Compute statistics for all horses/trainers/jockeys
- Generate ML features for all races
- Display status report

### 4. Train Baseline Model

```bash
python ml/train_baseline.py
```

## 📊 Pipeline Components

### 1. Form Parser (`form_parser.py`)

Parses racing form strings (e.g., "1-2-3-F-P") into structured features:

- **Input**: Form string like "1-2-3-4-P"
- **Output**: 13 computed features including:
  - Last position, averages (3/5/10 races)
  - Best/worst positions
  - Consistency (std dev)
  - Races since win/place
  - Improving trend
  - Win/place rates

**Usage:**
```python
from form_parser import FormParser

features = FormParser.compute_form_features("1-2-3-4-5")
print(features['avg_last_5'])  # 3.0
print(features['improving_trend'])  # -1 (declining)
```

### 2. Statistics Computer (`compute_stats.py`)

Aggregates historical results into pre-computed statistics for fast lookup:

**Tables populated:**
- `horse_career_stats` - Career performance by horse
- `trainer_stats` - Trainer performance (14d, 30d, 90d, 365d, career)
- `jockey_stats` - Jockey performance (multiple periods)
- `trainer_jockey_combos` - Partnership statistics

**Computed metrics:**
- Win rates, place rates, strike rates
- ROI (return on investment at SP)
- A/E ratio (actual vs expected wins)
- Course/distance/going specializations

**Usage:**
```bash
python ml/compute_stats.py
```

### 3. Feature Engineer (`feature_engineer.py`)

Generates comprehensive ML features for each runner in each race:

**Feature Categories (~50+ features):**

1. **Horse Features** (20 features)
   - Age, career runs/wins, win/place rates
   - Form metrics (last 5/10 averages)
   - Course/distance/going win rates
   - Days since last run
   - Consistency scores

2. **Trainer Features** (7 features)
   - Win rates (14d, 90d)
   - Strike rate, ROI, A/E ratio
   - Course/distance specialization

3. **Jockey Features** (7 features)
   - Win rates (14d, 90d)
   - Strike rate, ROI
   - Course specialization

4. **Trainer-Jockey Combo** (3 features)
   - Win rate, strike rate, runs together

5. **Race Context** (7 features)
   - Distance, going, surface, class
   - Prize money, field size

6. **Runner Specifics** (8 features)
   - Draw, weight, ratings (OFR/RPR/TS)
   - Headgear

7. **Relative Features** (4 features)
   - Rating vs field average
   - Weight vs field average
   - Age vs field average
   - Odds rank

**Usage:**
```bash
# Generate features for all races
python ml/feature_engineer.py

# Test mode (first 10 races)
python ml/feature_engineer.py --test
```

### 4. Baseline Trainer (`train_baseline.py`)

Trains XGBoost classifier for winner prediction:

**Features:**
- Binary classification (Win/Not Win)
- Temporal train/test split (80/20)
- Handles class imbalance
- Feature importance analysis
- Racing-specific evaluation metrics

**Metrics Computed:**
- Standard: Accuracy, Precision, Recall, F1, AUC-ROC
- Racing: Top pick win rate, Top 3 hit rate
- Betting: ROI simulation at various confidence thresholds

**Usage:**
```bash
# Train with defaults
python ml/train_baseline.py

# Custom test size
python ml/train_baseline.py --test-size 0.3

# Specify output directory
python ml/train_baseline.py --output-dir models/baseline_v1
```

**Output:**
- `xgboost_baseline.json` - Trained model
- `feature_importance.csv` - Feature importance scores
- `feature_columns.json` - Feature list

## 🔍 Monitoring & Validation

### Check Pipeline Status

```bash
python ml/monitor_progress.py
```

Shows:
- Racecard data summary
- Results fetched
- Statistics computed
- Features generated
- Next steps

### Manual Pipeline Steps

If you prefer to run steps individually:

```bash
# 1. Compute statistics
python ml/compute_stats.py

# 2. Generate features (with validation)
python ml/build_ml_dataset.py

# 3. Train model
python ml/train_baseline.py
```

## 📈 Database Schema

### New Tables Added

1. **`results`** - Race results with positions, times, odds
   - Links racecards to actual outcomes
   - 14+ columns including position, SP, prize money

2. **`horse_career_stats`** - Pre-computed horse statistics
   - Career totals and averages
   - Course/distance/going preferences

3. **`trainer_stats`** - Trainer performance by period
   - Multiple time windows (14d → career)
   - ROI, A/E ratios

4. **`jockey_stats`** - Jockey performance by period
   - Same structure as trainer stats

5. **`trainer_jockey_combos`** - Partnership statistics
   - Minimum 5 runs to be included

6. **`ml_features`** - Feature vectors for ML
   - 50+ features per runner
   - Ready for model input

7. **`ml_targets`** - Target variables
   - Position, won, placed, top_5
   - Prize money, times

## 🎯 Feature Engineering Details

### Temporal Integrity

All features are computed using only data available **before** the race:
- Statistics use only prior results
- Form strings show historical performance
- No data leakage

### Missing Value Handling

- Numeric features: Fill with median
- Categorical: Encode with defaults
- Career stats: 0 for new horses

### Relative Features

Computed after all runners processed:
- Compare each runner to field average
- Rating differentials
- Market rankings

## 🔬 Model Training Strategy

### Baseline Model (XGBoost)

**Approach:**
1. Binary classification (winner vs non-winner)
2. Handle ~10:1 class imbalance with `scale_pos_weight`
3. Temporal split (train on early dates, test on later)
4. Early stopping with validation set

**Hyperparameters:**
```python
{
    'max_depth': 6,
    'learning_rate': 0.05,
    'n_estimators': 200,
    'subsample': 0.8,
    'colsample_bytree': 0.8
}
```

### Future Models (Planned)

1. **Multi-class Classification**: Predict exact position (1st, 2nd, 3rd, etc.)
2. **Ranking Model**: LambdaRank for ordering runners
3. **Neural Network**: Deep learning with PyTorch
4. **Ensemble**: Combine XGBoost + NN

## 📊 Expected Performance

### Target Metrics

Based on historical ML racing models:

- **Winner Accuracy**: > 30% (vs ~10% random baseline)
- **Top 3 Hit Rate**: > 60% (vs ~30% random)
- **Log Loss**: < 2.0
- **ROI at SP**: > 0% (break-even or better)
- **A/E Ratio**: > 1.0 (beat market expectations)

### Betting Simulation

Model includes betting simulation at various confidence thresholds:
- Higher threshold = fewer bets, higher win rate
- Lower threshold = more bets, lower win rate
- Optimize for maximum ROI

## 🛠️ Development Workflow

### Adding New Features

1. **Add to database schema** (`extend_db_schema.py`)
   ```sql
   ALTER TABLE ml_features ADD COLUMN new_feature REAL;
   ```

2. **Compute in feature engineer** (`feature_engineer.py`)
   ```python
   features['new_feature'] = compute_new_feature(...)
   ```

3. **Add to feature list** (`train_baseline.py`)
   ```python
   FEATURE_COLS = [..., 'new_feature']
   ```

4. **Regenerate features**
   ```bash
   python ml/feature_engineer.py
   ```

### Testing Changes

```bash
# Test on small dataset
python ml/feature_engineer.py --test  # First 10 races
python ml/train_baseline.py --test-size 0.5  # Quick training
```

## 📝 Data Quality Notes

- **Results Coverage**: ~7-8% of races have results fetched
- **Form Parsing**: Handles all standard codes (F, U, P, R, etc.)
- **Missing Data**: Some jockeys TBR (To Be Ridden) in results
- **Non-finishers**: Coded as position 900-999
- **API Rate Limit**: 0.55s between requests

## 🚀 Future Enhancements

### Phase 4: Advanced Models
- [ ] Neural network with PyTorch
- [ ] Attention mechanism for runner interactions
- [ ] Recurrent network for sequential form
- [ ] Ensemble meta-learner

### Phase 5: Exotic Predictions
- [ ] Monte Carlo simulator for exacta/trifecta
- [ ] Probability distributions over positions
- [ ] Expected value calculations

### Phase 6: Production
- [ ] Real-time prediction API
- [ ] GUI integration for predictions
- [ ] Live odds tracking
- [ ] Automated betting strategy

### Phase 7: Advanced Features
- [ ] NLP on comments/spotlight text
- [ ] Track bias modeling
- [ ] Weather integration
- [ ] Pedigree deep features
- [ ] Multi-region models

## 📚 References

### Key Concepts

- **A/E Ratio**: Actual wins divided by expected wins (from SP odds). > 1.0 = beating the market
- **ROI**: Return on investment. (Returns - Stakes) / Stakes
- **Strike Rate**: Percentage of bets that win
- **Kelly Criterion**: Optimal bet sizing strategy
- **Form**: Recent race positions (e.g., "1-2-3" = won last 3)
- **OFR/RPR/TS**: Official Rating, Racing Post Rating, Timeform Speed

### Racing Data Science

- Temporal splits essential (no data leakage)
- Class imbalance (~10% winners) requires careful handling
- Market odds are strong baseline (efficient market hypothesis)
- Course/distance/going specialization important
- Trainer/jockey form highly predictive

## 🐛 Troubleshooting

### Database Locked

If you get "database is locked":
- Check if `fetch_historical_results.py` is still running
- Wait for it to complete or stop it
- SQLite doesn't support concurrent writes

### Missing Dependencies

```bash
pip install xgboost scikit-learn pandas numpy
```

### Low Feature Count

Check that statistics were computed:
```bash
python ml/monitor_progress.py
```

If stats are 0, run:
```bash
python ml/compute_stats.py
```

### Memory Issues

For large datasets, process in batches:
```python
# In feature_engineer.py
engineer.generate_features_for_all_races(limit=1000)
```

## 📞 Support

For issues or questions:
1. Check `ML_PROGRESS.md` in project root
2. Review logs: `fetch_results.log`, `ml_stats_computation.log`
3. Run `python ml/monitor_progress.py` for status

---

**Last Updated**: 2025-10-18  
**Version**: 1.0  
**Status**: Production Ready (pending results fetch completion)


