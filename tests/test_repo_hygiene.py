"""Repo hygiene: docs list every tool, pointer files point at CLAUDE.md, secrets and media cannot be committed."""
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


class DocsSync(unittest.TestCase):
    def test_every_tool_is_registered(self):
        doc = (REPO / "docs/tools.md").read_text(encoding="utf-8")
        tools = [p for p in (REPO / "pipeline").rglob("*.py")] + list((REPO / "scripts").rglob("*.py")) + \
                [REPO / "SRT/qaqc_srt.py", REPO / "dict/load.py", REPO / "gsn.py",
                 REPO / ".claude/skills/good-student-notes/scripts/groq_transcribe.py"] + \
                [p for p in (REPO / "matrix/tools").iterdir() if p.is_file() and p.suffix in (".py", ".cjs", ".txt")]
        tools = [p for p in tools if "__pycache__" not in p.parts]
        missing = [str(p.relative_to(REPO)) for p in tools if f"`{p.relative_to(REPO)}`" not in doc]
        self.assertEqual(missing, [], "add these to docs/tools.md")

    def test_registered_tools_exist(self):
        doc = (REPO / "docs/tools.md").read_text(encoding="utf-8")
        listed = re.findall(r"`((?:pipeline|matrix/tools|scripts|SRT|dict|\.claude)/[^`]+\.(?:py|cjs|txt))`", doc)
        self.assertEqual([p for p in listed if not (REPO / p).exists()], [])

    def test_pointer_files(self):
        for f in ("AGENTS.md", "GEMINI.md"):
            self.assertEqual((REPO / f).read_text().strip(), "CLAUDE.md")

    def test_stop_at_values_documented(self):
        from pipeline.common import STOP_AT
        readme = (REPO / "README.md").read_text(encoding="utf-8")
        for v in STOP_AT:
            self.assertIn(f"--stop-at {v}", readme)

    def test_stage_prompts_exist(self):
        from pipeline.common import STAGES
        for s in STAGES:
            if "prompt" in s:
                self.assertTrue((REPO / s["prompt"]).exists(), s["prompt"])


class Upstream(unittest.TestCase):
    def test_upstream_tools_unchanged(self):
        """Field-proven study tools must stay byte-identical; changes go upstream or become a compared upgrade."""
        r = subprocess.run(["shasum", "-c", "docs/upstream.sha1"], cwd=REPO, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class Secrets(unittest.TestCase):
    def test_scanner_flags_key_and_media(self):
        from pipeline.secret_scan import scan
        with tempfile.NamedTemporaryFile("w", dir=REPO, suffix=".txt", delete=False) as f:
            f.write("GROQ_API_KEY=gsk_" + "a1B2" * 12 + "\n")
            name = Path(f.name).name
        try:
            self.assertTrue(scan([name]))
            self.assertTrue(scan(["talk.m4a"]))
            self.assertTrue(scan([".env"]))
            self.assertTrue(scan(["sessions/2026-10-21_talk/cleaned.md"]))
            self.assertFalse(scan([".env.example"]))
        finally:
            (REPO / name).unlink()

    def test_gitignore_blocks_material(self):
        for path in (".env", "sessions/x/transcript.srt", "talk.mp4", "a/b/c.m4a", "matrix/runs/x/K.json"):
            r = subprocess.run(["git", "check-ignore", "-q", path], cwd=REPO)
            self.assertEqual(r.returncode, 0, f"{path} is not gitignored")
        r = subprocess.run(["git", "check-ignore", "-q", ".env.example"], cwd=REPO)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
