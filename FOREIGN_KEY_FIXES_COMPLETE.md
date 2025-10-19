# Foreign Key Constraint Fixes - Complete

## Problem Summary

When running "Update to Yesterday" in the GUI, we encountered FOREIGN KEY constraint failures preventing racecards and results from being inserted into the database.

## Root Causes

### Issue 1: Empty String Foreign Keys
The API sometimes returns empty strings `""` for `trainer_id`, `jockey_id`, or `owner_id` when:
- A jockey hasn't been declared yet (common for races days away)
- A trainer is missing from the data
- An owner is not available

SQLite foreign key constraints **do not accept empty strings** - they must be either:
- A valid ID that exists in the parent table
- `NULL` (which is allowed if the column definition permits it)

### Issue 2: Missing Entity Insertion in Results
The results endpoint sometimes includes horses/trainers/jockeys/owners that weren't in the racecard (e.g., late declarations, replacements). These entities need to be inserted before the result can reference them.

## Solutions Implemented

### Fix 1: Empty String → NULL Conversion (Racecards)

**File:** `Datafetch/gui/combined_fetcher_worker.py`
**Lines:** 255-285

```python
# Before: Direct usage (fails on empty strings)
trainer_id = runner.get('trainer_id')
if trainer_id:
    cursor.execute('INSERT OR IGNORE INTO trainers ...')

# After: Convert empty strings to None (NULL)
trainer_id = runner.get('trainer_id')
if trainer_id == '':
    trainer_id = None
if trainer_id:
    cursor.execute('INSERT OR IGNORE INTO trainers ...')
```

Applied to:
- ✅ `trainer_id`
- ✅ `jockey_id` 
- ✅ `owner_id`

### Fix 2: Entity Insertion + NULL Handling (Results)

**File:** `Datafetch/gui/combined_fetcher_worker.py`
**Lines:** 344-401

Results processing now:
1. **Inserts missing entities** before referencing them:
   ```python
   # Insert horse if not exists
   cursor.execute('INSERT OR IGNORE INTO horses (horse_id, name) VALUES (?, ?)', ...)
   
   # Insert trainer if not exists (and not empty)
   trainer_id = runner.get('trainer_id')
   if trainer_id == '':
       trainer_id = None
   if trainer_id:
       cursor.execute('INSERT OR IGNORE INTO trainers ...')
   ```

2. **Converts empty strings to NULL** for all foreign keys
3. **Uses converted values** in the INSERT statement:
   ```python
   cursor.execute('''INSERT OR IGNORE INTO results (...) VALUES (?, ?, ?, ?, ?, ...)''',
                  (race_id, horse_id, trainer_id, jockey_id, owner_id, ...))
   ```

## Verification

### Previous Errors (Before Fix)

```
Error processing racecards: FOREIGN KEY constraint failed
Problematic runner: horse=Spicy Knuckles, jockey_id=, owner_id=own_1145792

Error processing results for rac_10920338: FOREIGN KEY constraint failed
Error processing results for rac_10895638: FOREIGN KEY constraint failed
... (~105 races failed)
```

### Database Status (After Update)

- **Total Races:** 42,989
- **Total Runners:** 454,555
- **Total Results:** 393,067
- **Races with Results:** 41,010 (95.4%)
- **Missing Results:** 218 races
  - **62 races** from 2025-10-18 (today/upcoming - not yet run)
  - **156 races** from various past dates (may have been abandoned or had data issues)

### Expected Outcome After Fix

Running "Update to Yesterday" again should:
1. ✅ Process all racecards without foreign key errors
2. ✅ Insert results for the ~105 races that previously failed
3. ✅ Handle horses with missing jockey/trainer/owner data gracefully (NULL values)
4. ✅ Reduce the gap in missing historical results

## Testing

1. **Restart GUI** with updated code
2. **Navigate** to "Database Update" tab
3. **Click** "Update to Yesterday"
4. **Expected:** No foreign key errors in `/tmp/gui_debug.log`
5. **Verify:** Results count increases for previously failed races

## Technical Notes

### Why NULL Works

The database schema defines foreign key columns with these characteristics:
```sql
CREATE TABLE runners (
    ...
    trainer_id TEXT,  -- No NOT NULL constraint
    jockey_id TEXT,   -- No NOT NULL constraint
    owner_id TEXT,    -- No NOT NULL constraint
    FOREIGN KEY (trainer_id) REFERENCES trainers(trainer_id),
    FOREIGN KEY (jockey_id) REFERENCES jockeys(jockey_id),
    FOREIGN KEY (owner_id) REFERENCES owners(owner_id)
)
```

When a foreign key column is NULL:
- ✅ The foreign key constraint is **not checked**
- ✅ The row can be inserted even if no matching parent exists
- ✅ Later updates can fill in the actual ID once available

When a foreign key column is `""` (empty string):
- ❌ SQLite **checks** if a parent row with `id = ""` exists
- ❌ If not found, the constraint fails
- ❌ Insert is rejected

### Data Flow

```
API Response → Python dict
↓
runner.get('jockey_id') → "" (empty string)
↓
if jockey_id == '': jockey_id = None  ← CONVERSION
↓
SQLite receives NULL
↓
Foreign key constraint: NULL = OK ✅
```

## Files Modified

1. **`Datafetch/gui/combined_fetcher_worker.py`**
   - Added empty string → NULL conversion for trainer_id
   - Added empty string → NULL conversion for jockey_id (already done)
   - Added empty string → NULL conversion for owner_id (already done)
   - Added entity insertion in results processing
   - Added empty string → NULL handling in results processing

## Related Documentation

- `PROBABILITY_NORMALIZATION_FIX.md` - Initial ML model probability issues
- `RANKING_MODEL_IMPLEMENTATION.md` - Ranking model with race-context features
- `TARGET_INVERSION_FIX.md` - Points system for ranking model

## Next Steps

✅ **Immediate:** Test the updated GUI with "Update to Yesterday"
✅ **Verify:** Check that the ~105 previously failed races now have results
✅ **Monitor:** Ensure no new foreign key errors appear in the log

Once verified working:
- Consider backfilling the 156 historical races with missing results
- Document which races are legitimately abandoned vs data issues
- Add data quality metrics to the GUI dashboard

