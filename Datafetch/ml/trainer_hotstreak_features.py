#!/usr/bin/env python3
"""
Trainer Hot Streak Features
Identifies trainers in hot form (strong recent results)

Trainers go through cycles:
- Hot periods: Horses peaking together, confidence high, good strike rates
- Cold periods: Below normal form, fewer winners

Hot trainer with a runner = strong positive signal
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional


def calculate_trainer_hotstreak(trainer_id: Optional[str], 
                               race_date: Optional[str],
                               conn: sqlite3.Connection) -> Dict:
    """
    Calculate trainer recent form features
    
    Features:
        - trainer_wins_last_14d: Wins in last 14 days
        - trainer_runs_last_14d: Total runs in last 14 days
        - trainer_win_rate_recent: Win rate over last 14 days
        - trainer_is_hot: Binary flag (15%+ strike rate AND 3+ wins)
    
    Args:
        trainer_id: Trainer's database ID
        race_date: Today's race date (YYYY-MM-DD format)
        conn: Database connection
        
    Returns:
        Dict with 4 features
        
    Examples:
        Trainer with 5 wins from 20 runs in last 14 days = 25% SR (hot!)
        Trainer with 1 win from 15 runs = 6.7% SR (cold)
    """
    if not trainer_id or not race_date or not conn:
        return {
            'trainer_wins_last_14d': 0,
            'trainer_runs_last_14d': 0,
            'trainer_win_rate_recent': 0.0,
            'trainer_is_hot': 0
        }
    
    try:
        # Parse race date
        race_dt = datetime.strptime(race_date, '%Y-%m-%d')
        
        # Calculate date 14 days ago
        date_14d_ago = race_dt - timedelta(days=14)
        date_14d_str = date_14d_ago.strftime('%Y-%m-%d')
        
        # Query trainer's recent results (before this race)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total_runs,
                SUM(CASE WHEN r.position = '1' THEN 1 ELSE 0 END) as wins
            FROM results r
            JOIN races ra ON r.race_id = ra.race_id
            WHERE r.trainer_id = ?
              AND ra.date >= ?
              AND ra.date < ?
        """, (trainer_id, date_14d_str, race_date))
        
        result = cursor.fetchone()
        
        if result:
            total_runs = result[0] if result[0] is not None else 0
            wins = result[1] if result[1] is not None else 0
        else:
            total_runs = 0
            wins = 0
        
        # Calculate win rate
        if total_runs > 0:
            win_rate = wins / total_runs
        else:
            win_rate = 0.0
        
        # Flag "hot" trainer (15%+ strike rate AND 3+ wins in period)
        is_hot = 1 if (win_rate >= 0.15 and wins >= 3) else 0
        
        return {
            'trainer_wins_last_14d': int(wins),
            'trainer_runs_last_14d': int(total_runs),
            'trainer_win_rate_recent': float(win_rate),
            'trainer_is_hot': is_hot
        }
        
    except (ValueError, sqlite3.Error) as e:
        # Date parsing error or database error
        return {
            'trainer_wins_last_14d': 0,
            'trainer_runs_last_14d': 0,
            'trainer_win_rate_recent': 0.0,
            'trainer_is_hot': 0
        }

