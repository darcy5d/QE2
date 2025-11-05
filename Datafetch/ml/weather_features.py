#!/usr/bin/env python3
"""
Going/Weather Interaction Features
Calculates performance under different going and weather conditions
"""

import numpy as np
from typing import List, Dict, Optional


# Going scale for quantifying going conditions
GOING_SCALE = {
    'Hard': 1,
    'Firm': 2,
    'Good to Firm': 3,
    'Good': 4,
    'Good to Soft': 5,
    'Soft': 6,
    'Heavy': 7,
    'Yielding': 5,  # Irish term, similar to Good to Soft
}

# Weather categories
WET_WEATHER = ['Rain', 'Showers', 'Drizzle', 'Heavy Rain', 'Light Rain']
DRY_WEATHER = ['Fine', 'Sunny', 'Cloudy', 'Overcast', 'Clear']


def parse_rail_movements(rail_str: str) -> float:
    """
    Parse rail movements string to numeric value
    
    Examples:
    - "+3 yards" -> 3.0
    - "-2m" -> -2.0
    - "0" -> 0.0
    
    Args:
        rail_str: Rail movements string
    
    Returns:
        Numeric rail movement (positive = inside favored)
    """
    if not rail_str or rail_str == '':
        return 0.0
    
    try:
        rail_str = str(rail_str).lower().strip()
        
        # Extract numeric part
        import re
        match = re.search(r'([+-]?\d+(?:\.\d+)?)', rail_str)
        
        if match:
            value = float(match.group(1))
            
            # Check if it's inside (+) or outside (-)
            if '-' in rail_str or 'out' in rail_str:
                return -abs(value)
            else:
                return abs(value)
        
        return 0.0
    except:
        return 0.0


class WeatherFeatureCalculator:
    """Calculate going/weather interaction features"""
    
    def calculate_soft_going_speed_ratio(self, 
                                        horse_past_races: List[Dict]) -> float:
        """
        Calculate speed on soft going vs firm going
        
        Args:
            horse_past_races: Past races with 'going', 'time', 'distance_f'
        
        Returns:
            Ratio (<1.0 = prefers firm, >1.0 = prefers soft)
        """
        from .speed_features import parse_race_time, calculate_speed
        
        soft_speeds = []
        firm_speeds = []
        
        for race in horse_past_races:
            going = race.get('going', '')
            time_str = race.get('time')
            distance_f = race.get('distance_f')
            
            if not time_str or not distance_f:
                continue
            
            time_seconds = parse_race_time(time_str)
            if not time_seconds:
                continue
            
            speed = calculate_speed(distance_f, time_seconds)
            if not speed:
                continue
            
            # Categorize going
            if going in ['Soft', 'Heavy', 'Yielding']:
                soft_speeds.append(speed)
            elif going in ['Good', 'Good to Firm', 'Firm']:
                firm_speeds.append(speed)
        
        # Need at least 2 races in each condition
        if len(soft_speeds) < 2 or len(firm_speeds) < 2:
            return 1.0  # Neutral assumption
        
        avg_soft = np.mean(soft_speeds)
        avg_firm = np.mean(firm_speeds)
        
        if avg_firm > 0:
            return avg_soft / avg_firm
        else:
            return 1.0
    
    def calculate_weather_performance(self, 
                                     horse_past_races: List[Dict]) -> float:
        """
        Calculate win rate in wet weather vs dry
        
        Args:
            horse_past_races: Past races with 'weather', 'position'
        
        Returns:
            Ratio of wet/dry win rates
        """
        wet_races = []
        dry_races = []
        
        for race in horse_past_races:
            weather = race.get('weather', '')
            position = race.get('position')
            
            if not position:
                continue
            
            try:
                pos = int(position)
            except:
                continue
            
            # Skip if weather is None or empty
            if not weather:
                continue
            
            # Categorize weather
            if any(w in weather for w in WET_WEATHER):
                wet_races.append(pos)
            elif any(w in weather for w in DRY_WEATHER):
                dry_races.append(pos)
        
        if len(wet_races) < 2 or len(dry_races) < 2:
            return 1.0  # Neutral assumption
        
        wet_win_rate = sum(1 for p in wet_races if p == 1) / len(wet_races)
        dry_win_rate = sum(1 for p in dry_races if p == 1) / len(dry_races)
        
        if dry_win_rate > 0:
            return wet_win_rate / dry_win_rate
        else:
            return 1.0
    
    def calculate_rail_position_advantage(self, 
                                         rail_movements: str,
                                         draw: int,
                                         field_size: int) -> float:
        """
        Calculate advantage/disadvantage from rail movements
        
        Args:
            rail_movements: Rail movements string
            draw: Horse's draw position
            field_size: Number of runners
        
        Returns:
            Advantage score (positive = advantaged)
        """
        rail_value = parse_rail_movements(rail_movements)
        
        if rail_value == 0 or field_size <= 1:
            return 0.0
        
        # Normalize draw (0 = inside, 1 = outside)
        draw_normalized = (draw - 1) / (field_size - 1)
        
        if rail_value > 0:
            # Inside rail favored (positive rail movement)
            # Low draw number = advantaged
            return (1 - draw_normalized) * abs(rail_value)
        else:
            # Outside rail favored (negative rail movement)
            # High draw number = advantaged
            return draw_normalized * abs(rail_value)
    
    def calculate_going_change_adaptation(self, 
                                         horse_past_races: List[Dict],
                                         today_going: str) -> float:
        """
        Calculate how well horse adapts when going changes
        
        Args:
            horse_past_races: Past races with 'going', 'position'
            today_going: Going for today's race
        
        Returns:
            Adaptation score (0.0 to 1.0, higher = adapts well)
        """
        if not horse_past_races or not today_going:
            return 0.5  # Neutral assumption
        
        # Get last race going
        last_going = horse_past_races[0].get('going', '')
        
        if not last_going:
            return 0.5
        
        # Calculate going change magnitude
        today_scale = GOING_SCALE.get(today_going, 4)
        last_scale = GOING_SCALE.get(last_going, 4)
        going_change_magnitude = abs(today_scale - last_scale)
        
        if going_change_magnitude < 1:
            return 0.5  # No significant change
        
        # Look for similar going changes in past
        adaptations = []
        
        for i in range(1, len(horse_past_races)):
            current_race = horse_past_races[i]
            prev_race = horse_past_races[i-1] if i > 0 else None
            
            if not prev_race:
                continue
            
            current_going = current_race.get('going', '')
            prev_going = prev_race.get('going', '')
            position = current_race.get('position')
            
            if not current_going or not prev_going or not position:
                continue
            
            # Calculate magnitude of that going change
            current_scale = GOING_SCALE.get(current_going, 4)
            prev_scale = GOING_SCALE.get(prev_going, 4)
            past_change_magnitude = abs(current_scale - prev_scale)
            
            # If similar magnitude change
            if abs(past_change_magnitude - going_change_magnitude) <= 1:
                try:
                    pos = int(position)
                    # Good adaptation = finishing in top 3
                    if pos <= 3:
                        adaptations.append(1)
                    else:
                        adaptations.append(0)
                except:
                    continue
        
        if len(adaptations) < 2:
            return 0.5  # Insufficient data
        
        return np.mean(adaptations)


def calculate_all_weather_features(horse_past_races: List[Dict],
                                   rail_movements: str,
                                   draw: int,
                                   field_size: int,
                                   today_going: str) -> Dict[str, float]:
    """
    Calculate all going/weather features
    
    Returns:
        Dict of weather features
    """
    calculator = WeatherFeatureCalculator()
    
    return {
        'horse_soft_going_speed_ratio': calculator.calculate_soft_going_speed_ratio(
            horse_past_races
        ),
        'horse_weather_performance': calculator.calculate_weather_performance(
            horse_past_races
        ),
        'rail_position_advantage': calculator.calculate_rail_position_advantage(
            rail_movements, draw, field_size
        ),
        'going_change_adaptation': calculator.calculate_going_change_adaptation(
            horse_past_races, today_going
        )
    }

