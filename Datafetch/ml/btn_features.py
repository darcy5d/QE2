#!/usr/bin/env python3
"""
BTN (Beaten By) Features Module
Calculates finish proximity metrics from beaten distances
"""

import numpy as np
from typing import List, Dict, Optional
from scipy.stats import linregress


def parse_btn(btn_str: str) -> Optional[float]:
    """
    Convert BTN string to numeric lengths
    
    Formats:
    - "2.5" = beaten by 2.5 lengths
    - "nk" = neck (0.3 lengths)
    - "hd" = head (0.2 lengths)
    - "shd" = short head (0.1 lengths)
    - "dist" = distance (30+ lengths)
    - "" or NULL = won the race (0 lengths)
    
    Args:
        btn_str: BTN string from results.btn or results.ovr_btn
    
    Returns:
        Distance in lengths, or None if invalid
    """
    if btn_str is None or btn_str == '':
        return 0.0  # Won the race
    
    try:
        btn_str = str(btn_str).lower().strip()
        
        if not btn_str or btn_str == 'null':
            return 0.0
        
        # Handle special cases
        conversions = {
            'nk': 0.3,
            'neck': 0.3,
            'hd': 0.2,
            'head': 0.2,
            'shd': 0.1,
            'short-head': 0.1,
            'sht-hd': 0.1,
            'sh': 0.1,
            'dist': 30.0,
            'distance': 30.0,
            'dht': 0.0,  # Dead heat
            'dead-heat': 0.0
        }
        
        if btn_str in conversions:
            return conversions[btn_str]
        
        # Handle fractions like "1/2" or "3/4"
        if '/' in btn_str:
            parts = btn_str.split('/')
            if len(parts) == 2:
                try:
                    return float(parts[0]) / float(parts[1])
                except:
                    pass
        
        # Try to parse as float
        return float(btn_str)
    except (ValueError, AttributeError):
        return None


class BTNFeatureCalculator:
    """Calculate BTN (Beaten By) features for a horse"""
    
    def __init__(self):
        self.default_btn = 5.0  # Typical mid-field finish
    
    def calculate_all_btn_features(self, 
                                   horse_past_races: List[Dict],
                                   field_size: int) -> Dict[str, float]:
        """
        Calculate all BTN features for a horse
        
        Args:
            horse_past_races: List of past race dicts with 'btn', 'ovr_btn'
            field_size: Size of current race field
        
        Returns:
            Dict of BTN features
        """
        # Extract BTN values from past races
        btns = []
        ovr_btns = []
        
        for race in horse_past_races:
            btn = parse_btn(race.get('btn'))
            ovr_btn = parse_btn(race.get('ovr_btn'))
            
            if btn is not None:
                btns.append(btn)
            if ovr_btn is not None:
                ovr_btns.append(ovr_btn)
        
        features = {}
        
        # BTN Features (8 features)
        features['horse_avg_btn_last_5'] = self._avg_btn_last_n(btns, 5)
        features['horse_median_btn_last_5'] = self._median_btn_last_n(btns, 5)
        features['horse_btn_improving'] = self._btn_trend(btns, 5)
        features['horse_pct_within_3_lengths'] = self._pct_within_n_lengths(btns, 3.0)
        features['horse_btn_vs_field_avg'] = 0.0  # Will be calculated at field level
        features['horse_btn_vs_winner_percentile'] = 0.0  # Will be calculated at field level
        features['horse_best_btn_career'] = self._best_btn_career(btns)
        features['horse_btn_consistency'] = self._btn_consistency(btns, 5)
        
        # OVR_BTN Features (4 features)
        features['horse_avg_ovr_btn_last_5'] = self._avg_btn_last_n(ovr_btns, 5)
        features['horse_ovr_btn_improving'] = self._btn_trend(ovr_btns, 5)
        features['horse_ovr_btn_vs_field'] = 0.0  # Will be calculated at field level
        features['horse_pct_top_half_finishes'] = self._pct_top_half(horse_past_races)
        
        return features
    
    def _avg_btn_last_n(self, btns: List[float], n: int) -> float:
        """Average BTN over last N races"""
        if not btns or len(btns) < 3:
            return self.default_btn
        
        recent_btns = btns[:n]
        return np.mean(recent_btns)
    
    def _median_btn_last_n(self, btns: List[float], n: int) -> float:
        """Median BTN over last N races (more robust to outliers)"""
        if not btns or len(btns) < 3:
            return self.default_btn
        
        recent_btns = btns[:n]
        return np.median(recent_btns)
    
    def _btn_trend(self, btns: List[float], n: int) -> float:
        """
        Calculate BTN trend (improving or declining)
        
        Returns:
            Positive = improving (getting closer to winners)
            Negative = declining (getting further from winners)
        """
        if not btns or len(btns) < 3:
            return 0.0
        
        recent_btns = btns[:n]
        
        if len(recent_btns) < 3:
            return 0.0
        
        # Races ago: [5, 4, 3, 2, 1] (most recent has lowest number)
        races_ago = list(range(len(recent_btns), 0, -1))
        
        try:
            slope, _, _, _, _ = linregress(races_ago, recent_btns)
            
            # Negate so positive = improving (BTN decreasing)
            return -slope
        except:
            return 0.0
    
    def _pct_within_n_lengths(self, btns: List[float], max_lengths: float) -> float:
        """
        Percentage of races where horse finished within N lengths of winner
        
        Args:
            btns: List of BTN values
            max_lengths: Maximum BTN to count as "close"
        
        Returns:
            Percentage (0.0 to 1.0)
        """
        if not btns:
            return 0.0
        
        within_n = sum(1 for btn in btns if btn <= max_lengths)
        return within_n / len(btns)
    
    def _best_btn_career(self, btns: List[float]) -> float:
        """Closest finish to winner (minimum BTN) in career"""
        if not btns:
            return self.default_btn
        
        return min(btns)
    
    def _btn_consistency(self, btns: List[float], n: int) -> float:
        """
        Calculate BTN consistency (coefficient of variation)
        
        Returns:
            Lower = consistent finishes
            Higher = erratic
        """
        if not btns or len(btns) < 3:
            return 0.0
        
        recent_btns = btns[:n]
        
        if len(recent_btns) < 3:
            return 0.0
        
        mean_btn = np.mean(recent_btns)
        std_btn = np.std(recent_btns)
        
        if mean_btn > 0:
            return std_btn / mean_btn
        else:
            return 0.0
    
    def _pct_top_half(self, past_races: List[Dict]) -> float:
        """
        Percentage of races where horse finished in top half of field
        
        Uses position and field_size from each past race
        """
        if not past_races:
            return 0.5  # Neutral assumption
        
        top_half_finishes = 0
        valid_races = 0
        
        for race in past_races:
            position = race.get('position')
            field_size = race.get('field_size')
            
            if position and field_size:
                try:
                    pos = int(position)
                    size = int(field_size)
                    
                    if pos <= size / 2:
                        top_half_finishes += 1
                    
                    valid_races += 1
                except (ValueError, TypeError):
                    continue
        
        if valid_races == 0:
            return 0.5
        
        return top_half_finishes / valid_races


def calculate_field_btn_stats(all_horses_btns: List[Dict]) -> Dict[str, Dict]:
    """
    Calculate field-level BTN statistics and relative features
    
    Args:
        all_horses_btns: List of dicts with BTN features for each horse
    
    Returns:
        Dict mapping horse_id to relative BTN features
    """
    # Extract average BTNs
    avg_btns = []
    avg_ovr_btns = []
    
    for horse in all_horses_btns:
        btn = horse.get('horse_avg_btn_last_5', 0)
        ovr_btn = horse.get('horse_avg_ovr_btn_last_5', 0)
        
        if btn > 0:
            avg_btns.append(btn)
        if ovr_btn > 0:
            avg_ovr_btns.append(ovr_btn)
    
    if not avg_btns:
        return {}
    
    # Calculate field averages
    field_avg_btn = np.mean(avg_btns)
    field_avg_ovr_btn = np.mean(avg_ovr_btns) if avg_ovr_btns else 0
    
    # Sort BTNs for percentile calculation
    sorted_btns = sorted(avg_btns)
    
    # Calculate relative features for each horse
    relative_features = {}
    
    for i, horse in enumerate(all_horses_btns):
        horse_id = horse.get('horse_id')
        horse_btn = horse.get('horse_avg_btn_last_5', 0)
        horse_ovr_btn = horse.get('horse_avg_ovr_btn_last_5', 0)
        
        # BTN vs field average (positive = better than field)
        btn_vs_field = field_avg_btn - horse_btn
        
        # BTN percentile (lower percentile = better)
        if horse_btn in sorted_btns:
            rank = sorted_btns.index(horse_btn) + 1
            percentile = rank / len(sorted_btns)
        else:
            percentile = 0.5
        
        # OVR_BTN vs field
        ovr_btn_vs_field = field_avg_ovr_btn - horse_ovr_btn if field_avg_ovr_btn > 0 else 0
        
        relative_features[horse_id] = {
            'horse_btn_vs_field_avg': btn_vs_field,
            'horse_btn_vs_winner_percentile': percentile,
            'horse_ovr_btn_vs_field': ovr_btn_vs_field
        }
    
    return relative_features

