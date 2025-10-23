# Database Rebuild Implementation Summary

## What Was Implemented

### Problem Solved

The historical racing database had **only 2.2% odds coverage** because:
- Old fetcher stored odds as raw JSON strings in `runner_odds` table
- New fetcher properly aggregates odds into `runner_market_odds` table
- Migration script only partially converted existing data
- Result: ML model couldn't learn from odds for 97.8% of training data

### Solution

Implemented a complete database rebuild feature that:
1. **Backs up** existing database automatically
2. **Re-fetches** all historical data with proper odds aggregation
3. **Aggregates** odds for every runner (expected 80%+ coverage)
4. **Fetches** results for completed races
5. **Regenerates** ML features with full odds support
6. **Verifies** odds coverage meets quality standards

## Files Created/Modified

### 1. New File: `gui/rebuild_database_worker.py`
**Purpose**: Background worker thread for complete database rebuild

**Key Features**:
- Multi-phase progress tracking (6 phases)
- Automatic backup creation with timestamps
- Fresh schema creation using new format
- Racecard fetching with odds aggregation
- Results fetching for completed races
- Odds coverage verification
- ML feature regeneration
- Comprehensive error handling

**Main Class**:
```python
class RebuildDatabaseWorker(QThread):
    # Signals for GUI updates
    progress_update = Signal(str)
    phase_changed = Signal(str, int)
    item_processed = Signal(int)
    rebuild_complete = Signal(dict)
    rebuild_error = Signal(str)
```

**Phases**:
1. Backup database (~30s)
2. Create fresh schema (~5s)
3. Fetch racecards (~6-7h)
4. Fetch results (~2-3h)
5. Verify odds coverage (~10s)
6. Regenerate features (~25min)

### 2. Modified: `gui/data_fetch_view.py`
**Changes**: Added Option 3 UI and handlers

**UI Components Added**:
- Option 3 group box with warning message
- Date range pickers (start/end date)
- Large red "REBUILD ENTIRE DATABASE" button
- Warning styling (yellow background, border)
- Estimated time display

**Methods Added**:
- `confirm_and_rebuild()` - Shows detailed confirmation dialog
- `start_rebuild()` - Initializes and starts rebuild worker
- `on_rebuild_progress_text()` - Handles text progress updates
- `on_rebuild_phase_changed()` - Handles phase transitions
- `on_rebuild_item_processed()` - Updates progress bar
- `on_rebuild_complete()` - Handles successful completion
- `on_rebuild_error()` - Handles errors

**Confirmation Dialog**:
- Shows date range and day count
- Shows backup filename
- Shows estimated races to fetch
- Lists all operations
- Shows time estimate
- Requires explicit confirmation
- Default = No (safe)

### 3. New File: `DATABASE_REBUILD_GUIDE.md`
**Purpose**: Comprehensive user documentation

**Contents**:
- Overview and rationale
- Step-by-step usage instructions
- Testing recommendations (7-day test first)
- Progress monitoring guide
- Time estimates per phase
- Error recovery procedures
- Post-rebuild verification steps
- Technical details and API info
- FAQ section
- Troubleshooting guide

## How It Works

### Odds Aggregation Logic

The rebuild uses the same logic as `upcoming_fetcher.py`:

```python
def save_runner_odds(cursor, runner_id, odds_data):
    """
    1. Parse each bookmaker's fractional odds (e.g., "5/1")
    2. Convert to decimal (e.g., 6.0)
    3. Store individual odds in runner_odds
    4. Compute aggregates:
       - avg_decimal = mean(all_odds)
       - median_decimal = median(all_odds)
       - min_decimal = best odds
       - max_decimal = worst odds
       - bookmaker_count = count
       - implied_probability = 1.0 / avg_decimal
    5. Store aggregates in runner_market_odds
    6. Update favorite rankings per race
    """
```

### Database Schema

**New Tables**:
```sql
-- Individual bookmaker odds
CREATE TABLE runner_odds (
    odds_id INTEGER PRIMARY KEY,
    runner_id INTEGER,
    bookmaker TEXT,
    fractional_odds TEXT,
    decimal_odds REAL
);

-- Aggregated market odds (for ML)
CREATE TABLE runner_market_odds (
    market_odds_id INTEGER PRIMARY KEY,
    runner_id INTEGER UNIQUE,
    avg_decimal REAL,
    median_decimal REAL,
    min_decimal REAL,
    max_decimal REAL,
    bookmaker_count INTEGER,
    implied_probability REAL,
    is_favorite INTEGER,
    favorite_rank INTEGER,
    updated_at TIMESTAMP
);
```

### Progress Tracking

**Multi-level progress**:
1. Phase-level: Shows which of 6 phases is active
2. Item-level: Shows progress within current phase (e.g., 100/890 dates)
3. Text-level: Detailed status messages
4. Progress bar: Visual percentage complete

**Example flow**:
```
Phase 1/6: Backing up database (1 item)
├─> Creating backup: racing_pro_backup_20241020_143522.db
├─> ✓ Backup created (85.3 MB)
└─> Item 1/1 complete (100%)

Phase 2/6: Creating fresh schema (1 item)
├─> Removing old database...
├─> Creating fresh schema...
├─> ✓ Fresh schema created with runner_market_odds table
└─> Item 1/1 complete (100%)

Phase 3/6: Fetching racecards (890 dates)
├─> 10/890 dates (1.1%) - 384 races, 4,012 runners - ETA: 7.2h
├─> 20/890 dates (2.2%) - 768 races, 8,024 runners - ETA: 7.1h
...
└─> ✓ Racecards complete: 3,848 races, 40,291 runners

[continues through phases 4-6]
```

## Testing Instructions

### Before Testing

1. **Verify current odds coverage** (should be ~2.2%):
   ```bash
   cd Datafetch
   sqlite3 racing_pro.db "
     SELECT 
       COUNT(*) as total,
       COUNT(CASE WHEN mo.runner_id IS NOT NULL THEN 1 END) as with_odds,
       ROUND(100.0 * COUNT(CASE WHEN mo.runner_id IS NOT NULL THEN 1 END) / COUNT(*), 2) as pct
     FROM runners r
     LEFT JOIN runner_market_odds mo ON r.runner_id = mo.runner_id
   "
   ```

2. **Check database size**:
   ```bash
   ls -lh racing_pro.db
   ```

### Test 1: Small Date Range (Recommended First!)

**Purpose**: Verify everything works on small dataset

**Steps**:
1. Open GUI: `python racecard_gui.py`
2. Navigate to Tab 2: "Database Update"
3. Scroll to Option 3
4. Set dates:
   - Start: 2024-10-01
   - End: 2024-10-07 (7 days)
5. Click "🔄 REBUILD ENTIRE DATABASE"
6. Confirm in dialog
7. Wait ~30 minutes
8. Verify completion dialog shows:
   - ~280 races
   - ~2,800 runners
   - Odds coverage 75-85%

**Expected Results**:
- Backup file created in `Datafetch/`
- New database ~15-20 MB
- Progress updates in real-time
- Completion dialog with stats
- No errors

**Verification**:
```bash
cd Datafetch

# Check backup exists
ls -lh racing_pro_backup_*.db

# Check odds coverage
sqlite3 racing_pro.db "
  SELECT 
    COUNT(*) as total,
    COUNT(CASE WHEN mo.runner_id IS NOT NULL THEN 1 END) as with_odds,
    ROUND(100.0 * COUNT(CASE WHEN mo.runner_id IS NOT NULL THEN 1 END) / COUNT(*), 2) as pct
  FROM runners r
  LEFT JOIN runner_market_odds mo ON r.runner_id = mo.runner_id
"
# Expected: 75-85% with odds

# Check ML features populated
sqlite3 racing_pro.db "
  SELECT COUNT(*) FROM ml_features WHERE odds_implied_prob IS NOT NULL
"
# Expected: 75-85% of total features
```

### Test 2: Retrain and Predict

**Purpose**: Verify improved predictions

**Steps**:
1. In GUI, navigate to Tab 3: "ML Training"
2. Click "Train Model"
3. Wait for completion (~1-2 minutes on small dataset)
4. Check feature importance - odds features should rank highly
5. Navigate to Tab 5: "Predictions"
6. Generate predictions for upcoming races
7. **Verify**: Predictions are differentiated (not all 5-7%)

**Expected Results**:
- Favorite (low odds): 25-35% win probability
- Mid-range: 8-15% win probability
- Longshot (high odds): 1-5% win probability

**Before rebuild** (flat predictions):
```
Runner A: 6.2%
Runner B: 6.5%
Runner C: 6.1%
```

**After rebuild** (differentiated):
```
Runner A (favorite): 28.3%
Runner B (mid): 9.2%
Runner C (longshot): 2.1%
```

### Test 3: Full Historical Rebuild (Optional)

**Purpose**: Rebuild complete historical dataset

⚠️ **Only run after successful Test 1!**

**Steps**:
1. In GUI, Tab 2, Option 3
2. Set dates:
   - Start: 2023-01-23
   - End: Yesterday
3. Click rebuild
4. Confirm
5. **Wait 8-10 hours** (can leave running overnight)
6. Verify completion

**Expected Results**:
- ~41,000 races
- ~434,000 runners
- 80%+ odds coverage
- Database ~120-150 MB

## Verification Queries

### Check Odds Coverage by Date Range

```sql
SELECT 
    DATE(date, 'start of month') as month,
    COUNT(*) as total_runners,
    COUNT(CASE WHEN mo.runner_id IS NOT NULL THEN 1 END) as with_odds,
    ROUND(100.0 * COUNT(CASE WHEN mo.runner_id IS NOT NULL THEN 1 END) / COUNT(*), 2) as pct
FROM runners r
LEFT JOIN runner_market_odds mo ON r.runner_id = mo.runner_id
GROUP BY month
ORDER BY month;
```

### Check Bookmaker Coverage

```sql
SELECT 
    bookmaker,
    COUNT(*) as odds_count
FROM runner_odds
GROUP BY bookmaker
ORDER BY odds_count DESC
LIMIT 10;
```

### Check Feature Population

```sql
SELECT 
    COUNT(*) as total_features,
    COUNT(odds_implied_prob) as with_odds_prob,
    COUNT(odds_decimal) as with_odds_decimal,
    COUNT(horse_sex_encoded) as with_demographics,
    COUNT(trainer_14d_win_pct) as with_trainer_form
FROM ml_features;
```

### Check Favorite Identification

```sql
SELECT 
    r.race_id,
    h.name,
    mo.avg_decimal as odds,
    mo.is_favorite,
    mo.favorite_rank
FROM runners r
JOIN horses h ON r.horse_id = h.horse_id
JOIN runner_market_odds mo ON r.runner_id = mo.runner_id
WHERE r.race_id = 'some_race_id'
ORDER BY mo.favorite_rank;
```

## Error Handling

### Backup Creation Fails

**Symptom**: Error before Phase 1 completes

**Cause**: Disk space, permissions

**Solution**:
- Check disk space: `df -h`
- Check permissions: `ls -l racing_pro.db`
- Manual backup: `cp racing_pro.db racing_pro_backup_manual.db`

### API Errors During Fetch

**Symptom**: Many "Error fetching YYYY-MM-DD" messages

**Causes**:
- Internet connection issue
- API credentials invalid
- API rate limit exceeded
- API down/maintenance

**Solution**:
- Check internet: `ping api.theracingapi.com`
- Verify credentials in `reqd_files/cred.txt`
- Wait and retry
- Check API status page

### Low Odds Coverage After Rebuild

**Symptom**: Verification shows < 50% coverage

**Causes**:
- API changed odds format
- Odds not available for date range
- Parsing logic issue

**Investigation**:
```sql
-- Check raw odds exist
SELECT COUNT(*) FROM runner_odds;

-- Check if aggregation failed
SELECT 
    COUNT(DISTINCT ro.runner_id) as runners_with_raw_odds,
    COUNT(DISTINCT mo.runner_id) as runners_with_aggregated_odds
FROM runner_odds ro
LEFT JOIN runner_market_odds mo ON ro.runner_id = mo.runner_id;
```

**Solution**: File bug report with sample data

### Feature Generation Fails

**Symptom**: Phase 6 error but Phases 1-5 succeeded

**Cause**: Feature engineer issues

**Recovery**:
```bash
# Manually regenerate features
cd Datafetch
python -m ml.feature_engineer_optimized
```

Or use GUI: Tab 3 → "Regenerate ML Features"

### Application Crash During Rebuild

**Symptom**: Application closed, partial database

**Recovery**:
```bash
cd Datafetch

# List backups
ls -lt racing_pro_backup_*.db | head -5

# Restore most recent
cp racing_pro_backup_20241020_143522.db racing_pro.db

# Verify restoration
sqlite3 racing_pro.db "SELECT COUNT(*) FROM races"
```

## Performance Considerations

### API Rate Limiting

- **Rate**: 0.55 seconds between requests
- **Reason**: API provider's terms of service
- **Cannot be changed**: Risk of account ban

### Database Performance

During rebuild:
- **Write-heavy** workload
- **No indexes** during bulk insert (faster)
- **Indexes added** after completion
- **VACUUM** not run automatically (do manually if needed)

### Memory Usage

- **Peak**: ~500 MB during feature generation
- **Average**: ~200 MB during fetching
- **Minimum**: 2 GB RAM recommended

### Disk I/O

- **Backup**: Read entire old DB
- **Create**: Write entire new DB
- **Peak**: 2x database size temporarily

## Future Enhancements

### Potential Improvements

1. **Checkpoint System**
   - Save progress periodically
   - Resume from last checkpoint if interrupted
   - Implementation: SQLite savepoint + state file

2. **Incremental Rebuild**
   - Rebuild specific date ranges
   - Merge with existing data
   - Useful for fixing specific periods

3. **Parallel Fetching**
   - Fetch multiple dates simultaneously
   - Respect rate limit globally
   - Faster completion (~4-5 hours vs 8-10)

4. **Progress Persistence**
   - Save progress to database
   - Show progress across app restarts
   - History of rebuilds

5. **Odds Source Selection**
   - Choose which bookmakers to include
   - Filter by region
   - Custom aggregation formulas

6. **Validation Reports**
   - Detailed coverage by course
   - Coverage by race type
   - Anomaly detection

### Not Planned

- **Automatic scheduling**: User should trigger manually
- **Multiple versions**: One database version only
- **Undo/redo**: Use backups instead

## Summary

### What Was Built

✅ **Complete rebuild worker** with 6-phase processing  
✅ **GUI integration** with Option 3 in Database Update tab  
✅ **Automatic backup** with timestamp naming  
✅ **Comprehensive progress tracking** (phase, item, text levels)  
✅ **Odds aggregation logic** matching new fetcher  
✅ **Verification system** ensuring quality standards  
✅ **Error handling** with recovery guidance  
✅ **User documentation** with testing guide  

### Expected Impact

**Before**:
- 2.2% odds coverage
- Flat predictions (5-7%)
- Poor favorite identification

**After**:
- 80%+ odds coverage
- Differentiated predictions (3-40%)
- Clear favorite identification
- Improved model accuracy

### Recommended Usage

1. **Test on 7 days first** (~30 min)
2. **Verify odds coverage** (75-85%)
3. **Retrain model and test predictions**
4. **If successful, run full rebuild** (~8-10 hours)
5. **Retrain model on complete data**
6. **Enjoy improved predictions!** 🎯

### Maintenance

- **Run rebuild**: Only when necessary (schema changes, data quality issues)
- **Daily updates**: Use Option 2 ("Update to Yesterday")
- **Backups**: Keep last 2-3, delete older ones
- **Verification**: Periodically check odds coverage

---

**Questions?** See `DATABASE_REBUILD_GUIDE.md` for detailed documentation.

**Issues?** Check backup exists, restore if needed, file bug report with details.


