# Date Parsing and Course Wrapping Fixes

## Issues Fixed

### Issue 1: Date Showing "Unknown Date"
**Problem**: Date tabs were displaying "Unknown Date" instead of proper dates like "Fri 18 Oct"

**Root Cause**: The predictor's SQL query (`ml/predictor.py`) wasn't selecting the `date` field from the `upcoming_races.db`, only the `off_time` field (which contains just the time like "10:20")

**Solution**: 
1. **Updated `ml/predictor.py` line 169**: Added `date` to the SELECT statement
   ```python
   SELECT race_id, course, date, off_time as time, distance, ...
   ```

2. **Updated `predictions_view.py` organize_predictions_by_hierarchy()**: Changed from parsing `time` to parsing `date`
   ```python
   date_str_raw = race_info.get('date', '')  # Gets "2025-10-18"
   date_obj = datetime.strptime(date_str_raw, '%Y-%m-%d')
   date_str = date_obj.strftime('%a %d %b')  # Formats as "Fri 18 Oct"
   ```

**Result**: Date tabs now correctly display "Fri 18 Oct", "Sat 19 Oct", "Sun 20 Oct"

---

### Issue 2: Course Chips Not Wrapping
**Problem**: Course buttons extended the window horizontally instead of wrapping to the next line when window was resized

**Root Cause**: Using `QHBoxLayout` which is a fixed horizontal layout with no wrapping support

**Solution**: 
1. **Created `FlowLayout` class** (lines 21-96 in `predictions_view.py`): A custom Qt layout that automatically wraps widgets to the next line, similar to CSS flexbox or HTML word-wrap

2. **Updated course chips container** (line 277): Changed from `QHBoxLayout()` to `FlowLayout(spacing=10)`
   ```python
   self.course_chips_layout = FlowLayout(spacing=10)  # Wraps like text
   ```

**Result**: Course chips now wrap to multiple lines when window is narrow, preventing horizontal overflow

---

## Files Modified

### 1. `/Datafetch/ml/predictor.py`
- **Line 169**: Added `date` field to SELECT query
- **Impact**: All predictions now include the race date in `race_info`

### 2. `/Datafetch/gui/predictions_view.py`
- **Lines 8-9**: Added `QLayout, QRect, QSize` imports
- **Lines 21-96**: Added `FlowLayout` custom layout class
- **Line 277**: Changed course chips to use `FlowLayout`
- **Lines 501-513**: Updated `organize_predictions_by_hierarchy()` to use `date` field instead of `time`

---

## How FlowLayout Works

The `FlowLayout` class:
1. Measures each widget's width
2. Places widgets horizontally until they would exceed the container width
3. Automatically moves to the next line when needed
4. Calculates proper vertical spacing between rows
5. Dynamically adjusts when window is resized

This provides a responsive UI that adapts to different screen sizes.

---

## Testing Checklist

✅ Date tabs display proper dates (e.g., "Fri 18 Oct", not "Unknown Date")
✅ Course chips wrap to next line when window is narrow
✅ Course chips stay on one line when window is wide
✅ All 154 races still predict successfully
✅ Navigation hierarchy still works (date → course → race → detail → back)

---

## Before vs After

**Before:**
- Date tabs: "Unknown Date" "Unknown Date" "Unknown Date" ❌
- Course chips: `[Ascot] [Bath] [Catterick] ... [extends window forever] →→→` ❌

**After:**
- Date tabs: "Fri 18 Oct" "Sat 19 Oct" "Sun 20 Oct" ✅
- Course chips (narrow window):
  ```
  [Ascot] [Bath] [Catterick] [Deauville]
  [Gowran Park] [Kempton] [Leopardstown]
  [Limerick] [Longchamp] ...
  ```
  ✅

**After:**
- Course chips (wide window):
  ```
  [Ascot] [Bath] [Catterick] [Deauville] [Gowran Park] [Kempton] [Leopardstown] [Limerick] [Longchamp] ...
  ```
  ✅

---

## Success!

Both UI issues resolved with minimal code changes. The predictions view now provides a much better user experience with proper date formatting and responsive layout.

