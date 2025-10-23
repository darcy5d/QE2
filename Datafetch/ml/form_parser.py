"""
Form String Parser
Parse racing form strings (e.g., "1-2-3-4") into structured features
"""

import re
from typing import List, Dict, Optional
import numpy as np


class FormParser:
    """Parse and extract features from form strings"""
    
    # Form code mappings
    FORM_CODES = {
        # Non-finishers
        'F': 999,   # Fell
        'U': 998,   # Unseated rider
        'P': 997,   # Pulled up
        'R': 996,   # Refused
        'BD': 995,  # Brought down
        'C': 994,   # Carried out
        'S': 993,   # Slipped
        'RO': 992,  # Ran out
        'UR': 991,  # Unseated rider
        # Did not finish codes
        '0': 900,   # Finished outside top 9, beaten
        # Symbols
        '/': None,  # Separator for different seasons/years
        '-': None,  # Separator between races
    }
    
    @staticmethod
    def parse_form(form_string: str) -> List[int]:
        """
        Parse a form string into list of positions
        
        Args:
            form_string: e.g., "1-2-3-4-P" or "112-3"
            
        Returns:
            List of position integers (999+ for non-finishers)
        """
        if not form_string or form_string == '-' or form_string == '':
            return []
        
        positions = []
        form_string = form_string.strip().upper()
        
        # Split by common delimiters
        parts = re.split(r'[-/]', form_string)
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Check for known codes
            if part in FormParser.FORM_CODES:
                code_value = FormParser.FORM_CODES[part]
                if code_value is not None:
                    positions.append(code_value)
                continue
            
            # Try to parse as integer (position)
            try:
                pos = int(part)
                if pos >= 0:  # Valid position
                    positions.append(pos)
            except ValueError:
                # Try to extract digits from string like "1st"
                digits = re.search(r'\d+', part)
                if digits:
                    positions.append(int(digits.group()))
        
        return positions
    
    @staticmethod
    def get_last_n_positions(form_string: str, n: int = 5) -> List[Optional[int]]:
        """Get last N positions from form string"""
        positions = FormParser.parse_form(form_string)
        
        # Pad with None if fewer than n races
        if len(positions) < n:
            return positions + [None] * (n - len(positions))
        
        return positions[:n]
    
    @staticmethod
    def compute_form_features(form_string: str) -> Dict[str, any]:
        """
        Compute comprehensive features from form string
        
        Returns dict with:
        - last_position: Most recent position
        - avg_last_3: Average position in last 3 races
        - avg_last_5: Average position in last 5 races
        - avg_last_10: Average position in last 10 races
        - best_last_5: Best position in last 5 races
        - worst_last_5: Worst position in last 5 races
        - consistency: Standard deviation of last 5 (lower = more consistent)
        - races_since_win: Number of races since last win
        - races_since_place: Number of races since top 3 finish
        - improving_trend: 1 if improving, -1 if declining, 0 if stable
        - completed_last_5: Number of completed races in last 5
        - dnf_last_5: Number of DNF in last 5
        """
        positions = FormParser.parse_form(form_string)
        
        if not positions:
            return {
                'last_position': None,
                'avg_last_3': None,
                'avg_last_5': None,
                'avg_last_10': None,
                'best_last_5': None,
                'worst_last_5': None,
                'consistency': None,
                'races_since_win': None,
                'races_since_place': None,
                'improving_trend': 0,
                'completed_last_5': 0,
                'dnf_last_5': 0,
                'win_rate_last_10': 0.0,
                'place_rate_last_10': 0.0
            }
        
        # Separate completed races from DNFs (position < 900)
        completed = [p for p in positions if p < 900]
        dnf = [p for p in positions if p >= 900]
        
        # Last position
        last_pos = positions[0] if positions else None
        
        # Averages (only for completed races)
        avg_3 = np.mean(completed[:3]) if len(completed) >= 1 else None
        avg_5 = np.mean(completed[:5]) if len(completed) >= 1 else None
        avg_10 = np.mean(completed[:10]) if len(completed) >= 1 else None
        
        # Best and worst in last 5
        last_5_completed = completed[:5]
        best_5 = min(last_5_completed) if last_5_completed else None
        worst_5 = max(last_5_completed) if last_5_completed else None
        
        # Consistency (std dev of last 5)
        consistency = np.std(last_5_completed) if len(last_5_completed) >= 2 else None
        
        # Races since win
        races_since_win = None
        for i, pos in enumerate(positions):
            if pos == 1:
                races_since_win = i
                break
        if races_since_win is None and positions:
            races_since_win = len(positions)  # Never won
        
        # Races since place (top 3)
        races_since_place = None
        for i, pos in enumerate(positions):
            if pos <= 3 and pos < 900:  # Top 3 and completed
                races_since_place = i
                break
        if races_since_place is None and positions:
            races_since_place = len(positions)  # Never placed
        
        # Improving trend (compare first half vs second half of last 6 races)
        improving_trend = 0
        if len(completed) >= 6:
            first_half = np.mean(completed[:3])
            second_half = np.mean(completed[3:6])
            if first_half < second_half - 0.5:  # Improving (lower positions = better)
                improving_trend = 1
            elif first_half > second_half + 0.5:  # Declining
                improving_trend = -1
        
        # DNF counts
        last_5_dnf = len([p for p in positions[:5] if p >= 900])
        last_5_completed = 5 - last_5_dnf if len(positions) >= 5 else len(completed[:5])
        
        # Win and place rates (last 10)
        last_10 = positions[:10]
        wins_last_10 = len([p for p in last_10 if p == 1])
        places_last_10 = len([p for p in last_10 if p <= 3 and p < 900])
        
        win_rate_10 = wins_last_10 / len(last_10) if last_10 else 0.0
        place_rate_10 = places_last_10 / len(last_10) if last_10 else 0.0
        
        return {
            'last_position': last_pos,
            'avg_last_3': float(avg_3) if avg_3 is not None else None,
            'avg_last_5': float(avg_5) if avg_5 is not None else None,
            'avg_last_10': float(avg_10) if avg_10 is not None else None,
            'best_last_5': int(best_5) if best_5 is not None else None,
            'worst_last_5': int(worst_5) if worst_5 is not None else None,
            'consistency': float(consistency) if consistency is not None else None,
            'races_since_win': races_since_win,
            'races_since_place': races_since_place,
            'improving_trend': improving_trend,
            'completed_last_5': last_5_completed,
            'dnf_last_5': last_5_dnf,
            'win_rate_last_10': win_rate_10,
            'place_rate_last_10': place_rate_10
        }
    
    @staticmethod
    def parse_last_run_days(last_run_string: str) -> Optional[int]:
        """
        Parse 'last_run' field to get days since last race
        
        Args:
            last_run_string: e.g., "14" or "28 days"
            
        Returns:
            Days as integer, or None if can't parse
        """
        if not last_run_string:
            return None
        
        # Extract first number
        match = re.search(r'\d+', str(last_run_string))
        if match:
            return int(match.group())
        
        return None


# Testing/example usage
if __name__ == "__main__":
    # Test examples
    test_forms = [
        "1-2-3-4-5",
        "2-1-3-P-1",
        "1-2-F-3-4",
        "112-34-5",
        "P-P-U-2-1",
        "",
        None
    ]
    
    print("Form Parser Test\n" + "="*60)
    for form in test_forms:
        print(f"\nForm: '{form}'")
        positions = FormParser.parse_form(form)
        print(f"Parsed: {positions}")
        
        features = FormParser.compute_form_features(form)
        print(f"Features:")
        for key, value in features.items():
            print(f"  {key}: {value}")


