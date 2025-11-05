#!/usr/bin/env python3
"""
Speed Features Module
Calculates race speed metrics from finish times and distances
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from scipy.stats import linregress


def parse_race_time(time_str: str) -> Optional[float]:
    """
    Parse race time to seconds
    
    Formats:
    - "1:23.45" -> 83.45 seconds
    - "23.45" -> 23.45 seconds  
    - "2:15" -> 135.0 seconds
    
    Args:
        time_str: Time string from results.time
    
    Returns:
        Time in seconds, or None if invalid
    """
    if not time_str or time_str == '':
        return None
    
    try:
        time_str = str(time_str).strip()
        
        if ':' in time_str:
            parts = time_str.split(':')
            if len(parts) != 2:
                return None
            
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        else:
            return float(time_str)
    except (ValueError, AttributeError):
        return None


def calculate_speed(distance_f: float, time_seconds: float) -> Optional[float]:
    """
    Calculate speed in furlongs per second
    
    Args:
        distance_f: Distance in furlongs
        time_seconds: Time in seconds
    
    Returns:
        Speed in furlongs/second, or None if invalid
    """
    if distance_f is None or time_seconds is None or time_seconds <= 0:
        return None
    
    try:
        distance_f = float(distance_f)
        time_seconds = float(time_seconds)
        
        if distance_f <= 0 or time_seconds <= 0:
            return None
        
        return distance_f / time_seconds
    except (ValueError, TypeError):
        return None


class SpeedFeatureCalculator:
    """Calculate speed-based features for a horse"""
    
    def __init__(self):
        self.default_speed = 0.12  # Typical flat racing: ~7.2 furlongs/minute
    
    def calculate_all_speed_features(self, 
                                     horse_past_races: List[Dict],
                                     course: str,
                                     distance_f: float) -> Dict[str, float]:
        """
        Calculate all speed features for a horse
        
        Args:
            horse_past_races: List of past race dicts with 'time', 'distance_f', 'course'
            course: Current race course
            distance_f: Current race distance
        
        Returns:
            Dict of speed features
        """
        # Ensure distance_f is float (might be string from database)
        try:
            distance_f = float(distance_f) if distance_f is not None else 0
        except (ValueError, TypeError):
            distance_f = 0
        
        # Extract speeds from past races
        speeds = []
        for race in horse_past_races:
            time_seconds = parse_race_time(race.get('time'))
            race_distance = race.get('distance_f')
            
            if time_seconds and race_distance:
                speed = calculate_speed(race_distance, time_seconds)
                if speed:
                    # Ensure distance_f is float (might be string from database)
                    try:
                        race_distance_float = float(race_distance)
                    except (ValueError, TypeError):
                        continue
                    
                    speeds.append({
                        'speed': speed,
                        'course': race.get('course'),
                        'distance_f': race_distance_float
                    })
        
        # Calculate features
        features = {}
        
        # 1. Average speed (last 5 races)
        features['horse_avg_speed_furlongs_per_sec'] = self._avg_speed_last_n(speeds, 5)
        
        # 2. Best speed career
        features['horse_best_speed_career'] = self._best_speed_career(speeds)
        
        # 3. Average speed last 3 (more recent)
        features['horse_speed_last_3_avg'] = self._avg_speed_last_n(speeds, 3)
        
        # 4. Speed improving (trend)
        features['horse_speed_improving'] = self._speed_trend(speeds, 5)
        
        # 5. Speed vs track record
        features['horse_speed_vs_track_record'] = self._speed_vs_track_record(
            speeds, course, distance_f
        )
        
        # 6. Speed consistency (coefficient of variation)
        features['horse_speed_consistency'] = self._speed_consistency(speeds, 5)
        
        return features
    
    def _avg_speed_last_n(self, speeds: List[Dict], n: int) -> float:
        """Average speed over last N races"""
        if not speeds:
            return self.default_speed
        
        recent_speeds = [s['speed'] for s in speeds[:n]]
        
        if len(recent_speeds) < 3:
            return self.default_speed
        
        return np.mean(recent_speeds)
    
    def _best_speed_career(self, speeds: List[Dict]) -> float:
        """Best (maximum) speed ever recorded"""
        if not speeds:
            return self.default_speed
        
        all_speeds = [s['speed'] for s in speeds]
        return max(all_speeds)
    
    def _speed_trend(self, speeds: List[Dict], n: int) -> float:
        """
        Calculate speed trend (improving or declining)
        
        Returns:
            Positive = improving (getting faster)
            Negative = declining
            Zero = no trend
        """
        if not speeds or len(speeds) < 3:
            return 0.0
        
        recent_speeds = [s['speed'] for s in speeds[:n]]
        
        if len(recent_speeds) < 3:
            return 0.0
        
        # Races ago: [5, 4, 3, 2, 1] (most recent has lowest number)
        races_ago = list(range(len(recent_speeds), 0, -1))
        
        try:
            slope, _, _, _, _ = linregress(races_ago, recent_speeds)
            
            # Normalize by average speed (percentage change per race)
            avg_speed = np.mean(recent_speeds)
            if avg_speed > 0:
                return slope / avg_speed
            else:
                return 0.0
        except:
            return 0.0
    
    def _speed_vs_track_record(self, speeds: List[Dict], 
                               course: str, distance_f: float) -> float:
        """
        Compare horse's best speed at this course/distance to typical best
        
        Note: We don't have access to actual track records, so we approximate
        by comparing to horse's own best at this venue
        """
        if not speeds:
            return 0.0
        
        # Filter to same course and similar distance (within 0.5f)
        course_speeds = [
            s['speed'] for s in speeds
            if s['course'] == course and abs(s['distance_f'] - distance_f) <= 0.5
        ]
        
        if not course_speeds:
            return 0.0
        
        # Best speed at this course/distance
        best_course_speed = max(course_speeds)
        
        # Compare to overall best speed (approximation of track record)
        best_overall = max(s['speed'] for s in speeds)
        
        if best_overall > 0:
            return best_course_speed / best_overall
        else:
            return 0.0
    
    def _speed_consistency(self, speeds: List[Dict], n: int) -> float:
        """
        Calculate speed consistency (coefficient of variation)
        
        Returns:
            Lower = more consistent
            Higher = more erratic
        """
        if not speeds or len(speeds) < 3:
            return 0.0
        
        recent_speeds = [s['speed'] for s in speeds[:n]]
        
        if len(recent_speeds) < 3:
            return 0.0
        
        mean_speed = np.mean(recent_speeds)
        std_speed = np.std(recent_speeds)
        
        if mean_speed > 0:
            return std_speed / mean_speed
        else:
            return 0.0


def calculate_field_speed_stats(all_horses_speeds: List[Dict]) -> Dict[str, float]:
    """
    Calculate field-level speed statistics
    
    Args:
        all_horses_speeds: List of dicts with 'horse_avg_speed_furlongs_per_sec' for each horse
    
    Returns:
        Dict with field statistics
    """
    speeds = [h.get('horse_avg_speed_furlongs_per_sec', 0) 
              for h in all_horses_speeds if h.get('horse_avg_speed_furlongs_per_sec', 0) > 0]
    
    if not speeds:
        return {
            'field_avg_speed': 0.12,
            'field_best_speed': 0.15,
            'field_worst_speed': 0.10
        }
    
    return {
        'field_avg_speed': np.mean(speeds),
        'field_best_speed': max(speeds),
        'field_worst_speed': min(speeds)
    }

