# Additional Fixes: addStretch Error and Date Sorting

## Issues Fixed

### Issue 1: AttributeError - 'FlowLayout' object has no attribute 'addStretch'
**Problem**: When clicking date tabs, the app crashed with error:
```
AttributeError: 'FlowLayout' object has no attribute 'addStretch'
```

**Root Cause**: The `create_course_chips()` method was calling `self.course_chips_layout.addStretch()`, which is a method available on standard Qt layouts (QHBoxLayout, QVBoxLayout) but not on our custom `FlowLayout` class.

**Solution**: 
Removed the `addStretch()` call from line 623 in `predictions_view.py`:
```python
# Before:
self.course_chips_layout.addStretch()  # ERROR!
self.course_chips_container.setVisible(True)

# After:
# FlowLayout doesn't have addStretch(), wrapping is automatic
self.course_chips_container.setVisible(True)
```

**Why FlowLayout doesn't need addStretch()**: FlowLayout automatically handles spacing and wrapping. Unlike QHBoxLayout which needs `addStretch()` to push items to the left, FlowLayout fills space naturally by wrapping to new lines.

---

### Issue 2: Dates Not in Chronological Order
**Problem**: Date tabs were showing in alphabetical order instead of chronological:
- Displayed: "Mon 20 Oct", "Sat 18 Oct", "Sun 19 Oct"
- Expected: "Sat 18 Oct", "Sun 19 Oct", "Mon 20 Oct"

**Root Cause**: The `create_date_tabs()` method was sorting dates as strings using Python's default string sort:
```python
dates = sorted(self.organized_predictions.keys())  # Alphabetical sort!
```

This resulted in alphabetical order: "Mon" comes before "Sat" alphabetically, even though Oct 20 comes after Oct 18 chronologically.

**Solution**: 
1. **Added `date_objects` dictionary** to store actual date objects alongside formatted strings
2. **Updated `organize_predictions_by_hierarchy()`** to populate this mapping
3. **Updated `create_date_tabs()`** to sort by date object instead of string
4. **Updated `on_predictions_ready()`** to select first date chronologically

**Code Changes**:

**Line 113** - Added date_objects storage:
```python
self.date_objects = {}  # {date_str: date_obj} for proper sorting
```

**Lines 510-512** - Store date objects during organization:
```python
date_obj = datetime.strptime(date_str_raw, '%Y-%m-%d')
date_str = date_obj.strftime('%a %d %b')  # e.g., "Fri 18 Oct"
self.date_objects[date_str] = date_obj  # Store for sorting
```

**Lines 535-538** - Sort dates chronologically:
```python
dates = sorted(
    self.organized_predictions.keys(),
    key=lambda d: self.date_objects.get(d, datetime.min)
)
```

**Lines 486-489** - Select first date chronologically:
```python
first_date = sorted(
    self.organized_predictions.keys(),
    key=lambda d: self.date_objects.get(d, datetime.min)
)[0]
```

---

## How Chronological Sorting Works

The key is using a lambda function with the `key` parameter in `sorted()`:

```python
sorted(date_strings, key=lambda d: self.date_objects.get(d, datetime.min))
```

This:
1. Iterates through each date string (e.g., "Mon 20 Oct")
2. Looks up the actual datetime object (e.g., datetime(2025, 10, 20))
3. Sorts based on the datetime object, not the string
4. Returns the list in chronological order

The `datetime.min` fallback handles "Unknown Date" entries by placing them first.

---

## Files Modified

**`/Datafetch/gui/predictions_view.py`**:
- **Line 113**: Added `self.date_objects = {}` dictionary
- **Line 498**: Initialize/clear date_objects in organize method
- **Lines 510-512**: Store date objects during parsing
- **Lines 535-538**: Sort dates chronologically in create_date_tabs
- **Lines 486-489**: Sort dates chronologically in on_predictions_ready
- **Line 623**: Removed `addStretch()` call

---

## Testing Results

✅ Date tabs now display in chronological order: "Sat 18 Oct", "Sun 19 Oct", "Mon 20 Oct"
✅ Clicking date tabs no longer crashes the app
✅ Course chips still wrap correctly
✅ All 154 races still generate predictions
✅ Navigation flow works smoothly: date → course → race → detail → back

---

## Before vs After

**Before:**
```
Date Tabs: [Mon 20 Oct] [Sat 18 Oct] [Sun 19 Oct]  ❌ Wrong order
Click → CRASH: AttributeError: 'FlowLayout' object has no attribute 'addStretch'  ❌
```

**After:**
```
Date Tabs: [Sat 18 Oct] [Sun 19 Oct] [Mon 20 Oct]  ✅ Correct chronological order
Click → Smoothly switches to course chips  ✅
```

---

## Success!

The Predictions view is now fully functional with:
- ✅ Proper date formatting (not "Unknown Date")
- ✅ Chronological date ordering
- ✅ Course chip wrapping (FlowLayout)
- ✅ No crashes when navigating
- ✅ All 154 races with predictions
- ✅ Complete hierarchical navigation

The UI is polished and ready for production use! 🎉

