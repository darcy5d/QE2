#!/usr/bin/env python3
"""
Weight-Adjusted Performance Features
Calculates performance metrics adjusted for weight carried
"""

import numpy as np
from typing import List, Dict
from scipy.stats import linregress


STANDARD_WEIGHT_FLAT = 126  # lbs (typical flat racing weight)
WEIGHT_TO_RATING_FACTOR = 1.0  # 1 lb = ~1 point of rating


class WeightFeatureCalculator:
    """Calculate weight-adjusted performance features"""
    
    def calculate_weight_adjusted_rating(self, 
                                        rating: float,
                                        weight_lbs: float,
                                        standard_weight: float = STANDARD_WEIGHT_FLAT) -> float:
        """
        Adjust rating for weight carried
        
        Rule of thumb: 1 lb = ~1 point of rating in Flat racing
        Carrying more weight is harder, so we increase the effective rating
        to reflect the difficulty
        
        Args:
            rating: Base rating (RPR, OR, etc.)
            weight_lbs: Weight carried
            standard_weight: Standard weight for comparison
        
        Returns:
            Weight-adjusted rating
        """
        if not rating or rating <= 0:
            return 0.0
        
        if not weight_lbs or weight_lbs <= 0:
            return rating
        
        weight_difference = weight_lbs - standard_weight
        adjusted_rating = rating + (weight_difference * WEIGHT_TO_RATING_FACTOR)
        
        return adjusted_rating
    
    def calculate_weight_performance_trend(self, 
                                          horse_past_races: List[Dict]) -> float:
        """
        Calculate how performance changes as weight increases
        
        Args:
            horse_past_races: Past races with 'weight_lbs', 'rpr'
        
        Returns:
            Slope of weight vs rating regression
            Negative = struggles with weight
            Positive = handles weight well
        """
        if not horse_past_races or len(horse_past_races) < 5:
            return 0.0
        
        weights = []
        ratings = []
        
        for race in horse_past_races[:10]:  # Last 10 races
            weight = race.get('weight_lbs')
            rpr = race.get('rpr')
            
            if weight and rpr:
                try:
                    weights.append(float(weight))
                    ratings.append(float(rpr))
                except:
                    continue
        
        if len(weights) < 5:
            return 0.0
        
        try:
            slope, _, _, _, _ = linregress(weights, ratings)
            return slope
        except:
            return 0.0


def calculate_all_weight_features(horse_past_races: List[Dict],
                                  current_rating: float,
                                  current_weight: float,
                                  race_type: str = 'Flat') -> Dict[str, float]:
    """
    Calculate all weight-adjusted features
    
    Args:
        horse_past_races: Past race data
        current_rating: Current race rating
        current_weight: Current race weight
        race_type: Type of race (Flat, Hurdle, Chase)
    
    Returns:
        Dict of weight features
    """
    calculator = WeightFeatureCalculator()
    
    # Determine standard weight based on race type
    if race_type == 'Flat':
        standard_weight = 126
    elif race_type == 'Hurdle':
        standard_weight = 140
    elif race_type == 'Chase':
        standard_weight = 154
    else:
        standard_weight = 126
    
    return {
        'horse_weight_adjusted_rating': calculator.calculate_weight_adjusted_rating(
            current_rating, current_weight, standard_weight
        ),
        'horse_weight_performance_trend': calculator.calculate_weight_performance_trend(
            horse_past_races
        )
    }

