#!/usr/bin/env python3
"""
Race Quality & Competitiveness Features
Calculates field strength and race competitiveness metrics
"""

import numpy as np
from typing import List, Dict, Optional
from btn_features import parse_btn


class QualityFeatureCalculator:
    """Calculate race quality and competitiveness features"""
    
    def calculate_field_quality_rating(self, field_horses: List[Dict]) -> float:
        """
        Calculate weighted average of field's past performance
        
        Args:
            field_horses: List of horse dicts with ratings and form
        
        Returns:
            Field quality rating
        """
        rprs = []
        forms = []
        
        for horse in field_horses:
            rpr = horse.get('horse_best_rating', 0) or horse.get('rpr', 0)
            form = horse.get('horse_form_last_5_avg', 0)
            
            if rpr and rpr > 0:
                rprs.append(rpr)
            if form and form > 0:
                forms.append(form)
        
        if not rprs:
            return 0.0
        
        avg_rpr = np.mean(rprs)
        avg_form = np.mean(forms) if forms else 1.0
        
        # Weight by recency (form) and ability (RPR)
        return avg_rpr * avg_form
    
    def calculate_race_competitiveness(self, 
                                      similar_races: List[Dict]) -> float:
        """
        Calculate historical competitiveness at this course/distance/class
        
        Args:
            similar_races: Past races at similar venue/conditions
        
        Returns:
            Competitiveness score (higher = tighter finishes)
        """
        if not similar_races:
            return 0.5  # Neutral assumption
        
        avg_btns = []
        
        for race in similar_races:
            # Get BTN values for all finishers in that race
            race_btns = []
            for result in race.get('results', []):
                btn = parse_btn(result.get('btn'))
                if btn is not None and btn < 30:  # Exclude "dist"
                    race_btns.append(btn)
            
            if race_btns:
                avg_btns.append(np.mean(race_btns))
        
        if not avg_btns:
            return 0.5
        
        # Lower average BTN = tighter finishes = more competitive
        # Invert so higher score = more competitive
        mean_avg_btn = np.mean(avg_btns)
        
        if mean_avg_btn > 0:
            return 1.0 / mean_avg_btn
        else:
            return 0.5
    
    def calculate_horse_beaten_by_quality(self, 
                                         horse_past_races: List[Dict],
                                         all_historical_data: Dict) -> float:
        """
        Calculate average quality of horses that beat this horse
        
        Args:
            horse_past_races: This horse's past races
            all_historical_data: Database of all horses' ratings
        
        Returns:
            Average RPR of horses that beat this one
        """
        beaten_by_rprs = []
        
        for race in horse_past_races:
            horse_position = race.get('position')
            race_id = race.get('race_id')
            
            if not horse_position or not race_id:
                continue
            
            try:
                pos = int(horse_position)
            except:
                continue
            
            # Get horses that finished ahead
            horses_ahead = all_historical_data.get(race_id, {}).get('results', [])
            
            for result in horses_ahead:
                try:
                    other_pos = int(result.get('position', 99))
                    if other_pos < pos:
                        # This horse beat our horse
                        other_rpr = result.get('rpr')
                        if other_rpr:
                            try:
                                beaten_by_rprs.append(float(other_rpr))
                            except:
                                pass
                except:
                    continue
        
        if not beaten_by_rprs:
            return 0.0
        
        return np.mean(beaten_by_rprs)


def calculate_all_quality_features(horse_past_races: List[Dict],
                                   field_horses: List[Dict],
                                   similar_races: List[Dict],
                                   all_historical_data: Dict) -> Dict[str, float]:
    """
    Calculate all quality features
    
    Returns:
        Dict of quality features
    """
    calculator = QualityFeatureCalculator()
    
    return {
        'field_quality_rating': calculator.calculate_field_quality_rating(field_horses),
        'race_competitiveness': calculator.calculate_race_competitiveness(similar_races),
        'horse_beaten_by_quality': calculator.calculate_horse_beaten_by_quality(
            horse_past_races, all_historical_data
        )
    }

