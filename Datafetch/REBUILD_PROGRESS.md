# Database Rebuild Progress Tracker

**Started**: November 5, 2025 05:40 AM
**Expected Completion**: November 5, 2025 1:40 PM (~8 hours)

---

## ✅ Phase 1: Fix Data Fetching Script - COMPLETE

### Step 1: Updated fetch_racecards_pro.py ✓
**File**: `Datafetch/fetch_racecards_pro.py` line 608

**Changed**: Added 17 new fields to runners INSERT statement:
- Age, sex, sex_code, dob
- Sire, sire_id, dam, dam_id, damsire, damsire_id
- Region, breeder, colour
- Trainer_location
- Trainer_14d_runs, trainer_14d_wins, trainer_14d_percent

**Status**: ✓ Script modified and verified (no syntax errors)

---

## 🔄 Phase 2: Database Rebuild - IN PROGRESS

### Step 3: Backup Current Database ✓
**Backup file**: `racing_pro_backup_pre_age_fix_20251105_053946.db`
**Size**: 806MB
**Status**: ✓ Backup created successfully

### Step 4: Delete Old Database ✓
**Status**: ✓ Old database deleted

### Step 5: Re-fetch Racecards - RUNNING ⏳
**Process**: Running in background (PID: 69861)
**Log file**: `fetch_racecards_rebuild.log`
**Date range**: 2023-01-23 to 2023-04-30 (98 days)
**Progress**: 1/98 dates started
**Started**: 05:40 AM
**Expected duration**: 6-8 hours
**Monitor**: `tail -f Datafetch/fetch_racecards_rebuild.log`

**Status**: 🔄 IN PROGRESS - Let this run overnight/background

---

## ⏸️ Phase 2 (Continued): Steps Waiting for Racecards Completion

### Step 6: Re-fetch Results - PENDING
**Command**: `python fetch_historical_results.py`
**Duration**: 2-3 hours
**Status**: ⏸️ Will run after racecards complete

### Step 7: Verify Age Coverage - PENDING
**What to check**: Age field should be >95% populated in runners table
**Status**: ⏸️ Will verify after rebuild completes

---

## 📋 Phase 3: Re-enable Age Features - READY TO EXECUTE

### Step 8: Add Age Features Back
**File**: `Datafetch/ml/models/feature_columns_flat.json`
**Changes needed**:
- Add `horse_age` (near top)
- Add `age_vs_avg` (after weight_vs_avg)
- Add `age_rank` (after weight_lbs_rank)
**Features**: 111 → 114
**Status**: ⏸️ Ready to execute after rebuild

---

## 📋 Phase 4: Feature Regeneration & Retraining - READY TO EXECUTE

### Step 10: Regenerate ML Features
**Command**: `cd Datafetch/ml && python feature_engineer_optimized.py`
**Duration**: ~1 hour
**Status**: ⏸️ Execute after age features added back

### Step 11: Retrain All Models
**Commands**:
```bash
python train_baseline.py
python train_btn_model.py
python train_speed_model.py
python train_speed_relative_model.py
```
**Duration**: ~30-45 minutes total
**Status**: ⏸️ Execute after features regenerated

### Step 12: Compare Models
**Command**: `python compare_models.py`
**Duration**: ~5 minutes
**Status**: ⏸️ Final step

---

## 🔍 How to Monitor Progress

### Check Racecards Fetch Status
```bash
# See live progress
tail -f Datafetch/fetch_racecards_rebuild.log

# Check how many dates completed
grep -c "Progress:" Datafetch/fetch_racecards_rebuild.log

# Check if process is still running
ps aux | grep fetch_racecards_pro.py
```

### Check Database Size (Should Grow)
```bash
ls -lh Datafetch/racing_pro.db
```

### Estimate Time Remaining
- Total dates: 98
- Rate: ~1 date per 5-6 minutes
- Total time: ~8 hours for racecards + 2-3 hours for results
- **Total rebuild time: ~10-11 hours**

---

## ⚠️ If Something Goes Wrong

### Racecards Fetch Failed
1. Check log: `tail -100 Datafetch/fetch_racecards_rebuild.log`
2. Look for API errors or network issues
3. Can restart from where it left off (script checks existing data)
4. Restore backup if needed: `cp racing_pro_backup_pre_age_fix_20251105_053946.db racing_pro.db`

### Process Killed/Interrupted
1. Just restart: `python fetch_racecards_pro.py`
2. Script will skip already-fetched dates
3. Progress is saved continuously

---

## ✅ What to Do When Rebuild Completes

### 1. Verify Age Data (Step 7)
```bash
python -c "
import sqlite3
conn = sqlite3.connect('Datafetch/racing_pro.db')
cursor = conn.cursor()
cursor.execute('''
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN age IS NOT NULL AND age != '' THEN 1 ELSE 0 END) as has_age,
        ROUND(100.0 * SUM(CASE WHEN age IS NOT NULL AND age != '' THEN 1 ELSE 0 END) / COUNT(*), 1) as pct
    FROM runners
''')
row = cursor.fetchone()
print(f'Age coverage: {row[1]:,}/{row[0]:,} ({row[2]}%)')
conn.close()
"
```

**Expected**: >95% coverage

### 2. Re-enable Age Features (Phase 3, Step 8)
Edit `Datafetch/ml/models/feature_columns_flat.json` to add back:
- `horse_age`
- `age_vs_avg`
- `age_rank`

### 3. Regenerate Features (Phase 4, Step 10)
```bash
cd Datafetch/ml
python feature_engineer_optimized.py
```

### 4. Retrain Models (Phase 4, Step 11)
```bash
python train_baseline.py
python train_btn_model.py
python train_speed_model.py  
python train_speed_relative_model.py
```

### 5. Compare Results (Phase 4, Step 12)
```bash
python compare_models.py
```

---

## 📊 Expected Improvements After Rebuild

**Data Quality**:
- Age coverage: 0% → 95%+
- Sire/Dam IDs: 0% → 95%+
- Overall missing data: 15.2% → ~8%

**Model Impact**:
- Age feature importance: Should be in top 20-30 features
- Top pick accuracy: Expected slight improvement
- Better discrimination between age groups (2yo vs 3yo vs older)

**Features**:
- Before: 111 features (age removed)
- After: 114 features (age restored)

---

## 📝 Summary

**Completed**:
- ✓ Fixed data fetching script to populate age field
- ✓ Created database backup (806MB)
- ✓ Started full database rebuild

**In Progress**:
- 🔄 Racecards fetch running (6-8 hours)

**Next** (after rebuild):
- Results fetch (2-3 hours)
- Re-enable age features
- Regenerate ML features
- Retrain models
- Compare performance

**Total Time**: ~10-12 hours (mostly unattended)

**Check back**: November 5, 2025 ~4:00 PM

