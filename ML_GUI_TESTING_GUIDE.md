# ML GUI Tabs - Testing Guide

## New Features Added

Two new tabs have been added to the Racing Data Dashboard GUI:

### 1. 🔬 ML Features Tab
**Location**: Navigation ribbon → "ML Features" button

**Features**:
- **Statistics Tab**: Shows summary statistics for all 44 ML features
  - Feature name, count, missing %, mean, std, min, max
  - Export to CSV functionality
  - Calculated on demand (lazy loading)

- **Sample Data Tab**: Browse actual feature vectors with pagination
  - Shows race_id, horse name, and key features
  - Search by horse name or race ID
  - 50 rows per page with next/previous navigation
  - Double-click any row to see all 44 features

- **Quality Metrics Tab**: Data quality dashboard
  - Total feature vectors count
  - Features with results count
  - Date range coverage
  - Feature completeness by category (Horse, Trainer, Jockey, etc.)
  - Progress bars showing completeness percentages

### 2. 🚀 Model Training Tab
**Location**: Navigation ribbon → "Model Training" button

**Features**:
- **Left Panel** - Model Configuration:
  - Model selector dropdown (XGBoost Winner Classifier active, others coming soon)
  - Detailed model explanation with:
    - Algorithm description
    - How it works
    - Pros and cons
    - Use cases
    - Feature categories used
  - Configuration options:
    - Test size slider (10-30%, default 20%)
    - Random seed input (default 42)
  - Train Model button
  - View Saved Models button

- **Right Panel** - Training Results:
  - Real-time training log (monospace font, terminal-style)
  - Results display after training:
    - Key metrics table (accuracy, precision, recall, F1, AUC, log loss)
    - Top 10 important features
    - View full results button
  - Model saved location displayed

## Testing Steps

### Prerequisites
1. Ensure ML features have been generated:
   ```bash
   cd /Users/darcy5d/Desktop/DD_AI_models/QE2/Datafetch
   python ml/monitor_progress.py  # Check if features exist
   ```

2. If no features exist, run:
   ```bash
   python ml/feature_engineer.py
   ```

### Test ML Features Tab

1. **Launch GUI**:
   ```bash
   cd /Users/darcy5d/Desktop/DD_AI_models/QE2/Datafetch
   python racecard_gui.py
   ```

2. **Click "🔬 ML Features" button** in the navigation ribbon

3. **Test Statistics Tab**:
   - Wait for statistics to load (should take 5-10 seconds)
   - Verify table shows all features with statistics
   - Click "Export to CSV" and save a file
   - Verify CSV contains correct data

4. **Test Sample Data Tab**:
   - Should show first 50 feature vectors
   - Try searching for a horse name
   - Click "Next" to navigate pages
   - Click "Previous" to go back
   - Double-click a row to see all features
   - Clear search and verify results reset

5. **Test Quality Metrics Tab**:
   - Verify metric cards show correct counts
   - Check date range is correct
   - Verify completeness bars show percentages
   - All bars should be green and show high percentages (>80%)

### Test Model Training Tab

1. **Click "🚀 Model Training" button** in the navigation ribbon

2. **Review Model Information**:
   - Verify XGBoost Winner Classifier is selected
   - Read the model explanation
   - Verify feature categories are listed

3. **Configure Training**:
   - Adjust test size slider (try 25%)
   - Change random seed if desired
   - Note: "Coming Soon" models should be disabled

4. **Train Model**:
   - Click "🚀 Train Model" button
   - Button should change to "Training..." and disable
   - Watch real-time log output in right panel
   - Training should take 1-2 minutes
   - Verify no errors in log

5. **Review Results**:
   - After training completes, verify:
     - Success message dialog appears
     - Metrics table shows all values
     - Top 10 features table displays
     - "View Full Results" button appears
   - Click "View Full Results" to see JSON output
   - Verify model saved location is shown

6. **View Saved Models**:
   - Click "📁 View Saved Models" button
   - Verify model appears in list with size and timestamp
   - Close dialog

## Expected Results

### Data Volume
- **Feature Vectors**: ~39,494 (one per runner)
- **Features**: 44 total
- **Races**: ~3,759 with results
- **Date Range**: 2023-01-23 to 2023-04-30

### Model Performance (XGBoost Winner)
- **Accuracy**: ~85-92% (most horses don't win)
- **Precision**: ~0.25-0.35 (of predicted winners, how many actually won)
- **Top Pick Win Rate**: ~25-35% (better than ~10% random baseline)
- **Top 3 Hit Rate**: ~50-65%
- **Training Time**: 1-2 minutes

### Feature Importance (Expected Top Features)
- `ofr` (Official Rating)
- `horse_win_rate`
- `horse_avg_position`
- `trainer_win_rate_90d`
- `jockey_win_rate_90d`
- `field_size`
- `distance_f`

## Troubleshooting

### "No ML features found" message
- Run: `python ml/feature_engineer.py`
- Check: `python ml/monitor_progress.py`

### Training fails with import error
- Install dependencies: `pip install xgboost scikit-learn pandas numpy`
- Or: `pip install -r ml/requirements_ml.txt`

### GUI freezes during training
- Training runs in background thread - should not freeze
- If it does, check console for errors
- May need to restart GUI

### Database locked error
- Ensure no other processes are using the database
- Close and reopen GUI
- Check: `lsof Datafetch/racing_pro.db`

### Statistics take too long to load
- Normal for first load (5-15 seconds)
- Cached after first load
- Refresh button forces recalculation

## Performance Notes

- **Lazy Loading**: Statistics only load when tab is opened
- **Pagination**: Sample data limited to 50 rows at a time
- **Background Training**: Model training runs in separate thread
- **Memory Usage**: Should be < 500MB during normal operation
- **Training Memory**: May spike to 1-2GB during model training

## Files Created

1. `Datafetch/gui/ml_database_helper.py` - Database query functions
2. `Datafetch/gui/ml_features_view.py` - ML Features tab
3. `Datafetch/gui/training_worker.py` - Background training thread
4. `Datafetch/gui/ml_training_view.py` - Model Training tab
5. `Datafetch/gui/nav_ribbon.py` - Updated with new buttons
6. `Datafetch/gui/dashboard_window.py` - Integrated new views

## Next Steps

After successful testing:
1. Train your first model and save it
2. Explore feature importance to understand predictions
3. Test on upcoming races (when that functionality is added)
4. Experiment with different model configurations
5. Compare multiple trained models

## Known Limitations

1. Only XGBoost Winner Classifier is currently implemented
2. Cannot modify feature selection (uses all 44 features)
3. Cannot tune hyperparameters from GUI (uses defaults)
4. No visualization of ROC curves or confusion matrix
5. No real-time prediction on upcoming races yet

These will be addressed in future updates.


