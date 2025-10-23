#!/usr/bin/env python3
"""
Diagnostic tool to check RPR and TS coverage in upcoming races
"""

import sqlite3
from pathlib import Path

def check_coverage():
    db_path = Path(__file__).parent / "upcoming_races.db"
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    print("=" * 80)
    print("RPR & TS DATA COVERAGE ANALYSIS")
    print("=" * 80)
    
    # Overall statistics
    cursor.execute("""
        SELECT 
            COUNT(*) as total_runners,
            COUNT(CASE WHEN rpr IS NOT NULL AND rpr != '' AND rpr != '-' THEN 1 END) as has_rpr,
            COUNT(CASE WHEN ts IS NOT NULL AND ts != '' AND ts != '-' THEN 1 END) as has_ts,
            COUNT(CASE WHEN (rpr IS NULL OR rpr = '' OR rpr = '-') 
                        AND (ts IS NULL OR ts = '' OR ts = '-') THEN 1 END) as missing_both
        FROM runners
    """)
    
    total, has_rpr, has_ts, missing_both = cursor.fetchone()
    
    print(f"\n📊 OVERALL STATISTICS")
    print(f"{'─' * 80}")
    print(f"  Total runners:        {total:,}")
    print(f"  Has RPR:              {has_rpr:,} ({has_rpr/total*100:.1f}%)")
    print(f"  Has TS:               {has_ts:,} ({has_ts/total*100:.1f}%)")
    print(f"  Missing both RPR/TS:  {missing_both:,} ({missing_both/total*100:.1f}%)")
    print()
    
    # Race-by-race breakdown
    cursor.execute("""
        SELECT 
            r.race_id,
            races.course,
            races.off_time,
            races.race_name,
            races.distance,
            races.race_class,
            COUNT(*) as total_runners,
            COUNT(CASE WHEN r.rpr IS NOT NULL AND r.rpr != '' AND r.rpr != '-' THEN 1 END) as has_rpr,
            COUNT(CASE WHEN r.ts IS NOT NULL AND r.ts != '' AND r.ts != '-' THEN 1 END) as has_ts
        FROM runners r
        JOIN races ON r.race_id = races.race_id
        GROUP BY r.race_id
        ORDER BY 
            CAST((COUNT(CASE WHEN r.rpr IS NOT NULL AND r.rpr != '' AND r.rpr != '-' THEN 1 END) * 1.0 / COUNT(*)) AS REAL) ASC
    """)
    
    races = cursor.fetchall()
    
    print(f"📋 RACE-BY-RACE BREAKDOWN (sorted by RPR coverage, worst first)")
    print(f"{'─' * 80}")
    
    # Show worst 20 races
    print(f"\n⚠️  WORST 20 RACES FOR RPR COVERAGE:\n")
    for i, race in enumerate(races[:20], 1):
        race_id, course, time, race_name, distance, race_class, total, rpr_count, ts_count = race
        rpr_pct = (rpr_count / total * 100) if total > 0 else 0
        ts_pct = (ts_count / total * 100) if total > 0 else 0
        
        print(f"{i:2d}. {course:20s} {time:8s} - {distance:6s} {race_class or 'N/A':10s}")
        print(f"    {race_name[:60] if race_name else 'Unnamed Race'}")
        print(f"    Runners: {total:2d} | RPR: {rpr_count:2d}/{total:2d} ({rpr_pct:5.1f}%) | TS: {ts_count:2d}/{total:2d} ({ts_pct:5.1f}%)")
        print()
    
    # Show races with NO RPR data
    cursor.execute("""
        SELECT 
            races.course,
            races.off_time,
            races.race_name,
            races.distance,
            COUNT(*) as total_runners
        FROM runners r
        JOIN races ON r.race_id = races.race_id
        GROUP BY r.race_id
        HAVING COUNT(CASE WHEN r.rpr IS NOT NULL AND r.rpr != '' AND r.rpr != '-' THEN 1 END) = 0
    """)
    
    no_rpr_races = cursor.fetchall()
    
    if no_rpr_races:
        print(f"\n🚨 RACES WITH ZERO RPR DATA ({len(no_rpr_races)} races):\n")
        for course, time, race_name, distance, total in no_rpr_races:
            print(f"  • {course:20s} {time:8s} - {distance:6s} ({total} runners)")
            print(f"    {race_name[:60] if race_name else 'Unnamed Race'}")
            print()
    else:
        print(f"\n✅ All races have at least some RPR data")
    
    # Region/country breakdown
    cursor.execute("""
        SELECT 
            races.region,
            COUNT(DISTINCT r.race_id) as total_races,
            COUNT(*) as total_runners,
            COUNT(CASE WHEN r.rpr IS NOT NULL AND r.rpr != '' AND r.rpr != '-' THEN 1 END) as has_rpr,
            COUNT(CASE WHEN r.ts IS NOT NULL AND r.ts != '' AND r.ts != '-' THEN 1 END) as has_ts
        FROM runners r
        JOIN races ON r.race_id = races.race_id
        WHERE races.region IS NOT NULL AND races.region != ''
        GROUP BY races.region
        ORDER BY COUNT(*) DESC
    """)
    
    regions = cursor.fetchall()
    
    if regions:
        print(f"\n🌍 COVERAGE BY REGION:")
        print(f"{'─' * 80}")
        for region, race_count, total, rpr_count, ts_count in regions:
            rpr_pct = (rpr_count / total * 100) if total > 0 else 0
            ts_pct = (ts_count / total * 100) if total > 0 else 0
            print(f"  {region:15s}: {race_count:3d} races, {total:4d} runners")
            print(f"                  RPR: {rpr_pct:5.1f}% | TS: {ts_pct:5.1f}%")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("💡 TIP: RPR/TS data is often missing for international races")
    print("         The model uses smart defaults for missing values")
    print("=" * 80)

if __name__ == "__main__":
    check_coverage()


