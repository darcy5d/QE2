#!/usr/bin/env python3
"""
Monitor ML Pipeline Progress
Quick status check of data availability and processing state
"""

import sqlite3
from pathlib import Path
from datetime import datetime


def check_status():
    """Check current status of ML pipeline"""
    db_path = Path(__file__).parent.parent / "racing_pro.db"
    
    if not db_path.exists():
        print("❌ Database not found")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("ML PIPELINE STATUS")
    print("="*60 + "\n")
    
    # Racecard data
    print("📊 RACECARD DATA (Original)")
    cursor.execute("SELECT COUNT(*) FROM races")
    race_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM runners")
    runner_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT MIN(date), MAX(date) FROM races")
    date_range = cursor.fetchone()
    
    print(f"  Races: {race_count:,}")
    print(f"  Runners: {runner_count:,}")
    print(f"  Date range: {date_range[0]} to {date_range[1]}")
    
    # Results data
    print("\n📈 RESULTS DATA (Fetched)")
    cursor.execute("SELECT COUNT(*) FROM results")
    result_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT race_id) FROM results")
    races_with_results = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT horse_id) FROM results")
    horses_with_results = cursor.fetchone()[0]
    
    print(f"  Results: {result_count:,}")
    print(f"  Races with results: {races_with_results:,} ({races_with_results/race_count*100:.1f}% of total)")
    print(f"  Unique horses: {horses_with_results:,}")
    
    if result_count > 0:
        cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM results LIMIT 1")
        result_times = cursor.fetchone()
        print(f"  Fetch started: {result_times[0]}")
        print(f"  Last update: {result_times[1]}")
    
    # Statistics
    print("\n📊 COMPUTED STATISTICS")
    
    cursor.execute("SELECT COUNT(*) FROM horse_career_stats WHERE total_runs > 0")
    horse_stats = cursor.fetchone()[0]
    print(f"  Horse career stats: {horse_stats:,}")
    
    cursor.execute("SELECT COUNT(*) FROM trainer_stats")
    trainer_stats = cursor.fetchone()[0]
    print(f"  Trainer stats: {trainer_stats:,}")
    
    cursor.execute("SELECT COUNT(*) FROM jockey_stats")
    jockey_stats = cursor.fetchone()[0]
    print(f"  Jockey stats: {jockey_stats:,}")
    
    cursor.execute("SELECT COUNT(*) FROM trainer_jockey_combos")
    combo_stats = cursor.fetchone()[0]
    print(f"  Trainer-Jockey combos: {combo_stats:,}")
    
    # ML Features
    print("\n🤖 ML FEATURES")
    
    cursor.execute("SELECT COUNT(*) FROM ml_features")
    feature_count = cursor.fetchone()[0]
    print(f"  Feature vectors: {feature_count:,}")
    
    cursor.execute("SELECT COUNT(*) FROM ml_targets")
    target_count = cursor.fetchone()[0]
    print(f"  Target labels: {target_count:,}")
    
    if feature_count > 0:
        cursor.execute("SELECT COUNT(DISTINCT race_id) FROM ml_features")
        races_with_features = cursor.fetchone()[0]
        print(f"  Races with features: {races_with_features:,}")
    
    # Pipeline Status
    print("\n🔄 PIPELINE STATUS")
    
    if result_count == 0:
        print("  ⏳ Step 1: Fetching results... (in progress)")
        print("  ⏸️  Step 2: Computing stats... (waiting)")
        print("  ⏸️  Step 3: Generating features... (waiting)")
    elif horse_stats == 0:
        print("  ✅ Step 1: Results fetched")
        print("  ⏳ Step 2: Computing stats... (ready to run)")
        print("  ⏸️  Step 3: Generating features... (waiting)")
    elif feature_count == 0:
        print("  ✅ Step 1: Results fetched")
        print("  ✅ Step 2: Stats computed")
        print("  ⏳ Step 3: Generating features... (ready to run)")
    else:
        print("  ✅ Step 1: Results fetched")
        print("  ✅ Step 2: Stats computed")
        print("  ✅ Step 3: Features generated")
        print("\n  🎉 Ready for model training!")
    
    # Recommendations
    print("\n💡 NEXT STEPS")
    
    if result_count == 0:
        print("  → Wait for fetch_historical_results.py to complete")
        print("  → Check fetch_results.log for progress")
    elif horse_stats == 0:
        print("  → Run: python ml/compute_stats.py")
        print("  → This will compute career statistics for all entities")
    elif feature_count == 0:
        print("  → Run: python ml/build_ml_dataset.py")
        print("  → Or: python ml/feature_engineer.py")
    else:
        print("  → Ready to train models!")
        print("  → Run: python ml/train_models.py (coming soon)")
        print("  → Explore data in GUI Data Exploration tab")
    
    print("\n" + "="*60 + "\n")
    
    conn.close()


if __name__ == "__main__":
    check_status()





