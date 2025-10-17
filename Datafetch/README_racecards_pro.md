# Racecards Pro Data - Historical Fetch

## Overview

This directory contains a Python script to fetch historical racecard data from The Racing API's `/v1/racecards/pro` endpoint and store it in a fully normalized SQLite database.

## Data Summary

### Dataset Information
- **Date Range**: January 23, 2023 to April 30, 2023 (98 days)
- **Total Races**: 3,848
- **Total Runners**: 40,291
- **Database Size**: 85.32 MB

### Monthly Breakdown
| Month    | Races | Runners |
|----------|-------|---------|
| 2023-01  | 311   | 3,310   |
| 2023-02  | 1,033 | 10,550  |
| 2023-03  | 1,194 | 12,368  |
| 2023-04  | 1,310 | 14,063  |

### Entity Counts
| Entity Type              | Count   |
|--------------------------|---------|
| Unique Horses            | 17,625  |
| Unique Trainers          | 1,843   |
| Unique Jockeys           | 1,497   |
| Unique Owners            | 11,244  |
| Unique Dams (Mothers)    | 14,752  |
| Unique Sires (Fathers)   | 1,314   |
| Unique Damsires          | 1,842   |
| Odds Records             | 245,525 |
| Quote Records            | 19,195  |
| Medical Records          | 5,673   |
| Stable Tour Records      | 6,463   |
| Past Results Flags       | 14,268  |
| Previous Trainer Records | 26,806  |
| Previous Owner Records   | 32,353  |
| Trainer 14-Day Stats     | 120,873 |

## Database Schema

The database uses a **fully normalized** relational structure with 20 tables:

### Core Entity Tables
1. **`races`** - Main race information with race metadata
2. **`runners`** - Links horses to races with runner-specific data
3. **`horses`** - Unique horses with biographical data
4. **`trainers`** - Trainer information
5. **`jockeys`** - Jockey information
6. **`owners`** - Owner information

### Pedigree Tables
7. **`dams`** - Mother horses
8. **`sires`** - Father horses
9. **`damsires`** - Maternal grandsires

### Nested Data Tables (One-to-Many Relationships)
10. **`runner_odds`** - Historical odds for runners
11. **`runner_quotes`** - Press quotes about runners
12. **`runner_medical`** - Medical history
13. **`runner_stable_tour`** - Stable tour comments
14. **`runner_past_results_flags`** - Performance flags
15. **`prev_trainers`** - Historical trainer changes
16. **`prev_owners`** - Historical owner changes
17. **`trainer_14_days`** - Recent trainer performance statistics

### System Tables
18. **`sqlite_sequence`** - Auto-increment tracking
19. **`sqlite_stat1`** - Query optimizer statistics
20. **`sqlite_stat4`** - Query optimizer statistics

## Files

### `fetch_racecards_pro.py`
Main Python script for fetching and storing racecard data.

**Features:**
- ✅ Fully normalized database schema with foreign keys
- ✅ Incremental fetching (checks existing dates, only fetches missing)
- ✅ Rate limiting (0.55 seconds between requests)
- ✅ Retry logic with exponential backoff for API errors
- ✅ Comprehensive error handling and logging
- ✅ Transaction safety (rollback on errors)
- ✅ Database optimization (indexes, VACUUM, ANALYZE)

**Configuration:**
- API Credentials: `reqd_files/cred.txt`
- Rate Limit: 0.55 seconds
- Database Path: `racing_pro.db`
- Date Range: Configurable via `START_DATE` and `END_DATE`

### `racing_pro.db`
SQLite database containing all fetched data (gitignored).

### `fetch_racecards_pro.log`
Log file with detailed execution information (gitignored).

## Usage

### Running the Script

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the script
python Datafetch/fetch_racecards_pro.py
```

The script will:
1. Connect to the database (creates if doesn't exist)
2. Check for existing dates
3. Fetch missing dates only
4. Display progress for each date
5. Create indexes and optimize database
6. Show final statistics

### Example Queries

#### Get all races for a specific date
```sql
SELECT * FROM races WHERE date = '2023-04-30';
```

#### Get runners with full pedigree for a race
```sql
SELECT 
    h.name as horse,
    t.name as trainer,
    j.name as jockey,
    d.name as dam,
    s.name as sire,
    ds.name as damsire
FROM runners ru
LEFT JOIN horses h ON ru.horse_id = h.horse_id
LEFT JOIN trainers t ON ru.trainer_id = t.trainer_id
LEFT JOIN jockeys j ON ru.jockey_id = j.jockey_id
LEFT JOIN dams d ON h.dam_id = d.dam_id
LEFT JOIN sires s ON h.sire_id = s.sire_id
LEFT JOIN damsires ds ON h.damsire_id = ds.damsire_id
WHERE ru.race_id = 'rac_10879609';
```

#### Get all odds for a specific runner
```sql
SELECT odds_value, timestamp 
FROM runner_odds 
WHERE runner_id = 1234
ORDER BY created_at;
```

#### Find most active courses
```sql
SELECT course, COUNT(*) as race_count
FROM races
GROUP BY course
ORDER BY race_count DESC
LIMIT 10;
```

#### Get trainer statistics with recent performance
```sql
SELECT 
    t.name,
    t.location,
    td.stat_key,
    td.stat_value
FROM trainers t
LEFT JOIN trainer_14_days td ON t.trainer_id = td.trainer_id
WHERE t.trainer_id = 'trainer_123';
```

## Data Quality

### Foreign Key Integrity
- ✅ 100% of runners have a valid horse_id
- ✅ 100% of runners have a valid trainer_id
- ✅ 96.5% of runners have a valid jockey_id (some races don't have jockey assigned yet)
- ✅ 100% of horses have pedigree information (dam and sire)

### Coverage
- ✅ All 98 days from Jan 23 to Apr 30, 2023
- ✅ Comprehensive nested data capture (odds, quotes, medical records)
- ✅ Historical data preserved (previous trainers/owners)

## Performance

### Fetch Statistics
- **Total API Calls**: 95 (3 days already in DB from testing)
- **Average Time per Request**: ~2.5 seconds (including rate limiting)
- **Total Fetch Time**: ~3.5 minutes
- **Rate Limiting**: 0.55 seconds between requests

### Database Performance
- **Indexes**: 16 indexes on frequently queried fields
- **Optimized**: VACUUM and ANALYZE run after bulk insert
- **Size**: 85.32 MB for ~500K records across all tables

## API Endpoint Details

**Endpoint**: `https://api.theracingapi.com/v1/racecards/pro`

**Parameters**:
- `date`: YYYY-MM-DD format

**Authentication**: HTTP Basic Auth
- Username and password loaded from `reqd_files/cred.txt`

**Rate Limit**: 0.55 seconds between requests (conservative)

**Data Start Date**: 2023-01-23 (as per API documentation)

## Extending the Dataset

To fetch additional dates, modify the `START_DATE` and `END_DATE` constants in `fetch_racecards_pro.py`:

```python
START_DATE = "2023-01-23"
END_DATE = "2023-12-31"  # Extend to end of year
```

The script will automatically skip dates already in the database and only fetch missing dates.

## Top 10 Most Active Courses

| Course              | Races |
|---------------------|-------|
| Wolverhampton (AW)  | 194   |
| Sha Tin             | 160   |
| Southwell (AW)      | 156   |
| Lingfield (AW)      | 155   |
| Newcastle (AW)      | 142   |
| Kempton (AW)        | 126   |
| Dundalk (AW)        | 109   |
| Happy Valley        | 108   |
| Chelmsford (AW)     | 84    |
| Doncaster           | 82    |

## Troubleshooting

### Error: API 503 Service Unavailable
The script automatically retries with exponential backoff. Check the log file for details.

### Error: Database is locked
Ensure no other processes are accessing the database. Close any DB browser tools.

### Missing credentials
Ensure `reqd_files/cred.txt` exists with username on line 1 and password on line 2.

## Notes

- The database file (`racing_pro.db`) is excluded from git via `.gitignore`
- Log files are also gitignored
- The script is idempotent - it can be run multiple times safely
- Foreign keys are enabled for data integrity
- All transactions are atomic (either all succeed or all rollback)

## Future Enhancements

Potential improvements for consideration:
- Add command-line arguments for date range
- Progress bar with `tqdm` for better UX
- Parallel processing for faster fetching
- Export functions to CSV/JSON
- Data validation and quality checks
- Automated daily updates via cron/scheduler

---

**Created**: October 18, 2025  
**Last Updated**: October 18, 2025  
**Script Version**: 1.0  
**Database Schema Version**: 1.0

