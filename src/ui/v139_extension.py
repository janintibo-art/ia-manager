"""Extension v139 : Model Family Tree pour visualiser la filiation des modèles."""
import json
import re
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QAbstractItemView, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSplitter, QTextBrowser, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from src.backend import storage
from src.backend import training_lab as lab


ICONS = {
    "source": "🧬",
    "train": "🎓",
    "merge": "🧩",
    "obliteratus": "🧪",
    "lora": "🪶",
    "ollama": "💬",
    "moe": "🧠",
    "multi": "🔗",
    "unknown": "📦",
}


def _safe_json(path, default):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        return value
    except Exception:
        return default


def _node_key(value):
    value = str(value or "").strip()
    if not value:
        return ""
    try:
        p = Path(value).expanduser()
        if p.exists():
            return "path:" + str(p.resolve()).lower()
    except Exception:
        pass
    return "name:" + value.lower()


def _display_name(value):
    value = str(value or "").strip()
    if not value:
        return "Modèle inconnu"
    try:
        p = Path(value)
        if p.name and (p.exists() or "\\" in value or "/" in value):
            return p.name
    except Exception:
        pass
    return value


class FamilyGraph:
    def __init__(self):
        self.nodes = {}
        self.edges = []

    def add_node(self, ref, kind="unknown", path="", meta=None):
        key = _node_key(ref)
        if not key:
            return ""
        node = self.nodes.setdefault(key, {
            "key": key,
            "ref": str(ref),
            "name": _display_name(ref),
            "kind": kind,
            "path": str(path or ""),
            "meta": {},
        })
        if node["kind"] == "unknown" and kind != "unknown":
            node["kind"] = kind
        if path and not node["path"]:
            node["path"] = str(path)
        if meta:
            node["meta"].update(meta)
        return key

    def add_edge(self, parent, child, relation):
        p = self.add_node(parent, "source")
        c = self.add_node(child)
        if not p or not c or p == c:
            return
        edge = (p, c, relation)
        if edge not in self.edges:
            self.edges.append(edge)

    def parents(self, key):
        return [(p, rel) for p, c, rel in self.edges if c == key]

    def children(self, key):
        return [(c, rel) for p, c, rel in self.edges if p == key]


def _scan_training(graph):
    root = lab.lab_root()
    if not root.exists():
        return
    for folder in sorted(root.iterdir()):
        if not folder.is_dir():
            continue
        cfg_path = folder / "job.json"
        if not cfg_path.is_file():
            continue
        cfg = _safe_json(cfg_path, {})
        action = cfg.get("action")
        model = str(cfg.get("model") or "")
        other = str(cfg.get("other") or "")
        final = folder / "model"
        adapter = folder / "adapter"

        if model:
            graph.add_node(model, "source")

        if action == "train":
            if adapter.is_dir():
                akey = graph.add_node(
                    str(adapter), "lora", str(adapter),
                    {"source": model, "job": str(folder), "action": "Adaptateur LoRA/QLoRA"},
                )
                graph.add_edge(model, str(adapter), "LoRA / QLoRA")
            if final.is_dir():
                graph.add_node(
                    str(final), "train", str(final),
                    {"source": model, "job": str(folder), "action": "Entraînement Unsloth"},
                )
                graph.add_edge(model, str(final), "Entraînement Unsloth")
                if adapter.is_dir():
                    graph.add_edge(str(adapter), str(final), "Fusion de l’adaptateur")

        elif action == "merge" and final.is_dir():
            graph.add_node(
                str(final), "merge", str(final),
                {
                    "source_a": model,
                    "source_b": other,
                    "job": str(folder),
                    "method": cfg.get("merge_method", "linear"),
                },
            )
            if model:
                graph.add_edge(model, str(final), "Fusion MergeKit")
            if other:
                graph.add_node(other, "source")
                graph.add_edge(other, str(final), "Fusion MergeKit")


def _scan_obliteratus(graph):
    path = Path.home() / ".ia_manager" / "obliteratus_versions.json"
    versions = _safe_json(path, [])
    if not isinstance(versions, list):
        return
    for item in versions:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source_model") or item.get("source_checkpoint") or "")
        output = str(
            item.get("ollama_name")
            or item.get("gguf_path")
            or item.get("source_checkpoint")
            or ""
        )
        if not output:
            continue
        graph.add_node(
            output,
            "obliteratus",
            item.get("gguf_path") or item.get("source_checkpoint") or "",
            {
                "method": item.get("method") or "",
                "note": item.get("note") or "",
                "created": item.get("created") or "",
                "ollama_name": item.get("ollama_name") or "",
            },
        )
        if source:
            graph.add_node(source, "source")
            graph.add_edge(source, output, "Obliteratus")


def _models_from_yaml(text):
    refs = []
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"(?:-\s*)?(?:model|base_model|source_model)\s*:\s*(.+)$", line)
        if not m:
            continue
        value = m.group(1).strip().strip("'\"")
        if value and value not in refs:
            refs.append(value)
    return refs


def _scan_mergekit(graph):
    configs = Path.home() / ".ia_manager" / "mergekit" / "configs"
    outputs = storage.app_models() / "Fusionnes"
    if configs.is_dir():
        for cfg in configs.glob("*.yml"):
            refs = _models_from_yaml(cfg.read_text(encoding="utf-8", errors="replace"))
            out = outputs / cfg.stem
            if out.exists():
                graph.add_node(
                    str(out), "merge", str(out),
                    {"config": str(cfg), "action": "Fusion MergeKit"},
                )
                for ref in refs:
                    graph.add_node(ref, "source")
                    graph.add_edge(ref, str(out), "Fusion MergeKit")

    advanced = Path.home() / ".ia_manager" / "mergekit" / "advanced"
    if advanced.is_dir():
        for cfg in advanced.glob("*.yml"):
            refs = _models_from_yaml(cfg.read_text(encoding="utf-8", errors="replace"))
            stem = cfg.stem
            if stem.endswith("-moe"):
                name = stem[:-4]
                kind = "moe"
                relation = "MoE"
            elif stem.endswith("-multi"):
                name = stem[:-6]
                kind = "multi"
                relation = "Fusion multi-étapes"
            else:
                continue
            out = outputs / name
            if out.exists():
                graph.add_node(
                    str(out), kind, str(out),
                    {"config": str(cfg), "action": relation},
                )
                for ref in refs:
                    graph.add_node(ref, "source")
                    graph.add_edge(ref, str(out), relation)

    lora_root = storage.app_models() / "LoRA"
    if lora_root.is_dir():
        for folder in lora_root.iterdir():
            if folder.is_dir():
                graph.add_node(
                    str(folder), "lora", str(folder),
                    {"action": "LoRA extrait avec MergeKit"},
                )


def _scan_loose_outputs(graph):
    outputs = storage.app_models() / "Fusionnes"
    if outputs.is_dir():
        for folder in outputs.iterdir():
            if folder.is_dir():
                key = _node_key(str(folder))
                if key not in graph.nodes:
                    graph.add_node(str(folder), "merge", str(folder))


def _build_graph():
    graph = FamilyGraph()
    _scan_training(graph)
    _scan_obliteratus(graph)
    _scan_mergekit(graph)
    _scan_loose_outputs(graph)
    return graph


class ModelFamilyTree(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.graph = FamilyGraph()
        self.item_to_key = {}
        self.build_ui()
        self.refresh()

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("🌳 Model Family Tree")
        title.setObjectName("Title")
        root.addWidget(title)

        intro = QLabel(
            "Visualisez l’origine de vos modèles : entraînements Unsloth, adaptateurs LoRA, "
            "fusions MergeKit, MoE, traitements Obliteratus et versions locales."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filtrer par nom, méthode ou chemin…")
        row.addWidget(self.search, 1)
        self.refresh_btn = QPushButton("🔄 Reconstruire l’arbre")
        row.addWidget(self.refresh_btn)
        root.addLayout(row)

        self.stats = QLabel()
        self.stats.setWordWrap(True)
        root.addWidget(self.stats)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Modèle / variante", "Transformation"])
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setMinimumWidth(420)
        splitter.addWidget(self.tree)

        right = QWidget()
        rl = QVBoxLayout(right)
        self.details = QTextBrowser()
        self.details.setOpenExternalLinks(False)
        rl.addWidget(self.details, 1)

        actions = QHBoxLayout()
        self.open_btn = QPushButton("📁 Ouvrir les fichiers")
        actions.addWidget(self.open_btn)
        self.chat_btn = QPushButton("💬 Ouvrir dans Chat")
        actions.addWidget(self.chat_btn)
        self.merge_a_btn = QPushButton("A → MergeKit")
        actions.addWidget(self.merge_a_btn)
        self.merge_b_btn = QPushButton("B → MergeKit")
        actions.addWidget(self.merge_b_btn)
        actions.addStretch()
        rl.addLayout(actions)
        splitter.addWidget(right)
        splitter.setSizes([560, 440])
        root.addWidget(splitter, 1)

        legend = QLabel(
            "Légende · 🧬 source · 🎓 entraînement · 🪶 LoRA · 🧩 fusion · "
            "🧠 MoE · 🔗 multi-étapes · 🧪 Obliteratus · 💬 Ollama"
        )
        legend.setWordWrap(True)
        root.addWidget(legend)

        self.refresh_btn.clicked.connect(self.refresh)
        self.search.textChanged.connect(self.apply_filter)
        self.tree.itemSelectionChanged.connect(self.show_selected)
        self.open_btn.clicked.connect(self.open_selected)
        self.chat_btn.clicked.connect(self.chat_selected)
        self.merge_a_btn.clicked.connect(lambda: self.send_merge("a"))
        self.merge_b_btn.clicked.connect(lambda: self.send_merge("b"))

    def refresh(self):
        self.graph = _build_graph()
        self.populate_tree()
        counts = {}
        for node in self.graph.nodes.values():
            counts[node["kind"]] = counts.get(node["kind"], 0) + 1
        self.stats.setText(
            f"{len(self.graph.nodes)} nœud(s) · {len(self.graph.edges)} lien(s) de filiation · "
            f"{counts.get('train',0)} entraînement(s) · {counts.get('lora',0)} LoRA · "
            f"{counts.get('merge',0)} fusion(s) · {counts.get('obliteratus',0)} Obliteratus."
        )

    def populate_tree(self):
        self.tree.clear()
        self.item_to_key.clear()

        child_keys = {c for _, c, _ in self.graph.edges}
        roots = [k for k in self.graph.nodes if k not in child_keys]
        if not roots:
            roots = list(self.graph.nodes)

        visited_global = set()
        for key in sorted(roots, key=lambda k: self.graph.nodes[k]["name"].lower()):
            item = self.make_item(key, "")
            self.tree.addTopLevelItem(item)
            self.add_children(item, key, set())
            visited_global.add(key)

        # Afficher aussi les nœuds orphelins qui n'ont pas été atteints.
        shown = set(self.item_to_key.values())
        for key in self.graph.nodes:
            if key not in shown:
                self.tree.addTopLevelItem(self.make_item(key, "Orphelin / source locale"))

        self.tree.expandToDepth(1)
        self.apply_filter()

    def make_item(self, key, relation):
        node = self.graph.nodes[key]
        icon = ICONS.get(node["kind"], "📦")
        item = QTreeWidgetItem([f"{icon} {node['name']}", relation])
        item.setData(0, Qt.ItemDataRole.UserRole, key)
        self.item_to_key[id(item)] = key
        return item

    def add_children(self, parent_item, key, branch):
        if key in branch:
            cyc = QTreeWidgetItem(["↩ cycle détecté", ""])
            parent_item.addChild(cyc)
            return
        branch = set(branch)
        branch.add(key)
        for child, relation in sorted(
            self.graph.children(key),
            key=lambda x: self.graph.nodes[x[0]]["name"].lower()
        ):
            item = self.make_item(child, relation)
            parent_item.addChild(item)
            self.add_children(item, child, branch)

    def selected_key(self):
        items = self.tree.selectedItems()
        if not items:
            return ""
        return str(items[0].data(0, Qt.ItemDataRole.UserRole) or "")

    def selected_node(self):
        return self.graph.nodes.get(self.selected_key())

    def show_selected(self):
        node = self.selected_node()
        if not node:
            self.details.setHtml("<p>Sélectionnez un modèle dans l’arbre.</p>")
            self.update_buttons()
            return

        parents = self.graph.parents(node["key"])
        children = self.graph.children(node["key"])

        lines = [
            f"<h3>{ICONS.get(node['kind'],'📦')} {node['name']}</h3>",
            f"<p><b>Type :</b> {node['kind']}</p>",
            f"<p><b>Référence :</b> {node['ref']}</p>",
        ]
        if node.get("path"):
            lines.append(f"<p><b>Chemin :</b> {node['path']}</p>")

        if parents:
            lines.append("<p><b>Parent(s) :</b></p><ul>")
            for p, rel in parents:
                lines.append(
                    f"<li>{self.graph.nodes[p]['name']} — {rel}</li>"
                )
            lines.append("</ul>")

        if children:
            lines.append("<p><b>Dérivé(s) :</b></p><ul>")
            for c, rel in children:
                lines.append(
                    f"<li>{self.graph.nodes[c]['name']} — {rel}</li>"
                )
            lines.append("</ul>")

        if node.get("meta"):
            lines.append("<p><b>Métadonnées :</b></p><ul>")
            for k, v in node["meta"].items():
                if v not in ("", None, [], {}):
                    lines.append(f"<li>{k}: {v}</li>")
            lines.append("</ul>")

        self.details.setHtml("".join(lines))
        self.update_buttons()

    def update_buttons(self):
        node = self.selected_node()
        has = node is not None
        path_ok = False
        chat_ok = False
        if has:
            p = node.get("path") or node.get("ref")
            try:
                path_ok = Path(p).exists()
            except Exception:
                path_ok = False
            chat_ok = bool(
                node.get("meta", {}).get("ollama_name")
                or node.get("kind") == "ollama"
                or (node.get("kind") == "obliteratus" and "/" not in node.get("ref",""))
            )
        self.open_btn.setEnabled(has and path_ok)
        self.chat_btn.setEnabled(has and chat_ok)
        self.merge_a_btn.setEnabled(has)
        self.merge_b_btn.setEnabled(has)

    def open_selected(self):
        node = self.selected_node()
        if not node:
            return
        p = node.get("path") or node.get("ref")
        try:
            path = Path(p)
            if path.exists():
                if path.is_file():
                    path = path.parent
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        except Exception:
            pass

    def chat_selected(self):
        node = self.selected_node()
        if not node:
            return
        name = node.get("meta", {}).get("ollama_name") or node.get("ref")
        chat = getattr(self.window, "chat_tab", None)
        if chat is None:
            return
        try:
            chat.refresh_models()
            if chat.select_ref(name):
                self.window.tabs.setCurrentWidget(chat)
        except Exception:
            pass

    def send_merge(self, side):
        node = self.selected_node()
        tab = getattr(self.window, "mergekit_tab", None)
        if node is None or tab is None:
            return
        value = node.get("path") or node.get("ref")
        if side == "a":
            tab.model_a.setText(str(value))
        else:
            tab.model_b.setText(str(value))
        self.window.tabs.setCurrentWidget(tab)

    def apply_filter(self):
        query = self.search.text().strip().lower()

        def visit(item):
            own = (
                item.text(0) + " " + item.text(1)
            ).lower()
            child_visible = False
            for i in range(item.childCount()):
                if visit(item.child(i)):
                    child_visible = True
            visible = (not query) or (query in own) or child_visible
            item.setHidden(not visible)
            if visible and query:
                item.setExpanded(True)
            return visible

        for i in range(self.tree.topLevelItemCount()):
            visit(self.tree.topLevelItem(i))


def install_v139(window):
    if getattr(window, "_v139_family_tree", False):
        return
    tab = ModelFamilyTree(window)
    window.family_tree_tab = tab

    mergekit = getattr(window, "mergekit_tab", None)
    idx = window.tabs.indexOf(mergekit)
    insert_at = idx + 1 if idx >= 0 else window.tabs.count()
    window.tabs.insertTab(insert_at, tab, "🌳 Famille IA")
    window._v139_family_tree = True
