# Database Rebuild Troubleshooting Guide

## If GUI Freezes

The rebuild worker now prints detailed progress to the terminal. If the GUI appears frozen, **check the terminal** where you launched `racecard_gui.py` - it will show what's happening.

### Expected Terminal Output

When you click "REBUILD ENTIRE DATABASE", you should see:

```
[GUI] Starting rebuild: 2024-10-01 to 2024-10-21
[GUI] Database path: /Users/darcy5d/Desktop/DD_AI_models/QE2/Datafetch/racing_pro.db
[GUI] Creating RebuildDatabaseWorker...
[GUI] Worker created successfully
[GUI] Connecting signals...
[GUI] Signals connected
[GUI] Starting worker thread...
[GUI] Worker thread started, check terminal for progress updates

[RebuildWorker] Thread started!
[RebuildWorker] Date range: 2024-10-01 to 2024-10-21
[RebuildWorker] Database: /Users/darcy5d/Desktop/DD_AI_models/QE2/Datafetch/racing_pro.db

============================================================
DATABASE REBUILD STARTING
============================================================

Loading API credentials...
Looking for cred file at: /Users/darcy5d/Desktop/DD_AI_models/QE2/Datafetch/reqd_files/cred.txt
✓ Credentials loaded

Creating backup: racing_pro_backup_20241020_235959.db
✓ Backup created (85.3 MB)
  Location: /Users/darcy5d/Desktop/DD_AI_models/QE2/Datafetch/racing_pro_backup_20241020_235959.db

Removing old database...
Creating fresh schema...
✓ Fresh schema created with runner_market_odds table

... (more progress messages)
```

### If It Stops Early

**Check where the output stops**:

1. **Stops at "Creating RebuildDatabaseWorker..."**
   - Issue: Import error or Python path problem
   - Check: `import sys; print(sys.path)` in Python

2. **Stops at "Thread started!" but before "DATABASE REBUILD STARTING"**
   - Issue: Exception in try block before first print
   - Unlikely with current code

3. **Stops at "Loading API credentials..."**
   - Issue: Credentials file not found or can't be read
   - Fix: Check `/Users/darcy5d/Desktop/DD_AI_models/QE2/Datafetch/reqd_files/cred.txt` exists
   - Should have 2 lines: username on line 1, password on line 2

4. **Stops at "Creating backup..."**
   - Issue: Can't write backup file (permissions, disk space)
   - Fix: Check disk space and write permissions in Datafetch folder

5. **Stops at "Creating fresh schema..."**
   - Issue: Can't delete or create database file
   - Fix: Check no other process has database open
   - Fix: Check write permissions

6. **Shows "ERROR:" message**
   - The error details will be printed
   - Error will also appear in GUI error dialog

## How to Restart After Freeze

1. **Force quit the GUI** (if frozen):
   ```bash
   ps aux | grep racecard_gui
   kill <PID>
   ```

2. **Restart**:
   ```bash
   cd /Users/darcy5d/Desktop/DD_AI_models/QE2/Datafetch
   python racecard_gui.py
   ```

3. **Try again** - now with debug output!

## Common Issues

### Issue: "Failed to load API credentials"

**Cause**: Credentials file missing or malformed

**Fix**:
```bash
cd /Users/darcy5d/Desktop/DD_AI_models/QE2/Datafetch
cat reqd_files/cred.txt
```

Should show:
```
your_username
your_password
```

### Issue: "Permission denied" when creating backup

**Cause**: No write access to Datafetch folder

**Fix**:
```bash
ls -ld /Users/darcy5d/Desktop/DD_AI_models/QE2/Datafetch
chmod u+w /Users/darcy5d/Desktop/DD_AI_models/QE2/Datafetch
```

### Issue: "No such file or directory" for database

**Cause**: Database path incorrect

**Fix**: Check the database exists:
```bash
ls -lh /Users/darcy5d/Desktop/DD_AI_models/QE2/Datafetch/racing_pro.db
```

If it doesn't exist, you need to fetch data first using Option 1 or 2.

### Issue: GUI Freezes but No Terminal Output

**Cause**: Worker not starting at all

**Check**:
1. Is PySide6 installed? `pip list | grep PySide6`
2. Are there Python errors in terminal when launching GUI?
3. Try running from terminal with: `python -u racecard_gui.py` (unbuffered output)

## Test the Worker Directly

If the GUI keeps freezing, test the worker standalone:

```python
# test_rebuild.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'gui'))

from rebuild_database_worker import RebuildDatabaseWorker

# Create worker (don't use QThread features)
worker = RebuildDatabaseWorker(
    start_date="2024-10-15", 
    end_date="2024-10-16",  # Just 2 days
    db_path="racing_pro.db"
)

# Run directly (not as thread)
worker.run()
```

Run it:
```bash
cd /Users/darcy5d/Desktop/DD_AI_models/QE2/Datafetch
python test_rebuild.py
```

This will show if the worker itself has issues independent of the GUI.

## Getting Help

If stuck, provide:
1. **Terminal output** up to where it stops
2. **Date range** you selected
3. **Any error messages** from terminal or GUI
4. **Database size**: `ls -lh racing_pro.db`
5. **Disk space**: `df -h .`

## Quick Fix: Restore from Backup

If rebuild fails partway through:

```bash
cd /Users/darcy5d/Desktop/DD_AI_models/QE2/Datafetch

# Find latest backup
ls -lt racing_pro_backup_*.db | head -1

# Restore it
cp racing_pro_backup_YYYYMMDD_HHMMSS.db racing_pro.db
```

Your data is safe!


