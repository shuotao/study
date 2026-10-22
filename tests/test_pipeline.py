"""End-to-end and tamper tests for the pipeline (no network, no LLM).

A deterministic stand-in plays the implementer for Phase 3 so that the gates, the ledger and the audit can be
exercised — including the shortcuts they must catch. Run: python3 -m unittest discover tests
"""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from pipeline import gates  # noqa: E402
from pipeline.common import SESSIONS, append_ledger, read_ledger  # noqa: E402

PY = sys.executable
FIXTURE = REPO / "examples/talk-context/excerpt.srt"


def gsn(*args):
    return subprocess.run([PY, str(REPO / "gsn.py"), *map(str, args)], cwd=REPO, capture_output=True, text=True,
                          env={**os.environ, "GSN_ACTOR": "test"})


def fake_polish(plain: str) -> str:
    """Stand-in implementer: 5 cues per paragraph, punctuation added, headings inserted. Zero omission."""
    lines = [l.strip() for l in plain.splitlines() if l.strip()]
    paras = ["，".join(l.replace(" ", "，") for l in lines[i:i + 5]) + "。" for i in range(0, len(lines), 5)]
    out = ["# 測試講稿", ""]
    for n, p in enumerate(paras):
        if n % 4 == 0:
            out += [f"## 第 {n // 4 + 1} 段", ""]
        out += [p, ""]
    return "\n".join(out)


class Pipeline(unittest.TestCase):
    slug = f"test-{os.getpid()}"

    @classmethod
    def setUpClass(cls):
        cls.sdir = SESSIONS / cls.slug
        shutil.rmtree(cls.sdir, ignore_errors=True)
        r = gsn("new", "--from-srt", FIXTURE, "--slug", cls.slug, "--context", REPO / "examples/talk-context/context.txt")
        assert r.returncode == 0, r.stdout + r.stderr

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.sdir, ignore_errors=True)

    def test_1_happy_path_and_audit(self):
        md = self.sdir / "cleaned.md"
        md.write_text(fake_polish(md.read_text(encoding="utf-8")), encoding="utf-8")
        r = gsn("done", self.slug, "p3-polish")
        self.assertEqual(r.returncode, 0, r.stdout)
        subprocess.run([PY, str(REPO / "scripts/normalize_punctuation.py"), str(md), "--in-place"], check=True,
                       capture_output=True)
        self.assertEqual(gsn("done", self.slug, "p3-punct").returncode, 0)
        t = md.read_text(encoding="utf-8")
        t = re.sub(r"(## 第 \d+ 段\n\n)", r"\1接下來要談的是，", t)
        md.write_text(t, encoding="utf-8")
        r = gsn("done", self.slug, "p3-hooks")
        self.assertEqual(r.returncode, 0, r.stdout)
        r = gsn("audit", self.slug)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_2_tamper_after_done_is_caught(self):
        md = self.sdir / "cleaned.md"
        orig = md.read_text(encoding="utf-8")
        md.write_text(orig.replace("。", "！", 1), encoding="utf-8")
        r = gsn("audit", self.slug)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("FAIL A6 cleaned.md", r.stdout)
        md.write_text(orig, encoding="utf-8")

    def test_3_ledger_edit_is_caught(self):
        p = self.sdir / "ledger.jsonl"
        orig = p.read_text(encoding="utf-8")
        p.write_text(orig.replace("\"action\": \"create\"", "\"action\": \"created\"", 1), encoding="utf-8")
        r = gsn("audit", self.slug)
        self.assertIn("FAIL A0 ledger hash chain", r.stdout)
        p.write_text(orig, encoding="utf-8")

    def test_4_transcript_is_immutable(self):
        p = self.sdir / "transcript.srt"
        orig = p.read_bytes()
        p.write_bytes(orig.replace(b"00:00:03,000", b"00:00:03,100", 1))
        r = gsn("audit", self.slug)
        self.assertIn("FAIL A1", r.stdout)
        p.write_bytes(orig)


class Gates(unittest.TestCase):
    def make(self, slug):
        sdir = SESSIONS / slug
        shutil.rmtree(sdir, ignore_errors=True)
        r = gsn("new", "--from-srt", FIXTURE, "--slug", slug)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.addCleanup(shutil.rmtree, sdir, True)
        return sdir

    def test_summary_fails_polish(self):
        sdir = self.make(f"test-sum-{os.getpid()}")
        md = sdir / "cleaned.md"
        full = fake_polish(md.read_text(encoding="utf-8"))
        md.write_text(full[: len(full) // 2] + "\n\n講者提到了很多例子。\n", encoding="utf-8")
        r = gsn("done", sdir.name, "p3-polish")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("FAIL p3-polish     zero omission", r.stdout)
        self.assertIn("FAIL p3-polish     no new third-person summary phrases", r.stdout)
        self.assertTrue((sdir / ".p3-polish.pending.json").exists(), "marker must stay when the gate fails")

    def test_out_of_order_and_wordchange(self):
        sdir = self.make(f"test-ord-{os.getpid()}")
        self.assertNotEqual(gsn("done", sdir.name, "p3-hooks").returncode, 0)        # not next
        md = sdir / "cleaned.md"
        md.write_text(fake_polish(md.read_text(encoding="utf-8")), encoding="utf-8")
        self.assertEqual(gsn("done", sdir.name, "p3-polish").returncode, 0)
        t = md.read_text(encoding="utf-8")
        md.write_text(t.replace("產業", "行業", 1), encoding="utf-8")                  # a word, not punctuation
        r = gsn("done", sdir.name, "p3-punct")
        self.assertIn("FAIL p3-punct      only punctuation changed", r.stdout)


class Tools(unittest.TestCase):
    def test_phase_a_upgrade_keeps_terms_and_replies(self):
        from pipeline.phase_a_clean import is_garbled_cjk, is_garbled_latin
        self.assertFalse(is_garbled_cjk("domain knowledge"))
        self.assertFalse(is_garbled_cjk("Writing is rewriting"))      # upstream false drop (tool-comparison.md)
        self.assertFalse(is_garbled_cjk("我用 Google 的 Gemini Flash"))  # code-switching, dropped by upstream too
        self.assertTrue(is_garbled_cjk("這個 ┌┐└┘├┤ 符號"))               # noise still caught
        self.assertTrue(is_garbled_cjk("Subtitles by the Amara.org community"))
        self.assertTrue(is_garbled_latin("Thank you for watching"))
        self.assertFalse(is_garbled_latin("We shipped Claude Code to production last week"))

    def test_punctuation_protection(self):
        sys.path.insert(0, str(REPO / "scripts"))
        from normalize_punctuation import normalize_text
        out, _ = normalize_text("版本 9.30 與 ai.dev、shot-01.png 和 1,000 元,網址 https://x.io 時間 9:30.")
        self.assertIn("9.30", out); self.assertIn("ai.dev", out); self.assertIn("shot-01.png", out)
        self.assertIn("1,000", out); self.assertIn("https://x.io", out); self.assertIn("9:30", out)
        self.assertTrue(out.endswith("。")); self.assertIn("元，", out)

    def test_inserted_only(self):
        ok, _ = gates.inserted_only("a\n\nb\n", "a\n\n> note\n\nb\n")
        self.assertTrue(ok)
        ok, why = gates.inserted_only("a\n\nb\n", "a\n\nB\n")
        self.assertFalse(ok)

    def test_ledger_chain(self):
        tmp = SESSIONS / f"test-ledger-{os.getpid()}"
        tmp.mkdir(parents=True, exist_ok=True)
        self.addCleanup(shutil.rmtree, tmp, True)
        append_ledger(tmp, "x", None, actor="t"); append_ledger(tmp, "y", None, actor="t")
        from pipeline.common import verify_chain
        self.assertEqual(verify_chain(read_ledger(tmp)), [])


if __name__ == "__main__":
    unittest.main()
