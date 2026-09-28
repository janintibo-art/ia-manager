
"""Extension v120 : génération 3D directe depuis le Chat."""
import html
from pathlib import Path
from types import MethodType

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

from src.backend import creative_chat, creative_chat_3d, settings
from src.ui import style


def install_v120(window):
    tab = getattr(window, "chat_tab", None)
    if tab is None or getattr(tab, "_v120_chat_3d", False):
        return

    # Étendre le routeur créatif v119 sans toucher aux générateurs image/audio.
    old_generate = creative_chat.generate

    def generate(ref, prompt, attachments=None):
        try:
            model = creative_chat.model_for_ref(ref)
        except Exception:
            return old_generate(ref, prompt, attachments)
        if model.get("kind") == "3d":
            return creative_chat_3d.generate_3d(ref, prompt, attachments)
        return old_generate(ref, prompt, attachments)

    creative_chat.generate = generate

    old_hint = tab.show_hint
    old_render = tab.render_message
    old_link = tab.on_link

    def show_hint(self):
        ref = self.current_ref()
        if creative_chat.is_creative_ref(ref):
            try:
                model = creative_chat.model_for_ref(ref)
            except Exception:
                return old_hint()
            if model.get("kind") == "3d":
                state = creative_chat.tool_state(model["engine"])
                status = "✅ moteur installé" if state["installed"] else "⚠️ moteur à installer"
                self.hint.setText(
                    f"{model['label']} · {model['specialty']} · {status}\n"
                    "Joignez une image puis cliquez sur Envoyer : le GLB sera généré localement "
                    "et reviendra directement dans cette conversation."
                )
                return
        return old_hint()

    def render_message(self, index, model_ref):
        message = self.messages[index]
        result = message.get("creative_result") or {}
        if result.get("kind") != "3d":
            return old_render(index, model_ref)
        body = html.escape(message.get("content", "")).replace("\n", "<br>")
        path = Path(str(result.get("path") or ""))
        if path.is_file():
            body += f"<br><a href='creativefile:{index}'>🧊 Ouvrir le GLB</a>"
            body += f" · <a href='creativefolder:{index}'>📁 Dossier</a>"
            body += f"<br><a href='v120blender:{index}'>🛠️ Envoyer vers Blender Studio</a>"
            body += f" · <a href='v120pipeline:{index}'>🎮 Envoyer vers Pipeline personnage</a>"
        who = "Création · " + str(result.get("label") or "3D locale")
        self.append_html(self.bubble_html(who, body, style.SURFACE, style.GREEN))

    def on_link(self, url):
        link = url.toString()
        kind, _, rest = link.partition(":")
        if kind in ("v120blender", "v120pipeline"):
            try:
                index = int(rest)
                result = self.messages[index].get("creative_result") or {}
                path = Path(str(result.get("path") or ""))
                if not path.is_file():
                    self.status.setText("Le GLB n'existe plus.")
                    return
                studio = getattr(window, "studio_hub_tab", None)
                if studio is None:
                    self.status.setText("Studio IA local indisponible.")
                    return
                window.tabs.setCurrentWidget(studio)
                if kind == "v120blender":
                    page = studio.blender_v111
                    page.source.setText(str(path))
                    inner = studio.tabs.indexOf(page)
                    if inner >= 0:
                        studio.tabs.setCurrentIndex(inner)
                    self.status.setText("GLB envoyé vers Blender Studio.")
                else:
                    page = studio.pipeline_v116
                    page.source.setText(str(path))
                    page.name.setText(path.stem)
                    inner = studio.tabs.indexOf(page)
                    if inner >= 0:
                        studio.tabs.setCurrentIndex(inner)
                    self.status.setText("GLB envoyé vers Pipeline personnage.")
                return
            except (IndexError, ValueError, OSError, AttributeError) as exc:
                self.status.setText("Action 3D impossible : " + str(exc))
                return
        return old_link(url)

    tab.show_hint = MethodType(show_hint, tab)
    tab.render_message = MethodType(render_message, tab)
    tab.on_link = MethodType(on_link, tab)

    # Les signaux gardent les anciennes méthodes liées : reconnecter ceux modifiés.
    try:
        tab.model_select.currentIndexChanged.disconnect()
    except (TypeError, RuntimeError):
        pass
    tab.model_select.currentIndexChanged.connect(tab.show_hint)
    try:
        tab.chat_display.anchorClicked.disconnect()
    except (TypeError, RuntimeError):
        pass
    tab.chat_display.anchorClicked.connect(tab.on_link)

    tab._v120_chat_3d = True
    tab.show_hint()
