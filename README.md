# IA Manager

**Application desktop Windows pour gérer et exécuter plusieurs IA locales**

Gérateur complet pour utiliser Ollama, LM Studio, GPT4All et des modèles Hugging Face directement sur votre PC, avec analyse système automatique et allocation intelligente RAM/VRAM.

## 🎯 Fonctionnalités

- **💬 Chat** : Discuter en temps réel avec l'IA sélectionnée
- **📦 Modèles** : Télécharger/gérer une large sélection d'IA (Llama, Mistral, CodeLlama, Falcon, Orca...)
- **⚙️ Configuration** : Analyse CPU/GPU/RAM avec recommandations automatiques et slider allocation VRAM/RAM

## 📋 Prérequis

- **Python 3.11+**
- **Windows 10+** (ou Linux/macOS)
- **4GB RAM minimum** (8GB+ recommandé)
- **[Ollama](https://ollama.ai)** installé et lancé en arrière-plan (pour la plupart des modèles)

## 🚀 Installation

### Option 1 : Exécutable Windows (Recommandé)

Téléchargez `ia_manager.exe` depuis les [Releases GitHub](https://github.com/janintibo-art/ia-manager/releases) et lancez-le.

### Option 2 : Depuis les sources

```bash
git clone https://github.com/janintibo-art/ia-manager.git
cd ia_manager
pip install -r requirements.txt
python main.py
```

## 🎨 Interface

### Onglet Chat
- Sélectionner le modèle d'IA
- Converser naturellement
- Historique complet dans la session

### Onglet Modèles
- Liste complète des modèles disponibles (20+)
- Téléchargement en un clic
- Gestion des modèles (suppression, refresh)

### Onglet Configuration
- Analyse automatique du PC
- Recommandations d'IA basées sur vos specs
- Sliders pour répartition VRAM/RAM
- Choix entre Rapidité, Équilibré, Qualité

## 📦 IA Supportées

### Ollama (Local, Rapide)
- Llama 2 (7B-70B)
- Mistral 7B
- Neural Chat
- CodeLlama (Code)
- Orca Mini

### Hugging Face (Custom Models)
- Falcon 7B-180B
- Tous les modèles supportés

### GPT4All (Léger)
- Falcon
- Orca
- MPT

## 🔧 Configuration

L'application crée automatiquement :
- `~/.ia_manager/models/` — Stockage des modèles
- `~/.ia_manager/config/` — Configuration utilisateur

## 📊 Architecture

```
ia_manager/
├── main.py              # Point d'entrée
├── src/
│   ├── ui/              # Interface PyQt6
│   │   └── tabs/        # Chat, Modèles, Setup
│   ├── backend/         # Logique métier
│   │   ├── ai_manager.py
│   │   ├── system_analyzer.py
│   │   └── allocation.py
│   └── api/             # Intégrations
└── requirements.txt     # Dépendances
```

## 🛠️ Développement

```bash
# Installer les dépendances de développement
pip install -r requirements.txt
pip install PyInstaller

# Générer l'exe Windows
pyinstaller --onefile --windowed main.py
```

## 📝 Licence

Libre et gratuit.

## 🤝 Contribution

Contributions bienvenues ! Créez une issue pour signaler des bugs ou proposer des fonctionnalités.

---

**Créé par** [@janintibo-art](https://github.com/janintibo-art)
