#!/usr/bin/env python3
"""
Query Racecards Pro Database - Interactive Query Tool
Provides common queries and examples for exploring the racing data
"""

import sqlite3
import sys
from pathlib import Path
from typing import List, Tuple

DB_PATH = Path(__file__).parent / "racing_pro.db"

def connect_db():
    """Connect to the database"""
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        print("Run fetch_racecards_pro.py first to create the database.")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)


def print_table(headers: List[str], rows: List[Tuple], max_width: int = 30):
    """Print results in a formatted table"""
    # Calculate column widths
    col_widths = []
    for i, header in enumerate(headers):
        max_len = len(str(header))
        for row in rows:
            if i < len(row):
                max_len = max(max_len, len(str(row[i])))
        col_widths.append(min(max_len, max_width))
    
    # Print header
    header_row = " | ".join(str(h).ljust(w) for h, w in zip(headers, col_widths))
    print(header_row)
    print("-" * len(header_row))
    
    # Print rows
    for row in rows:
        row_str = " | ".join(str(val)[:w].ljust(w) for val, w in zip(row, col_widths))
        print(row_str)


def query_database_stats(conn):
    """Show database statistics"""
    cursor = conn.cursor()
    
    print("=" * 80)
    print("DATABASE STATISTICS")
    print("=" * 80)
    
    # Date range
    cursor.execute("SELECT MIN(date), MAX(date), COUNT(DISTINCT date) FROM races")
    min_date, max_date, unique_dates = cursor.fetchone()
    print(f"\nDate Range: {min_date} to {max_date} ({unique_dates} days)")
    
    # Total counts
    tables = [
        ('races', 'Total Races'),
        ('runners', 'Total Runners'),
        ('horses', 'Unique Horses'),
        ('trainers', 'Unique Trainers'),
        ('jockeys', 'Unique Jockeys'),
        ('owners', 'Unique Owners')
    ]
    
    print("\nRecord Counts:")
    for table, label in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {label:20s}: {count:>8,}")


def query_races_by_date(conn, date: str):
    """Get all races for a specific date"""
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT race_id, course, off_time, race_name, field_size
        FROM races
        WHERE date = ?
        ORDER BY off_time
    """, (date,))
    
    results = cursor.fetchall()
    
    if not results:
        print(f"No races found for {date}")
        return
    
    print(f"\n{'=' * 80}")
    print(f"RACES ON {date}")
    print('=' * 80)
    print_table(['Race ID', 'Course', 'Time', 'Race Name', 'Field'], results)
    print(f"\nTotal: {len(results)} races")


def query_race_details(conn, race_id: str):
    """Get detailed information about a specific race"""
    cursor = conn.cursor()
    
    # Race info
    cursor.execute("""
        SELECT date, course, off_time, race_name, distance, going, 
               surface, race_class, field_size
        FROM races
        WHERE race_id = ?
    """, (race_id,))
    
    race = cursor.fetchone()
    if not race:
        print(f"Race {race_id} not found")
        return
    
    print(f"\n{'=' * 80}")
    print(f"RACE DETAILS: {race_id}")
    print('=' * 80)
    print(f"Date: {race[0]}")
    print(f"Course: {race[1]}")
    print(f"Time: {race[2]}")
    print(f"Race Name: {race[3]}")
    print(f"Distance: {race[4]}")
    print(f"Going: {race[5]}")
    print(f"Surface: {race[6]}")
    print(f"Class: {race[7]}")
    print(f"Field Size: {race[8]}")
    
    # Runners
    cursor.execute("""
        SELECT 
            ru.number,
            h.name,
            t.name,
            j.name,
            ru.draw,
            ru.lbs
        FROM runners ru
        LEFT JOIN horses h ON ru.horse_id = h.horse_id
        LEFT JOIN trainers t ON ru.trainer_id = t.trainer_id
        LEFT JOIN jockeys j ON ru.jockey_id = j.jockey_id
        WHERE ru.race_id = ?
        ORDER BY CAST(ru.number AS INTEGER)
    """, (race_id,))
    
    runners = cursor.fetchall()
    print(f"\n{'=' * 80}")
    print("RUNNERS")
    print('=' * 80)
    print_table(['No.', 'Horse', 'Trainer', 'Jockey', 'Draw', 'Weight'], runners)


def query_horse_details(conn, horse_name: str):
    """Get detailed information about a horse"""
    cursor = conn.cursor()
    
    # Horse info
    cursor.execute("""
        SELECT 
            h.horse_id,
            h.name,
            h.age,
            h.sex,
            h.colour,
            d.name as dam,
            s.name as sire,
            ds.name as damsire,
            t.name as current_trainer
        FROM horses h
        LEFT JOIN dams d ON h.dam_id = d.dam_id
        LEFT JOIN sires s ON h.sire_id = s.sire_id
        LEFT JOIN damsires ds ON h.damsire_id = ds.damsire_id
        LEFT JOIN runners ru ON h.horse_id = ru.horse_id
        LEFT JOIN trainers t ON ru.trainer_id = t.trainer_id
        WHERE h.name LIKE ?
        LIMIT 1
    """, (f"%{horse_name}%",))
    
    horse = cursor.fetchone()
    if not horse:
        print(f"Horse matching '{horse_name}' not found")
        return
    
    print(f"\n{'=' * 80}")
    print(f"HORSE DETAILS: {horse[1]}")
    print('=' * 80)
    print(f"Horse ID: {horse[0]}")
    print(f"Age: {horse[2]}")
    print(f"Sex: {horse[3]}")
    print(f"Colour: {horse[4]}")
    print(f"Dam (Mother): {horse[5]}")
    print(f"Sire (Father): {horse[6]}")
    print(f"Damsire: {horse[7]}")
    print(f"Current Trainer: {horse[8]}")
    
    # Recent runs
    cursor.execute("""
        SELECT 
            r.date,
            r.course,
            r.race_name,
            ru.number
        FROM runners ru
        JOIN races r ON ru.race_id = r.race_id
        WHERE ru.horse_id = ?
        ORDER BY r.date DESC
        LIMIT 10
    """, (horse[0],))
    
    runs = cursor.fetchall()
    print(f"\n{'=' * 80}")
    print("RECENT RUNS")
    print('=' * 80)
    print_table(['Date', 'Course', 'Race', 'No.'], runs)


def query_trainer_stats(conn, trainer_name: str):
    """Get statistics for a trainer"""
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT trainer_id, name, location
        FROM trainers
        WHERE name LIKE ?
        LIMIT 1
    """, (f"%{trainer_name}%",))
    
    trainer = cursor.fetchone()
    if not trainer:
        print(f"Trainer matching '{trainer_name}' not found")
        return
    
    print(f"\n{'=' * 80}")
    print(f"TRAINER: {trainer[1]}")
    print('=' * 80)
    print(f"Trainer ID: {trainer[0]}")
    print(f"Location: {trainer[2]}")
    
    # Runner count
    cursor.execute("""
        SELECT COUNT(*)
        FROM runners
        WHERE trainer_id = ?
    """, (trainer[0],))
    
    runner_count = cursor.fetchone()[0]
    print(f"Runners in dataset: {runner_count}")
    
    # Recent runners
    cursor.execute("""
        SELECT 
            r.date,
            r.course,
            h.name,
            r.race_name
        FROM runners ru
        JOIN races r ON ru.race_id = r.race_id
        JOIN horses h ON ru.horse_id = h.horse_id
        WHERE ru.trainer_id = ?
        ORDER BY r.date DESC
        LIMIT 10
    """, (trainer[0],))
    
    recent_runners = cursor.fetchall()
    print(f"\n{'=' * 80}")
    print("RECENT RUNNERS")
    print('=' * 80)
    print_table(['Date', 'Course', 'Horse', 'Race'], recent_runners)


def query_course_stats(conn, course_name: str):
    """Get statistics for a course"""
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            course,
            COUNT(*) as race_count,
            MIN(date) as first_race,
            MAX(date) as last_race
        FROM races
        WHERE course LIKE ?
        GROUP BY course
    """, (f"%{course_name}%",))
    
    results = cursor.fetchall()
    
    if not results:
        print(f"Course matching '{course_name}' not found")
        return
    
    print(f"\n{'=' * 80}")
    print("COURSE STATISTICS")
    print('=' * 80)
    print_table(['Course', 'Races', 'First Date', 'Last Date'], results)
    
    # Sample races
    for course in results:
        cursor.execute("""
            SELECT date, race_name, field_size
            FROM races
            WHERE course = ?
            ORDER BY date DESC
            LIMIT 5
        """, (course[0],))
        
        races = cursor.fetchall()
        print(f"\n{'=' * 80}")
        print(f"RECENT RACES AT {course[0]}")
        print('=' * 80)
        print_table(['Date', 'Race Name', 'Field'], races)


def main():
    """Main interactive menu"""
    conn = connect_db()
    
    while True:
        print("\n" + "=" * 80)
        print("RACECARDS PRO DATABASE - QUERY TOOL")
        print("=" * 80)
        print("\n1. Database Statistics")
        print("2. Races by Date")
        print("3. Race Details")
        print("4. Horse Details")
        print("5. Trainer Statistics")
        print("6. Course Statistics")
        print("7. Custom SQL Query")
        print("0. Exit")
        
        choice = input("\nEnter your choice: ").strip()
        
        if choice == "0":
            print("Goodbye!")
            break
        elif choice == "1":
            query_database_stats(conn)
        elif choice == "2":
            date = input("Enter date (YYYY-MM-DD): ").strip()
            query_races_by_date(conn, date)
        elif choice == "3":
            race_id = input("Enter race ID: ").strip()
            query_race_details(conn, race_id)
        elif choice == "4":
            horse_name = input("Enter horse name (partial match OK): ").strip()
            query_horse_details(conn, horse_name)
        elif choice == "5":
            trainer_name = input("Enter trainer name (partial match OK): ").strip()
            query_trainer_stats(conn, trainer_name)
        elif choice == "6":
            course_name = input("Enter course name (partial match OK): ").strip()
            query_course_stats(conn, course_name)
        elif choice == "7":
            print("\nEnter your SQL query (press Enter twice to execute):")
            lines = []
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
            
            query = " ".join(lines)
            if query:
                try:
                    cursor = conn.cursor()
                    cursor.execute(query)
                    results = cursor.fetchall()
                    
                    if results:
                        # Get column names
                        headers = [desc[0] for desc in cursor.description]
                        print_table(headers, results)
                        print(f"\nTotal rows: {len(results)}")
                    else:
                        print("Query executed successfully (no results)")
                except Exception as e:
                    print(f"Error: {e}")
        else:
            print("Invalid choice. Please try again.")
        
        input("\nPress Enter to continue...")
    
    conn.close()


if __name__ == "__main__":
    main()

