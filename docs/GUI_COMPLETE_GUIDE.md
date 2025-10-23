# GUI Complete Guide - Racing Data Dashboard

Comprehensive guide to all 8 tabs in the QE2 Racing Data Dashboard. Each tab serves a specific purpose in the data pipeline from fetching raw data to generating ML predictions.

## Table of Contents

1. [Dashboard (Home)](#tab-1-dashboard-home)
2. [Database Update](#tab-2-database-update)
3. [Upcoming Races](#tab-3-upcoming-races)
4. [Racecard Viewer](#tab-4-racecard-viewer)
5. [Data Exploration](#tab-5-data-exploration)
6. [ML Features](#tab-6-ml-features)
7. [ML Training](#tab-7-ml-training)
8. [Predictions](#tab-8-predictions)

---

## Tab 1: Dashboard (Home)

**File**: `Datafetch/gui/dashboard_view.py`

### Purpose

Provides a high-level overview of your database status and serves as the navigation hub for the application. First thing you see when launching the GUI.

### Features

#### Stats Cards
- **Races Count**: Total number of races in database
- **Runners Count**: Total runners across all races
- **Results Count**: Completed race results with positions
- **Coverage %**: Percentage of races that have results

#### Date Coverage
- **Earliest Race**: First race date in database
- **Latest Race**: Most recent race date in database
- **Days of Data**: Total unique racing days

#### Quick Navigation
- **View Racecards**: Jump to Racecard Viewer
- **Fetch Data**: Jump to Database Update
- **Train Model**: Jump to ML Training
- **Make Predictions**: Jump to Predictions

### When to Use

- **On startup**: Check database health before working
- **After updates**: Verify new data was added correctly
- **Data quality check**: Ensure coverage % is high (>95%)
- **Quick navigation**: Jump to specific tabs

### What Good Data Looks Like

```
Races: 43,037
Runners: 455,242
Results: 395,463
Coverage: 95.9%

Date Range: 2023-01-23 to 2025-10-18
Days of Data: 999
```

If coverage is <90%, consider running database update to backfill missing results.

---

## Tab 2: Database Update

**File**: `Datafetch/gui/data_fetch_view.py`  
**Worker**: `Datafetch/gui/combined_fetcher_worker.py`

### Purpose

Fetch racecards and results from The Racing API and populate your SQLite database. This is the **data ingestion** step of the pipeline.

### Features

#### Update to Yesterday (Recommended)
- **One-click solution**: Fetches all missing data from 2023-01-23 to yesterday
- **Smart detection**: Only fetches dates not already in database
- **Two-phase process**:
  1. **Phase 1: Racecards** - Race info, runners, horses, trainers, jockeys, owners
  2. **Phase 2: Results** - Positions, times, starting prices, prize money
- **Progress tracking**: Shows "Fetching X/Y races" with phase indicator
- **Rate limiting**: Automatically sleeps between requests (0.55s)

#### Custom Date Range
- **Start Date**: Pick specific date to begin from
- **End Date**: Pick specific date to end at
- **Use case**: Backfilling specific date ranges, testing with small datasets

#### Progress Display
```
Phase 1: Racecards
Fetching racecard: 2024-10-15
Progress: 150/200

Phase 2: Results
Fetching results: 25/50
```

### When to Use

#### First Time Setup
Run "Update to Yesterday" to fetch full historical database (~20-30 minutes for 43k races)

#### Daily Maintenance
Run "Update to Yesterday" each day to get previous day's results (~1-2 minutes)

#### Backfilling
Use custom date range if you have gaps in historical data

#### After API Fixes
If API had issues and some dates failed, re-run to catch missed races

### How It Works

```
User clicks "Update to Yesterday"
    ↓
CombinedFetcherWorker starts in background thread
    ↓
Query database for existing dates
    ↓
Generate list of missing dates (2023-01-23 to yesterday)
    ↓
FOR EACH missing date:
    Fetch /v1/racecards/pro?date=YYYY-MM-DD
    Parse JSON response
    Insert: races, horses, trainers, jockeys, owners, runners
    Sleep 0.55s (rate limiting)
    ↓
Query races without results
    ↓
FOR EACH race without results:
    Fetch /v1/results/{race_id}
    Parse JSON response
    Insert: results (positions, times, SP, etc.)
    Sleep 0.55s (rate limiting)
    ↓
Optimize database (VACUUM, ANALYZE)
    ↓
Emit finished signal with counts
    ↓
GUI displays: "Complete! Added X races, Y runners, Z results"
```

### Foreign Key Handling

The combined fetcher includes robust handling for:
- **Empty jockey IDs**: Converts `""` → `NULL` (common for races days away)
- **Empty trainer IDs**: Converts `""` → `NULL` (rare but happens)
- **Empty owner IDs**: Converts `""` → `NULL`
- **Missing entities in results**: Inserts horses/trainers/jockeys/owners before results

This prevents "FOREIGN KEY constraint failed" errors.

### Troubleshooting

**"No new data found"**: Database is already up to date
**"API Error 401"**: Check your credentials in `Datafetch/reqd_files/cred.txt`
**"API Error 429"**: Rate limit hit - wait a minute and try again
**"Foreign key constraint failed"**: Ensure you have latest code (fixed in Oct 2025)

---

## Tab 3: Upcoming Races

**File**: `Datafetch/gui/upcoming_races_view.py`  
**Worker**: `Datafetch/gui/upcoming_fetcher.py`

### Purpose

View and fetch racecards for **future races** (tomorrow, next week, etc.). Essential for generating predictions on upcoming events.

### Features

#### Date Selection
- **Calendar picker**: Choose any future date
- **Default**: Tomorrow's races
- **Range**: Typically 7-14 days ahead available from API

#### Race Listing
- **Course**: Race venue (e.g., "Ascot", "Cheltenham")
- **Time**: Off time (e.g., "14:30")
- **Race Name**: Official race title
- **Distance**: In furlongs or meters
- **Type**: Flat, Hurdle, Chase, NHF

#### Fetch Button
- Fetches racecards for selected date
- Stores in `upcoming_races.db` (separate from main database)
- Required before generating predictions

### When to Use

#### Before Making Predictions
1. Come to this tab
2. Select tomorrow (or target date)
3. Click "Fetch Races"
4. Wait for completion
5. Go to Tab 8 (Predictions) to generate predictions

#### Planning Ahead
- Fetch multiple days in advance
- Check race schedule for big events
- See field sizes and horses declared

### Data Storage

Upcoming races are stored in `Datafetch/upcoming_races.db` (separate database) because:
- They don't have results yet (can't go in main DB)
- Want to keep them isolated until races complete
- After race completes, use Tab 2 to fetch results into main DB

### Workflow Example

```
1. October 18 evening: Fetch October 19 races
2. October 18 evening: Generate predictions for October 19
3. October 19 evening: Run "Update to Yesterday" to get October 19 results
4. October 19 evening: Regenerate features and retrain model with new data
5. October 19 evening: Fetch October 20 races
6. October 19 evening: Generate predictions for October 20
```

---

## Tab 4: Racecard Viewer

**File**: `Datafetch/gui/main_window.py`, `race_list_view.py`, `racecard_view.py`

### Purpose

Browse, filter, and analyze historical racecards stored in your main database. Great for exploring data, checking specific races, and understanding what information is available.

### Features

#### Left Panel: Filters
- **Date Range**: From/to date pickers
- **Course**: Filter by venue (e.g., "Ascot")
- **Region**: UK, IRE, or All
- **Race Type**: Flat, Jumps, or All
- **Class**: Race quality (Class 1-7)
- **Distance**: Furlong range
- **Going**: Ground conditions (Firm, Good, Soft, Heavy)

#### Middle Panel: Race List
- Shows all races matching filters
- Displays: Date, Time, Course, Race Name, Distance, Surface
- Click race to view full racecard

#### Right Panel: Racecard Details
- **Race Info**: Course, date, time, distance, going, prize, class
- **Runners Table**: All horses in race with:
  - Number, Draw
  - Horse name (click for profile)
  - Age, Weight carried
  - Trainer name (click for profile)
  - Jockey name (click for profile)
  - Owner name (click for profile)
  - RPR, TSR, OFR ratings
  - Form string (recent finishes)
  - Days since last run

### When to Use

#### Exploring Data
- See what races you have in database
- Check data quality for specific courses
- Find races with interesting fields

#### Research
- Look up how a specific horse performed
- Check trainer/jockey statistics
- Analyze form trends

#### Debugging
- Verify data fetched correctly
- Check for missing fields
- Validate foreign key relationships

### Entity Profiles

Clicking on any horse, trainer, jockey, or owner opens their profile view showing:
- **Summary stats**: Runs, wins, places, win %
- **Recent form**: Last 20 runs with positions and dates
- **Performance breakdown**: By distance, going, course, etc.

---

## Tab 5: Data Exploration

**File**: `Datafetch/gui/data_exploration_view.py`

### Purpose

Run SQL queries and perform statistical analysis on your database. Power-user feature for data scientists and analysts.

### Features

#### Query Builder
- Pre-built query templates
- Custom SQL input
- Result display in tables
- Export to CSV

#### Statistical Analysis
- **Course statistics**: Win rates, field sizes, distances
- **Trainer statistics**: Performance by venue, distance, going
- **Jockey statistics**: Strike rates, courses ridden
- **Horse statistics**: Career records, optimal conditions

#### Data Quality Checks
- Missing data counts
- Foreign key integrity
- Date range gaps
- Unusual values (outliers)

### When to Use

#### Data Quality Assurance
- Check for missing RPR/TSR values
- Verify all races have results
- Find duplicate records

#### Analysis
- Which trainers win most at Ascot?
- How do horses perform on soft going vs firm?
- What's the average field size by race class?

#### Feature Research
- Explore potential new features for ML model
- Understand data distributions
- Identify biases or patterns

### Example Queries

```sql
-- Races missing results
SELECT COUNT(*) FROM races 
WHERE race_id NOT IN (SELECT DISTINCT race_id FROM results);

-- Top trainers by win rate (min 100 runs)
SELECT t.name, COUNT(*) as runs, 
       SUM(CASE WHEN r.position = '1' THEN 1 ELSE 0 END) as wins,
       ROUND(100.0 * SUM(CASE WHEN r.position = '1' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_pct
FROM results r
JOIN trainers t ON r.trainer_id = t.trainer_id
GROUP BY t.trainer_id, t.name
HAVING COUNT(*) >= 100
ORDER BY win_pct DESC
LIMIT 20;

-- Average field size by race class
SELECT race_class, AVG(field_size) as avg_field, COUNT(*) as races
FROM races
WHERE race_class IS NOT NULL
GROUP BY race_class
ORDER BY race_class;
```

---

## Tab 6: ML Features

**File**: `Datafetch/gui/ml_features_view.py`  
**Worker**: `Datafetch/gui/feature_regen_worker.py`  
**Engine**: `Datafetch/ml/feature_engineer.py`

### Purpose

Generate machine learning features from raw race data. Transforms database records into the 23 features used by the XGBoost model.

### Features

#### Regenerate Features Button
- Processes all races that have results
- Computes 23 features per runner
- Saves to `ml_features` table in database
- Progress tracking: "Processing race X/Y"

#### Feature Statistics
- **Total features**: Should be ~9.5× number of results
- **Date coverage**: Earliest and latest feature dates
- **Missing features**: Races with results but no features

#### Feature List Display
Shows all 23 computed features:
1. RPR, TSR, OFR (ratings)
2. Days since last run
3. Horse age
4. Weight carried (lbs)
5. Draw position
6. Form points (recent finishes)
7. Best RPR in field
8. Worst RPR in field
9. Average RPR in field
10. RPR spread (best - worst)
11. Top 3 avg RPR
12. Horse RPR rank
13. Horse RPR vs best
14. Horse RPR vs worst
15. Horse in top quartile (binary)
16. Pace pressure
17. Jockey rating vs field avg
18. Trainer rating vs field avg
19. Weight rank
20. Age rank
21. Draw bias (historical win rate by draw)
22. Running style (parsed from form)
23. TSR trend

### When to Use

#### First Time Setup
After fetching database, regenerate features before training model (~10-15 minutes for 390k features)

#### After Database Updates
Whenever you add new results, regenerate features to include them in training

#### After Schema Changes
If ml_features table structure changes, regenerate all features

#### Before Retraining
Can use "Auto-regenerate" checkbox in Tab 7 to do this automatically

### How It Works

```
FeatureEngineer.generate_features_for_all_races()
    ↓
Query all races with results
    ↓
FOR EACH race:
    Query all runners in race
    FOR EACH runner:
        Basic features: RPR, TSR, form, weight, age, draw
        ↓
    Compute relative features (requires all runners):
        Field strength: best/worst/avg RPR, spread, ranks
        Weight/age ranks within field
        Jockey/trainer ratings vs field avg
        ↓
    Compute draw bias:
        Query historical win rates by draw at this course/distance
        ↓
    Compute pace features:
        Parse running style from form string
        Calculate TSR trends
        Pace pressure based on field dynamics
        ↓
    Save all features to ml_features table
    ↓
Emit progress signal (for GUI update)
    ↓
Complete
```

### Feature Engineering Details

See **[ML Pipeline Complete Guide](ML_PIPELINE_COMPLETE_GUIDE.md)** for detailed explanation of how each feature is calculated.

### Troubleshooting

**"No results found"**: Run Tab 2 (Database Update) first
**Very slow**: Normal for first run with 41k races. Subsequent runs only process new races.
**Missing features**: Some runners may not have RPR/TSR values - features will be NULL

---

## Tab 7: ML Training

**File**: `Datafetch/gui/ml_training_view.py`  
**Worker**: `Datafetch/gui/training_worker.py`  
**Trainer**: `Datafetch/ml/train_baseline.py`

### Purpose

Train the XGBoost ranking model on historical race data. Evaluates performance on test set and saves model for predictions.

### Features

#### Training Controls
- **Auto-regenerate Features**: Checkbox to regenerate features before training
- **Test Split**: Temporal split (80% train on older, 20% test on newer)
- **Start Training**: Button to begin training process

#### Progress Display
- **Status messages**: "Loading data...", "Training model...", "Evaluating..."
- **Progress bar**: Training progress (epochs/iterations)
- **Time estimates**: Approximate time remaining

#### Evaluation Metrics (Ranking)
- **Top Pick Win Rate**: % of races where highest-ranked horse won
- **Top 3 Hit Rate**: % of races where actual winner in model's top 3
- **NDCG@3**: Normalized Discounted Cumulative Gain at position 3
- **MRR**: Mean Reciprocal Rank of actual winners
- **Spearman Correlation**: Rank agreement between predicted and actual

#### Evaluation Metrics (Binary - Legacy)
- Accuracy, Precision, Recall, F1, AUC (if using old binary model)

#### Feature Importance Table
- **Feature name**: Which feature
- **Importance score**: Relative importance (gain)
- **Sorted**: Most important features at top

#### Model Explanation
- **Model type**: XGBoost Ranking Model
- **Objective**: rank:pairwise (pairwise ranking)
- **Key features**: Race grouping, points system, softmax probabilities

### When to Use

#### First Time Setup
After generating features, train initial model (~3-5 minutes)

#### After Significant Data Updates
When you've added months of new data, retrain to improve model

#### Model Experimentation
Test different hyperparameters or feature sets

#### Regular Maintenance
Retrain weekly/monthly as new results accumulate

### Training Process

```
1. Auto-regenerate? → Generate features if checkbox checked
2. Load data from ml_features + results tables
3. Temporal split:
   - Find date that splits data 80/20
   - Train on races before split date
   - Test on races after split date
4. Convert positions to points:
   - Position 1 (winner) gets max_position points
   - Position 2 gets max_position - 1 points
   - Last place gets 1 point
   - Ensures winner = highest value for ranking
5. Create race groups:
   - Tell XGBoost which runners are in same race
   - Critical for ranking objective
6. Train XGBoost:
   - Objective: rank:pairwise
   - Eval metric: ndcg@3
   - ~500-1000 iterations
7. Evaluate on test set:
   - Rank runners within each race
   - Compare to actual positions
   - Calculate metrics
8. Save model:
   - Save to Datafetch/ml/models/xgboost_baseline.json
   - Save feature columns to feature_columns.json
   - Save feature importance to feature_importance.csv
9. Display results in GUI
```

### Understanding Metrics

#### Top Pick Win Rate: 32%
Model's #1 ranked horse wins 32% of races. For 10-horse race, random guess = 10%, so model is 3.2× better than random.

#### Top 3 Hit Rate: 72%
Actual winner appears in model's top 3 picks 72% of the time. Very good for covering multiple horses.

#### NDCG@3: 0.63
Ranking quality score 0-1. Higher = better. 0.63 means model is good at putting winners near top.

#### Spearman: 0.35
Correlation between predicted ranks and actual ranks. 0.35 is solid for horse racing (high variance sport).

### Model Explanation

**Why Ranking vs Classification?**

Old approach: Train binary classifier for each horse independently.
Problem: Predictions don't consider horses compete together. Can get 9 horses at 27% win probability.

New approach: Train ranking model that understands race context.
Benefit: Probabilities properly normalized (sum to 100%), better reflects competition.

**How Does It Work?**

1. XGBoost rank:pairwise learns to compare pairs of horses in same race
2. Race grouping tells model which horses compete together
3. Points system ensures winner > second > third in training signal
4. At prediction time, get ranking scores (higher = better)
5. Softmax converts scores to probabilities (automatically sum to 100%)

### Troubleshooting

**"No features found"**: Run Tab 6 (ML Features) first
**"Training failed"**: Check logs in Datafetch/ml_pipeline_run.log
**Poor metrics**: May need more data or better feature engineering
**Out of memory**: Reduce data size or use smaller test split

---

## Tab 8: Predictions

**File**: `Datafetch/gui/predictions_view.py`  
**Worker**: `Datafetch/gui/prediction_worker.py`  
**Predictor**: `Datafetch/ml/predictor.py`

### Purpose

Generate win probability predictions for upcoming races using the trained XGBoost model. The end goal of the entire pipeline!

### Features

#### Race Selection
- **Date picker**: Choose date of upcoming races
- **Race dropdown**: Select specific race from that date
- **Race details**: Shows course, time, distance, going

#### Generate Predictions Button
- Loads trained model
- Generates features for all runners in race
- Ranks runners and converts to win probabilities
- Displays results in table

#### Predictions Table
| Rank | Horse | Probability | Confidence | Trainer | Jockey | RPR |
|------|-------|-------------|------------|---------|--------|-----|
| 1 | Star Runner | 28.5% | Strong Pick | J. Smith | R. Moore | 125 |
| 2 | Fast Horse | 18.2% | Good Chance | M. Jones | W. Buick | 120 |
| 3 | Third Place | 14.7% | Decent | A. Brown | J. Doyle | 118 |

#### Confidence Indicators
- **Strong Pick**: Probability > 20% (clear favorite)
- **Good Chance**: Probability > 15% (solid contender)
- **Decent**: Probability > 10% (worth considering)
- **Longshot**: Probability < 10% (outsider)

#### Probability Visualization
- Color-coded bars showing relative probabilities
- Green = Strong pick, Yellow = Good chance, Blue = Decent

#### Export Options
- Export predictions to CSV
- Save for later analysis or betting records

### When to Use

#### Daily Predictions
1. Evening before race day: Fetch tomorrow's races (Tab 3)
2. Generate predictions for each race
3. Review probabilities and value bets
4. Export for record keeping

#### Value Betting
- Compare model probabilities to bookmaker odds
- Look for discrepancies (model 25%, bookie offers 5/1 = 16.7%)
- Identify value bets where model thinks horse is underpriced

#### Research
- See how model evaluates different horses
- Understand which features drive predictions
- Test model on historical races (if fetched as "upcoming")

### How It Works

```
User selects race from upcoming_races.db
    ↓
PredictionWorker starts in background
    ↓
Load trained model (xgboost_baseline.json)
    ↓
Load runner data from upcoming race
    ↓
Generate features for each runner:
    - Basic: RPR, TSR, form, weight, age, draw
    - Relative: Field strength, ranks, vs best/worst
    - Draw bias: Historical win rates for this course/distance
    - Pace: Running style, TSR trends
    ↓
Create feature matrix (n_runners × 23 features)
    ↓
Model predicts ranking scores (higher = better)
    ↓
Apply softmax: scores → probabilities
    prob_i = exp(score_i) / sum(exp(score_j) for all j)
    ↓
Probabilities automatically sum to 100%
    ↓
Sort by probability (highest first)
    ↓
Assign confidence levels based on thresholds
    ↓
Display in GUI table
```

### Understanding Probabilities

#### Example Race (10 horses)

```
1. Horse A: 28.5%  ← Strong favorite
2. Horse B: 18.2%  ← Second choice
3. Horse C: 14.7%  ← Third choice
4. Horse D: 10.1%  ← Decent chance
5. Horse E: 8.3%   ← Outsider
6. Horse F: 6.9%   ← Longshot
7. Horse G: 5.2%   ← Longshot
8. Horse H: 3.8%   ← Longshot
9. Horse I: 2.7%   ← Longshot
10. Horse J: 1.6%  ← Longshot

Total: 100.0% ✓
```

**Key Points:**
- Probabilities sum to 100% (guaranteed by softmax)
- Reflects relative strength within this specific field
- Not independent probabilities - they depend on competition
- Higher field quality = more even distribution
- Lower field quality = stronger favorite

### Value Betting Example

```
Model Prediction: Horse A = 28.5% win probability
Bookmaker Odds: 5/2 = 2.5 odds = 1/(2.5+1) = 28.6% implied probability

→ No value (roughly equal)

Model Prediction: Horse B = 18.2% win probability  
Bookmaker Odds: 7/1 = 7.0 odds = 1/(7+1) = 12.5% implied probability

→ VALUE BET! Model thinks 18.2%, market only 12.5%
```

### Confidence Levels

**Strong Pick (>20%)**
- Clear favorite in model's view
- Significantly better than field average (10%)
- Often but not always matches market favorite
- Win rate: ~25-30% when model gives >20%

**Good Chance (15-20%)**
- Solid contender
- Could win but not overwhelming favorite
- Worth considering for place bets
- Win rate: ~12-15% when model gives 15-20%

**Decent (10-15%)**
- Around field average
- Potential for upset
- Each-way possibilities
- Win rate: ~8-10% when model gives 10-15%

**Longshot (<10%)**
- Outsider in model's view
- Would need things to go their way
- High variance plays
- Win rate: ~4-6% when model gives 5-10%

### Troubleshooting

**"No model found"**: Train model first in Tab 7
**"No races available"**: Fetch upcoming races in Tab 3
**"Feature generation failed"**: Check if race has required data (RPR, TSR, etc.)
**Probabilities seem off**: Retrain model with latest data
**All horses similar probability**: Weak field or missing key features (RPR/TSR)

---

## Complete Workflow: From Setup to Predictions

### First Time User

```
1. Install & Setup (5 mins)
   - Clone repo, create venv, install requirements
   - Add API credentials

2. Launch GUI (Datafetch/racecard_gui.py)
   - Tab 1: Dashboard - Check it's empty (expected)

3. Fetch Historical Data (20-30 mins)
   - Tab 2: Database Update
   - Click "Update to Yesterday"
   - Wait for Phase 1 (Racecards) + Phase 2 (Results)
   - Dashboard now shows 43k races

4. Generate ML Features (10-15 mins)
   - Tab 6: ML Features
   - Click "Regenerate Features"
   - Wait for ~390k features to be computed

5. Train Model (3-5 mins)
   - Tab 7: ML Training
   - Click "Start Training" (Auto-regenerate unchecked)
   - Wait for training and evaluation
   - Review metrics: Top Pick Win Rate ~30-35%

6. Fetch Upcoming Races (1 min)
   - Tab 3: Upcoming Races
   - Select tomorrow's date
   - Click "Fetch Races"

7. Generate Predictions (30 seconds per race)
   - Tab 8: Predictions
   - Select race from dropdown
   - Click "Generate Predictions"
   - View probabilities and confidence levels

Total time: ~40-50 minutes for complete setup
```

### Daily User

```
1. Launch GUI

2. Update Database (1-2 mins)
   - Tab 2: Database Update
   - Click "Update to Yesterday"
   - Gets previous day's results

3. Retrain Model (10-15 mins, weekly)
   - Tab 7: ML Training
   - Check "Auto-regenerate"
   - Click "Start Training"
   - Only needed when significant new data added

4. Fetch Tomorrow's Races (1 min)
   - Tab 3: Upcoming Races
   - Select tomorrow
   - Click "Fetch"

5. Generate Predictions (5-10 mins for all races)
   - Tab 8: Predictions
   - For each race: select, predict, export

Total time: 2-3 minutes daily, 15-20 minutes on retrain days
```

---

## Tips & Best Practices

### Data Quality
- Check Dashboard (Tab 1) regularly for coverage %
- Aim for >95% of races having results
- Gaps in data = gaps in training = worse predictions

### Model Maintenance
- Retrain weekly as new results accumulate
- After major racing festivals (Cheltenham, Royal Ascot), retrain with new data
- Monitor Top Pick Win Rate - should stay 30-35%

### Predictions
- Generate predictions same day or evening before
- Export and save for record keeping
- Compare model vs bookmaker odds to find value
- Don't bet exclusively on model - use as tool alongside other analysis

### Performance
- Database updates fastest off-peak hours
- Feature regeneration is CPU-intensive - let it run overnight
- Training benefits from good CPU (uses all cores)
- Predictions are fast (seconds per race)

### Troubleshooting
- Check `/tmp/gui_debug.log` for errors (Mac/Linux)
- Most issues: wrong working directory (must be in Datafetch/)
- Foreign key errors: Update to latest code (Oct 2025)
- Out of memory: Reduce training data size

---

## Keyboard Shortcuts

- **Esc**: Go back (in Racecard Viewer profile views)
- **Ctrl/Cmd + Q**: Quit application
- **Ctrl/Cmd + R**: Refresh current view
- **Ctrl/Cmd + 1-8**: Jump to tab 1-8 (if configured)

---

## Support & Feedback

For questions, issues, or suggestions:
- Open issue on GitHub: `https://github.com/darcy5d/QE2/issues`
- Check documentation: All .md files in repository
- Review logs: Look for .log files in Datafetch/ directory

---

**Built with PySide6 and lots of coffee ☕**

