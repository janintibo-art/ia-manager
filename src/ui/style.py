"""Thème visuel de l'application : sombre ou clair, taille de police réglable.

Les couleurs sont des variables du module : apply_theme() les change, et tout ce qui
est affiché ensuite (feuille de style, bulles du Chat…) utilise les nouvelles valeurs.
"""

BASE_FONT_PT = 13

THEMES = {
    "sombre": {
        "ACCENT": "#7c6cff", "ACCENT_HOVER": "#9486ff", "BG": "#16171d", "SURFACE": "#1f2029",
        "SURFACE_2": "#292a36", "BORDER": "#363848", "TEXT": "#ececf1", "TEXT_MUTED": "#a3a5b8",
        "GREEN": "#3ecf8e", "ORANGE": "#f5a524", "RED": "#f25f5c", "CODE_BG": "#0d0e12",
        "CODE_FG": "#e6e6f0", "INLINE_CODE_BG": "#2b2d3a",
    },
    "clair": {
        "ACCENT": "#6a5cf0", "ACCENT_HOVER": "#5646e0", "BG": "#f4f5f9", "SURFACE": "#ffffff",
        "SURFACE_2": "#eceef5", "BORDER": "#d4d7e3", "TEXT": "#1d1f2b", "TEXT_MUTED": "#5d6275",
        "GREEN": "#16875a", "ORANGE": "#b36b00", "RED": "#cc3b3b", "CODE_BG": "#f0f1f6",
        "CODE_FG": "#1d1f2b", "INLINE_CODE_BG": "#e4e6f0",
    },
}

CURRENT_THEME = "sombre"
ACCENT = ACCENT_HOVER = BG = SURFACE = SURFACE_2 = BORDER = TEXT = TEXT_MUTED = ""
GREEN = ORANGE = RED = CODE_BG = CODE_FG = INLINE_CODE_BG = ""


def apply_theme(name: str = "sombre", font_pt: int = 13) -> None:
    """Change les couleurs et la taille de police (à suivre de app.setStyleSheet(build_stylesheet()))"""
    global CURRENT_THEME, BASE_FONT_PT
    CURRENT_THEME = name if name in THEMES else "sombre"
    BASE_FONT_PT = max(10, min(20, int(font_pt)))
    globals().update(THEMES[CURRENT_THEME])


def code_colors() -> dict:
    """Couleurs utilisées pour afficher le code dans le Chat"""
    return {"code_bg": INLINE_CODE_BG, "code_fg": CODE_FG, "block_bg": CODE_BG, "muted": TEXT_MUTED}


def build_stylesheet() -> str:
    return f"""
QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: "Segoe UI", "Arial";
    font-size: {BASE_FONT_PT}pt;
}}

QMainWindow {{
    background-color: {BG};
}}
QFrame#Hero {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 {SURFACE}, stop:0.55 {SURFACE_2}, stop:1 {BG});
    border: 1px solid {BORDER};
    border-radius: 16px;
    padding: 4px;
}}
QLabel#Brand {{
    background: transparent;
    color: {TEXT};
    font-size: {BASE_FONT_PT + 9}pt;
    font-weight: 700;
}}
QLabel#BrandAccent {{
    background: transparent;
    color: {ACCENT_HOVER};
    font-size: {BASE_FONT_PT + 9}pt;
    font-weight: 700;
}}
QLabel#Pill {{
    background-color: {SURFACE_2};
    color: {TEXT_MUTED};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 5px 10px;
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
    background-color: {SURFACE_2};
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
    background-color: {CODE_BG};
    font-family: "Consolas", "Courier New", monospace;
    font-size: {BASE_FONT_PT - 1}pt;
}}
QLabel#Command {{
    background-color: {CODE_BG};
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

QGroupBox {{
    background: transparent;
    border: 1px solid {BORDER};
    border-radius: 10px;
    margin-top: 12px;
    padding: 12px 8px 8px 8px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {TEXT_MUTED};
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

/* Atelier v53 : surfaces, navigation et retours d'interaction. */
QFrame#NavigationRail {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 16px;
}}
QFrame#NavigationRail QLabel, QFrame#NavigationRail QWidget {{
    background: transparent;
}}
QFrame#NavigationRail QLabel#Brand {{ font-size: {BASE_FONT_PT + 5}pt; }}
QLabel#NavigationCaption {{
    color: {TEXT_MUTED};
    font-size: {max(9, BASE_FONT_PT - 3)}pt;
    font-weight: 600;
    background: transparent;
}}
QListWidget#StudioNavigation {{
    background: transparent;
    border: none;
    padding: 0;
    min-width: {BASE_FONT_PT * 17}px;
    max-width: {BASE_FONT_PT * 17}px;
    outline: none;
}}
QListWidget#StudioNavigation::item {{
    padding: 8px 12px;
    margin: 2px 0;
    border: 1px solid transparent;
    border-radius: 8px;
}}
QListWidget#StudioNavigation::item:disabled {{
    color: {TEXT_MUTED};
    background: transparent;
    border: none;
    padding: 14px 12px 4px 12px;
}}
QListWidget#StudioNavigation::item:selected {{
    background: {SURFACE_2};
    color: {TEXT};
    border: 1px solid {ACCENT};
    border-left: 4px solid {ACCENT};
}}
QListWidget#StudioNavigation::item:hover:enabled {{ background: {SURFACE_2}; }}
QFrame#StudioHeader {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 {SURFACE_2}, stop:1 {SURFACE});
    border: 1px solid {BORDER};
    border-radius: 14px;
}}
QFrame#StudioHeader QLabel {{ background: transparent; }}
QPushButton:pressed {{ background: {BORDER}; }}
QPushButton:focus, QComboBox:focus, QListWidget:focus {{ border: 1px solid {ACCENT}; }}
QPushButton#Primary:pressed {{ background: {ACCENT_HOVER}; }}
QTextEdit, QPlainTextEdit, QLineEdit {{
    selection-background-color: {ACCENT};
    selection-color: white;
}}
QScrollBar:horizontal {{ background: transparent; height: 12px; }}
QScrollBar::handle:horizontal {{ background: {BORDER}; border-radius: 6px; min-width: 30px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{ background: {TEXT_MUTED}; }}
QMenu {{ background: {SURFACE}; border: 1px solid {BORDER}; padding: 6px; }}
QMenu::item {{ padding: 8px 20px; border-radius: 6px; }}
QMenu::item:selected {{ background: {SURFACE_2}; color: {TEXT}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 5px; }}

QToolTip {{
    background-color: {SURFACE_2};
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 6px;
}}
"""


apply_theme("sombre", 13)
STYLESHEET = build_stylesheet()
