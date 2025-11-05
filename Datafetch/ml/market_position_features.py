#!/usr/bin/env python3
"""
Market Position Features
Converts market odds to categorical tiers for baseline anchoring
"""

from typing import Optional


def calculate_market_position(market_odds: Optional[float]) -> int:
    """
    Convert market odds to categorical tier (0-4)
    
    Provides baseline anchor without full data leakage.
    Model can adjust from this baseline using fundamental features.
    
    Args:
        market_odds: Market decimal odds (e.g., 5.5)
        
    Returns:
        Integer tier 0-4:
            0 = Strong Favorite (< 3.0)
            1 = Co-Favorite (3.0-5.0)
            2 = Mid-range (5.0-10.0)
            3 = Outsider (10.0-20.0)
            4 = Longshot (> 20.0)
            2 = Default if odds missing
    
    Examples:
        >>> calculate_market_position(2.5)   # Favorite
        0
        >>> calculate_market_position(7.0)   # Mid-range
        2
        >>> calculate_market_position(25.0)  # Longshot
        4
    """
    if market_odds is None or market_odds <= 0:
        return 2  # Default to mid-range
    
    if market_odds < 3.0:
        return 0  # Strong Favorite
    elif market_odds < 5.0:
        return 1  # Co-Favorite
    elif market_odds < 10.0:
        return 2  # Mid-range
    elif market_odds < 20.0:
        return 3  # Outsider
    else:
        return 4  # Longshot


def get_market_position_name(tier: int) -> str:
    """
    Get human-readable name for market position tier
    
    Args:
        tier: Market position tier (0-4)
        
    Returns:
        String name of tier
    """
    names = {
        0: "Strong Favorite",
        1: "Co-Favorite",
        2: "Mid-range",
        3: "Outsider",
        4: "Longshot"
    }
    return names.get(tier, "Unknown")

