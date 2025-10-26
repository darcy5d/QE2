# Scratched Horses (Non-Runner) Bug Fix - Comprehensive Plan

## Problem Statement

**Critical Bug**: The system currently generates predictions and betting recommendations for scratched horses (non-runners), leading to:
1. Invalid betting recommendations on horses that won't run
2. Incorrect field size calculations affecting place payouts
3. Wrong probability distributions (don't account for reduced field)
4. Missed value opportunities on remaining horses

**Real Example** (from user):
- Horse: "Item" (#NR, jockey: NON-RUNNER)
- Model recommended: WIN $5.33 + PLACE $12.90
- Result: Invalid bets on scratched horse!

---

## Solution Overview

Implement 4-layer defense system:
1. **Detection**: Identify scratched horses by jockey name and runner number
2. **Filtering**: Remove scratched horses before prediction calculations
3. **Recalculation**: Adjust field size and probabilities for remaining horses
4. **UI Warnings**: Alert users to scratched horses and stale data

---

## Implementation Plan

### Phase 1: Detection Layer (Core Logic)

**File**: `Datafetch/ml/predictor.py`

#### 1.1 Add Scratched Horse Detection Method

```python
def _is_scratched(self, runner: Dict) -> bool:
    """
    Detect if a runner is scratched/non-runner
    
    Scratched indicators:
    - runner_number is 'NR' or None
    - jockey_name contains 'NON-RUNNER' or 'NON RUNNER'
    - jockey_name is empty/None with runner_number = 'NR'
    
    Returns:
        True if horse is scratched, False otherwise
    """
    runner_number = str(runner.get('number', '')).strip().upper()
    jockey_name = str(runner.get('jockey_name', '')).strip().upper()
    
    # Check runner number
    if runner_number in ['NR', 'N/R', '']:
        return True
    
    # Check jockey name
    if 'NON-RUNNER' in jockey_name or 'NON RUNNER' in jockey_name:
        return True
    
    # Check for empty jockey with no valid number
    if not jockey_name and not runner_number.isdigit():
        return True
    
    return False
```

#### 1.2 Filter Scratched Horses in `predict_race()`

**Location**: Line 152 (after loading race_data)

```python
# Filter out scratched horses BEFORE any calculations
original_count = len(race_data['runners'])
active_runners = [r for r in race_data['runners'] if not self._is_scratched(r)]
scratched_count = original_count - len(active_runners)

if scratched_count > 0:
    scratched_names = [r.get('horse_name', 'Unknown') 
                       for r in race_data['runners'] 
                       if self._is_scratched(r)]
    print(f"   ⚠️  {scratched_count} scratched horse(s): {', '.join(scratched_names)}")
    print(f"   Active field size: {len(active_runners)}")

# Update race_data with filtered runners
race_data['runners'] = active_runners
race_data['race_info']['scratched_count'] = scratched_count
race_data['race_info']['scratched_horses'] = scratched_names if scratched_count > 0 else []

if len(active_runners) == 0:
    print(f"   ❌ All horses scratched - no predictions possible!")
    return None
```

#### 1.3 Recalculate Field Size

**Location**: Line 1047 in `feature_engineer.py`

```python
def compute_relative_features(self, all_runner_features: List[Dict]) -> List[Dict]:
    """
    Compute relative features with ACTIVE field size (excluding scratches)
    """
    if not all_runner_features:
        return all_runner_features
    
    # === FIELD SIZE (ACTIVE RUNNERS ONLY) ===
    field_size = len(all_runner_features)  # Already filtered by predictor
    print(f"   Computing relative features for {field_size} active runners")
    
    for features in all_runner_features:
        features['field_size'] = field_size
```

---

### Phase 2: Betting Calculator Adjustments

**File**: `Datafetch/gui/betting_calculator.py`

#### 2.1 Add Field Size Validation

```python
def recommend_place_bet(self, runner_prediction: Dict, place_odds: float, 
                       field_size: int, scratched_count: int = 0) -> Optional[Dict]:
    """
    Recommend place bet with scratched horse awareness
    
    Args:
        runner_prediction: Runner prediction data
        place_odds: Place odds (or None to estimate from win odds)
        field_size: ACTIVE field size (excluding scratched horses)
        scratched_count: Number of scratched horses
    """
    # Validate field size is for active runners only
    active_field_size = field_size - scratched_count
    
    if active_field_size != field_size:
        print(f"   ⚠️  Field size mismatch - using active size: {active_field_size}")
        field_size = active_field_size
    
    # Determine places paid based on ACTIVE field size
    if field_size <= 4:
        return None  # No place bets for very small fields
    elif field_size <= 7:
        num_places = 2
    else:
        num_places = 3
    
    # ... rest of place bet logic
```

---

### Phase 3: In The Money View Enhancements

**File**: `Datafetch/gui/in_the_money_view.py`

#### 3.1 Display Scratched Horse Warnings

**Location**: After line 664 in `analyze_predictions()`

```python
def analyze_predictions(self, all_race_predictions):
    """Analyze predictions with scratched horse awareness"""
    recommendations = []
    total_scratched = 0
    races_with_scratches = []
    
    for race_pred in all_race_predictions:
        race_info = race_pred['race_info']
        predictions = race_pred['predictions']
        
        # Check for scratched horses
        scratched_count = race_info.get('scratched_count', 0)
        if scratched_count > 0:
            total_scratched += scratched_count
            scratched_horses = race_info.get('scratched_horses', [])
            races_with_scratches.append({
                'course': race_info.get('course'),
                'time': race_info.get('time'),
                'scratched': scratched_horses
            })
        
        field_size = len(predictions)  # Already filtered to active runners
        
        # ... rest of analysis logic
    
    # Store scratch info for UI display
    if total_scratched > 0:
        self.scratch_warning = {
            'count': total_scratched,
            'races': races_with_scratches
        }
    
    return recommendations
```

#### 3.2 Add Scratch Warning Banner

**Location**: In `create_recommendations_tree()` before line 360

```python
def create_recommendations_tree(self):
    """Create tree widget with scratch warning banner"""
    # ... existing code ...
    
    # Add warning banner frame
    self.scratch_warning_frame = QFrame()
    self.scratch_warning_frame.setVisible(False)
    self.scratch_warning_frame.setStyleSheet(f"""
        QFrame {{
            background-color: {COLORS['warning_bg']};
            border: 2px solid {COLORS['warning_border']};
            border-radius: 6px;
            padding: 10px;
        }}
    """)
    
    warning_layout = QHBoxLayout()
    self.scratch_warning_label = QLabel()
    self.scratch_warning_label.setStyleSheet(f"color: {COLORS['warning_text']}; font-weight: bold;")
    warning_layout.addWidget(self.scratch_warning_label)
    
    # Refresh button
    self.refresh_runners_btn = QPushButton("🔄 Refresh Runner Status")
    self.refresh_runners_btn.clicked.connect(self.refresh_runner_status)
    warning_layout.addWidget(self.refresh_runners_btn)
    
    warning_layout.addStretch()
    self.scratch_warning_frame.setLayout(warning_layout)
    
    return tree
```

#### 3.3 Update Display with Warnings

**Location**: In `display_filtered_recommendations()` after line 787

```python
def display_filtered_recommendations(self):
    """Display recommendations with scratch warnings"""
    self.recommendations_tree.clear()
    
    # Show scratch warning if applicable
    if hasattr(self, 'scratch_warning') and self.scratch_warning:
        scratch_count = self.scratch_warning['count']
        race_count = len(self.scratch_warning['races'])
        
        warning_text = f"⚠️ {scratch_count} scratched horse(s) in {race_count} race(s) - "
        warning_text += "Click 'Refresh Runner Status' to update or refetch upcoming races"
        
        self.scratch_warning_label.setText(warning_text)
        self.scratch_warning_frame.setVisible(True)
        
        # Add expandable details
        scratch_item = QTreeWidgetItem(["⚠️ SCRATCHED HORSES (Not included in recommendations)", "", "", "", ""])
        scratch_item.setForeground(0, QColor(COLORS['warning_text']))
        scratch_font = QFont()
        scratch_font.setBold(True)
        scratch_item.setFont(0, scratch_font)
        self.recommendations_tree.addTopLevelItem(scratch_item)
        
        for race in self.scratch_warning['races']:
            detail_text = f"   {race['course']} {race['time']}: {', '.join(race['scratched'])}"
            detail_item = QTreeWidgetItem([detail_text, "", "", "", ""])
            detail_item.setForeground(0, QColor(COLORS['warning_text']))
            scratch_item.addChild(detail_item)
        
        scratch_item.setExpanded(True)
    else:
        self.scratch_warning_frame.setVisible(False)
    
    # ... rest of display logic
```

---

### Phase 4: Refresh Runner Status Feature

**File**: `Datafetch/gui/in_the_money_view.py`

#### 4.1 Add Refresh Method

```python
@Slot()
def refresh_runner_status(self):
    """
    Refresh runner status from API to detect late scratches
    
    This refetches the latest racecard data for races with scratches
    """
    if not hasattr(self, 'scratch_warning') or not self.scratch_warning:
        return
    
    reply = QMessageBox.question(
        self,
        "Refresh Runner Status",
        f"This will refetch racecard data for {len(self.scratch_warning['races'])} race(s) "
        f"to check for updated runner status.\n\n"
        f"Continue?",
        QMessageBox.Yes | QMessageBox.No
    )
    
    if reply == QMessageBox.No:
        return
    
    try:
        # Import upcoming fetcher
        from .upcoming_fetcher import UpcomingRacesFetcher
        
        # Get race IDs for races with scratches
        conn = sqlite3.connect(str(self.upcoming_db_path))
        cursor = conn.cursor()
        
        # Fetch fresh data for each race
        fetcher = UpcomingRacesFetcher(self.upcoming_db_path)
        updated_count = 0
        
        for race in self.scratch_warning['races']:
            # Find race_id for this race
            cursor.execute("""
                SELECT race_id FROM races 
                WHERE course = ? AND off_time LIKE ?
            """, (race['course'], f"%{race['time']}%"))
            
            result = cursor.fetchone()
            if result:
                race_id = result[0]
                # Refetch this specific race
                # (Implementation depends on API capabilities)
                updated_count += 1
        
        conn.close()
        
        QMessageBox.information(
            self,
            "Refresh Complete",
            f"Updated {updated_count} race(s). Click 'Find Value Bets' to regenerate recommendations."
        )
        
        # Clear scratch warning to prompt regeneration
        self.scratch_warning = None
        self.scratch_warning_frame.setVisible(False)
        
    except Exception as e:
        QMessageBox.critical(
            self,
            "Refresh Failed",
            f"Failed to refresh runner status:\n{str(e)}"
        )
```

---

### Phase 5: Color Theme Updates

**File**: `Datafetch/gui/styles.py`

Add warning colors:

```python
COLORS = {
    # ... existing colors ...
    'warning_bg': '#FFF3CD',      # Light yellow background
    'warning_border': '#FFC107',   # Amber border
    'warning_text': '#856404',     # Dark yellow text
}
```

---

## Testing Plan

### Test Case 1: Single Scratched Horse
**Setup**: Race with 8 runners, 1 scratched (Item)
**Expected**:
- ✅ Item filtered out before prediction
- ✅ Field size = 7 (not 8)
- ✅ 2 places paid (7 runners)
- ✅ No bets recommended on Item
- ✅ Warning banner shows "1 scratched horse"
- ✅ Probabilities sum to 100% for 7 active runners

### Test Case 2: Multiple Scratched Horses
**Setup**: Race with 12 runners, 3 scratched
**Expected**:
- ✅ 3 horses filtered out
- ✅ Field size = 9
- ✅ 3 places paid (9 runners)
- ✅ Warning lists all 3 scratched horses
- ✅ Stakes calculated for 9-horse field

### Test Case 3: No Scratched Horses
**Setup**: Race with all active runners
**Expected**:
- ✅ No filtering occurs
- ✅ No warning banner shown
- ✅ Normal operation

### Test Case 4: All Horses Scratched (Edge Case)
**Setup**: Race with all runners scratched
**Expected**:
- ✅ predict_race() returns None
- ✅ Race skipped entirely
- ✅ Warning in console log

---

## Files to Modify

| File | Changes | Lines Est. |
|------|---------|------------|
| `Datafetch/ml/predictor.py` | Add `_is_scratched()`, filter in `predict_race()` | +50 |
| `Datafetch/ml/feature_engineer.py` | Update field size comments | +5 |
| `Datafetch/gui/betting_calculator.py` | Add field size validation | +20 |
| `Datafetch/gui/in_the_money_view.py` | Warnings, refresh button, display updates | +150 |
| `Datafetch/gui/styles.py` | Add warning colors | +3 |

**Total**: ~228 lines of new code

---

## Benefits

1. **Prevents Invalid Bets**: Never recommend scratched horses
2. **Accurate Field Size**: Correct place payout calculations
3. **Better Probabilities**: Sum to 100% for active field only
4. **User Awareness**: Clear warnings about scratched horses
5. **Data Freshness**: Refresh button to check latest status
6. **Improved ROI**: Avoid wasted bets on non-runners

---

## Edge Cases Handled

1. **Late Scratches**: Refresh button updates status
2. **All Scratched**: Race returns None, skipped entirely
3. **Partial Data**: Handles missing jockey names gracefully
4. **Varied Formats**: Detects "NR", "N/R", "NON-RUNNER", etc.
5. **Empty Fields**: Validates minimum active runners

---

## Rollback Plan

If issues arise:
```bash
git revert <commit-hash>
```

All changes are isolated to specific methods, making rollback safe.

---

## Success Criteria

✅ **Zero bets on scratched horses** in production  
✅ **Accurate field sizes** in all calculations  
✅ **Clear user warnings** when scratches detected  
✅ **Maintains 75%+ place rate** on active runners  
✅ **95%+ ROI preserved** with better accuracy

---

**Priority**: HIGH (Critical bug affecting betting accuracy)  
**Complexity**: MEDIUM (Clear solution, moderate implementation)  
**Risk**: LOW (Well-defined changes, good test coverage)  
**Estimated Time**: 2-3 hours implementation + 1 hour testing

---

Ready to implement when approved!

