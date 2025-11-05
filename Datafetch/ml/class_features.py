#!/usr/bin/env python3
"""
Class Movement Features
Calculates class-based features for horse racing predictions

Class changes are HUGE in racing:
- Dropping in class = easier competition (strong positive signal)
- Rising in class = harder competition (negative signal)
"""

import numpy as np
from typing import List, Dict, Optional


def parse_race_class(class_str: Optional[str]) -> Optional[int]:
    """
    Parse race class string to numeric value
    
    Class hierarchy (lower = better quality):
        Class 1 = 1 (highest quality)
        Class 2 = 2
        ...
        Class 7 = 7 (lowest quality)
        Empty/None = None
    
    Args:
        class_str: Class string from database (e.g., "Class 5", "5", "")
        
    Returns:
        Integer 1-7 or None if unparseable
    """
    if not class_str or class_str.strip() == '':
        return None
    
    class_str = str(class_str).strip().upper()
    
    # Try to extract number from "Class 5" format
    if 'CLASS' in class_str:
        parts = class_str.split()
        for part in parts:
            try:
                num = int(part)
                if 1 <= num <= 7:
                    return num
            except ValueError:
                continue
    
    # Try direct integer conversion
    try:
        num = int(class_str)
        if 1 <= num <= 7:
            return num
    except ValueError:
        pass
    
    return None


def calculate_class_features(horse_past_races: List[Dict], 
                            current_race_class: Optional[str]) -> Dict:
    """
    Calculate class-based features
    
    Features:
        - class_last_3_avg: Average class of last 3 races
        - class_change: Difference from recent average (negative = dropping)
        - dropping_in_class: Binary flag (1 if dropping significantly)
        - rising_in_class: Binary flag (1 if rising significantly)
    
    Args:
        horse_past_races: List of past race dicts with 'class' field
        current_race_class: Today's race class string
        
    Returns:
        Dict with 4 features
        
    Examples:
        Recent classes [5, 5, 6], today's class 6 = dropping (easier race)
        Recent classes [4, 4, 4], today's class 3 = rising (harder race)
    """
    # Parse current race class
    current_class = parse_race_class(current_race_class)
    
    if not horse_past_races or current_class is None:
        return {
            'class_last_3_avg': None,
            'class_change': None,
            'dropping_in_class': 0,
            'rising_in_class': 0
        }
    
    # Extract classes from past races (last 3)
    recent_classes = []
    for race in horse_past_races[:3]:
        # Skip if race is not a dict
        if not isinstance(race, dict):
            continue
        
        class_val = race.get('class')
        
        # Skip if class is a dict
        if isinstance(class_val, dict):
            continue
            
        race_class = parse_race_class(class_val)
        if race_class is not None:
            recent_classes.append(race_class)
    
    if not recent_classes:
        return {
            'class_last_3_avg': None,
            'class_change': None,
            'dropping_in_class': 0,
            'rising_in_class': 0
        }
    
    # Calculate average recent class
    avg_recent_class = np.mean(recent_classes)
    
    # Class change (positive = rising to harder class, negative = dropping to easier)
    # Note: Class 1 is hardest, Class 7 is easiest
    # So current_class - avg = positive means going to easier races (good!)
    class_change = current_class - avg_recent_class
    
    # Flag significant changes (>0.5 class difference)
    # Dropping = going to easier class (class number increases)
    dropping_in_class = 1 if class_change > 0.5 else 0
    
    # Rising = going to harder class (class number decreases)  
    rising_in_class = 1 if class_change < -0.5 else 0
    
    return {
        'class_last_3_avg': float(avg_recent_class),
        'class_change': float(class_change),
        'dropping_in_class': dropping_in_class,
        'rising_in_class': rising_in_class
    }

