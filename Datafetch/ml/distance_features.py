#!/usr/bin/env python3
"""
Distance Optimization Features
Identifies horses' optimal distances and suitability for today's race

Horses have preferred distances based on:
- Stamina vs speed balance
- Running style (front-runner vs closer)
- Breeding (sprinter vs stayer bloodlines)

1200m sprinter in 2400m race = wrong trip (major disadvantage)
2000m specialist at 2000m = optimal distance (advantage)
"""

import numpy as np
from typing import List, Dict, Optional


def round_distance(distance_f: float) -> float:
    """Round distance to nearest 0.5 furlong for grouping"""
    return round(distance_f * 2) / 2


def calculate_distance_features(horse_past_races: List[Dict],
                               current_distance_f: Optional[float]) -> Dict:
    """
    Calculate distance suitability features
    
    Features:
        - best_distance_f: Distance with best average finishing position
        - distance_from_optimal: Absolute difference from best distance
        - runs_at_distance: Runs at similar distance (±0.5f)
        - win_rate_at_distance: Win rate at this distance range
    
    Args:
        horse_past_races: List of past race dicts with 'distance_f', 'position'
        current_distance_f: Today's race distance in furlongs
        
    Returns:
        Dict with 4 features
        
    Examples:
        Horse best at 8f racing at 8f = optimal (distance_from_optimal = 0)
        Horse best at 6f racing at 10f = wrong trip (distance_from_optimal = 4)
    """
    if not horse_past_races or current_distance_f is None or current_distance_f <= 0:
        return {
            'best_distance_f': None,
            'distance_from_optimal': None,
            'runs_at_distance': 0,
            'win_rate_at_distance': 0.0
        }
    
    # Convert current distance to float
    try:
        current_distance_f = float(current_distance_f)
    except (ValueError, TypeError):
        return {
            'best_distance_f': None,
            'distance_from_optimal': None,
            'runs_at_distance': 0,
            'win_rate_at_distance': 0.0
        }
    
    # Group past races by distance, calculate average position
    distance_performance = {}  # {distance: [positions]}
    
    for race in horse_past_races:
        dist = race.get('distance_f')
        position = race.get('position')
        
        if dist is None or position is None:
            continue
        
        try:
            dist_float = float(dist)
            pos_int = int(position)
            
            if dist_float > 0 and pos_int > 0:
                # Round to nearest 0.5f for grouping
                dist_rounded = round_distance(dist_float)
                
                if dist_rounded not in distance_performance:
                    distance_performance[dist_rounded] = []
                distance_performance[dist_rounded].append(pos_int)
        except (ValueError, TypeError):
            continue
    
    if not distance_performance:
        return {
            'best_distance_f': None,
            'distance_from_optimal': None,
            'runs_at_distance': 0,
            'win_rate_at_distance': 0.0
        }
    
    # Find best distance (lowest average position, min 2 runs)
    best_distance = None
    best_avg_position = 999
    
    for dist, positions in distance_performance.items():
        if len(positions) >= 2:  # Need meaningful sample
            avg_pos = np.mean(positions)
            if avg_pos < best_avg_position:
                best_avg_position = avg_pos
                best_distance = dist
    
    # If no distance with 2+ runs, use distance with best single result
    if best_distance is None:
        for dist, positions in distance_performance.items():
            avg_pos = np.mean(positions)
            if avg_pos < best_avg_position:
                best_avg_position = avg_pos
                best_distance = dist
    
    # Calculate distance from optimal
    if best_distance is not None:
        distance_from_optimal = abs(current_distance_f - best_distance)
    else:
        distance_from_optimal = None
    
    # Performance at today's distance (±0.5f range)
    same_distance_runs = []
    same_distance_wins = 0
    
    for race in horse_past_races:
        dist = race.get('distance_f')
        position = race.get('position')
        
        if dist is None or position is None:
            continue
        
        try:
            dist_float = float(dist)
            pos_int = int(position)
            
            # Check if within 0.5f of current distance
            if abs(dist_float - current_distance_f) <= 0.5:
                same_distance_runs.append(race)
                if pos_int == 1:
                    same_distance_wins += 1
        except (ValueError, TypeError):
            continue
    
    runs_at_distance = len(same_distance_runs)
    
    if runs_at_distance > 0:
        win_rate_at_distance = same_distance_wins / runs_at_distance
    else:
        win_rate_at_distance = 0.0
    
    return {
        'best_distance_f': float(best_distance) if best_distance is not None else None,
        'distance_from_optimal': float(distance_from_optimal) if distance_from_optimal is not None else None,
        'runs_at_distance': runs_at_distance,
        'win_rate_at_distance': float(win_rate_at_distance)
    }

