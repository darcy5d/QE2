# In The Money Betting System - Implementation Complete

## Overview

Successfully implemented a sophisticated value betting system that identifies profitable betting opportunities by comparing ML model predictions against market odds, using Kelly Criterion for intelligent stake sizing.

## What Was Built

### 1. Betting Calculator Module (`betting_calculator.py`)

**Core Functionality:**
- **Kelly Criterion Implementation**: Calculates optimal stake sizes based on edge and odds
- **Expected Value Calculation**: Determines if bets have positive expected value
- **Multiple Kelly Fractions**: Supports 1/8, 1/4, 1/3, 1/2, 2/3, and Full Kelly with appropriate warnings
- **Bet Type Support**: Win, Place, Exacta, Trifecta, First Four

**Key Methods:**
- `probability_to_odds()` - Converts probabilities to decimal odds
- `calculate_expected_value()` - Calculates EV as (probability × odds) - 1
- `kelly_stake()` - Applies Kelly formula with safety caps
- `recommend_win_bet()` - Generates win bet recommendations
- `recommend_place_bet()` - Calculates place betting opportunities
- `recommend_exacta()` - Identifies exacta value (>10% probability threshold)
- `recommend_trifecta()` - Identifies trifecta value (>5% probability threshold)
- `recommend_first_four()` - Identifies first four value (>2% probability threshold)

**Safety Features:**
- Maximum 10% of bankroll per bet (safety cap)
- Configurable minimum edge threshold (default 5%)
- Reduced stakes for exotic bets (50% for exacta, 33% for trifecta, 25% for first four)

### 2. Updated Predictions View

**New Table Columns:**
| Column | Description |
|--------|-------------|
| Rank | Predicted finishing position |
| No. | Horse number |
| Horse | Horse name |
| Jockey | Jockey name |
| Trainer | Trainer name |
| **Assessment** | **"Top Pick", "Strong Chance", "Good Chance", or "Outsider"** |
| **Our Win Odds** | **Model's fair odds (converted from probability)** |
| **Mkt Win Odds** | **Market consensus odds from bookmakers** |
| **Our Place Odds** | **Fair place odds (1/4 or 1/5 based on field size)** |
| **Mkt Place Odds** | **Market place odds** |
| Top Features | Most important features for this prediction |

**Visual Indicators:**
- Green highlighting when market odds > our odds (value bet)
- Color-coded assessments (green for top picks, amber for strong chances, etc.)

**Assessment Thresholds:**
- **Top Pick**: >25% win probability
- **Strong Chance**: 15-25% win probability
- **Good Chance**: 10-15% win probability
- **Outsider**: <10% win probability

### 3. In The Money View (`in_the_money_view.py`)

**Settings Panel:**
- **Bankroll Input**: User-configurable total betting bankroll (default $1000)
- **Kelly Fraction Selector**: Six options from 1/8 Kelly to Full Kelly
- **Dynamic Warnings**: Updates based on Kelly selection to show risk level
- **Minimum Edge Filter**: 5%, 10%, 15%, or 20% edge required
- **Bet Type Filters**: Checkboxes to show/hide Win, Place, Exacta, Trifecta, First Four

**Kelly Fraction Options:**
1. **1/8 Kelly (0.125)**: Very Conservative - Stakes 1-3% on strong bets
2. **1/4 Kelly (0.25)**: Conservative - Stakes 3-6% on strong bets
3. **1/3 Kelly (0.33)**: Cautious - Stakes 5-8% on strong bets
4. **1/2 Kelly (0.50)**: Balanced ✓ DEFAULT - Stakes 7-12% on strong bets
5. **2/3 Kelly (0.67)**: Bold - Stakes 10-18% on strong bets
6. **Full Kelly (1.0)**: Aggressive ⚠️ - Stakes 15-25% on strong bets

**Recommendations Display:**
- Hierarchical tree structure: Date → Course → Race → Bets
- Shows stake amount, odds, EV%, and potential profit for each bet
- Color-coded by bet type (green for wins, blue for places, amber for exotics)
- Expandable/collapsible sections for easy navigation

**Summary Panel:**
- Total number of recommended bets
- Total stake across all bets
- Expected profit (probability-weighted)
- Return on Investment (ROI) percentage

**Export Feature:**
- Export recommendations to CSV with all bet details
- Includes date, course, race details, bet type, selection, odds, stakes, and EV

### 4. Enhanced Predictor

**Market Odds Integration:**
- Modified `_get_race_data()` to join with `runner_market_odds` table
- Added `market_odds` and `market_prob` to prediction output
- Enables direct comparison between model and market

**Place Odds Calculation:**
- UK convention: 1/4 odds for 5-7 runners, 1/5 odds for 8+ runners
- Formula: `place_odds = (win_odds - 1) × fraction + 1`

### 5. Navigation Integration

**Updated Files:**
- `nav_ribbon.py` - Added "💰 In The Money" button
- `dashboard_window.py` - Integrated new view into main application

## How To Use

### Step 1: Fetch Upcoming Races
1. Go to "Upcoming Races" tab
2. Click "Fetch Upcoming Races"
3. Wait for races to be downloaded

### Step 2: Generate Predictions
1. Go to "Predictions" tab
2. Click "Generate Predictions"
3. Review predictions with new odds columns

### Step 3: Find Value Bets
1. Go to "💰 In The Money" tab
2. Configure settings:
   - Set your bankroll (e.g., $1000)
   - Choose Kelly fraction (recommend Half Kelly for balanced approach)
   - Set minimum edge threshold (recommend 5-10%)
   - Select bet types to analyze
3. Click "🚀 Find Value Bets"
4. Review recommendations hierarchically organized by date/course/race

### Step 4: Place Bets (Manual)
1. Review the recommendations
2. Check the EV% and potential profit
3. Note the recommended stake sizes
4. Place bets with your bookmaker
5. Optional: Export to CSV for record keeping

## Key Formulas

### Expected Value (EV)
```
EV = (our_probability × market_odds) - 1.0
Example: 30% probability, 4.0 odds → EV = (0.30 × 4.0) - 1.0 = 0.20 (20% edge)
```

### Kelly Criterion Stake
```
edge = (our_prob × market_odds) - 1.0
kelly_percentage = (edge / (market_odds - 1))
stake = kelly_percentage × kelly_fraction × bankroll
stake = min(stake, bankroll × 0.10)  // Safety cap at 10%
```

### Place Odds Conversion
```
if runners <= 7:
    place_odds = (win_odds - 1) × 0.25 + 1  // 1/4 odds
else:
    place_odds = (win_odds - 1) × 0.20 + 1  // 1/5 odds
```

### Probability to Decimal Odds
```
decimal_odds = 1.0 / probability
Example: 25% (0.25) → 4.0 odds
```

## Safety Features

1. **Maximum Stake Cap**: Never stake more than 10% of bankroll on a single bet
2. **Minimum Edge Threshold**: Configurable filter (5-20%) to avoid marginal bets
3. **Reduced Stakes for Exotics**: Exotic bets use fractional stakes due to higher variance
4. **Kelly Fraction Warnings**: Clear warnings about risk levels for each Kelly setting
5. **Probability Thresholds**: Exotics only recommended when probability exceeds sensible minimums

## Files Modified/Created

### New Files:
- `/Datafetch/gui/betting_calculator.py` - Core betting logic and Kelly Criterion
- `/Datafetch/gui/in_the_money_view.py` - Main betting recommendations interface

### Modified Files:
- `/Datafetch/gui/predictions_view.py` - Added new columns for odds comparison
- `/Datafetch/ml/predictor.py` - Enhanced to include market odds in predictions
- `/Datafetch/gui/nav_ribbon.py` - Added In The Money navigation button
- `/Datafetch/gui/dashboard_window.py` - Integrated new view

## Technical Details

### Database Schema Used

**runner_market_odds** table:
```sql
CREATE TABLE runner_market_odds (
    market_odds_id INTEGER PRIMARY KEY,
    runner_id INTEGER NOT NULL UNIQUE,
    avg_decimal REAL,           -- Average market odds
    median_decimal REAL,         -- Median market odds
    min_decimal REAL,            -- Best available odds
    max_decimal REAL,            -- Worst available odds
    bookmaker_count INTEGER,     -- Number of bookmakers
    implied_probability REAL,    -- Market's implied probability
    is_favorite INTEGER,         -- 1 if favorite
    favorite_rank INTEGER,       -- Rank by market odds
    updated_at TIMESTAMP
);
```

### Exotic Bet Probability Calculations

**Exacta (1-2 in order):**
```python
exacta_probability = p1 × p2
# Simplified model assuming independence
```

**Trifecta (1-2-3 in order):**
```python
trifecta_probability = p1 × p2 × p3
```

**First Four (1-2-3-4 in order):**
```python
first_four_probability = p1 × p2 × p3 × p4
```

Note: These are simplified calculations. In reality, conditional probabilities would be more accurate.

## Recommended Workflow

### Conservative Approach (Start Here)
1. **Bankroll**: $500-$1000
2. **Kelly Fraction**: 1/4 Kelly
3. **Min Edge**: 10%
4. **Bet Types**: Win and Place only
5. **Focus**: Top 2-3 ranked horses per race

### Balanced Approach (After Testing)
1. **Bankroll**: $1000-$5000
2. **Kelly Fraction**: 1/2 Kelly (default)
3. **Min Edge**: 5-10%
4. **Bet Types**: Win, Place, Exacta
5. **Focus**: Value opportunities across all rankings

### Aggressive Approach (Experienced Only)
1. **Bankroll**: $5000+
2. **Kelly Fraction**: 2/3 Kelly
3. **Min Edge**: 5%
4. **Bet Types**: All types including exotics
5. **Focus**: Maximum value extraction

## Important Notes

⚠️ **Risk Warning**: This system is for educational purposes. Betting carries financial risk. Never bet more than you can afford to lose.

📊 **Track Results**: Export your bets and track actual vs predicted performance over time to validate the model.

🎯 **Model Quality**: The value betting system is only as good as your ML model's predictions. Regularly retrain and evaluate model performance.

💰 **Bankroll Management**: Start conservatively and only increase stakes after proving profitability over a significant sample size (100+ bets).

🔄 **Market Efficiency**: In highly efficient markets, finding consistent value is challenging. Focus on races where your model has informational advantages.

## Future Enhancements

Potential improvements for future versions:

1. **Historical Bet Tracking**: Store placed bets and track P&L over time
2. **Auto-betting Integration**: API integration with betting exchanges
3. **Live Odds Updates**: Real-time odds monitoring and alerts
4. **Advanced Exotic Pricing**: More sophisticated models for exotic bet probabilities
5. **Portfolio Optimization**: Optimal bet selection across multiple races
6. **Risk Metrics**: Drawdown analysis, Sharpe ratio, win rate tracking
7. **Market Movement**: Track odds movements and identify steaming/drifting horses

## Conclusion

The In The Money betting system provides a sophisticated, mathematically-sound approach to value betting on horse racing. By combining ML predictions with Kelly Criterion stake sizing, it offers a disciplined framework for identifying and exploiting market inefficiencies.

Remember: **Long-term profitability requires discipline, patience, and rigorous tracking of results.**

Good luck! 🍀

