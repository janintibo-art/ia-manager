"""Thème visuel de l'application (sombre, gros caractères)"""

BASE_FONT_PT = 13

ACCENT = "#7c6cff"
ACCENT_HOVER = "#9486ff"
BG = "#16171d"
SURFACE = "#1f2029"
SURFACE_2 = "#292a36"
BORDER = "#363848"
TEXT = "#ececf1"
TEXT_MUTED = "#a3a5b8"
GREEN = "#3ecf8e"
ORANGE = "#f5a524"
RED = "#f25f5c"

STYLESHEET = f"""
QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: "Segoe UI", "Arial";
    font-size: {BASE_FONT_PT}pt;
}}

QLabel#Title {{
    font-size: {BASE_FONT_PT + 7}pt;
    font-weight: 600;
    padding: 4px 0 2px 0;
}}
QLabel#Subtitle {{
    color: {TEXT_MUTED};
    padding-bottom: 6px;
}}
QLabel#Muted {{
    color: {TEXT_MUTED};
}}
QLabel#Status {{
    color: {TEXT_MUTED};
    padding: 4px;
}}

QFrame#Card {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QFrame#Card QLabel {{
    background: transparent;
}}
QLabel#CardTitle {{
    font-size: {BASE_FONT_PT + 2}pt;
    font-weight: 600;
}}
QLabel#BigValue {{
    font-size: {BASE_FONT_PT + 4}pt;
    font-weight: 600;
    color: {ACCENT_HOVER};
}}

QTabWidget::pane {{
    border: none;
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_MUTED};
    padding: 11px 16px;
    margin-right: 2px;
    border-bottom: 3px solid transparent;
    font-size: {BASE_FONT_PT + 1}pt;
}}
QTabBar::tab:selected {{
    color: {TEXT};
    border-bottom: 3px solid {ACCENT};
}}
QTabBar::tab:hover {{
    color: {TEXT};
}}

QPushButton {{
    background-color: {SURFACE_2};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 9px 18px;
}}
QPushButton:hover {{
    border-color: {ACCENT};
}}
QPushButton:disabled {{
    color: {TEXT_MUTED};
    background-color: {SURFACE};
}}
QPushButton#Primary {{
    background-color: {ACCENT};
    border: none;
    color: white;
    font-weight: 600;
}}
QPushButton#Primary:hover {{
    background-color: {ACCENT_HOVER};
}}
QPushButton#Primary:disabled {{
    background-color: {SURFACE_2};
    color: {TEXT_MUTED};
}}
QPushButton#Danger {{
    background-color: transparent;
    border: 1px solid {RED};
    color: {RED};
}}
QPushButton#Chip {{
    border-radius: 16px;
    padding: 7px 16px;
}}
QPushButton#Chip:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
    color: white;
}}

QListWidget, QTextEdit, QTextBrowser, QComboBox, QTableWidget, QLineEdit, QPlainTextEdit {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 6px;
}}
QListWidget::item {{
    padding: 12px 10px;
    border-radius: 8px;
    margin: 2px 0;
}}
QListWidget::item:selected {{
    background-color: {SURFACE_2};
    border: 1px solid {ACCENT};
    color: {TEXT};
}}
QListWidget::item:hover {{
    background-color: {SURFACE_2};
}}

QComboBox, QLineEdit {{
    padding: 8px 12px;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {ACCENT};
}}
QPlainTextEdit#Console {{
    background-color: #0d0e12;
    font-family: "Consolas", "Courier New", monospace;
    font-size: {BASE_FONT_PT - 1}pt;
}}
QLabel#Command {{
    background-color: #0d0e12;
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 10px 12px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: {BASE_FONT_PT - 1}pt;
}}
QCheckBox {{
    spacing: 8px;
    background: transparent;
}}
QTabWidget#SubTabs QTabBar::tab {{
    padding: 8px 18px;
    font-size: {BASE_FONT_PT}pt;
}}
QComboBox QAbstractItemView {{
    background-color: {SURFACE};
    selection-background-color: {ACCENT};
}}

QTableWidget {{
    gridline-color: {BORDER};
}}
QHeaderView::section {{
    background-color: {SURFACE_2};
    color: {TEXT_MUTED};
    border: none;
    padding: 8px;
    font-weight: 600;
}}
QTableWidget::item {{
    padding: 6px;
}}

QRadioButton {{
    spacing: 8px;
    padding: 4px 10px 4px 0;
    background: transparent;
}}

QSlider::groove:horizontal {{
    height: 8px;
    background: {SURFACE_2};
    border-radius: 4px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 4px;
}}
QSlider::handle:horizontal {{
    background: white;
    width: 20px;
    margin: -7px 0;
    border-radius: 10px;
}}

QProgressBar {{
    background-color: {SURFACE_2};
    border: none;
    border-radius: 5px;
    height: 10px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 5px;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 12px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 6px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QSplitter::handle {{
    background: transparent;
    width: 10px;
}}

QToolTip {{
    background-color: {SURFACE_2};
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 6px;
}}
"""
