#!/usr/bin/env python3
"""
Course Specialist Features
Identifies horses that perform exceptionally well at specific courses

Some horses LOVE certain tracks due to:
- Track shape (left/right handed, turning radius)
- Surface characteristics
- Distance suited to track
- Familiarity with environment
"""

from typing import List, Dict, Optional


def calculate_course_specialist_features(horse_past_races: List[Dict],
                                        current_course: Optional[str]) -> Dict:
    """
    Calculate course-specific performance features
    
    Features:
        - course_runs: Number of previous runs at this course
        - course_wins: Wins at this course
        - course_win_rate: Win rate at this course
        - course_place_rate: Top 3 rate at this course
        - course_specialist: Binary flag (3+ runs, 30%+ win rate)
    
    Args:
        horse_past_races: List of past race dicts with 'course', 'position'
        current_course: Today's course name
        
    Returns:
        Dict with 5 features
        
    Examples:
        Horse with 4 wins from 10 runs at Wolverhampton = 40% win rate (specialist!)
        Horse with 0 runs at Newbury = no specialist signal
    """
    # Default return
    default_return = {
        'course_runs': 0,
        'course_wins': 0,
        'course_win_rate': 0.0,
        'course_place_rate': 0.0,
        'course_specialist': 0
    }
    
    # Check if inputs are valid
    if not horse_past_races or not current_course or isinstance(current_course, dict):
        return default_return
    
    # Convert course to string
    try:
        current_course = str(current_course).lower().strip()
        if not current_course:
            return default_return
    except:
        return default_return
    
    # Filter races at this specific course
    course_runs = []
    for race in horse_past_races:
        # Skip if race is not a dict
        if not isinstance(race, dict):
            continue
            
        race_course = race.get('course')
        
        # Skip if course is None or dict
        if race_course is None or isinstance(race_course, dict):
            continue
        
        try:
            race_course_str = str(race_course).lower().strip()
            if race_course_str == current_course:
                course_runs.append(race)
        except:
            continue
    
    if not course_runs:
        return default_return
    
    # Count wins and places
    course_wins = 0
    course_places = 0
    
    for race in course_runs:
        position = race.get('position')
        
        # Skip if position is None or dict
        if position is None or isinstance(position, dict):
            continue
        
        # Try to parse position
        try:
            pos_int = int(position)
            if pos_int == 1:
                course_wins += 1
                course_places += 1
            elif pos_int <= 3:
                course_places += 1
        except (ValueError, TypeError):
            # Skip non-numeric positions (e.g., 'DQ', 'PU')
            pass
    
    # Calculate rates (need at least 2 runs for meaningful rate)
    num_runs = len(course_runs)
    
    if num_runs >= 2:
        course_win_rate = course_wins / num_runs
        course_place_rate = course_places / num_runs
    else:
        # Too few runs, use counts only
        course_win_rate = 0.0
        course_place_rate = 0.0
    
    # Flag true specialists (3+ runs AND 30%+ win rate)
    is_specialist = 1 if (num_runs >= 3 and course_win_rate >= 0.3) else 0
    
    return {
        'course_runs': num_runs,
        'course_wins': course_wins,
        'course_win_rate': float(course_win_rate),
        'course_place_rate': float(course_place_rate),
        'course_specialist': is_specialist
    }
