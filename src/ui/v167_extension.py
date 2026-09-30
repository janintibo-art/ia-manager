"""v167 : correction double titre + scroll global Entraîner/Fusionner."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QPlainTextEdit, QScrollArea, QSizePolicy, QTabWidget,
    QVBoxLayout, QWidget,
)


def _remove_duplicate_global_header(window):
    """Chaque page possède déjà son propre titre : masquer le gros bandeau StudioShell."""
    shell = getattr(window, "studio_shell", None)
    if shell is None or getattr(shell, "_v167_header_compacted", False):
        return

    try:
        header = shell.title.parentWidget()
        if header is not None:
            header.setVisible(False)
            header.setMinimumHeight(0)
            header.setMaximumHeight(0)
            header.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    except Exception:
        pass

    # Les labels restent alimentés pour la logique interne, mais ne prennent plus de place.
    for attr in ("section", "title", "subtitle"):
        widget = getattr(shell, attr, None)
        if widget is not None:
            widget.setVisible(False)

    shell._v167_header_compacted = True


def _transfer_item(item, target_layout):
    widget = item.widget()
    layout = item.layout()
    spacer = item.spacerItem()
    if widget is not None:
        target_layout.addWidget(widget)
    elif layout is not None:
        target_layout.addLayout(layout)
    elif spacer is not None:
        target_layout.addItem(spacer)


def _make_training_globally_scrollable(window):
    tab = getattr(window, "training_tab", None)
    if tab is None or getattr(tab, "_v167_global_scroll", False):
        return

    old = tab.layout()
    if old is None:
        return

    # Si une future version a déjà ajouté un scroll global, ne pas l'imbriquer à nouveau.
    for i in range(old.count()):
        widget = old.itemAt(i).widget()
        if isinstance(widget, QScrollArea) and getattr(widget, "_v167_training_outer", False):
            tab._v167_global_scroll = True
            return

    items = []
    while old.count():
        items.append(old.takeAt(0))

    host = QWidget()
    host.setObjectName("TrainingScrollableHost")
    host.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
    lay = QVBoxLayout(host)
    lay.setContentsMargins(8, 8, 8, 18)
    lay.setSpacing(10)

    for item in items:
        _transfer_item(item, lay)

    # Important : le QTabWidget garde une hauteur raisonnable mais n'écrase plus
    # le bas de la page. Les pages internes ont déjà leur propre scroll.
    pages = getattr(tab, "pages", None)
    if isinstance(pages, QTabWidget):
        pages.setMinimumHeight(430)
        pages.setMaximumHeight(720)
        pages.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    # Consoles techniques : visibles mais bornées pour ne plus manger tout l'écran.
    for log in tab.findChildren(QPlainTextEdit):
        if log.isReadOnly():
            log.setMinimumHeight(110)
            log.setMaximumHeight(210)

    scroll = QScrollArea()
    scroll._v167_training_outer = True
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setWidget(host)

    old.setContentsMargins(0, 0, 0, 0)
    old.setSpacing(0)
    old.addWidget(scroll)

    tab.v167_outer_scroll = scroll
    tab._v167_global_scroll = True


def _ensure_nested_pages_scroll(window):
    """Les sous-pages Entraînement/Fusion/Ollama restent elles aussi accessibles."""
    tab = getattr(window, "training_tab", None)
    if tab is None:
        return
    pages = getattr(tab, "pages", None)
    if not isinstance(pages, QTabWidget):
        return

    for i in range(pages.count()):
        page = pages.widget(i)
        if isinstance(page, QScrollArea):
            page.setWidgetResizable(True)
            page.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            page.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            inner = page.widget()
            if inner is not None:
                inner.setMinimumWidth(0)
                inner.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)


def install_v167(window):
    if getattr(window, "_v167_visible_fixes", False):
        return

    _remove_duplicate_global_header(window)
    _make_training_globally_scrollable(window)
    _ensure_nested_pages_scroll(window)

    window._v167_visible_fixes = True
