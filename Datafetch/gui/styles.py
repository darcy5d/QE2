"""
Unified Style Guide - Claude/CLI Inspired Dark Theme
All views should use these consistent styles for a professional, cohesive look
"""

# ============================================================================
# COLOR PALETTE
# ============================================================================

COLORS = {
    # Backgrounds
    'bg_primary': '#1E1E1E',      # Main background (almost black)
    'bg_secondary': '#2A2A2A',    # Panels, cards
    'bg_tertiary': '#333333',     # Elevated elements
    'bg_hover': '#3A3A3A',        # Hover states
    'bg_selected': '#2C4A6E',     # Selected items
    
    # Text
    'text_primary': '#FFFFFF',    # Main text (white)
    'text_secondary': '#CCCCCC',  # Secondary text (light gray)
    'text_muted': '#888888',      # Muted text (gray)
    'text_disabled': '#666666',   # Disabled text
    
    # Accents
    'accent_blue': '#4A90E2',     # Primary actions, links
    'accent_blue_hover': '#357ABD',  # Blue hover state
    'accent_blue_pressed': '#2868A8',  # Blue pressed state
    'accent_green': '#5CB85C',    # Success, positive
    'accent_green_hover': '#4A9D4A',  # Green hover state
    'accent_red': '#E74C3C',      # Errors, warnings
    'accent_yellow': '#F39C12',   # Warnings, highlights
    
    # Borders
    'border_light': '#444444',
    'border_medium': '#555555',
    'border_heavy': '#666666',
}

# ============================================================================
# TYPOGRAPHY
# ============================================================================

FONTS = {
    'base_size': 11,              # Base font size
    'heading_1': 18,              # Main titles
    'heading_2': 16,              # Section headers
    'heading_3': 14,              # Subsection headers
    'body': 12,                   # Body text
    'small': 10,                  # Small text
    'tiny': 9,                    # Tiny text
    'family': 'system-ui, -apple-system, sans-serif',
}

# ============================================================================
# COMPONENT STYLES
# ============================================================================

# Buttons
BUTTON_PRIMARY = f"""
    QPushButton {{
        background-color: {COLORS['accent_blue']};
        color: {COLORS['text_primary']};
        border: none;
        border-radius: 4px;
        padding: 10px 20px;
        font-size: {FONTS['body']}px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: {COLORS['accent_blue_hover']};
    }}
    QPushButton:pressed {{
        background-color: {COLORS['accent_blue_pressed']};
    }}
    QPushButton:disabled {{
        background-color: {COLORS['border_medium']};
        color: {COLORS['text_muted']};
    }}
"""

BUTTON_SUCCESS = f"""
    QPushButton {{
        background-color: {COLORS['accent_green']};
        color: {COLORS['text_primary']};
        border: none;
        border-radius: 4px;
        padding: 10px 20px;
        font-size: {FONTS['body']}px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: {COLORS['accent_green_hover']};
    }}
    QPushButton:pressed {{
        background-color: #3E8A3E;
    }}
    QPushButton:disabled {{
        background-color: {COLORS['border_medium']};
        color: {COLORS['text_muted']};
    }}
"""

BUTTON_SMALL = f"""
    QPushButton {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border_medium']};
        border-radius: 3px;
        padding: 5px 10px;
        font-size: {FONTS['small']}px;
    }}
    QPushButton:hover {{
        background-color: {COLORS['bg_hover']};
        border-color: {COLORS['accent_blue']};
    }}
"""

# Tables
TABLE_STYLE = f"""
    QTableWidget {{
        background-color: {COLORS['bg_primary']};
        color: {COLORS['text_primary']};
        gridline-color: {COLORS['border_light']};
        border: none;
        font-size: {FONTS['body']}px;
    }}
    QTableWidget::item {{
        padding: 8px;
        color: {COLORS['text_primary']};
    }}
    QTableWidget::item:selected {{
        background-color: {COLORS['accent_blue']};
        color: {COLORS['text_primary']};
    }}
    QTableWidget::item:hover {{
        background-color: {COLORS['bg_hover']};
    }}
    QHeaderView::section {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_primary']};
        padding: 8px;
        border: none;
        font-weight: bold;
        font-size: {FONTS['body']}px;
    }}
"""

# Scroll Areas
SCROLL_AREA_STYLE = f"""
    QScrollArea {{
        background-color: {COLORS['bg_primary']};
        border: none;
    }}
    QScrollBar:vertical {{
        background-color: {COLORS['bg_secondary']};
        width: 12px;
        border-radius: 6px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {COLORS['border_heavy']};
        border-radius: 6px;
        min-height: 20px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {COLORS['text_muted']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        background-color: {COLORS['bg_secondary']};
        height: 12px;
        border-radius: 6px;
    }}
    QScrollBar::handle:horizontal {{
        background-color: {COLORS['border_heavy']};
        border-radius: 6px;
        min-width: 20px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background-color: {COLORS['text_muted']};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
"""

# Labels
LABEL_HEADING_1 = f"""
    font-size: {FONTS['heading_1']}px;
    font-weight: bold;
    color: {COLORS['text_primary']};
    padding: 10px;
"""

LABEL_HEADING_2 = f"""
    font-size: {FONTS['heading_2']}px;
    font-weight: bold;
    color: {COLORS['accent_blue']};
    padding: 8px;
"""

LABEL_HEADING_3 = f"""
    font-size: {FONTS['heading_3']}px;
    font-weight: bold;
    color: {COLORS['text_primary']};
    padding: 5px;
"""

LABEL_BODY = f"""
    font-size: {FONTS['body']}px;
    color: {COLORS['text_primary']};
"""

LABEL_MUTED = f"""
    font-size: {FONTS['body']}px;
    color: {COLORS['text_muted']};
"""

# Frames and Panels
FRAME_PANEL = f"""
    QFrame {{
        background-color: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border_medium']};
        border-radius: 4px;
        padding: 10px;
    }}
"""

FRAME_CARD = f"""
    QFrame {{
        background-color: {COLORS['bg_tertiary']};
        border: 1px solid {COLORS['border_light']};
        border-radius: 4px;
        padding: 15px;
    }}
"""

# Group Boxes
GROUPBOX_STYLE = f"""
    QGroupBox {{
        color: {COLORS['text_primary']};
        font-weight: bold;
        font-size: {FONTS['heading_3']}px;
        border: 1px solid {COLORS['border_medium']};
        border-radius: 4px;
        margin-top: 10px;
        padding-top: 15px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
    }}
"""

# List Widgets
LIST_STYLE = f"""
    QListWidget {{
        background-color: {COLORS['bg_primary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border_medium']};
        border-radius: 4px;
        font-size: {FONTS['body']}px;
    }}
    QListWidget::item {{
        padding: 8px;
        border-bottom: 1px solid {COLORS['border_light']};
    }}
    QListWidget::item:selected {{
        background-color: {COLORS['accent_blue']};
        color: {COLORS['text_primary']};
    }}
    QListWidget::item:hover {{
        background-color: {COLORS['bg_hover']};
    }}
"""

# Combo Boxes
COMBOBOX_STYLE = f"""
    QComboBox {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border_medium']};
        border-radius: 4px;
        padding: 5px 10px;
        font-size: {FONTS['body']}px;
    }}
    QComboBox:hover {{
        border-color: {COLORS['accent_blue']};
    }}
    QComboBox::drop-down {{
        border: none;
    }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid {COLORS['text_primary']};
        margin-right: 5px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_primary']};
        selection-background-color: {COLORS['accent_blue']};
        border: 1px solid {COLORS['border_medium']};
    }}
"""

# Progress Bars
PROGRESSBAR_STYLE = f"""
    QProgressBar {{
        background-color: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border_medium']};
        border-radius: 4px;
        text-align: center;
        color: {COLORS['text_primary']};
        font-size: {FONTS['body']}px;
    }}
    QProgressBar::chunk {{
        background-color: {COLORS['accent_blue']};
        border-radius: 3px;
    }}
"""

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def apply_dark_theme(widget):
    """Apply consistent dark theme to any widget"""
    widget.setStyleSheet(f"""
        QWidget {{
            background-color: {COLORS['bg_primary']};
            color: {COLORS['text_primary']};
            font-size: {FONTS['body']}px;
        }}
    """)

def get_clickable_label_style():
    """Style for clickable entity labels (horses, trainers, etc.)"""
    return f"""
        color: {COLORS['accent_blue']};
        text-decoration: underline;
        font-size: {FONTS['body']}px;
    """

def get_clickable_label_hover_style():
    """Hover style for clickable labels"""
    return f"""
        color: {COLORS['accent_blue_hover']};
        text-decoration: underline;
        font-size: {FONTS['body']}px;
    """

