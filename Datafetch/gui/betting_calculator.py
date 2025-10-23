"""
Betting Calculator - Kelly Criterion and Expected Value calculations for value betting
"""

from typing import Dict, List, Optional, Tuple
import math


class BettingCalculator:
    """Calculate bet recommendations using Kelly Criterion and Expected Value"""
    
    def __init__(self, bankroll: float = 1000.0, kelly_fraction: float = 0.5, min_edge: float = 0.05,
                 market_confidence: float = 0.0):
        """
        Initialize betting calculator
        
        Args:
            bankroll: Total betting bankroll (default $1000)
            kelly_fraction: Fraction of Kelly to use (0.125 to 1.0, default 0.5 = half Kelly)
            min_edge: Minimum edge required to recommend bet (default 0.05 = 5%)
            market_confidence: How much to blend market probability (0.0 = pure model, 0.5 = 50/50 blend, default 0.0)
        """
        self.bankroll = bankroll
        self.kelly_fraction = kelly_fraction
        self.min_edge = min_edge
        self.market_confidence = market_confidence
        
        # Safety cap: never stake more than this % of bankroll on single bet
        self.max_stake_cap = 0.05  # 5% max per individual bet (safety cap)
    
    def probability_to_odds(self, probability: float) -> float:
        """
        Convert probability to decimal odds
        
        Args:
            probability: Win probability (0.0 to 1.0)
            
        Returns:
            Decimal odds (e.g., 0.25 -> 4.0)
        """
        if probability <= 0 or probability >= 1:
            return None
        return 1.0 / probability
    
    def odds_to_probability(self, decimal_odds: float) -> float:
        """
        Convert decimal odds to implied probability
        
        Args:
            decimal_odds: Decimal odds (e.g., 4.0)
            
        Returns:
            Implied probability (e.g., 4.0 -> 0.25)
        """
        if decimal_odds <= 1.0:
            return None
        return 1.0 / decimal_odds
    
    def blend_probability(self, our_prob: float, market_odds: float) -> float:
        """
        Blend our model's probability with market probability
        
        This is a conservative risk management approach that acknowledges
        "wisdom of the crowds" - the market might know things we don't.
        
        market_confidence = 0.0: Pure model (traditional Kelly)
        market_confidence = 0.3: 70% model, 30% market  
        market_confidence = 0.5: 50/50 blend
        market_confidence = 0.65: 35% model, 65% market (CONSERVATIVE)
        
        Args:
            our_prob: Our model's probability estimate
            market_odds: Market decimal odds
            
        Returns:
            Blended probability for Kelly calculation
        """
        if self.market_confidence == 0.0:
            # Pure model approach (traditional Kelly)
            return our_prob
        
        # Calculate market implied probability
        market_prob = self.odds_to_probability(market_odds)
        if market_prob is None:
            return our_prob
        
        # Blend: higher market_confidence = more conservative (closer to market)
        # Example: market_confidence=0.65 means 65% market + 35% model
        blended = (1.0 - self.market_confidence) * our_prob + self.market_confidence * market_prob
        
        return blended
    
    def calculate_expected_value(self, our_prob: float, market_odds: float) -> float:
        """
        Calculate Expected Value (EV) of a bet
        
        EV = (our_probability × market_odds) - 1
        
        Args:
            our_prob: Our estimated win probability (0.0 to 1.0)
            market_odds: Market decimal odds
            
        Returns:
            Expected value as decimal (e.g., 0.20 = 20% edge)
        """
        if our_prob <= 0 or market_odds <= 1.0:
            return -1.0
        
        expected_return = our_prob * market_odds
        ev = expected_return - 1.0
        return ev
    
    def kelly_stake(self, our_prob: float, market_odds: float) -> Tuple[float, float]:
        """
        Calculate optimal stake using Kelly Criterion
        
        Kelly = (edge / (odds - 1)) × bankroll × kelly_fraction
        
        Note: Uses blended probability for Kelly if market_confidence > 0
        
        Args:
            our_prob: Our estimated win probability
            market_odds: Market decimal odds
            
        Returns:
            Tuple of (stake_amount, percentage_of_bankroll)
        """
        # Calculate edge (always use our true probability for EV)
        ev = self.calculate_expected_value(our_prob, market_odds)
        
        if ev <= 0:
            return 0.0, 0.0
        
        # Use blended probability for Kelly calculation (if confidence adjustment is set)
        p = self.blend_probability(our_prob, market_odds)
        
        # Kelly formula: (bp - q) / b
        # where b = odds - 1 (net odds), p = probability, q = 1 - probability
        b = market_odds - 1.0
        q = 1.0 - p
        
        kelly_percentage = (b * p - q) / b
        
        # Apply Kelly fraction (e.g., half Kelly)
        adjusted_kelly = kelly_percentage * self.kelly_fraction
        
        # Safety cap
        adjusted_kelly = min(adjusted_kelly, self.max_stake_cap)
        
        # Calculate stake
        stake = adjusted_kelly * self.bankroll
        
        # Ensure non-negative
        stake = max(0.0, stake)
        
        return stake, adjusted_kelly * 100
    
    def is_value_bet(self, our_prob: float, market_odds: float) -> bool:
        """
        Check if bet has sufficient edge to be considered value
        
        Args:
            our_prob: Our estimated probability
            market_odds: Market odds
            
        Returns:
            True if EV >= min_edge threshold
        """
        ev = self.calculate_expected_value(our_prob, market_odds)
        return ev >= self.min_edge
    
    def scale_recommendations_to_bankroll(self, recommendations: List[Dict], 
                                         max_allocation: float = 0.5) -> List[Dict]:
        """
        Scale all recommendation stakes proportionally to fit within bankroll
        
        Args:
            recommendations: List of bet recommendations with 'stake' field
            max_allocation: Maximum fraction of bankroll to allocate (default 0.5 = 50%)
            
        Returns:
            Scaled recommendations with adjusted stakes
        """
        if not recommendations:
            return recommendations
        
        # Calculate total raw stake
        total_stake = sum(rec['stake'] for rec in recommendations)
        max_stake = self.bankroll * max_allocation
        
        # If total exceeds limit, scale proportionally
        if total_stake > max_stake:
            scale_factor = max_stake / total_stake
            
            for rec in recommendations:
                rec['stake'] *= scale_factor
                rec['stake_percentage'] *= scale_factor
                rec['potential_profit'] = rec['stake'] * rec['market_odds'] - rec['stake']
        
        # Apply minimum stake filter (don't recommend bets < $1)
        min_stake = 1.0
        recommendations = [rec for rec in recommendations if rec['stake'] >= min_stake]
        
        return recommendations
    
    def calculate_place_probability(self, win_prob: float, rank: int, field_size: int) -> float:
        """
        Estimate place probability from win probability using a more realistic model
        
        This uses a field-size aware approach that's more conservative for longshots.
        The model accounts for the fact that the top few horses dominate place outcomes.
        
        Args:
            win_prob: Win probability
            rank: Predicted rank
            field_size: Number of runners
            
        Returns:
            Place probability (normalized)
        """
        # Determine number of places paid
        if field_size <= 4:
            # No places or only 1-2 places - not worth betting
            return win_prob * 1.5
        elif field_size <= 7:
            num_places = 2  # Win + 1 place
        else:
            num_places = 3  # Win + 2 places
        
        # More realistic multipliers based on rank and field competitiveness
        # These are calibrated to be closer to market reality
        if rank == 1:
            # Top pick: very likely to place if strong
            if win_prob >= 0.25:
                return min(0.90, win_prob * 3.0)
            elif win_prob >= 0.15:
                return min(0.80, win_prob * 3.5)
            else:
                return min(0.70, win_prob * 4.0)
        
        elif rank == 2:
            # Second choice: good place chance if competitive
            if win_prob >= 0.20:
                return min(0.85, win_prob * 3.2)
            elif win_prob >= 0.10:
                return min(0.75, win_prob * 3.8)
            else:
                return min(0.60, win_prob * 4.5)
        
        elif rank == 3:
            # Third choice: decent place chance in small fields
            if win_prob >= 0.15:
                return min(0.75, win_prob * 3.5)
            elif win_prob >= 0.08:
                return min(0.65, win_prob * 4.0)
            else:
                return min(0.50, win_prob * 4.5)
        
        else:
            # Rank 4+: Longshots - be much more conservative
            # These horses rarely place, especially in large fields
            if win_prob >= 0.10:
                # Still has some chance
                return min(0.50, win_prob * 3.0)
            elif win_prob >= 0.07:
                # Outside chance - conservative
                return min(0.35, win_prob * 2.8)
            elif win_prob >= 0.05:
                # Real longshot - very conservative  
                return min(0.25, win_prob * 2.3)
            elif win_prob >= 0.03:
                # Extreme longshot - minimal place chance
                # For 4% win prob: 4% * 1.8 = 7.2% place prob
                return min(0.15, win_prob * 1.8)
            else:
                # Ultra longshot - almost zero place chance
                # For 2% win prob: 2% * 1.5 = 3% place prob
                return min(0.10, win_prob * 1.5)
    
    def calculate_place_odds(self, win_odds: float, field_size: int) -> float:
        """
        Calculate place odds from win odds based on field size
        
        UK convention:
        - 5-7 runners: 1/4 odds
        - 8+ runners: 1/5 odds
        
        Args:
            win_odds: Decimal win odds
            field_size: Number of runners
            
        Returns:
            Place decimal odds
        """
        if field_size <= 4:
            # Too few runners for place betting in most markets
            return None
        elif field_size <= 7:
            # 1/4 odds: payout = (win_odds - 1) / 4 + 1
            return (win_odds - 1) * 0.25 + 1
        else:
            # 1/5 odds: payout = (win_odds - 1) / 5 + 1
            return (win_odds - 1) * 0.20 + 1
    
    def recommend_win_bet(self, runner_prediction: dict, market_odds: float) -> Optional[Dict]:
        """
        Generate win bet recommendation
        
        Args:
            runner_prediction: Prediction dict with win_probability, horse_name, etc.
            market_odds: Market decimal odds for win
            
        Returns:
            Recommendation dict or None if not value
        """
        win_prob = runner_prediction['win_probability']
        
        if not market_odds or market_odds <= 1.0:
            return None
        
        # Check if value bet
        if not self.is_value_bet(win_prob, market_odds):
            return None
        
        # Calculate stake and EV
        stake, stake_pct = self.kelly_stake(win_prob, market_odds)
        ev = self.calculate_expected_value(win_prob, market_odds)
        
        if stake <= 0:
            return None
        
        return {
            'bet_type': 'WIN',
            'horse_name': runner_prediction.get('horse_name', 'Unknown'),
            'runner_number': runner_prediction.get('runner_number'),
            'predicted_rank': runner_prediction.get('predicted_rank'),
            'our_probability': win_prob,
            'our_odds': self.probability_to_odds(win_prob),
            'market_odds': market_odds,
            'stake': stake,
            'stake_percentage': stake_pct,
            'expected_value': ev,
            'potential_profit': stake * market_odds - stake,
            'ev_percentage': ev * 100
        }
    
    def recommend_place_bet(self, runner_prediction: dict, market_place_odds: float, 
                           field_size: int) -> Optional[Dict]:
        """
        Generate place bet recommendation
        
        Args:
            runner_prediction: Prediction dict
            market_place_odds: Market place odds (if available)
            field_size: Number of runners in race
            
        Returns:
            Recommendation dict or None
        """
        win_prob = runner_prediction['win_probability']
        rank = runner_prediction.get('predicted_rank', 1)
        
        # Calculate place probability
        place_prob = self.calculate_place_probability(win_prob, rank, field_size)
        
        # If no market place odds provided, estimate from win odds
        if not market_place_odds and 'market_odds' in runner_prediction:
            market_place_odds = self.calculate_place_odds(
                runner_prediction['market_odds'], 
                field_size
            )
        
        if not market_place_odds or market_place_odds <= 1.0:
            return None
        
        # Check if value
        if not self.is_value_bet(place_prob, market_place_odds):
            return None
        
        # Calculate stake and EV
        stake, stake_pct = self.kelly_stake(place_prob, market_place_odds)
        ev = self.calculate_expected_value(place_prob, market_place_odds)
        
        if stake <= 0:
            return None
        
        return {
            'bet_type': 'PLACE',
            'horse_name': runner_prediction.get('horse_name', 'Unknown'),
            'runner_number': runner_prediction.get('runner_number'),
            'predicted_rank': runner_prediction.get('predicted_rank'),
            'our_probability': place_prob,
            'our_odds': self.probability_to_odds(place_prob),
            'market_odds': market_place_odds,
            'stake': stake,
            'stake_percentage': stake_pct,
            'expected_value': ev,
            'potential_profit': stake * market_place_odds - stake,
            'ev_percentage': ev * 100
        }
    
    def recommend_exacta(self, top_2_predictions: List[dict], exacta_odds: float = None) -> Optional[Dict]:
        """
        Generate exacta bet recommendation (1-2 in correct order)
        
        Args:
            top_2_predictions: List of top 2 predictions
            exacta_odds: Market exacta odds (if available)
            
        Returns:
            Recommendation dict or None
        """
        if len(top_2_predictions) < 2:
            return None
        
        # Calculate exacta probability (simplified)
        p1 = top_2_predictions[0]['win_probability']
        p2 = top_2_predictions[1]['win_probability']
        exacta_prob = p1 * p2  # Simplified model
        
        # Threshold: must be >10% probability
        if exacta_prob < 0.10:
            return None
        
        # If no market odds, estimate
        if not exacta_odds:
            # Estimate: exacta typically pays more than win odds multiplied
            our_exacta_odds = self.probability_to_odds(exacta_prob)
            # Use a conservative estimate if no market data
            exacta_odds = our_exacta_odds * 0.8  # Assume market is slightly better
        
        if exacta_odds <= 1.0:
            return None
        
        # Check value
        if not self.is_value_bet(exacta_prob, exacta_odds):
            return None
        
        # Calculate stake (use reduced Kelly for exotics due to higher variance)
        stake, stake_pct = self.kelly_stake(exacta_prob, exacta_odds)
        stake *= 0.5  # Half stake for exotics
        stake_pct *= 0.5
        ev = self.calculate_expected_value(exacta_prob, exacta_odds)
        
        if stake <= 0:
            return None
        
        return {
            'bet_type': 'EXACTA',
            'combination': f"{top_2_predictions[0].get('horse_name')} → {top_2_predictions[1].get('horse_name')}",
            'our_probability': exacta_prob,
            'our_odds': self.probability_to_odds(exacta_prob),
            'market_odds': exacta_odds,
            'stake': stake,
            'stake_percentage': stake_pct,
            'expected_value': ev,
            'potential_profit': stake * exacta_odds - stake,
            'ev_percentage': ev * 100
        }
    
    def recommend_trifecta(self, top_3_predictions: List[dict], trifecta_odds: float = None) -> Optional[Dict]:
        """
        Generate trifecta bet recommendation (1-2-3 in correct order)
        
        Args:
            top_3_predictions: List of top 3 predictions
            trifecta_odds: Market trifecta odds (if available)
            
        Returns:
            Recommendation dict or None
        """
        if len(top_3_predictions) < 3:
            return None
        
        # Calculate trifecta probability
        p1 = top_3_predictions[0]['win_probability']
        p2 = top_3_predictions[1]['win_probability']
        p3 = top_3_predictions[2]['win_probability']
        trifecta_prob = p1 * p2 * p3
        
        # Threshold: must be >5% probability
        if trifecta_prob < 0.05:
            return None
        
        # If no market odds, estimate
        if not trifecta_odds:
            our_trifecta_odds = self.probability_to_odds(trifecta_prob)
            trifecta_odds = our_trifecta_odds * 0.7
        
        if trifecta_odds <= 1.0:
            return None
        
        # Check value
        if not self.is_value_bet(trifecta_prob, trifecta_odds):
            return None
        
        # Calculate stake (reduced for exotics)
        stake, stake_pct = self.kelly_stake(trifecta_prob, trifecta_odds)
        stake *= 0.33  # Third stake for trifectas
        stake_pct *= 0.33
        ev = self.calculate_expected_value(trifecta_prob, trifecta_odds)
        
        if stake <= 0:
            return None
        
        return {
            'bet_type': 'TRIFECTA',
            'combination': f"{top_3_predictions[0].get('horse_name')} → {top_3_predictions[1].get('horse_name')} → {top_3_predictions[2].get('horse_name')}",
            'our_probability': trifecta_prob,
            'our_odds': self.probability_to_odds(trifecta_prob),
            'market_odds': trifecta_odds,
            'stake': stake,
            'stake_percentage': stake_pct,
            'expected_value': ev,
            'potential_profit': stake * trifecta_odds - stake,
            'ev_percentage': ev * 100
        }
    
    def recommend_first_four(self, top_4_predictions: List[dict], first_four_odds: float = None) -> Optional[Dict]:
        """
        Generate first four bet recommendation (1-2-3-4 in correct order)
        
        Args:
            top_4_predictions: List of top 4 predictions
            first_four_odds: Market first four odds (if available)
            
        Returns:
            Recommendation dict or None
        """
        if len(top_4_predictions) < 4:
            return None
        
        # Calculate first four probability
        p1 = top_4_predictions[0]['win_probability']
        p2 = top_4_predictions[1]['win_probability']
        p3 = top_4_predictions[2]['win_probability']
        p4 = top_4_predictions[3]['win_probability']
        first_four_prob = p1 * p2 * p3 * p4
        
        # Threshold: must be >2% probability
        if first_four_prob < 0.02:
            return None
        
        # If no market odds, estimate
        if not first_four_odds:
            our_first_four_odds = self.probability_to_odds(first_four_prob)
            first_four_odds = our_first_four_odds * 0.6
        
        if first_four_odds <= 1.0:
            return None
        
        # Check value
        if not self.is_value_bet(first_four_prob, first_four_odds):
            return None
        
        # Calculate stake (heavily reduced for first four)
        stake, stake_pct = self.kelly_stake(first_four_prob, first_four_odds)
        stake *= 0.25  # Quarter stake for first four
        stake_pct *= 0.25
        ev = self.calculate_expected_value(first_four_prob, first_four_odds)
        
        if stake <= 0:
            return None
        
        return {
            'bet_type': 'FIRST FOUR',
            'combination': f"{top_4_predictions[0].get('horse_name')} → {top_4_predictions[1].get('horse_name')} → {top_4_predictions[2].get('horse_name')} → {top_4_predictions[3].get('horse_name')}",
            'our_probability': first_four_prob,
            'our_odds': self.probability_to_odds(first_four_prob),
            'market_odds': first_four_odds,
            'stake': stake,
            'stake_percentage': stake_pct,
            'expected_value': ev,
            'potential_profit': stake * first_four_odds - stake,
            'ev_percentage': ev * 100
        }
    
    @staticmethod
    def get_kelly_description(kelly_fraction: float) -> str:
        """
        Get description for Kelly fraction setting
        
        Args:
            kelly_fraction: Kelly fraction value
            
        Returns:
            Description string with warning level
        """
        if kelly_fraction >= 1.0:
            return "⚠️ AGGRESSIVE: Can stake 15-25% of bankroll on strong bets. High variance, high reward."
        elif kelly_fraction >= 0.67:
            return "⚠️ BOLD: Stakes 10-18% on strong bets. Higher risk, faster growth."
        elif kelly_fraction >= 0.5:
            return "✓ BALANCED: Stakes 7-12% on strong bets. Recommended for most users."
        elif kelly_fraction >= 0.33:
            return "✓ CAUTIOUS: Stakes 5-8% on strong bets. Lower variance."
        elif kelly_fraction >= 0.25:
            return "✓ CONSERVATIVE: Stakes 3-6% on strong bets. Lower risk, slower growth."
        else:
            return "✓ VERY CONSERVATIVE: Stakes 1-3% on strong bets. Minimal risk."

