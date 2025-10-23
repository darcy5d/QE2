# Hybrid Odds Enrichment Guide

## Overview

This guide explains how to enrich your existing historical racing database with Starting Price (SP) odds from the `/v1/results` endpoint, combined with live odds from the `/v1/racecards/pro` endpoint for predictions.

## The Problem

- Current database: Only **2.2%** of runners have aggregated odds data
- Reason: Historical racecards endpoint doesn't provide old odds data
- Impact: ML model can't learn from odds for 97.8% of training data
- Result: Flat, undifferentiated predictions (all runners 5-7%)

## The Solution

### Two-Pronged Approach

**1. Historical Data (Training)**:
- Use `/v1/results/{race_id}` endpoint
- Extract SP (Starting Price) - the actual consensus odds at race start
- Enrich existing 43,037 races with SP odds
- Expected coverage: **80-90%** (up from 2.2%)

**2. Upcoming Races (Predictions)**:
- Use `/v1/racecards/pro` endpoint
- Get current live odds from bookmakers
- Already implemented and working!

## Why Starting Price is Better

| Feature | Pre-race Odds | Starting Price (SP) |
|---------|---------------|---------------------|
| **Availability** | ❌ Not in historical data | ✅ Always in results |
| **Stability** | ❌ Changes constantly | ✅ Fixed at race start |
| **Reliability** | ⚠️ Varies by bookmaker | ✅ Market consensus |
| **Predictive Power** | 📊 Good | 📈 Better |
| **API Access** | ❌ Limited historical | ✅ Full historical |

## Quick Start

### Step 1: Test on 100 Races (~1 minute)

```bash
cd /Users/darcy5d/Desktop/DD_AI_models/QE2/Datafetch
python test_enrich_odds.py
```

**Expected Output**:
```
📊 BEFORE Enrichment:
  9,686/434,939 (2.23%)

============================================================
ODDS ENRICHMENT FROM RESULTS ENDPOINT
============================================================

Found 100 races needing odds enrichment
Estimated time: 0.0 hours

  50/100 (50.0%) - 47 enriched, 512 runners
  100/100 (100.0%) - 93 enriched, 1,024 runners

✓ Complete!
  Races enriched: 93
  Runners processed: 1,024

📊 Final Odds Coverage:
  10,710/434,939 (2.46%)

✓ Added odds for 1,024 runners
```

### Step 2: Verify Data Quality

Check a sample of enriched odds:

```bash
cd /Users/darcy5d/Desktop/DD_AI_models/QE2/Datafetch
sqlite3 racing_pro.db
```

```sql
-- Check recent enriched races
SELECT 
    r.race_id,
    r.date,
    r.course,
    COUNT(mo.runner_id) as runners_with_odds
FROM races r
JOIN runners run ON r.race_id = run.race_id
JOIN runner_market_odds mo ON run.runner_id = mo.runner_id
WHERE mo.bookmaker_count = 1  -- SP odds
GROUP BY r.race_id
ORDER BY r.date DESC
LIMIT 10;

-- Check sample odds values
SELECT 
    h.name as horse,
    mo.avg_decimal as sp_decimal,
    mo.implied_probability
FROM runner_market_odds mo
JOIN runners run ON mo.runner_id = run.runner_id
JOIN horses h ON run.horse_id = h.horse_id
WHERE mo.bookmaker_count = 1
LIMIT 20;
```

### Step 3: Run Full Enrichment (2-3 hours)

```bash
cd /Users/darcy5d/Desktop/DD_AI_models/QE2/Datafetch
python enrich_odds_from_results.py
```

**What to Expect**:
- **Duration**: 2-3 hours (depends on how many races need enrichment)
- **Progress**: Updates every 50 races
- **Rate**: 0.55 seconds per race (API rate limit)
- **Coverage**: Should reach 80-90%

**Example Output**:
```
============================================================
ODDS ENRICHMENT FROM RESULTS ENDPOINT
============================================================

Found 42,944 races needing odds enrichment
Estimated time: 6.6 hours

  50/42,944 (0.1%) - 48 enriched, 523 runners
  100/42,944 (0.2%) - 96 enriched, 1,047 runners
  ...
  42,900/42,944 (99.9%) - 38,412 enriched, 389,456 runners
  42,944/42,944 (100.0%) - 38,456 enriched, 390,123 runners

✓ Complete!
  Races enriched: 38,456
  Runners processed: 390,123

📊 Final Odds Coverage:
  399,809/434,939 (91.93%)
```

### Step 4: Regenerate ML Features

After enrichment, regenerate features to include odds data:

```bash
cd /Users/darcy5d/Desktop/DD_AI_models/QE2/Datafetch
python -m ml.feature_engineer_optimized
```

**Expected**:
- Duration: ~25 minutes (optimized parallel processing)
- Result: Odds features populated for 90%+ of training data

### Step 5: Retrain Model

Open the GUI and retrain:

```bash
cd /Users/darcy5d/Desktop/DD_AI_models/QE2/Datafetch
python racecard_gui.py
```

1. Go to **Tab 3**: "ML Training"
2. Click **"Train Model"**
3. Wait ~5 minutes
4. Check feature importance - odds features should rank highly!

### Step 6: Test Predictions

1. Go to **Tab 5**: "Predictions"
2. Load upcoming races
3. Click **"Generate Predictions"**
4. **Verify**: Predictions are now differentiated!

**Before Enrichment**:
```
Runner A: 6.2% win probability
Runner B: 6.5% win probability
Runner C: 6.1% win probability
(All very similar - flat)
```

**After Enrichment**:
```
Runner A (favorite, 2.5 odds): 28.3% win probability
Runner B (mid-range, 7.0 odds): 9.2% win probability
Runner C (longshot, 25.0 odds): 2.1% win probability
(Clear differentiation!)
```

## Understanding the Data

### Starting Price (SP) Format

From `/v1/results` endpoint:

```json
{
  "horse_id": "hrs_21687631",
  "horse": "Cisco Disco (IRE)",
  "sp": "9/4",          // Fractional odds
  "sp_dec": "3.25",     // Decimal odds
  "position": "1"       // Finished 1st
}
```

### How It's Stored

**runner_market_odds table**:
```sql
runner_id: 12345
avg_decimal: 3.25      -- SP decimal odds
median_decimal: 3.25   -- Same (only 1 value)
min_decimal: 3.25      -- Same
max_decimal: 3.25      -- Same
bookmaker_count: 1     -- Indicates this is SP
implied_probability: 0.3077  -- 1 / 3.25
```

**runner_odds table**:
```sql
runner_id: 12345
bookmaker: 'Starting Price'
fractional: '9/4'
decimal: 3.25
```

## Monitoring Progress

### During Enrichment

Watch terminal output:
```
  1,000/42,944 (2.3%) - 947 enriched, 10,234 runners
  2,000/42,944 (4.7%) - 1,894 enriched, 20,468 runners
  ...
```

### Check Coverage

```bash
cd Datafetch
sqlite3 racing_pro.db "
  SELECT 
    COUNT(*) as total,
    COUNT(mo.runner_id) as with_odds,
    ROUND(100.0 * COUNT(mo.runner_id) / COUNT(*), 2) as pct
  FROM runners r
  LEFT JOIN runner_market_odds mo ON r.runner_id = mo.runner_id
"
```

### Check by Date Range

```sql
SELECT 
    strftime('%Y-%m', r.date) as month,
    COUNT(*) as total_runners,
    COUNT(mo.runner_id) as with_odds,
    ROUND(100.0 * COUNT(mo.runner_id) / COUNT(*), 2) as pct
FROM runners r
LEFT JOIN runner_market_odds mo ON r.runner_id = mo.runner_id
GROUP BY month
ORDER BY month DESC;
```

## Troubleshooting

### Issue: Low Enrichment Rate

**Symptom**: Many races showing "0 enriched"

**Possible Causes**:
1. Races don't have results yet (too recent)
2. API rate limit exceeded
3. Network issues

**Solution**:
```bash
# Check if races have results
sqlite3 racing_pro.db "
  SELECT COUNT(DISTINCT race_id) 
  FROM results
"

# Should be close to total races if results are fetched
```

### Issue: Script Interrupted

**Good news**: Script is resumable!

Just run it again:
```bash
python enrich_odds_from_results.py
```

It will skip races that already have odds (INSERT OR IGNORE).

### Issue: No SP Data for Some Horses

**Symptom**: Warning messages like "Invalid SP for runner..."

**Cause**: Some runners may not have SP (non-runners, withdrawn, etc.)

**Impact**: Minimal - these are edge cases

**Action**: No action needed - script continues

### Issue: Coverage Still Low After Full Run

**Check**:
```bash
sqlite3 racing_pro.db "
  SELECT 
    COUNT(DISTINCT r.race_id) as total_races,
    COUNT(DISTINCT CASE WHEN res.result_id IS NOT NULL THEN r.race_id END) as races_with_results
  FROM races r
  LEFT JOIN results res ON r.race_id = res.race_id
"
```

If many races don't have results, you may need to fetch them first:
- GUI → Tab 2 → "Update to Yesterday"

## Performance Optimization

### Batch Processing

The script processes races sequentially but commits in batches for efficiency.

### Rate Limiting

- 0.55 seconds between requests (API requirement)
- Non-negotiable - faster = risk of ban
- ~6,400 races per hour

### Database Performance

After enrichment, optimize database:

```bash
cd Datafetch
sqlite3 racing_pro.db "VACUUM; ANALYZE;"
```

This will:
- Reclaim unused space
- Update query optimizer statistics
- Improve feature generation speed

## Expected Timeline

| Step | Duration | Description |
|------|----------|-------------|
| Test (100 races) | ~1 minute | Verify setup works |
| Full enrichment | 2-3 hours | Process all historical races |
| Database optimize | ~2 minutes | VACUUM and ANALYZE |
| Regenerate features | ~25 minutes | ML feature computation |
| Retrain model | ~5 minutes | XGBoost training |
| **Total** | **~3 hours** | Complete end-to-end |

## Verification Queries

### Check Odds Distribution

```sql
SELECT 
    CASE 
        WHEN avg_decimal < 2.0 THEN 'Favorite (< 2.0)'
        WHEN avg_decimal < 5.0 THEN 'Mid-range (2.0-5.0)'
        WHEN avg_decimal < 10.0 THEN 'Outsider (5.0-10.0)'
        ELSE 'Longshot (10.0+)'
    END as odds_category,
    COUNT(*) as count,
    ROUND(AVG(implied_probability), 4) as avg_prob
FROM runner_market_odds
WHERE bookmaker_count = 1  -- SP only
GROUP BY odds_category;
```

### Check Feature Population

```sql
SELECT 
    COUNT(*) as total_features,
    COUNT(odds_implied_prob) as with_odds_prob,
    COUNT(odds_decimal) as with_odds_decimal,
    COUNT(odds_favorite_rank) as with_favorite_rank,
    ROUND(100.0 * COUNT(odds_implied_prob) / COUNT(*), 2) as odds_coverage_pct
FROM ml_features;
```

### Find Races Ready for Training

```sql
SELECT 
    r.race_id,
    r.date,
    r.course,
    COUNT(mo.runner_id) as runners_with_odds
FROM races r
JOIN runners run ON r.race_id = run.race_id
JOIN runner_market_odds mo ON run.runner_id = mo.runner_id
JOIN results res ON r.race_id = res.race_id
WHERE r.date < date('now', '-7 days')  -- At least 1 week old
GROUP BY r.race_id
HAVING runners_with_odds >= 5  -- At least 5 runners with odds
ORDER BY r.date DESC
LIMIT 20;
```

## Benefits Summary

### Data Quality
- ✅ Starting Price = actual market consensus
- ✅ More reliable than pre-race odds
- ✅ Always available in results

### Coverage
- ✅ From 2.2% to 80-90%
- ✅ 40x improvement in odds coverage
- ✅ Model can actually learn from odds

### Predictions
- ✅ Clear favorite identification
- ✅ Differentiated probabilities (3-40% range)
- ✅ Better risk assessment

### Implementation
- ✅ No data loss (enriches existing DB)
- ✅ Resumable if interrupted
- ✅ Rate limited (API safe)
- ✅ 3 hours vs 8-10 hours for rebuild

## Next Steps

After successful enrichment:

1. **Monitor Model Performance**
   - Check feature importance
   - Odds features should rank in top 10
   - Log-loss should improve

2. **A/B Test Predictions**
   - Compare predictions before/after
   - Validate on recent races
   - Measure calibration

3. **Document Findings**
   - Record coverage improvement
   - Note prediction quality changes
   - Share insights with team

4. **Regular Maintenance**
   - Run enrichment weekly for new results
   - Monitor odds coverage
   - Retrain model monthly

## Support

If you encounter issues:

1. Check terminal output for error messages
2. Verify API credentials in `reqd_files/cred.txt`
3. Confirm database is not locked (close other connections)
4. Check disk space: `df -h`
5. Review this guide's troubleshooting section

---

**Remember**: This is a one-time enrichment for historical data. Ongoing predictions use live odds from the racecards endpoint automatically!

🎯 **Goal**: Transform flat predictions into actionable, differentiated probabilities by leveraging actual Starting Price odds from 80-90% of your historical data.


