"""État mémoire et commandes explicites de déchargement Ollama."""
from PyQt6.QtWidgets import QWidget,QVBoxLayout,QLabel,QCheckBox,QPushButton,QListWidget,QListWidgetItem,QMessageBox
from PyQt6.QtCore import Qt,QTimer
from src.backend import settings,local_jobs,dashboard
from src.backend.ai_manager import AIManager
from src.ui.workers import FunctionWorker


class ResourcesTab(QWidget):
    def __init__(self):
        super().__init__()
        self.worker=None
        self.ai=AIManager()
        lay=QVBoxLayout(self)
        self.serial=QCheckBox("Exécuter les générations locales une par une")
        self.serial.setChecked(local_jobs.enabled())
        self.serial.toggled.connect(lambda value:settings.set('serialize_local_jobs',value))
        lay.addWidget(self.serial)
        note=QLabel("La file couvre le chat, le comparateur et les tâches de cette application. "
                    "L’atelier Obliteratus réserve le créneau jusqu’à son arrêt. "
                    "Les tests de vitesse, applications externes et serveurs distants ne sont pas pilotés par cette file.")
        note.setWordWrap(True);lay.addWidget(note)
        self.queue=QLabel();self.queue.setWordWrap(True);lay.addWidget(self.queue)
        self.memory=QLabel("Actualisez pour lire la mémoire disponible.")
        self.memory.setWordWrap(True);lay.addWidget(self.memory)
        self.models=QListWidget();lay.addWidget(self.models)
        self.refresh_btn=QPushButton("Actualiser RAM / VRAM et modèles chargés")
        self.refresh_btn.clicked.connect(self.refresh);lay.addWidget(self.refresh_btn)
        self.unload_btn=QPushButton("Décharger le modèle Ollama sélectionné")
        self.unload_btn.clicked.connect(self.unload);lay.addWidget(self.unload_btn)
        self.timer=QTimer(self);self.timer.timeout.connect(self.update_queue);self.timer.start(1000)
        self.update_queue()

    def update_queue(self):
        state=local_jobs.state()
        self.queue.setText("Actif : " +(state['active'] or 'aucun') + "\nEn attente : " + (", ".join(state['waiting']) or 'aucun'))
        self.unload_btn.setEnabled(self.worker is None and not state['active'] and not state['waiting'])

    def refresh(self):
        if self.worker:return
        self.refresh_btn.setEnabled(False)
        self.worker=FunctionWorker(dashboard.snapshot,self.ai)
        self.worker.done.connect(self.on_snapshot)
        self.worker.start()

    def on_snapshot(self,ok,result):
        self.worker=None;self.refresh_btn.setEnabled(True)
        if not ok:
            self.memory.setText(str(result));return
        gpu=result['gpu']
        self.memory.setText(f"RAM : {result['ram_used_gb']:.1f}/{result['ram_total_gb']:.1f} Go · "
                            f"VRAM : {gpu['used_gb']:.1f}/{gpu['total_gb']:.1f} Go" +
                            ("" if gpu.get('exact') else " (mesure GPU indisponible ou estimée)"))
        self.models.clear()
        for m in result['running']:
            name=m.get('name') or m.get('model','')
            item=QListWidgetItem(name);item.setData(Qt.ItemDataRole.UserRole,name);self.models.addItem(item)
        self.update_queue()

    def unload(self):
        item=self.models.currentItem()
        if not item or self.worker:return
        name=item.data(Qt.ItemDataRole.UserRole)
        if QMessageBox.question(self,"Libérer la mémoire",f"Décharger {name} ? Une autre application pourrait l’utiliser.",
                                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        token=local_jobs.reserve("Déchargement Ollama")
        if token is None:
            self.memory.setText("Un travail local a démarré. Attendez sa fin.");return
        def action():
            try:return self.ai.unload_model(name)
            finally:local_jobs.release(token)
        self.worker=FunctionWorker(action)
        self.worker.done.connect(self.on_unloaded);self.worker.start();self.update_queue()

    def on_unloaded(self,ok,result):
        self.worker=None
        self.memory.setText("Modèle déchargé." if ok and result else "Impossible de décharger le modèle.")
        self.refresh()
