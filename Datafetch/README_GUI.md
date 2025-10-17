# Racecard Viewer GUI

## Overview

A simple, lightweight desktop application for browsing historical racecard data using PySide6 (Qt for Python). The interface is optimized for clarity and information density, presenting data in a format similar to traditional paper racecards.

## Features

✅ **Hierarchical Navigation**: Browse by Region → Course → Date → Race  
✅ **Racecard Display**: View race details formatted like traditional racecards  
✅ **Entity Profiles**: Click any horse, trainer, jockey, or owner to view their profile  
✅ **Pedigree Information**: Complete family lineage for all horses  
✅ **Performance History**: Recent runs, rides, and statistics  
✅ **Clean Interface**: Simple, text-focused design optimized for readability  
✅ **Keyboard Shortcuts**: ESC to go back, quick navigation  

## Installation

### Prerequisites

- Python 3.9 or higher
- Virtual environment (recommended)
- The `racing_pro.db` database file (created by `fetch_racecards_pro.py`)

### Setup

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (if not already installed)
pip install PySide6>=6.7.0

# Or install from requirements.txt
pip install -r requirements.txt
```

## Usage

### Starting the Application

```bash
# From the QE2 directory
python Datafetch/racecard_gui.py

# Or make it executable and run directly
chmod +x Datafetch/racecard_gui.py
./Datafetch/racecard_gui.py
```

### Navigation Flow

1. **Select Region** (Optional)
   - Use the region filter to narrow down courses
   - "All" shows courses from all regions

2. **Select Course**
   - Click on a course from the list
   - Courses are sorted alphabetically

3. **Select Date**
   - Year dropdown populates with available years for the course
   - Month dropdown shows months with races
   - Day dropdown shows specific days with races

4. **Select Race**
   - List shows all races for the selected date and course
   - Format: "14:30 - Sprint Handicap (Class 4)"

5. **View Racecard**
   - Race details display in the main panel
   - Formatted like a traditional paper racecard

6. **Click Entity Names**
   - Click any horse, trainer, jockey name to view their profile
   - Click "Back to Racecard" or press ESC to return

### Keyboard Shortcuts

- **ESC**: Go back to previous view
- **Ctrl+Q**: Quit application (standard Qt shortcut)

## Interface Layout

```
┌─────────────────────────────────────────────────────────────┐
│                     Racecard Viewer                         │
├──────────────────┬──────────────────────────────────────────┤
│  Navigation      │  Content Area                            │
│  Panel (Left)    │  (Racecard or Profile)                   │
│                  │                                           │
│  ┌────────────┐  │  ════════════════════════════════        │
│  │ Region     │  │  MUSSELBURGH - 2023-04-30      14:30    │
│  │  All  ▼    │  │  Sprint Handicap                         │
│  └────────────┘  │  ════════════════════════════════        │
│                  │  Distance: 5f | Going: Good              │
│  ┌────────────┐  │  Class: 3 | Prize: £12,000              │
│  │ Courses    │  │  Surface: Turf | Field: 17 runners      │
│  │            │  │                                           │
│  │ Musselburgh│  │  No. Horse    Trainer      Jockey  Draw  │
│  │ Newcastle  │  │  ─────────────────────────────────────   │
│  │ ...        │  │  1   Digital   Roger Fell  Curtis   7    │
│  └────────────┘  │  2   Edward    Dalgleish   Fanning  3    │
│                  │  ...                                      │
│  ┌────────────┐  │                                           │
│  │ Date       │  │  [Clickable names show profiles]         │
│  │ 2023  ▼    │  │                                           │
│  │ April ▼    │  │                                           │
│  │ 30    ▼    │  │                                           │
│  └────────────┘  │                                           │
│                  │                                           │
│  ┌────────────┐  │                                           │
│  │ Races      │  │                                           │
│  │            │  │                                           │
│  │ 14:30 -... │  │                                           │
│  │ 15:00 -... │  │                                           │
│  └────────────┘  │                                           │
└──────────────────┴──────────────────────────────────────────┘
```

## Data Views

### 1. Racecard View

Displays race information in a traditional format:

- **Header**: Course name, date, and off time
- **Race Details**: Distance, going, class, prize, surface, field size
- **Runners Table**: 
  - Number, Horse name, Trainer, Jockey, Draw, Weight
  - All names are clickable links to profiles
- **Additional Info**: Going details, verdict (if available)

### 2. Horse Profile

Complete horse information:

- **Basic Details**: Age, sex, colour, region, breeder
- **Pedigree**: Sire (father), dam (mother), damsire (maternal grandsire)
- **Recent Runs**: Date, course, race, trainer, jockey, number
  - Shows up to 20 most recent runs in the dataset

### 3. Trainer Profile

Trainer statistics and history:

- **Basic Info**: Location, total runners in dataset
- **14-Day Statistics**: Recent performance metrics (if available)
- **Recent Runners**: Horses trained with date, course, jockey
  - Horse names are clickable
  - Shows up to 30 recent runners

### 4. Jockey Profile

Jockey riding history:

- **Basic Info**: Total rides in dataset
- **Recent Rides**: Date, course, horse, trainer, number
  - Horse names are clickable
  - Shows up to 30 recent rides

### 5. Owner Profile

Owner's horses and racing activity:

- **Basic Info**: Total horses in dataset
- **Recent Runners**: Horses owned with date, course, trainer, jockey
  - Horse names are clickable
  - Shows up to 30 recent runners

## Technical Details

### Architecture

```
Datafetch/
├── racecard_gui.py          # Main entry point
└── gui/
    ├── __init__.py          # Package initialization
    ├── database.py          # Database query helper
    ├── main_window.py       # Main window & coordination
    ├── navigation_panel.py  # Left sidebar navigation
    ├── racecard_view.py     # Racecard display widget
    └── profile_view.py      # Entity profile display
```

### Components

**DatabaseHelper** (`gui/database.py`)
- Manages SQLite database connection
- Provides query methods for all data access
- Handles data transformation for UI

**NavigationPanel** (`gui/navigation_panel.py`)
- Region filter ComboBox
- Course selection ListWidget
- Date selectors (Year/Month/Day ComboBoxes)
- Race list for selected date/course
- Emits `race_selected(race_id)` signal

**RacecardView** (`gui/racecard_view.py`)
- Displays race header and details
- Renders runners in formatted table
- Makes entity names clickable
- Emits `entity_clicked(type, id, name)` signal

**ProfileView** (`gui/profile_view.py`)
- Dynamic profile rendering based on entity type
- Displays related records (runs, rides, horses)
- Back button to return to racecard
- Emits `back_clicked()` and `entity_clicked()` signals

**MainWindow** (`gui/main_window.py`)
- Coordinates all components
- Manages view switching (racecard ↔ profile)
- Handles navigation history
- Connects signals between components

### Styling Philosophy

**Simple & Clear Over Beautiful**

- System default fonts (monospace for tables)
- Minimal colors (black text, white background, blue links)
- Clear section separators (═══ lines)
- Adequate spacing and padding
- Simple grid tables with alternating row colors
- No images or fancy graphics
- Optimized for information density

### Performance

- **Startup Time**: < 1 second
- **Race Loading**: Instant (single DB query)
- **Profile Loading**: < 0.1 seconds
- **Memory Usage**: ~50-80 MB
- **Database**: Read-only, no modifications

## Troubleshooting

### Application Won't Start

**Error**: `Database not found`
```
Solution: Ensure racing_pro.db exists in Datafetch/ directory
Run: python Datafetch/fetch_racecards_pro.py
```

**Error**: `No module named 'PySide6'`
```
Solution: Install PySide6
Run: pip install PySide6
```

### UI Issues

**Blank content area**
- Ensure you've selected a course and date
- Check that the selected date has races

**Clickable names don't work**
- This is expected if the entity has no ID
- Some older records may have missing data

**Tables cut off**
- Resize window wider
- Tables should scroll horizontally if needed

### Performance Issues

**Slow loading**
- Check database file isn't corrupted
- Ensure database has proper indexes
- Restart application

## Dataset Information

**Date Range**: January 23 - April 30, 2023 (98 days)  
**Total Races**: 3,848  
**Total Runners**: 40,291  
**Unique Horses**: 17,625  
**Unique Trainers**: 1,843  
**Unique Jockeys**: 1,497  
**Unique Owners**: 11,244  

## Future Enhancements

Potential improvements for consideration:

- [ ] Search functionality (search by horse/trainer/jockey name)
- [ ] Bookmarks/favorites for quick access
- [ ] Export racecard to PDF
- [ ] Compare horses side-by-side
- [ ] Statistics and analytics view
- [ ] Dark mode theme
- [ ] Configurable column display
- [ ] Advanced filtering options
- [ ] Print racecard function

## Development

### Running in Development Mode

```bash
cd Datafetch
python racecard_gui.py
```

### Code Structure

Each GUI component is self-contained with:
- Clear separation of concerns
- Signal/slot architecture for communication
- Minimal dependencies between components
- Documented public methods

### Adding New Features

1. **New View**: Create widget in `gui/` directory
2. **New Data Query**: Add method to `DatabaseHelper`
3. **Navigation**: Update `NavigationPanel` or `MainWindow`
4. **Styling**: Keep consistent with existing simple style

## License & Credits

Part of the QE2 Racing Data Project  
Uses The Racing API for data  
Built with PySide6 (Qt for Python)

---

**Version**: 1.0.0  
**Last Updated**: October 18, 2025  
**Python**: 3.9+  
**Qt Framework**: PySide6 6.10+

