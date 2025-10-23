# Database Rebuild - Quick Start Guide

## What This Does

Rebuilds your entire racing database from scratch with **proper odds aggregation**, fixing the 2.2% odds coverage problem and enabling significantly improved ML predictions.

## Before You Start

**Current Status**:
- Odds coverage: 2.2% (9,686 out of 434,939 runners)
- Predictions: Flat (all runners 5-7% win probability)

**After Rebuild**:
- Odds coverage: 80%+ (estimated ~348,000 out of 434,939 runners)
- Predictions: Differentiated (3-40% range with clear favorites)

## Quick Test (30 minutes) - START HERE!

1. Open GUI: `cd Datafetch && python racecard_gui.py`
2. Go to **Tab 2** (Database Update)
3. Scroll to **Option 3** (Complete Database Rebuild)
4. Set dates:
   - **Start**: 2024-10-01
   - **End**: 2024-10-07 (7 days)
5. Click **"🔄 REBUILD ENTIRE DATABASE"**
6. Confirm and wait ~30 minutes

### Verify Test Worked

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

**Expected**: 75-85% odds coverage

### Test Predictions

1. Tab 3: Train Model
2. Tab 5: Generate Predictions
3. **Verify**: Predictions are now differentiated (not all 5-7%)

## Full Rebuild (8-10 hours)

⚠️ **Only run after successful test!**

1. Same steps as test, but use dates:
   - **Start**: 2023-01-23
   - **End**: Yesterday
2. Can run overnight
3. **Do NOT close application**

## If Something Goes Wrong

Restore from backup:
```bash
cd Datafetch
ls -lt racing_pro_backup_*.db | head -1
cp racing_pro_backup_YYYYMMDD_HHMMSS.db racing_pro.db
```

## After Full Rebuild

1. Verify odds coverage (should be 80%+)
2. **Retrain model** (Tab 3)
3. Generate predictions (Tab 5)
4. Enjoy improved predictions! 🎯

## Documentation

- **User Guide**: `DATABASE_REBUILD_GUIDE.md`
- **Technical Details**: `DATABASE_REBUILD_IMPLEMENTATION.md`
- **Summary**: `COMPLETE_DATABASE_REBUILD_SUMMARY.md`

## Key Points

- ✅ Automatic backup before rebuild
- ✅ Test on 7 days first (30 min)
- ✅ Full rebuild takes 8-10 hours
- ✅ Can restore from backup if needed
- ✅ Must retrain model after rebuild
- ⚠️ Don't close app during rebuild

---

**Start with the 30-minute test, then decide on full rebuild!**


