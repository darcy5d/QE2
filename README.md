# QE2 - Horse Racing ML Prediction Platform

A comprehensive platform for collecting, analyzing, and predicting horse racing outcomes using machine learning. Features a full-stack GUI application with XGBoost ranking models trained on 999 days of historical UK racing data.

## 📋 Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [GUI Dashboard](#gui-dashboard)
- [ML Pipeline](#ml-pipeline)
- [Database](#database)
- [Implementation History](#implementation-history)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Project Structure](#project-structure)

---

## Overview

QE2 is an end-to-end horse racing analysis and prediction system that:
- **Fetches data** from The Racing API (racecards, results, upcoming races)
- **Stores** in optimized SQLite database with 43k+ races and 395k+ results
- **Engineers** 23 race-context features (field strength, draw bias, pace dynamics)
- **Trains** XGBoost ranking models that understand horses compete together
- **Predicts** win probabilities for upcoming races with proper normalization
- **Visualizes** everything through a beautiful PySide6 GUI dashboard

### Key Features

- 🖥️ **GUI Dashboard**: 8-tab interface covering entire workflow (data fetch → predictions)
- 🤖 **ML Ranking Model**: XGBoost rank:pairwise with race grouping and points system
- 📊 **Race-Context Features**: Field strength metrics, draw advantage, pace pressure, relative ratings
- 📈 **Performance Metrics**: Top Pick Win Rate ~30-35%, Top 3 Hit Rate ~70-75%, NDCG@3 ~0.60-0.65
- 🎯 **Proper Probabilities**: Softmax ensures predictions sum to 100% per race
- 📅 **Historical Coverage**: 999 days of data from 2023-01-23 to 2025-10-18

### Database Statistics

| Metric | Count | Coverage |
|--------|-------|----------|
| **Races** | 43,037 | 999 days (2023-2025) |
| **Runners** | 455,242 | Avg ~10.6 per race |
| **Results** | 395,463 | 95.9% of races |
| **Horses** | 57,136 | Unique competitors |
| **Trainers** | 3,737 | Active trainers |
| **Jockeys** | 3,191 | Active jockeys |
| **Owners** | 31,778 | Unique owners |
| **ML Features** | ~390,000 | 23 features per runner |

**Date Range**: 2023-01-23 to 2025-10-18 (almost 3 years)  
**Database Size**: 356 MB

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/darcy5d/QE2.git
cd QE2

python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure API Credentials

Create `Datafetch/reqd_files/cred.txt`:
```
your_username
your_password
```

**⚠️ IMPORTANT**: This file is gitignored. Never commit credentials.

### 3. Launch GUI

```bash
cd Datafetch
python racecard_gui.py
```

### 4. Initial Data Setup

1. **Tab 2: Database Update** → Click "Update to Yesterday"
   - Fetches ~43k races, 455k runners, 395k results (~20-30 minutes)
   
2. **Tab 6: ML Features** → Click "Regenerate Features"
   - Generates ~390k feature records (~10-15 minutes)
   
3. **Tab 7: ML Training** → Check "Auto-regenerate" → Click "Start Training"
   - Trains XGBoost ranking model (~3-5 minutes)

4. **Tab 8: Predictions** → Select upcoming race → View predictions!

---

## Architecture

### Tech Stack

- **Language**: Python 3.9+
- **GUI**: PySide6 (Qt for Python)
- **Database**: SQLite with foreign key constraints
- **ML**: XGBoost (ranking objective), pandas, numpy
- **API**: The Racing API (Professional tier)
- **Visualization**: matplotlib, custom Qt widgets

### Data Flow

```
API Endpoints (racecards + results)
    ↓
Database (43k races, 455k runners, 395k results)
    ↓
ML Features (23 features × 390k runners)
    ↓
XGBoost Ranking (rank:pairwise with race grouping)
    ↓
Win Probabilities (softmax normalized, sum to 100%)
```

### API Endpoints Used

- **`/v1/racecards/pro`** - Professional racecards with enhanced data
- **`/v1/results/{race_id}`** - Individual race results
- **`/v1/courses`** - Course information

Rate limiting: 0.55s between requests (respects API limits)

---

## GUI Dashboard

The application provides an 8-tab interface covering the complete workflow:

### 🏠 Tab 1: Dashboard (Home)
- Database overview with stats cards
- Quick navigation to all features
- Real-time coverage metrics
- System status indicators

### 🔄 Tab 2: Database Update
- **Combined Fetcher**: Racecards + Results in one operation
- **Update to Yesterday**: Automated catch-up from last date
- **Update to Date**: Fetch up to specific date
- **Fetch Upcoming**: Get today's/tomorrow's races
- Progress tracking with detailed logs
- Foreign key constraint handling

### 📅 Tab 3: Upcoming Races
- View and manage upcoming race cards
- Fetch races for prediction
- Filter by date, course, region
- Race details and runner information

### 🏇 Tab 4: Racecard Viewer
- Browse historical racecards
- Filter by:
  - Region (UK, Ireland, All)
  - Year, Month, Day
  - Course
- Detailed race information
- Full runner cards with pedigree

### 📊 Tab 5: Data Exploration
- Statistical analysis
- Data quality checks
- Coverage reports
- Trend visualization
- Database health monitoring

### ⚙️ Tab 6: ML Features
- **Regenerate Features**: Generate/update ML feature set
- **Auto-regenerate**: Automatic feature generation before training
- Feature statistics and coverage metrics
- Progress tracking with worker threads
- Feature validation

### 🤖 Tab 7: ML Training
- **Train Model**: XGBoost ranking model training
- Race type selection (Flat/Jump)
- Test size configuration
- Real-time training progress
- Feature importance display
- Model evaluation metrics:
  - Top Pick Win Rate
  - Top 3 Hit Rate
  - NDCG@1, NDCG@3, NDCG@5
  - Mean Reciprocal Rank (MRR)
  - Spearman Correlation
  - Position distribution analysis

### 🎯 Tab 8: Predictions
- Generate win probabilities for upcoming races
- Race selection with detailed information
- Prediction results with:
  - Win probability (%)
  - Confidence indicators (⭐ Strong Pick, ✓ Good Chance)
  - Ranking by probability
  - Key features for each runner
- Probabilities properly normalized (sum to 100%)
- Model-based insights

**For detailed GUI documentation, see**: `docs/GUI_COMPLETE_GUIDE.md`

---

## ML Pipeline

### Model Architecture

**XGBoost Ranking Model** with `rank:pairwise` objective:
- Learns relative performance within races
- Race grouping ensures horses compete in proper context
- Softmax normalization for valid probabilities
- Temporal train/test split (no data leakage)

### Feature Engineering (23 Features)

#### 1. Horse Features (8)
- RPR (Racing Post Rating) - Official rating
- TSR (Top Speed Rating) - Speed rating
- OFR (Official Rating) - BHA official rating
- Age, sex, weight carried
- Days since last run
- Career statistics (wins, places, runs)
- Recent form trends

#### 2. Field Strength Features (8)
- **Field Best RPR**: Highest rating in race
- **Field Average RPR**: Mean rating of field
- **Horse RPR vs Best**: Gap to highest rated
- **Horse RPR vs Field Avg**: Relative position
- **Field RPR Spread**: Competitiveness indicator
- **Top 3 RPR Average**: Elite tier strength
- **Horse in Top Quartile**: Boolean top 25%
- **Pace Pressure**: Count of front-runners

#### 3. Draw Bias Features (4)
- **Draw Position Normalized**: 0-1 scale by field size
- **Course Distance Draw Bias**: Historical win rate by draw
- **Low Draw Advantage**: Boolean for low-bias tracks
- **High Draw Advantage**: Boolean for high-bias tracks

#### 4. Relative Rankings (3)
- **Weight Rank**: Position in field by weight
- **Age Rank**: Position in field by age
- **Odds Rank**: Position in betting market

### Training Process

```python
# 1. Load data with race grouping
train_df = load_features_from_db()

# 2. Convert positions to points (higher = better)
points = max_position - position + 1

# 3. Create DMatrix with race groups
train_groups = train_df.groupby('race_id').size().values
dtrain = xgb.DMatrix(X_train, label=points)
dtrain.set_group(train_groups)

# 4. Train with pairwise ranking
model = xgb.train({
    'objective': 'rank:pairwise',
    'eval_metric': 'ndcg@3',
    'max_depth': 8,
    'learning_rate': 0.03
}, dtrain)

# 5. Predict and convert to probabilities
scores = model.predict(dtest)
exp_scores = np.exp(scores - np.max(scores))
probabilities = exp_scores / exp_scores.sum()  # Sums to 100%
```

### Model Performance

**Evaluation Metrics** (Test Set):
- **Top Pick Win Rate**: 30-35% (baseline: ~10% for 10-horse race)
- **Top 3 Hit Rate**: 70-75% (model's top 3 includes winner)
- **NDCG@3**: 0.60-0.65 (ranking quality)
- **Mean Reciprocal Rank (MRR)**: 0.45-0.50
- **Spearman Correlation**: 0.30-0.40 (rank agreement)

**Top Features** (by importance):
1. RPR (Racing Post Rating)
2. RPR vs Best in Field
3. Field Average RPR
4. TSR (Topspeed Rating)
5. Days Since Last Run
6. Horse Age
7. Draw Position (distance-adjusted)
8. Jockey Rating vs Field Avg
9. Pace Pressure Score
10. Form Points (recent finishes)

**For detailed ML documentation, see**: `docs/ML_PIPELINE_COMPLETE_GUIDE.md`

---

## Database

### Schema Overview

#### Core Tables (Racing Data)
- **races**: Race information (course, distance, going, class, prize money)
- **runners**: Individual horses in races (draw, weight, ratings, form)
- **horses**: Horse master data (pedigree, age, sex)
- **trainers**: Trainer information
- **jockeys**: Jockey information
- **owners**: Owner information
- **courses**: Course details (region, type)

#### Results & Performance
- **results**: Race outcomes (position, time, SP odds, beaten distances)
- **horse_career_stats**: Pre-computed career statistics
- **trainer_stats**: Trainer performance by period
- **jockey_stats**: Jockey performance by period
- **trainer_jockey_combos**: Partnership statistics

#### ML Pipeline
- **ml_features**: Feature vectors (83 columns per runner)
- **ml_targets**: Target labels (position, won, placed)

#### Market Data
- **runner_odds**: Individual bookmaker odds
- **runner_market_odds**: Aggregated market odds

### Database Maintenance

**Rebuild Database** (if needed):
```bash
cd Datafetch
# GUI: Tab 2 → "Complete Database Rebuild"
# This fetches 999 days of historical data (30-45 minutes)
```

**Regenerate Features**:
```bash
cd Datafetch
# GUI: Tab 6 → "Regenerate Features"
# This computes all ML features (10-15 minutes)
```

---

## Implementation History

### Key Milestones

#### October 2025: Production Release
- ✅ Complete 8-tab GUI dashboard
- ✅ 999 days of historical data (43k races)
- ✅ XGBoost ranking model with race grouping
- ✅ Proper probability normalization (softmax)
- ✅ 23 race-context features
- ✅ Combined fetcher (racecards + results)

#### Major Technical Achievements

**1. Target Inversion Fix (Oct 19)**
- **Problem**: Model predicted backwards (Spearman = -0.28)
- **Solution**: Points system (higher = better)
- **Implementation**: `max_position - position + 1`
- **Result**: Proper rankings, positive correlation

**2. Probability Normalization (Oct 19)**
- **Problem**: 9 horses with 27%+ probability (sum ~300%)
- **Solution**: Softmax normalization within races
- **Implementation**: `exp(scores) / sum(exp(scores))`
- **Result**: Valid probabilities summing to 100%

**3. Ranking Model Migration (Oct 19)**
- **Before**: Binary classification (independent predictions)
- **After**: Pairwise ranking with race grouping
- **Improvement**: Model understands race context
- **Metrics**: Top pick win rate 5.6% → 30%+

**4. Foreign Key Constraint Handling (Oct 20)**
- **Problem**: Empty string IDs causing foreign key violations
- **Solution**: Convert empty strings to NULL before insertion
- **Implementation**: `value if value and value.strip() else None`
- **Result**: Clean database with proper relationships

**5. Field Strength Features (Oct 19)**
- **Addition**: 23 new race-context features
- **Categories**: Field strength, draw bias, pace pressure
- **Impact**: Model now understands competitive fields vs weak fields
- **Result**: Better predictions in varied race qualities

**6. Database Rebuild System (Oct 21)**
- **Feature**: Complete database rebuild from scratch
- **Process**: Fetch 999 days in one operation
- **Safety**: Foreign key handling, progress tracking
- **Result**: Clean, consistent database structure

**7. Odds Integration (Oct 20-21)**
- **Implementation**: Hybrid enrichment system
- **Sources**: Racecards (forecast odds) + Results (SP odds)
- **Coverage**: 87% of runners have odds data
- **Usage**: Market comparison and value betting

**8. GUI Optimization (Oct 22)**
- **Worker Threads**: Non-blocking operations
- **Progress Tracking**: Real-time updates
- **Error Handling**: Graceful failures with user feedback
- **Performance**: Smooth UI even during long operations

---

## Troubleshooting

### Common Issues & Solutions

#### "Database not found"
**Solution**: Ensure you're in the `Datafetch/` directory when running the GUI.
```bash
cd /path/to/QE2/Datafetch
python racecard_gui.py
```

#### "Foreign key constraint failed"
**Solution**: This was fixed in recent updates. Ensure you have the latest code.
- Empty string IDs are now converted to NULL
- Foreign key constraints handle missing relationships

#### "No module named 'xgboost'"
**Solution**: Install ML dependencies.
```bash
pip install xgboost scikit-learn scipy numpy pandas
# Or: pip install -r requirements.txt
```

#### Poor Model Performance (Top Pick <20%)
**Diagnosis**:
1. Check database coverage (Tab 1):
   - Need at least 10k races with results
   - Need at least 50% odds coverage
2. Check feature generation (Tab 6):
   - Ensure features regenerated recently
   - Verify no errors in feature generation log
3. Check model training (Tab 7):
   - Ensure using "Flat" race type filter
   - Check Spearman correlation (should be positive)

**Solution**: 
```bash
# Regenerate features and retrain
# Tab 6: Regenerate Features
# Tab 7: Train Model (with "Auto-regenerate" checked)
```

#### Predictions Sum to >100%
**Solution**: This was fixed with softmax normalization.
- Ensure model was trained after Oct 19, 2025
- Retrain model using ranking objective
- Restart GUI to reload predictor module

#### GUI Freezes During Long Operations
**Solution**: Worker threads prevent this, but if it happens:
- Close and restart GUI
- Check for errors in console/log files
- Use smaller date ranges for testing

#### API Rate Limiting Errors
**Solution**: The fetcher respects rate limits (0.55s between requests).
- If still seeing errors, increase delay in code
- Check API subscription status
- Use "Update to Yesterday" for catch-up (not full rebuild)

### Debug Mode

Enable detailed logging:
```bash
cd Datafetch
python racecard_gui.py 2>&1 | tee gui_debug.log
```

Check logs in:
- `gui_debug.log` - GUI operations
- `feature_generation_optimized.log` - Feature generation
- `ml_pipeline_run.log` - Training pipeline

---

## Development

### Running from Source

```bash
cd /path/to/QE2
source venv/bin/activate
cd Datafetch
python racecard_gui.py
```

### Code Style

The project follows standard Python conventions:
```bash
# Format code
black Datafetch/

# Lint code
flake8 Datafetch/

# Type checking (if implemented)
mypy Datafetch/
```

### Testing

```bash
# Run tests (if implemented)
pytest tests/

# Test database connection
cd Datafetch
python -c "import sqlite3; print('OK' if sqlite3.connect('racing_pro.db') else 'FAIL')"

# Test feature generation on small dataset
python -m ml.feature_engineer --test
```

### Shell Scripts (CLI Alternatives)

The repository includes shell scripts for command-line workflows:

```bash
# Train Flat racing model
./RUN_TRAINING.sh

# Rebuild features and train
./rebuild_features_and_train.sh

# Full ML pipeline (automated)
./Datafetch/ml/run_full_pipeline.sh
```

### Jupyter Notebooks

Ad-hoc analysis notebooks:
- `Datafetch/data_pull.ipynb` - Data exploration
- `Datafetch/data_pull_db.ipynb` - Database queries
- `Datafetch/ad_hoc_analysis.ipynb` - Experimental analysis

---

## Project Structure

```
QE2/
├── Datafetch/
│   ├── racecard_gui.py              # GUI entry point
│   ├── racing_pro.db                # Main database (gitignored)
│   ├── upcoming_races.db            # Upcoming races (gitignored)
│   │
│   ├── gui/                         # GUI components
│   │   ├── dashboard_window.py      # Main window with tab navigation
│   │   ├── dashboard_view.py        # Dashboard tab
│   │   ├── data_fetch_view.py       # Database update tab
│   │   ├── upcoming_races_view.py   # Upcoming races tab
│   │   ├── racecard_view.py         # Racecard viewer tab
│   │   ├── data_exploration_view.py # Data exploration tab
│   │   ├── ml_features_view.py      # ML features tab
│   │   ├── ml_training_view.py      # ML training tab
│   │   ├── predictions_view.py      # Predictions tab
│   │   ├── combined_fetcher_worker.py  # Background fetcher
│   │   ├── feature_regen_worker.py  # Feature generation worker
│   │   ├── training_worker.py       # Model training worker
│   │   ├── prediction_worker.py     # Prediction worker
│   │   └── styles.py                # UI styling
│   │
│   ├── ml/                          # Machine learning pipeline
│   │   ├── feature_engineer.py      # 23 feature computation
│   │   ├── train_baseline.py        # XGBoost ranking trainer
│   │   ├── predictor.py             # Prediction generation
│   │   ├── form_parser.py           # Form string parsing
│   │   ├── compute_stats.py         # Career statistics
│   │   ├── build_ml_dataset.py      # Dataset orchestration
│   │   ├── models/                  # Trained models (gitignored)
│   │   │   ├── xgboost_flat.json    # Flat racing model
│   │   │   ├── feature_columns.json # Feature list
│   │   │   └── feature_importance.csv  # Feature rankings
│   │   └── run_full_pipeline.sh     # Automated pipeline
│   │
│   ├── fetch_racecards_pro.py       # Core racecard fetcher
│   ├── fetch_historical_results.py  # Historical results fetcher
│   ├── query_racecards.py           # CLI query tool
│   ├── check_rpr_ts_coverage.py     # Diagnostic tool
│   ├── enrich_odds_from_results.py  # Odds enrichment utility
│   │
│   ├── reqd_files/
│   │   └── cred.txt                 # API credentials (gitignored)
│   │
│   ├── csv_exports/                 # CSV exports (optional)
│   │   ├── course_names.csv
│   │   └── example_csv.csv
│   │
│   ├── data_pull.ipynb              # Data exploration notebook
│   ├── data_pull_db.ipynb           # Database queries notebook
│   └── ad_hoc_analysis.ipynb        # Analysis notebook
│
├── docs/                            # Detailed documentation
│   ├── GUI_COMPLETE_GUIDE.md        # Tab-by-tab GUI reference
│   ├── ML_PIPELINE_COMPLETE_GUIDE.md  # ML technical deep dive
│   ├── WORKFLOWS.md                 # Diagrams and workflows
│   └── ML_GUI_TESTING_GUIDE.md      # QA procedures
│
├── requirements.txt                 # Python dependencies
├── setup.py                         # Package setup
├── openapi.json                     # API specification
├── README.md                        # This file
│
├── RUN_TRAINING.sh                  # CLI training script
├── rebuild_features_and_train.sh   # CLI rebuild script
│
└── venv/                            # Virtual environment (gitignored)
```

### Key Files

**Entry Points**:
- `Datafetch/racecard_gui.py` - Launch GUI application
- `Datafetch/fetch_racecards_pro.py` - CLI data fetcher
- `Datafetch/ml/train_baseline.py` - CLI model trainer

**Core Logic**:
- `Datafetch/gui/dashboard_window.py` - Main application window
- `Datafetch/ml/feature_engineer.py` - Feature engineering
- `Datafetch/ml/train_baseline.py` - Model training
- `Datafetch/ml/predictor.py` - Prediction generation

**Documentation**:
- `README.md` - This comprehensive guide
- `docs/GUI_COMPLETE_GUIDE.md` - Detailed GUI reference
- `docs/ML_PIPELINE_COMPLETE_GUIDE.md` - ML technical details
- `docs/WORKFLOWS.md` - Visual workflows

---

## Common Workflows

### Daily Update

```bash
# Open GUI → Tab 2: Database Update → "Update to Yesterday"
# Automatically fetches new racecards and results since last update
```

### Retrain Model with New Data

```bash
# Tab 7: ML Training → Check "Auto-regenerate" → "Start Training"
# Regenerates features + trains model in one operation
```

### Generate Predictions

```bash
# Tab 3: Upcoming Races → Fetch tomorrow's races
# Tab 8: Predictions → Select race → Generate predictions → View probabilities
```

### Analyze Performance

```bash
# Tab 5: Data Exploration → View coverage statistics
# Tab 7: ML Training → Check feature importance
# Tab 8: Predictions → Compare predictions to results (after races run)
```

---

## Security Notes

- **API credentials**: Never commit `cred.txt` to version control
- **Database files**: `.db` files are gitignored (contain racing data)
- **Model files**: Trained models in `ml/models/` are gitignored
- **Logs**: Log files (`.log`) are gitignored

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## Acknowledgments

- **The Racing API** for comprehensive UK racing data
- **XGBoost** team for the powerful ranking framework
- **PySide6** for the beautiful GUI framework

---

## Support

For issues related to:
- **API Access**: Contact The Racing API support
- **Code/Bugs**: Open an issue in this repository
- **Feature Requests**: Open an issue with the "enhancement" label
- **Questions**: Check documentation or open a discussion

---

## Changelog

### Recent Updates (October 2025)

- ✅ XGBoost ranking model with race grouping
- ✅ 23 race-context features (field strength, draw bias, pace)
- ✅ Foreign key constraint handling for empty IDs
- ✅ Combined fetcher for racecards + results
- ✅ Softmax probability normalization
- ✅ Points system for target inversion
- ✅ Comprehensive GUI with 8 tabs
- ✅ 999 days of historical data (43k races)
- ✅ Odds integration (87% coverage)
- ✅ Database rebuild system
- ✅ Worker threads for non-blocking operations

---

**Built with ❤️ for horse racing enthusiasts and data scientists**
