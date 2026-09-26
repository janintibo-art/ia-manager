"""Tests sans API : restauration et commits limités dans un vrai dépôt temporaire."""
import os
import sys
import tempfile
import subprocess
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.backend import change_review as cr, attachments as att


def block(name, code):
    return {"filename": name, "code": code, "lang": "text"}


class ChangeReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.home = Path(self.temp.name) / "profile"
        self.home.mkdir()
        self.profile = patch.object(Path, "home", return_value=self.home)
        self.profile.start()

    def tearDown(self):
        self.profile.stop()
        self.temp.cleanup()

    def test_preview_apply_restore_exact_bytes(self):
        existing = self.root / "old.txt"
        existing.write_bytes(b"old\r\n")
        review = cr.prepare([block("old.txt", "new"), block("src/new.txt", "created")], self.root)
        self.assertIn("-old", review["entries"][0]["diff"])
        self.assertEqual(existing.read_bytes(), b"old\r\n")
        backup = cr.apply(review)
        self.assertEqual(existing.read_bytes(), b"new\n")
        cr.restore(backup)
        self.assertEqual(existing.read_bytes(), b"old\r\n")
        self.assertFalse((self.root / "src/new.txt").exists())
        with self.assertRaises(ValueError):
            cr.restore(backup)

    def test_stale_preview_and_stale_restore_are_rejected(self):
        target = self.root / "a.txt"
        target.write_text("old")
        review = cr.prepare([block("a.txt", "new")], self.root)
        target.write_text("changed")
        with self.assertRaises(ValueError):
            cr.apply(review)
        backup = cr.apply(cr.prepare([block("a.txt", "new"), block("b.txt", "new")], self.root))
        target.write_text("new personal edit")
        with self.assertRaises(ValueError):
            cr.restore(backup)
        self.assertEqual(target.read_text(), "new personal edit")
        self.assertTrue((self.root / "b.txt").exists())

    def test_failed_batch_rolls_back(self):
        (self.root / "a.txt").write_bytes(b"original")
        review = cr.prepare([block("a.txt", "new"), block("b.txt", "new")], self.root)
        write = cr.atomic_write
        def fail_second(path, data, mode=0o644):
            if path.name == "b.txt":
                raise OSError("disk failure")
            return write(path, data, mode)
        with patch.object(cr, "atomic_write", side_effect=fail_second):
            with self.assertRaises(OSError):
                cr.apply(review)
        self.assertEqual((self.root / "a.txt").read_bytes(), b"original")
        self.assertFalse((self.root / "b.txt").exists())

    def test_path_and_binary_protection(self):
        for name in ("../bad.py", ".git/config", "/bad.py", "C:/bad.py"):
            with self.assertRaises(ValueError):
                cr.prepare([block(name, "bad")], self.root)
        (self.root / "binary.txt").write_bytes(b"\0data")
        with self.assertRaises(ValueError):
            cr.prepare([block("binary.txt", "text")], self.root)
        link = self.root / "linked"
        try:
            link.symlink_to(self.home, target_is_directory=True)
        except OSError:
            return
        with self.assertRaises(ValueError):
            cr.prepare([block("linked/a.txt", "bad")], self.root)

    def test_commit_excludes_other_staged_changes(self):
        def git(*args):
            return subprocess.check_output(["git", "-C", str(self.root), *args], stderr=subprocess.STDOUT, text=True)
        git("init")
        git("config", "user.email", "test@example.invalid")
        git("config", "user.name", "Test")
        for name in ("selected.txt", "other.txt"):
            (self.root / name).write_text("initial\n")
        git("add", ".")
        git("commit", "-m", "Initial")
        (self.root / "other.txt").write_text("unrelated\n")
        git("add", "other.txt")
        review = cr.prepare([block("selected.txt", "selected"), block("new.txt", "new")], self.root)
        cr.apply(review)
        for step in cr.commit_steps(["selected.txt", "new.txt"], "Selected files")[:-1]:
            git(*step["args"])
        committed = git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines()
        self.assertEqual(set(committed), {"selected.txt", "new.txt"})
        self.assertEqual(git("diff", "--cached", "--name-only").strip(), "other.txt")

    def test_large_zip_entry_is_not_decompressed(self):
        archive = self.root / "data.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("too_large.txt", b"x" * (att.MAX_ENTRY_BYTES + 1))
            z.writestr("small.txt", "read me")
        original = zipfile.ZipFile.open
        opened = []
        def tracked(obj, name, *args, **kwargs):
            opened.append(name.filename if isinstance(name, zipfile.ZipInfo) else name)
            return original(obj, name, *args, **kwargs)
        with patch.object(zipfile.ZipFile, "open", tracked):
            result = att.load_attachment(str(archive))
        self.assertNotIn("too_large.txt", opened)
        self.assertIn("small.txt", opened)
        self.assertIn("read me", result["text"])

    def test_oversized_attachment_and_docx(self):
        target = self.root / "big.txt"
        with target.open("wb") as f:
            f.truncate(att.MAX_ATTACHMENT_BYTES + 1)
        with self.assertRaises(ValueError):
            att.load_attachment(str(target))
        word = self.root / "big.docx"
        with zipfile.ZipFile(word, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("word/document.xml", b"a" * (att.MAX_DOCX_XML_BYTES + 1))
        with self.assertRaises(ValueError):
            att.load_attachment(str(word))


if __name__ == "__main__":
    unittest.main()
