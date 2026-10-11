import sys, tempfile, unittest, zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.backend import skills as sk
from src.backend.skills_catalog import PLUGINS


def fake_settings():
    store = {}
    return SimpleNamespace(get=lambda k: store.get(k), set=lambda k, v: store.__setitem__(k, v))


class SkillsTests(unittest.TestCase):
    def setUp(self):
        p = patch.object(sk, "settings", fake_settings())
        p.start()
        self.addCleanup(p.stop)

    def test_catalog(self):
        ids = [s["id"] for s in sk.builtin_skills()]
        self.assertGreaterEqual(len(ids), 60)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(s["prompt"] and s["name"] for s in sk.builtin_skills()))
        self.assertEqual(len(PLUGINS), len(sk.plugins()) - 1)

    def test_plugin_activation_and_instructions(self):
        self.assertEqual(sk.active_instructions(), "")
        self.assertEqual(sk.set_plugin_enabled("code", True), 8)
        n, chars = sk.active_summary()
        self.assertEqual(n, 8)
        self.assertIn("Relecture de code", sk.active_instructions())
        sk.set_plugin_enabled("code", False)
        self.assertEqual(sk.active_instructions(), "")

    def test_user_skills(self):
        s = sk.save_user_skill("Ma skill", "d", "Fais X.")
        s2 = sk.save_user_skill("Ma skill", "d", "Fais Y.")
        self.assertNotEqual(s["id"], s2["id"])
        sk.save_user_skill("Ma skill", "d2", "Fais Z.", sid=s["id"])
        self.assertEqual(sk.get_skill(s["id"])["prompt"], "Fais Z.")
        with self.assertRaises(ValueError):
            sk.save_user_skill("", "", "x")
        sk.set_enabled(s["id"], True)
        self.assertTrue(sk.delete_user_skill(s["id"]))
        self.assertNotIn(s["id"], sk.enabled_ids())

    def test_import(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "a.md").write_text("---\nname: Imp A\ndescription: dA\n---\nCorps A", encoding="utf-8")
            (d / "b.txt").write_text("# Titre B\ncorps B", encoding="utf-8")
            with zipfile.ZipFile(d / "z.zip", "w") as z:
                z.writestr("x/SKILL.md", "---\nname: Zip C\n---\nCorps C")
            (d / "c.pdf").write_text("x")
            n, errors = sk.import_files([str(d / f) for f in ("a.md", "b.txt", "z.zip", "c.pdf")])
        self.assertEqual(n, 3)
        self.assertEqual(len(errors), 1)
        self.assertEqual({s["name"] for s in sk.user_skills()}, {"Imp A", "Titre B", "Zip C"})

    def test_active_text_is_capped(self):
        for k in range(30):
            sk.save_user_skill(f"big{k}", "", "z" * 400)
        sk.set_plugin_enabled("mes-skills", True)
        text = sk.active_instructions()
        self.assertIn("omises", text)
        self.assertLess(len(text), sk.MAX_ACTIVE_CHARS + 600)

    def test_search(self):
        self.assertEqual(sk.search(sk.all_skills(), "relecture code")[0]["id"], "code-review")


if __name__ == "__main__": unittest.main()
