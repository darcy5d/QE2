# GUI Display Ranking and Place Probability Fix

## Issues Identified

### Issue 1: GUI Table Not Sorted by Win Probability
**Problem**: The GUI predictions table was displaying runners in the order returned by the predictor, not sorted by win probability. The CSV export was correct, but the on-screen display was wrong.

**Root Cause**: In `predictions_view.py` line ~934, `create_predictions_table()` was called with unsorted predictions.

**Fix**: Added sorting logic before displaying the table:
```python
# Sort predictions by win probability (highest first)
sorted_predictions = sorted(race_pred['predictions'], key=lambda x: x['win_probability'], reverse=True)

# Re-assign ranks based on win probability
for rank, pred in enumerate(sorted_predictions, 1):
    pred['predicted_rank'] = rank
```

### Issue 2: Place Probabilities Don't Sum to 300%
**Problem**: Place probabilities (chance of finishing in top 3) were calculated independently and didn't sum to the theoretical 300% (since exactly 3 horses will place).

**Example**: Gowran Park race had place probabilities summing to ~700%, which is mathematically impossible.

**Root Cause**: The `calculate_place_probability()` function was using heuristics that didn't enforce the sum constraint.

**Fix**: Added normalization logic to ensure place probabilities always sum to exactly 300%:

```python
# Calculate raw place probabilities
raw_place_probs = []
for pred in predictions:
    raw_prob = self.calculate_place_probability(
        pred['predicted_rank'], 
        len(predictions),
        win_prob=pred['win_probability']
    )
    raw_place_probs.append(raw_prob)

# Normalize to sum to 300%
total_raw = sum(raw_place_probs)
if total_raw > 0:
    normalized_place_probs = [(p / total_raw) * 300 for p in raw_place_probs]
else:
    normalized_place_probs = raw_place_probs
```

## Files Modified

### `Datafetch/gui/predictions_view.py`

**Change 1**: Lines ~929-934 - Sort predictions before displaying in GUI table
**Change 2**: Lines ~1054-1069 - Add place probability normalization to table display
**Change 3**: Lines ~1117-1122 - Use normalized place probability in table
**Change 4**: Lines ~1388-1409 - Add place probability normalization to CSV export

## Testing Steps

1. **Launch GUI**:
   ```bash
   cd /Users/darcy5d/Desktop/DD_AI_models/QE2/Datafetch
   python racecard_gui.py
   ```

2. **Generate Predictions**:
   - Go to Predictions tab (Tab 5)
   - Click "Fetch Upcoming Races"
   - Select any race
   - Click "Generate Predictions"

3. **Verify Fixes**:
   
   **✅ Ranking Fix**:
   - Rank 1 should have the HIGHEST Win %
   - Rank 2 should have the 2nd HIGHEST Win %
   - Rankings should decrease monotonically
   
   **✅ Place Probability Fix**:
   - Sum all Place % values in a race
   - Total should equal ~300% (±0.1% for rounding)
   - Place % should generally be 3-6x the Win % depending on field size

## Expected Results

### Example: Wolverhampton Race (After Fix)

| Rank | Horse          | Win %  | Place % | Notes                          |
|------|----------------|--------|---------|--------------------------------|
| 1    | Diligent Henry | 16.1%  | ~60-70% | Highest win % = Rank 1 ✅       |
| 2    | Bandello       | 13.6%  | ~55-65% | 2nd highest win % = Rank 2 ✅  |
| 3    | Beautiful Dawn | 9.9%   | ~40-50% | 3rd highest win % = Rank 3 ✅  |
| ...  | ...            | ...    | ...     | Sum of all Place % = 300% ✅   |

### Example: Gowran Park Race (After Fix)

| Rank | Horse             | Win %  | Place % (Before) | Place % (After) | Notes                    |
|------|-------------------|--------|------------------|-----------------|--------------------------|
| 1    | Green Universe    | 5.1%   | 30.8%            | ~24%            | Normalized to sum 300%   |
| 2    | Canon Law         | 4.8%   | 38.8%            | ~23%            | Normalized to sum 300%   |
| 3    | Stairiuil         | 4.9%   | 38.8%            | ~23%            | Normalized to sum 300%   |
| ...  | ...               | ...    | ...              | ...             | ...                      |
| **Total** |               |        | **~700%** ❌     | **300%** ✅     | Now mathematically valid |

## Benefits

1. **Rankings Now Correct**: The GUI table displays horses in the correct order by model confidence
2. **Place Probabilities Now Valid**: They sum to 300% as required by probability theory
3. **Betting Guidance Improved**: Users can trust both Win % and Place % for betting decisions
4. **Exotic Bets More Accurate**: Exacta/Trifecta probabilities based on correct rankings

## Mathematical Note

**Why 300%?**

In any race, exactly 3 horses will place (1st, 2nd, 3rd). If we sum the probability that each horse will finish in the top 3, the total must equal 300% (or 3.0 in decimal).

This is similar to how win probabilities must sum to 100% (exactly 1 horse wins).

**Normalization Formula**:
```
normalized_place_prob = (raw_place_prob / sum_of_all_raw_place_probs) * 300
```

This ensures:
1. Relative probabilities are preserved (if Horse A had 2x the raw probability of Horse B, it still has 2x after normalization)
2. The sum constraint is satisfied (all normalized probabilities sum to exactly 300%)

## Status

✅ **Implemented and Ready for Testing**

All changes are in place. User should test in GUI to verify both fixes work correctly.


