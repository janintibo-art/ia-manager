"""v155 : catalogue gratuit/local dans une fenêtre dédiée."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog,QDialogButtonBox,QHeaderView,QLabel,QTableWidget,QTableWidgetItem,QVBoxLayout
from src.ui.v153_extension import FREE_CATALOG

def _show_catalog(parent):
    d=QDialog(parent); d.setWindowTitle("ComfyUI — gratuit / local / API"); d.resize(980,620)
    lay=QVBoxLayout(d)
    info=QLabel("✅ LOCAL = pas de crédits par génération dans IA Manager. 💳 API = service partenaire pouvant être facturé.")
    info.setWordWrap(True); lay.addWidget(info)
    t=QTableWidget(len(FREE_CATALOG),4,d); t.setHorizontalHeaderLabels(["Type","Outil / famille","Coût d'usage","Remarque"])
    t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers); t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    t.setAlternatingRowColors(True); t.verticalHeader().hide(); t.setWordWrap(True)
    for r,row in enumerate(FREE_CATALOG):
        for c,val in enumerate(row):
            it=QTableWidgetItem(val); it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable); t.setItem(r,c,it)
    h=t.horizontalHeader()
    h.setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents); h.setSectionResizeMode(1,QHeaderView.ResizeMode.ResizeToContents)
    h.setSectionResizeMode(2,QHeaderView.ResizeMode.ResizeToContents); h.setSectionResizeMode(3,QHeaderView.ResizeMode.Stretch)
    t.resizeRowsToContents()
    for r in range(t.rowCount()): t.setRowHeight(r,max(40,t.rowHeight(r)))
    lay.addWidget(t,1)
    note=QLabel("Pour rester 100 % local, privilégiez les lignes ✅ LOCAL et laissez les nœuds API partenaires désactivés.")
    note.setWordWrap(True); lay.addWidget(note)
    buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Close); buttons.rejected.connect(d.reject); buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(d.accept)
    lay.addWidget(buttons); d.exec()

def install_v155(window):
    if getattr(window,"_v155_free_catalog_dialog",False): return
    tab=getattr(window,"creative_tools_tab",None)
    if tab is None or not hasattr(tab,"v153_free"): return
    old=getattr(tab,"v153_free_table",None)
    if old is not None: old.setVisible(False); old.setMaximumHeight(0)
    try: tab.v153_free.clicked.disconnect()
    except Exception: pass
    tab.v153_free.clicked.connect(lambda:_show_catalog(tab))
    tab.v153_free.setText("💚 Voir ce qui est gratuit / local")
    window._v155_free_catalog_dialog=True
