"""Pilotage de tâches ML dans un interpréteur externe, interface non bloquante."""
import codecs
import json
import os
from pathlib import Path
import shutil

from PyQt6.QtCore import QProcess, QProcessEnvironment, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QSpinBox, QDoubleSpinBox,
    QPlainTextEdit, QMessageBox, QTabWidget, QComboBox, QScrollArea)
from src.backend import training_lab as lab, training_resources as resources, training_workspace as workspace, settings, local_jobs

from src.ui.tabs.training_workspace_tab import ExamplesEditor, TrainingHistory


class TrainingTab(QWidget):
    models_changed = pyqtSignal()
    analyze_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.system_info = None
        self.model_edited = False
        self.process = None
        self.token = None
        self.job = None
        self.logfile = None
        self.cancelled = False
        self.importing = False
        self.decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
        layout = QVBoxLayout(self)
        intro = QLabel('Entraîner une spécialité, fusionner deux variantes compatibles, puis tester dans Ollama. '
                       'Les modèles originaux restent intacts. Fermez les modèles Ollama chargés avant un entraînement.')
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.hardware_label = QLabel('Matériel : en attente de l’analyse du PC.')
        self.hardware_label.setWordWrap(True)
        layout.addWidget(self.hardware_label)
        hardware_buttons = QHBoxLayout()
        refresh = QPushButton('Actualiser le matériel')
        refresh.clicked.connect(self.analyze_requested.emit)
        self.apply_recommended = QPushButton('Appliquer le profil conseillé')
        self.apply_recommended.setEnabled(False)
        self.apply_recommended.clicked.connect(self.apply_recommendation)
        hardware_buttons.addWidget(refresh)
        hardware_buttons.addWidget(self.apply_recommended)
        layout.addLayout(hardware_buttons)
        form = QFormLayout()
        self.python = QLineEdit(str(settings.get('training_python') or ''))
        self.python.setPlaceholderText('Python de votre environnement Unsloth / MergeKit (python.exe)')
        row = QHBoxLayout()
        row.addWidget(self.python)
        choose = QPushButton('Parcourir…')
        choose.clicked.connect(self.choose_python)
        row.addWidget(choose)
        form.addRow('Moteur Python externe', row)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        diagnostic = QPushButton('Diagnostic CUDA et outils')
        diagnostic.clicked.connect(lambda: self.launch('diagnostic'))
        help_button = QPushButton('Installer Unsloth sous Windows')
        help_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl('https://unsloth.ai/docs/get-started/install/windows-installation')))
        merge_help = QPushButton('Installation MergeKit')
        merge_help.clicked.connect(lambda: QDesktopServices.openUrl(QUrl('https://github.com/arcee-ai/mergekit#installation')))
        for b in (diagnostic, help_button, merge_help): buttons.addWidget(b)
        layout.addLayout(buttons)
        pages = QTabWidget()
        self.pages = pages
        layout.addWidget(pages, 3)
        def scroll_page(widget):
            area = QScrollArea()
            area.setWidgetResizable(True)
            area.setWidget(widget)
            return area
        train = QWidget()
        f = QFormLayout(train)
        self.profiles = QComboBox()
        for profile in resources.PROFILES:
            self.profiles.addItem(profile['label'], profile)
        self.profiles.setCurrentIndex(1)
        apply_profile = QPushButton('Utiliser ce profil')
        apply_profile.clicked.connect(lambda: self.apply_profile(self.profiles.currentData()))
        profile_row = QHBoxLayout()
        profile_row.addWidget(self.profiles)
        profile_row.addWidget(apply_profile)
        f.addRow('Profils de départ', profile_row)
        self.model = QLineEdit('Qwen/Qwen2.5-3B-Instruct')
        self.model.textEdited.connect(self.mark_model_edited)
        f.addRow('Modèle Hugging Face / dossier', self.model)
        self.dataset = QLineEdit()
        row = QHBoxLayout()
        row.addWidget(self.dataset)
        pick = QPushButton('Choisir JSONL…')
        pick.clicked.connect(self.choose_dataset)
        row.addWidget(pick)
        f.addRow('Exemples validés', row)
        self.epochs = QSpinBox()
        self.epochs.setRange(1, 3)
        f.addRow('Passages sur les exemples', self.epochs)
        self.context = QComboBox()
        self.rank = QComboBox()
        self.batch = QComboBox()
        for widget, values, default in ((self.context, (512,1024,2048,4096), 1024),
                                        (self.rank, (4,8,16,32), 8), (self.batch, (1,2,4), 1)):
            for value in values: widget.addItem(str(value), value)
            widget.setCurrentIndex(widget.findData(default))
        f.addRow('Contexte (tokens)', self.context)
        f.addRow('Rang LoRA', self.rank)
        f.addRow('Exemples simultanés (lot)', self.batch)
        self.budget = QLabel()
        self.budget.setWordWrap(True)
        f.addRow(self.budget)
        self.model.textChanged.connect(self.update_budget)
        for widget in (self.context, self.rank, self.batch):
            widget.currentIndexChanged.connect(self.update_budget)
            widget.activated.connect(self.mark_model_edited)
        text = QLabel('QLoRA 4 bits. Les réglages ci-dessus sont transmis au moteur. '
                      '20 % des exemples réservés à l’évaluation. Minimum 10 exemples distincts ; '
                      'plusieurs centaines de bons exemples sont préférables. La RAM ne remplace pas la VRAM pour l’entraînement.')
        text.setWordWrap(True)
        f.addRow(text)
        start = QPushButton('Entraîner et exporter')
        start.clicked.connect(lambda: self.launch('train'))
        trial = QPushButton('Essai court · 2 étapes')
        trial.clicked.connect(lambda: self.launch('trial'))
        train_buttons = QHBoxLayout()
        train_buttons.addWidget(trial)
        train_buttons.addWidget(start)
        f.addRow(train_buttons)
        pages.addTab(scroll_page(train), 'Entraînement')
        merge = QWidget()
        f = QFormLayout(merge)
        self.model_a = QLineEdit()
        self.model_b = QLineEdit()
        f.addRow('Modèle A — Hugging Face / dossier', self.model_a)
        f.addRow('Modèle B — même base', self.model_b)
        self.merge_method = QComboBox()
        self.merge_method.addItem('Moyenne pondérée (linéaire)', 'linear')
        self.merge_method.addItem('Interpolation sphérique (SLERP)', 'slerp')
        f.addRow('Méthode de fusion', self.merge_method)
        self.weight = QDoubleSpinBox()
        self.weight.setRange(.05, .95)
        self.weight.setSingleStep(.05)
        self.weight.setValue(.5)
        f.addRow('Part du modèle B (0,5 = moitié)', self.weight)
        self.merge_budget = QLabel('Fusion CPU : le diagnostic CUDA n’est pas une condition nécessaire.')
        self.merge_budget.setWordWrap(True)
        f.addRow(self.merge_budget)
        self.model_a.textChanged.connect(self.update_merge_budget)
        self.model_b.textChanged.connect(self.update_merge_budget)
        text = QLabel('Fusion linéaire ou SLERP sur CPU/RAM avec MergeKit. Deux variantes issues du même modèle de base, '
                      'poids Safetensors non quantifiés. Architectures et vocabulaires vérifiés avant fusion ; '
                      'cette vérification ne garantit pas la qualité. Ne fusionne pas directement les modèles GGUF d’Ollama. '
                      'Prévoir plusieurs dizaines de Go libres sur disque.')
        text.setWordWrap(True)
        f.addRow(text)
        start_merge = QPushButton('Vérifier et fusionner')
        start_merge.clicked.connect(lambda: self.launch('merge'))
        f.addRow(start_merge)
        pages.addTab(scroll_page(merge), 'Fusion')
        export = QWidget()
        f = QFormLayout(export)
        self.export_folder = QLineEdit()
        row = QHBoxLayout()
        row.addWidget(self.export_folder)
        pick_export = QPushButton('Dossier model…')
        pick_export.clicked.connect(self.choose_export)
        row.addWidget(pick_export)
        f.addRow('Résultat Safetensors', row)
        self.export_name = QLineEdit('mon-ia-personnelle')
        f.addRow('Nouveau nom Ollama', self.export_name)
        text = QLabel('Import local quantifié Q4_K_M. Ollama doit être installé et accepter cette architecture. '
                      'Un modèle de même nom sera remplacé : choisissez un nouveau nom pour comparer les versions. '
                      'Utilisez ensuite le Comparateur d’IA Manager avec des questions absentes de l’entraînement.')
        text.setWordWrap(True)
        f.addRow(text)
        imp = QPushButton('Importer dans Ollama')
        imp.clicked.connect(self.import_model)
        f.addRow(imp)
        pages.addTab(scroll_page(export), 'Ollama')
        self.examples_editor = ExamplesEditor()
        self.examples_editor.dataset_ready.connect(self.use_dataset)
        pages.addTab(scroll_page(self.examples_editor), 'Exemples')
        self.history = TrainingHistory(lambda: self.job if self.process is not None else None)
        self.history.result_selected.connect(self.use_history_result)
        pages.addTab(self.history, 'Historique')
        guide = QPlainTextEdit()
        guide.setReadOnly(True)
        guide.setPlainText('DÉMARRAGE\n1. Installer un environnement Unsloth Windows selon le guide officiel (bouton ci-dessus). '
            'Sélectionner son python.exe, pas ia_manager.exe. Pour la fusion, sélectionner un environnement avec MergeKit installé. '
            'Ces bibliothèques ne sont pas incluses dans IA Manager.\n'
            '2. Lancer le diagnostic : CUDA doit être disponible pour entraîner.\n'
            '3. Préparer un fichier JSONL : un objet par ligne, avec instruction, output et éventuellement input.\n'
            'Exemple de ligne :\n'+json.dumps({'instruction':'Comment nommer mes archives ?', 'input':'', 'output':'Utilise le nom du programme suivi du numéro de version.'}, ensure_ascii=False)+
            '\n4. Préférer un modèle 3B pour commencer ; un 7B/8B peut demander des réglages supplémentaires. '
            'Les noms Ollama comme qwen3:14b ne sont pas des identifiants Hugging Face.\n'
            '5. Entraîner ; les journaux, adaptateur, évaluations et modèle complet sont conservés dans le dossier de la tâche. '
            'Si l’export échoue après sauvegarde, l’adaptateur reste disponible.\n'
            '6. Importer le dossier model dans Ollama. En cas d’architecture non prise en charge, une conversion GGUF externe est nécessaire.\n'
            '7. Comparer avant/après. Une loss plus basse ne prouve pas que toutes les réponses sont meilleures.\n\n'
            'FUSION\nChoisir deux variantes entraînées à partir de la même base. Une moyenne de poids n’additionne pas simplement les connaissances. '
            'Le modèle peut perdre des capacités. Conserver les originaux.\n\n'
            'Cette version ne collecte pas automatiquement les conversations et ne réentraîne pas en permanence. '
            'Seuls les exemples du fichier choisi sont utilisés. Les téléchargements initiaux nécessitent Internet ; '
            'les exemples ne sont pas téléversés par cet atelier.\n'
            'La fermeture de l’application arrête la tâche. Une tâche interrompue reste marquée incomplète ; '
            'il n’y a pas de reprise automatique dans cette version.')
        guide.appendPlainText('\n\nMATÉRIEL ÉVOLUTIF (v91)\n'
            'L’analyse commune du PC alimente cet atelier. Actualiser le matériel refait la détection du GPU. '
            'Le profil conseillé est une estimation prudente sur un seul GPU, pas une addition RAM + VRAM. '
            'Il tient compte de la RAM totale pour l’export. Les réglages déjà modifiés ne sont pas remplacés lors d’une nouvelle analyse : '
            'utiliser Appliquer le profil conseillé. Les budgets affichés sont indicatifs et non des minima universels.\n'
            'Le moteur relit la VRAM libre de son GPU CUDA avant chaque tâche et enregistre hardware.json. '
            'Cela peut différer de la première carte vue par Windows si CUDA_VISIBLE_DEVICES est configuré. '
            'Un essai de deux étapes effectue réellement des calculs, sans sauvegarder de modèle final. '
            'Il mesure la VRAM allouée/réservée par PyTorch, pas toute la consommation du PC, et ne garantit pas l’export complet. '
            'Choisir des exemples représentatifs. Sur un modèle personnalisé, le budget est inconnu.\n'
            'Sur une machine sans NVIDIA/CUDA, la fusion CPU reste accessible ; cet atelier QLoRA utilise actuellement CUDA. '
            'Sur plusieurs GPU, les mémoires ne sont pas additionnées : entraînement sur le GPU CUDA 0 du moteur. '
            'Réduire d’abord le lot, le contexte ou le modèle si la mémoire manque.')
        guide.appendPlainText('\n\nEXEMPLES ET HISTORIQUE (v94)\n'
            'Dans Exemples, ajouter des questions, un contexte facultatif et les réponses attendues. '
            'Les modifications restent en mémoire jusqu’au clic sur Enregistrer. Chaque sauvegarde crée une nouvelle copie ; '
            'le fichier choisi dans Entraînement est mis à jour. Un brouillon de moins de 10 exemples peut être conservé, '
            'mais il ne peut pas encore servir à entraîner. Aucun contenu de vos conversations n’est importé automatiquement.\n'
            'Historique affiche jusqu’à 200 expériences locales, leurs métriques disponibles et les résultats complets. '
            'Les boutons préparent un import Ollama ou renseignent A/B pour une future fusion, sans lancer les calculs. '
            'Une tâche ancienne sans marque de réussite est affichée Incomplet.\n'
            'SLERP utilise une interpolation sphérique entre deux modèles, avec A comme point de départ et le réglage B comme '
            'coefficient de transition. Les mêmes exigences de compatibilité s’appliquent ; ni SLERP ni la moyenne linéaire '
            'ne garantissent un gain de qualité. Comparer les résultats sur des questions nouvelles.')
        pages.addTab(guide, 'Guide')
        self.status = QLabel('Prêt — commencez par le moteur Python et le diagnostic.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(2000)
        layout.addWidget(self.log, 1)
        row = QHBoxLayout()
        self.stop = QPushButton('Arrêter la tâche')
        self.stop.setEnabled(False)
        self.stop.clicked.connect(self.shutdown)
        open_folder = QPushButton('Ouvrir les résultats')
        open_folder.clicked.connect(self.open_results)
        row.addWidget(self.stop)
        row.addWidget(open_folder)
        layout.addLayout(row)
        self.update_budget()

    def use_dataset(self, path):
        self.dataset.setText(path)
        self.status.setText('Fichier d’exemples sélectionné. Ouvrez Entraînement pour lancer un essai.')

    def use_history_result(self, target, path):
        if self.process is not None:
            self.status.setText('Attendez la fin de la tâche pour préparer une autre opération.')
            return
        if target == 'ollama':
            self.export_folder.setText(path)
            self.pages.setCurrentIndex(2)
        else:
            (self.model_a if target == 'a' else self.model_b).setText(path)
            self.pages.setCurrentIndex(1)

    def record_task_state(self, status, code=None):
        if not self.job or self.importing: return
        try: workspace.record_state(self.job, status, code)
        except OSError as exc: self.log.appendPlainText('État de la tâche non enregistré : '+str(exc))

    def tuning(self):
        return dict(context=self.context.currentData(), rank=self.rank.currentData(), batch=self.batch.currentData())

    def mark_model_edited(self, *_):
        self.model_edited = True

    def set_system_info(self, info):
        self.system_info = dict(info)
        exact = '' if info.get('vram_exact') else ' (valeur incertaine)'
        self.hardware_label.setText(
            f"{info.get('cpu', 'CPU inconnu')} · {info.get('gpu_type', 'GPU inconnu')} · "
            f"VRAM {resources.number(info.get('vram_gb')):.1f} Go{exact} · "
            f"RAM {resources.number(info.get('ram_gb')):.1f} Go "
            f"({resources.number(info.get('ram_available_gb')):.1f} Go libres à l’analyse).")
        suggested = resources.recommend(info)
        self.apply_recommended.setEnabled(suggested is not None)
        self.apply_recommended.setText('Conseillé : '+suggested['label'] if suggested else 'Profil automatique indisponible — diagnostic requis')
        # Ne jamais écraser des choix utilisateur après un changement matériel.
        if suggested and not self.model_edited and self.process is None:
            self.apply_profile(suggested)
        self.update_budget()
        self.update_merge_budget()

    def apply_recommendation(self):
        profile = resources.recommend(self.system_info)
        if profile: self.apply_profile(profile)

    def apply_profile(self, profile):
        if self.process is not None or not profile: return
        self.model_edited = True
        self.model.setText(profile['model'])
        for widget, key in ((self.context, 'context'), (self.rank, 'rank'), (self.batch, 'batch')):
            widget.setCurrentIndex(widget.findData(profile[key]))
        index = next((i for i,p in enumerate(resources.PROFILES) if p['model'] == profile['model']), -1)
        if index >= 0: self.profiles.setCurrentIndex(index)
        self.update_budget()

    def update_budget(self, *_):
        message = resources.advisory(self.system_info, self.model.text(), **self.tuning())
        try: message += f" Disque de sortie : {resources.disk_free(lab.lab_root()):.1f} Go libres."
        except OSError: message += ' Espace disque non mesuré.'
        self.budget.setText(message)

    def update_merge_budget(self, *_):
        req = resources.requirements(self.model_a.text(), action='merge')
        available = resources.number((self.system_info or {}).get('ram_available_gb'))
        if req:
            message = f"Fusion CPU : budget indicatif RAM {req['ram_gb']:.0f} Go / disque {req['disk_gb']:.0f} Go pour deux modèles de cette taille."
        else:
            message = 'Fusion CPU : budget inconnu pour ces modèles personnalisés ; dépend de la taille des poids et des tenseurs.'
        if self.system_info: message += f' RAM libre à l’analyse : {available:.1f} Go.'
        self.merge_budget.setText(message)

    def choose_python(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Python de l’environnement ML')
        if path: self.python.setText(path)

    def choose_dataset(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Exemples validés', '', 'JSONL (*.jsonl)')
        if path: self.dataset.setText(path)

    def choose_export(self):
        path = QFileDialog.getExistingDirectory(self, 'Dossier model exporté')
        if path: self.export_folder.setText(path)

    def open_results(self):
        root = self.job or lab.lab_root()
        root.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(root)))

    def launch(self, action):
        if self.process is not None: return
        try:
            python = Path(self.python.text().strip())
            if not python.is_file() or 'ia_manager' in python.name.lower():
                raise ValueError('Sélectionnez le vrai python.exe de l’environnement ML.')
            settings.set('training_python', str(python))
            job = lab.create_job(action, self.model.text() if action in ('train', 'trial') else self.model_a.text(),
                self.model_b.text(), self.dataset.text(), self.epochs.value(), self.weight.value(),
                tuning=self.tuning(), hardware=self.system_info, merge_method=self.merge_method.currentData())
            self.start_process(str(python), ['-u', str(job/'runner.py'), str(job)], job)
        except Exception as exc:
            self.status.setText(str(exc))

    def import_model(self):
        if self.process is not None: return
        try:
            name = self.export_name.text().strip()
            mf = lab.import_modelfile(self.export_folder.text(), name)
            ollama = shutil.which('ollama')
            if not ollama: raise ValueError('Ollama introuvable dans le PATH.')
            if QMessageBox.question(self, 'Import Ollama',
                    f'Créer {name} ? Si ce nom existe déjà dans Ollama, il sera remplacé.',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes: return
            self.start_process(ollama, ['create', name, '-f', str(mf), '--quantize', 'q4_K_M'], mf.parent, True)
        except Exception as exc:
            self.status.setText(str(exc))

    def start_process(self, program, args, job, importing=False):
        token = local_jobs.reserve('Entraînement / fusion / import')
        if token is None:
            raise ValueError('Une génération locale est en cours ou en attente. Réessayez après sa fin.')
        self.token = token
        self.job = job
        self.importing = importing
        self.cancelled = False
        self.log.clear()
        self.decoder.reset()
        self.logfile = job/'execution.log'
        self.status.setText('En cours — résultats : '+str(job))
        self.stop.setEnabled(True)
        p = QProcess(self)
        self.process = p
        env = QProcessEnvironment.systemEnvironment()
        env.insert('PYTHONIOENCODING', 'utf-8')
        env.insert('HF_HUB_DISABLE_TELEMETRY', '1')
        env.insert('WANDB_DISABLED', 'true')
        p.setProcessEnvironment(env)
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(self.read_output)
        p.finished.connect(self.finished)
        p.errorOccurred.connect(self.process_error)
        self.record_task_state('running')
        self.history.refresh()
        p.start(program, args)

    def read_output(self):
        if self.process is None: return
        data = bytes(self.process.readAllStandardOutput())
        text = self.decoder.decode(data)
        self.log.insertPlainText(text)
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())
        try:
            with self.logfile.open('ab') as stream: stream.write(data)
        except OSError:
            self.status.setText('Attention : journal disque inaccessible ; sortie visible ci-dessous.')

    def process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.log.appendPlainText(self.process.errorString())
            self.finished(-1, QProcess.ExitStatus.CrashExit)

    def finished(self, code, status):
        if self.process is None: return
        self.read_output()
        success = not self.cancelled and code == 0 and status == QProcess.ExitStatus.NormalExit
        self.status.setText('Terminé.' if success else 'Arrêté ou en échec — consultez le journal. Les fichiers partiels sont conservés.')
        if success and (self.job/'trial.json').is_file():
            try:
                result = json.loads((self.job/'trial.json').read_text(encoding='utf-8'))
                self.status.setText(f"Essai réussi · pic PyTorch {result['peak_allocated_gb']:.2f} Go alloués / "
                    f"{result['peak_reserved_gb']:.2f} Go réservés. Export complet non testé.")
            except (OSError, ValueError, KeyError): pass
        if success and (self.job/'hardware.json').is_file() and not (self.job/'trial.json').is_file():
            try:
                data = json.loads((self.job/'hardware.json').read_text(encoding='utf-8'))
                if (self.job/'SUCCESS').read_text() == 'diagnostic':
                    self.status.setText('Diagnostic terminé · '+('CUDA disponible.' if data.get('cuda') else
                        'CUDA indisponible : entraînement impossible dans ce moteur ; fusion CPU possible si MergeKit est installé.'))
            except (OSError, ValueError, KeyError): pass
        if success and (self.job/'model').is_dir():
            self.export_folder.setText(str(self.job/'model'))
        if success and self.importing: self.models_changed.emit()
        self.record_task_state('cancelled' if self.cancelled else ('success' if success else 'failed'), code)
        self.process.deleteLater()
        self.process = None
        self.stop.setEnabled(False)
        local_jobs.release(self.token)
        self.token = None
        self.history.refresh()

    def shutdown(self):
        if self.process is None: return
        self.cancelled = True
        # Arrêter aussi les sous-processus (MergeKit, téléchargement, etc.).
        import psutil
        pid = int(self.process.processId())
        if pid:
            try:
                children = psutil.Process(pid).children(recursive=True)
                for child in children:
                    try: child.kill()
                    except psutil.Error: pass
            except psutil.Error: pass
        process = self.process
        process.kill()
        process.waitForFinished(3000)
