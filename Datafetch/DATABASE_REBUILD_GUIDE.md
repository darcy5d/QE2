# Complete Database Rebuild Guide

## Overview

The database rebuild feature allows you to completely rebuild your racing database from scratch, ensuring all odds data is properly aggregated and ML features are correctly populated.

## Why Rebuild?

### Current Problem

- **Historical data**: Only 2.2% of runners have aggregated odds data
- **Cause**: Old historical fetcher stored raw odds as strings, new fetcher properly aggregates them
- **Impact**: ML model cannot effectively use odds features for 97.8% of training data

### After Rebuild

- **Expected coverage**: 80%+ of runners will have properly aggregated odds
- **Result**: Model will learn from odds data across entire historical period
- **Prediction quality**: Significantly improved differentiation (3-40% range vs flat 5-7%)

## What Happens During Rebuild

### Phase 1: Backup (30 seconds)
- Creates timestamped backup of current database
- Format: `racing_pro_backup_YYYYMMDD_HHMMSS.db`
- Stored in `Datafetch/` directory
- Backup is NOT deleted after successful rebuild

### Phase 2: Fresh Schema (5 seconds)
- Removes old database completely
- Creates new schema with:
  - `runner_market_odds` table (aggregated odds)
  - All core tables (races, runners, horses, etc.)
  - Proper foreign key relationships
  - Indexes for performance

### Phase 3: Fetch Racecards (6-7 hours)
- Re-fetches ALL historical racecards from API
- Date range: 2023-01-23 to yesterday (or custom range)
- API endpoint: `/v1/racecards/pro`
- Rate limiting: 0.55s between requests
- **KEY**: Uses NEW odds aggregation logic for every runner
- Progress: Updates every 10 dates

**What's different:**
```python
# OLD (historical fetch):
# Stored odds as: "[{'bookmaker': 'Bet365', 'price': '5/1'}, ...]"
# No aggregation → ML features empty

# NEW (rebuild):
# Parses each bookmaker's odds
# Computes: avg_decimal, median, min, max, count
# Stores in runner_market_odds table
# ML features properly populated
```

### Phase 4: Fetch Results (2-3 hours)
- Fetches results for all completed races
- API endpoint: `/v1/results/{race_id}`
- Only fetches races in the past
- Skips abandoned races
- Progress: Updates every 50 races

### Phase 5: Verify Odds (10 seconds)
- Counts runners with vs without odds
- Expects 80%+ coverage
- Warns if coverage is low
- Shows exact percentage

### Phase 6: Regenerate Features (25 minutes)
- Uses optimized parallel feature generation
- Processes all races with results
- Computes all 95 features including odds
- Multi-core processing (4-8 workers)
- Progress: Updates every 100 races

## How to Use

### From GUI

1. **Open GUI**
   ```bash
   cd Datafetch
   python racecard_gui.py
   ```

2. **Navigate to Tab 2**: "Database Update"

3. **Scroll to Option 3**: "Complete Database Rebuild ⚠️"

4. **Set Date Range** (optional)
   - Default start: 2023-01-23 (API data start date)
   - Default end: Yesterday
   - Can customize for testing (e.g., 7 days)

5. **Click "🔄 REBUILD ENTIRE DATABASE"**

6. **Review Confirmation Dialog**
   - Shows date range
   - Shows backup filename
   - Shows estimated time
   - Shows what will happen

7. **Click "Yes" to Confirm**

8. **Wait for Completion**
   - Monitor progress bar
   - Check status messages
   - **DO NOT CLOSE APPLICATION**
   - Process runs in background thread

9. **Completion Dialog**
   - Shows final statistics
   - Shows backup location
   - Shows odds coverage %

### Testing First

**RECOMMENDED**: Test on small date range first!

```python
# In GUI:
Start Date: 2024-10-01
End Date: 2024-10-07  # Just 7 days

# Expected time: ~30 minutes
# Expected races: ~280
# Verify odds coverage: should be 80%+
```

This allows you to:
- Verify odds aggregation works
- Check ML features populate correctly
- Test model training on new data
- Confirm predictions improve

Then run full rebuild with confidence!

## Progress Monitoring

### Progress Bar
- Shows percentage complete for current phase
- Updates in real-time
- Each phase has separate progress tracking

### Status Messages
Examples:
```
Backing up database...
✓ Backup created (85.3 MB)

Creating fresh schema...
✓ Fresh schema created with runner_market_odds table

Phase 3/6: Fetching racecards (890 dates)
  100/890 dates (11.2%) - 3,842 races, 40,123 runners - ETA: 6.2h
  
Phase 4/6: Fetching results (3,842 races)
  500/3,842 races (13.0%) - 487 results - ETA: 1.8h
  
Phase 5/6: Verifying odds aggregation
✓ Odds coverage: 30,458/40,123 (75.9%)

Phase 6/6: Regenerating ML features
Starting optimized feature generation...
✓ Features generated: 35,221 runners
```

## Time Estimates

| Phase | Description | Estimated Time |
|-------|-------------|----------------|
| 1 | Backup | ~30 seconds |
| 2 | Schema | ~5 seconds |
| 3 | Racecards | ~6-7 hours |
| 4 | Results | ~2-3 hours |
| 5 | Verification | ~10 seconds |
| 6 | Features | ~25 minutes |
| **TOTAL** | **Full Rebuild** | **8-10 hours** |

**Test rebuild (7 days)**: ~30 minutes

## What If Something Goes Wrong?

### Error During Rebuild

The rebuild worker has comprehensive error handling:

1. **Error message displayed** in status label and dialog
2. **Backup still available** - your original data is safe
3. **Can restore manually**:
   ```bash
   cd Datafetch
   cp racing_pro_backup_YYYYMMDD_HHMMSS.db racing_pro.db
   ```

### Low Odds Coverage

If verification shows < 50% coverage:
- Warning displayed but rebuild continues
- Check API might have changed format
- Inspect `runner_odds` and `runner_market_odds` tables
- File issue with details

### Feature Generation Fails

If Phase 6 fails:
- Rebuild completes but features empty
- Can regenerate manually:
  ```bash
  cd Datafetch
  python -m ml.feature_engineer_optimized
  ```
- Or use GUI: Tab 3 → "Regenerate ML Features"

### Interrupted Rebuild

If application crashes or is closed:
- Partial database may exist (incomplete)
- **Restore from backup**:
  ```bash
  cd Datafetch
  # Find backup file (sorted by date)
  ls -lt racing_pro_backup_*.db | head -1
  # Restore it
  cp racing_pro_backup_YYYYMMDD_HHMMSS.db racing_pro.db
  ```
- No checkpoint/resume system (yet)
- Must restart rebuild from beginning

## After Rebuild

### 1. Verify Odds Coverage

```bash
cd Datafetch
sqlite3 racing_pro.db
```

```sql
SELECT 
    COUNT(*) as total_runners,
    COUNT(CASE WHEN mo.runner_id IS NOT NULL THEN 1 END) as with_odds,
    ROUND(100.0 * COUNT(CASE WHEN mo.runner_id IS NOT NULL THEN 1 END) / COUNT(*), 2) as pct
FROM runners r
LEFT JOIN runner_market_odds mo ON r.runner_id = mo.runner_id;
```

**Expected**: 80%+ coverage

### 2. Check ML Features

```sql
SELECT COUNT(*) FROM ml_features WHERE odds_implied_prob IS NOT NULL;
SELECT COUNT(*) FROM ml_features;
```

**Expected**: ~80% of rows should have odds_implied_prob populated

### 3. Retrain Model

In GUI:
1. Navigate to Tab 3: "ML Training"
2. Click "Train Model"
3. Wait for completion (~5 minutes)
4. Check feature importance - odds features should rank highly

### 4. Test Predictions

In GUI:
1. Navigate to Tab 5: "Predictions"
2. Load upcoming races
3. Click "Generate Predictions"
4. **Verify**: Predictions are now differentiated (not all 5-7%)
5. **Verify**: Favorites have higher win probabilities

### 5. Compare Results

Before rebuild:
```
Runner A: 6.2% win probability
Runner B: 6.5% win probability
Runner C: 6.1% win probability
(All very similar)
```

After rebuild:
```
Runner A (favorite, 2.5 odds): 28.3% win probability
Runner B (7.0 odds): 9.2% win probability  
Runner C (25.0 odds): 2.1% win probability
(Clear differentiation based on odds + other features)
```

## Technical Details

### Odds Aggregation Logic

The rebuild uses the same logic as `upcoming_fetcher.py`:

```python
def save_runner_odds(cursor, runner_id, odds_data):
    """
    For each bookmaker:
      1. Parse fractional odds (e.g., "5/1")
      2. Convert to decimal (e.g., 6.0)
      3. Store individual odds in runner_odds
    
    Then aggregate:
      - avg_decimal = mean of all bookmaker odds
      - median_decimal = median
      - min_decimal = best odds
      - max_decimal = worst odds
      - bookmaker_count = number of bookmakers
      - implied_probability = 1.0 / avg_decimal
    
    Store aggregates in runner_market_odds
    """
```

### Schema Comparison

**Old runner_odds table:**
```sql
CREATE TABLE runner_odds (
    odds_id INTEGER PRIMARY KEY,
    runner_id INTEGER,
    odds_value TEXT  -- Stored as JSON string!
);
```

**New schema:**
```sql
CREATE TABLE runner_odds (
    odds_id INTEGER PRIMARY KEY,
    runner_id INTEGER,
    bookmaker TEXT,
    fractional_odds TEXT,
    decimal_odds REAL
);

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

### API Endpoints

Both endpoints provide odds data:

**Racecards** (`/v1/racecards/pro`):
```json
{
  "races": [{
    "race_id": "...",
    "runners": [{
      "horse_id": "...",
      "odds": [
        {"bookmaker": "Bet365", "price": "5/1"},
        {"bookmaker": "Paddy Power", "price": "11/2"},
        {"bookmaker": "William Hill", "price": "6/1"}
      ]
    }]
  }]
}
```

**Results** (`/v1/results/{race_id}`):
```json
{
  "results": [{
    "horse_id": "...",
    "position": 1,
    "rpr": 145,
    "ts": 82
  }]
}
```

## Maintenance

### Backup Retention

Backups are NOT automatically deleted. To manage:

```bash
cd Datafetch

# List all backups
ls -lh racing_pro_backup_*.db

# Delete old backups (keep last 3)
ls -t racing_pro_backup_*.db | tail -n +4 | xargs rm

# Or delete all except latest
ls -t racing_pro_backup_*.db | tail -n +2 | xargs rm
```

### Regular Rebuilds

**Recommendation**: Rebuild when:
1. API schema changes significantly
2. Odds coverage drops unexpectedly
3. New features added to schema
4. Corruption suspected

**Not needed for**: Daily updates (use Option 2 instead)

### Database Size

- Before rebuild: ~85 MB
- After rebuild (with odds): ~120-150 MB
- Backup: Same as before (~85 MB)
- **Total disk space needed**: ~250 MB during rebuild

## FAQ

### Q: Will I lose my data?

**A**: No! Backup is created first. If anything goes wrong, restore from backup.

### Q: Can I cancel during rebuild?

**A**: Not recommended. If you must:
1. Close application
2. Delete incomplete racing_pro.db
3. Restore from backup

### Q: Why 8-10 hours?

**A**: API rate limiting (0.55s between requests). For ~41,000 races × 0.55s = ~6 hours just for racecards, plus results fetching and processing.

### Q: Can I speed it up?

**A**: No - API has strict rate limits. Faster = risk of ban.

### Q: What about upcoming races?

**A**: Rebuild only affects `racing_pro.db` (historical). Upcoming races stay in `upcoming_races.db`.

### Q: Should I rebuild for just a few missing odds?

**A**: No - use Option 1 or 2 to update incrementally. Rebuild is for systematic data quality issues.

### Q: Will model improve immediately?

**A**: After rebuild, you MUST retrain the model (Tab 3). Then predictions will improve.

## Support

If you encounter issues:

1. **Check backup exists**: `ls Datafetch/racing_pro_backup_*.db`
2. **Check logs**: Look for error messages in status label
3. **Verify API access**: Test in browser or curl
4. **Disk space**: Ensure 250+ MB free
5. **Memory**: Ensure 2+ GB RAM available

## Summary

The database rebuild feature:
- ✅ Safely backs up your data
- ✅ Re-fetches all data with proper odds aggregation  
- ✅ Populates 80%+ of runners with odds features
- ✅ Enables effective ML model training on odds
- ✅ Significantly improves prediction quality
- ⏱️ Takes 8-10 hours for full historical data
- 🧪 Can test on 7 days first (~30 min)

**Next steps after rebuild**:
1. Verify odds coverage (SQL query)
2. Retrain model (Tab 3)
3. Generate predictions (Tab 5)
4. Enjoy differentiated predictions! 🎯


