
"""Extension v121 : aperçu 3D dans le Chat et préparation Game Ready."""
import base64
import html
from pathlib import Path
from types import MethodType

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

from src.backend import chat_3d_preview
from src.ui import style
from src.ui.workers import FunctionWorker


def install_v121(window):
    tab = getattr(window, "chat_tab", None)
    if tab is None or getattr(tab, "_v121_chat_preview", False):
        return

    old_render = tab.render_message
    old_link = tab.on_link
    tab.preview3d_worker = None

    def _preview_html(self, path):
        p = Path(str(path or ""))
        if not p.is_file():
            return ""
        data = base64.b64encode(p.read_bytes()).decode("ascii")
        return self.image_html(data)

    def render_message(self, index, model_ref):
        message = self.messages[index]
        result = message.get("creative_result") or {}
        if result.get("kind") != "3d":
            return old_render(index, model_ref)

        body = html.escape(message.get("content", "")).replace("\n", "<br>")
        path = Path(str(result.get("path") or ""))
        preview = str(result.get("preview_path") or "")

        if preview:
            image = _preview_html(self, preview)
            if image:
                body += "<br><br><b>Aperçu 3D rendu par Blender :</b><br>" + image

        if path.is_file():
            body += f"<br><a href='creativefile:{index}'>🧊 Ouvrir le GLB</a>"
            body += f" · <a href='creativefolder:{index}'>📁 Dossier</a>"
            if not preview:
                body += f"<br><a href='v121preview:{index}'>👁️ Générer l’aperçu 3D</a>"
            else:
                body += f"<br><a href='v121preview:{index}'>🔄 Refaire l’aperçu</a>"
            body += f" · <a href='v120blender:{index}'>🛠️ Blender Studio</a>"
            body += f"<br><a href='v121game:{index}'>🎮 Préparer automatiquement pour le jeu</a>"
            body += f" · <a href='v120pipeline:{index}'>⚙️ Régler le pipeline manuellement</a>"

        who = "Création · " + str(result.get("label") or "3D locale")
        self.append_html(self.bubble_html(who, body, style.SURFACE, style.GREEN))

    def on_link(self, url):
        link = url.toString()
        kind, _, rest = link.partition(":")

        if kind == "v121preview":
            try:
                index = int(rest)
                result = self.messages[index].get("creative_result") or {}
                path = Path(str(result.get("path") or ""))
                if not path.is_file():
                    self.status.setText("Le GLB n'existe plus.")
                    return
                if self.preview3d_worker is not None and self.preview3d_worker.isRunning():
                    self.status.setText("Un aperçu 3D est déjà en cours.")
                    return
                self.status.setText("⏳ Blender prépare l'aperçu 3D…")
                target_message = self.messages[index]
                generation = getattr(self, "creative_generation", 0)
                worker = FunctionWorker(chat_3d_preview.render_preview, str(path))
                self.preview3d_worker = worker
                worker.done.connect(
                    lambda ok, value, w=worker, m=target_message, g=generation: self.preview3d_done(w, m, g, ok, value)
                )
                worker.start()
                return
            except (IndexError, ValueError, OSError) as exc:
                self.status.setText("Aperçu 3D impossible : " + str(exc))
                return

        if kind == "v121game":
            try:
                index = int(rest)
                result = self.messages[index].get("creative_result") or {}
                path = Path(str(result.get("path") or ""))
                defaults = chat_3d_preview.game_pipeline_defaults(str(path))
                studio = getattr(window, "studio_hub_tab", None)
                if studio is None:
                    self.status.setText("Studio IA local indisponible.")
                    return
                page = studio.pipeline_v116
                if page.proc:
                    QMessageBox.information(
                        self, "Pipeline personnage",
                        "Un pipeline Blender est déjà en cours."
                    )
                    return

                page.source.setText(defaults["source"])
                page.name.setText(defaults["name"])
                page.clean.setChecked(defaults["clean"])
                page.decimate.setChecked(defaults["decimate"])
                page.uv.setChecked(defaults["uv"])
                page.rig.setChecked(defaults["rig"])
                page.animation.setChecked(defaults["animation"])
                page.retarget.setChecked(defaults["retarget"])
                page.lod.setChecked(defaults["lod"])
                page.collision.setChecked(defaults["collision"])
                page.ratio.setValue(defaults["decimate_ratio"])
                ci = page.collision_mode.findData(defaults["collision_mode"])
                if ci >= 0:
                    page.collision_mode.setCurrentIndex(ci)
                ei = page.engine.findData(defaults["engine"])
                if ei >= 0:
                    page.engine.setCurrentIndex(ei)

                window.tabs.setCurrentWidget(studio)
                inner = studio.tabs.indexOf(page)
                if inner >= 0:
                    studio.tabs.setCurrentIndex(inner)

                answer = QMessageBox.question(
                    page, "Préparer pour le jeu",
                    "Le pipeline est prêt avec :\n\n"
                    "• nettoyage\n• low-poly 50 %\n• UV\n• auto-rig\n"
                    "• LOD\n• collisions convexes\n• export Godot\n\n"
                    "Lancer maintenant toutes les étapes ?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if answer == QMessageBox.StandardButton.Yes:
                    page.plan = {}
                    page.run_all()
                    self.status.setText("🎮 Pipeline Game Ready lancé.")
                else:
                    self.status.setText("Pipeline Game Ready préparé. Vous pouvez modifier les options.")
                return
            except (IndexError, ValueError, OSError, AttributeError) as exc:
                self.status.setText("Préparation Game Ready impossible : " + str(exc))
                return

        return old_link(url)

    def preview3d_done(self, worker, target_message, generation, ok, value):
        if self.preview3d_worker is not worker:
            return
        self.preview3d_worker = None
        if generation != getattr(self, "creative_generation", 0) or not any(m is target_message for m in self.messages):
            self.status.setText("Aperçu terminé pour une ancienne conversation ; résultat ignoré ici.")
            return
        if not ok:
            self.status.setText("❌ Aperçu 3D : " + str(value))
            return
        try:
            result = target_message.setdefault("creative_result", {})
            result["preview_path"] = str(value["preview_path"])
            ref = self.current_ref()
            try:
                self.save_current(ref)
            except Exception:
                pass
            image = _preview_html(self, result["preview_path"])
            if image:
                body = "<b>👁️ Aperçu 3D terminé :</b><br>" + image
                self.append_html(self.bubble_html("Blender · aperçu", body, style.SURFACE, style.GREEN))
            self.status.setText("✅ Aperçu 3D créé et enregistré dans la conversation.")
        except (IndexError, KeyError, OSError, TypeError) as exc:
            self.status.setText("Aperçu créé mais affichage impossible : " + str(exc))

    tab.render_message = MethodType(render_message, tab)
    tab.on_link = MethodType(on_link, tab)
    tab.preview3d_done = MethodType(preview3d_done, tab)

    try:
        tab.chat_display.anchorClicked.disconnect()
    except (TypeError, RuntimeError):
        pass
    tab.chat_display.anchorClicked.connect(tab.on_link)

    tab._v121_chat_preview = True
