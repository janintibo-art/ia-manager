"""Onglet Setup - Analyse système et configuration RAM/VRAM"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSlider, QPushButton, QTextEdit, QGroupBox
)
from PyQt6.QtCore import Qt
from src.backend.system_analyzer import SystemAnalyzer
from src.backend.allocation import AllocationCalculator


class SetupTab(QWidget):
    """Interface d'analyse système et configuration"""

    def __init__(self):
        super().__init__()
        self.analyzer = SystemAnalyzer()
        self.allocator = AllocationCalculator()
        self.init_ui()

    def init_ui(self):
        """Initialiser l'interface de setup"""
        layout = QVBoxLayout()

        # Bouton d'analyse
        analyze_btn = QPushButton("🔍 Analyser mon ordinateur")
        analyze_btn.clicked.connect(self.analyze_system)
        layout.addWidget(analyze_btn)

        # Résultats d'analyse
        analysis_group = QGroupBox("📊 Analyse système")
        analysis_layout = QVBoxLayout()

        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setMaximumHeight(250)
        analysis_layout.addWidget(self.analysis_text)

        analysis_group.setLayout(analysis_layout)
        layout.addWidget(analysis_group)

        # Recommandations
        recomm_group = QGroupBox("💡 Recommandations d'IA")
        recomm_layout = QVBoxLayout()

        self.recomm_text = QTextEdit()
        self.recomm_text.setReadOnly(True)
        self.recomm_text.setMaximumHeight(200)
        recomm_layout.addWidget(self.recomm_text)

        recomm_group.setLayout(recomm_layout)
        layout.addWidget(recomm_group)

        # Configuration RAM/VRAM
        config_group = QGroupBox("⚙️ Configuration de l'allocation")
        config_layout = QVBoxLayout()

        # Slider VRAM
        vram_layout = QHBoxLayout()
        vram_layout.addWidget(QLabel("VRAM (GPU) :"))

        self.vram_slider = QSlider(Qt.Orientation.Horizontal)
        self.vram_slider.setMinimum(0)
        self.vram_slider.setMaximum(100)
        self.vram_slider.setValue(50)
        self.vram_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.vram_slider.valueChanged.connect(self.update_allocation)
        vram_layout.addWidget(self.vram_slider)

        self.vram_label = QLabel("50%")
        vram_layout.addWidget(self.vram_label)

        config_layout.addLayout(vram_layout)

        # Slider Priorité
        priority_layout = QHBoxLayout()
        priority_layout.addWidget(QLabel("Priorité :"))

        self.priority_slider = QSlider(Qt.Orientation.Horizontal)
        self.priority_slider.setMinimum(0)
        self.priority_slider.setMaximum(100)
        self.priority_slider.setValue(50)
        self.priority_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.priority_slider.valueChanged.connect(self.update_allocation)
        priority_layout.addWidget(self.priority_slider)

        self.priority_label = QLabel("Équilibré")
        priority_layout.addWidget(self.priority_label)

        config_layout.addLayout(priority_layout)

        # Allocation résultat
        self.allocation_text = QTextEdit()
        self.allocation_text.setReadOnly(True)
        self.allocation_text.setMaximumHeight(120)
        config_layout.addWidget(self.allocation_text)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        layout.addStretch()
        self.setLayout(layout)

    def analyze_system(self):
        """Analyser le système"""
        info = self.analyzer.get_system_info()

        analysis = f"""
🖥️ **Processeur** : {info['cpu']}
💾 **RAM** : {info['ram_gb']:.1f} GB ({info['ram_available_gb']:.1f} GB disponible)
🎮 **GPU** : {info['gpu_type']} ({info['vram_gb']:.1f} GB VRAM)
⚡ **Type GPU** : {info['gpu_vendor']}
        """

        self.analysis_text.setText(analysis)

        # Obtenir les recommandations
        recommendations = self.analyzer.get_recommendations(info)

        recomm_text = "\n".join([f"✓ {r}" for r in recommendations])
        self.recomm_text.setText(recomm_text)

        # Mettre à jour l'allocation
        self.update_allocation()

    def update_allocation(self):
        """Mettre à jour l'allocation RAM/VRAM"""
        vram_percent = self.vram_slider.value()
        priority = self.priority_slider.value()

        # Mettre à jour les labels
        self.vram_label.setText(f"{vram_percent}%")

        if priority < 33:
            priority_text = "Rapidité maximale"
        elif priority < 66:
            priority_text = "Équilibré"
        else:
            priority_text = "Qualité maximale"

        self.priority_label.setText(priority_text)

        # Calculer l'allocation
        allocation = self.allocator.calculate_allocation(
            vram_percent=vram_percent,
            priority=priority_text
        )

        alloc_text = f"""
📊 Allocation recommandée :

🎮 VRAM (GPU) : {allocation['vram_mb']} MB
💾 RAM (CPU) : {allocation['ram_mb']} MB
⚡ Priorité : {priority_text}

💡 Conseil : {allocation['advice']}
        """

        self.allocation_text.setText(alloc_text)
