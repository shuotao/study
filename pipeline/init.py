#!/usr/bin/env python3
"""init.py — environment doctor behind `/init` and `python3 gsn.py doctor`.

Checks (never prints a key's value):
  required  Python >= 3.10, requests, ffmpeg, .env with GROQ_API_KEY, git pre-commit secret hook
  phase 6   playwright + chromium (page gates), node + matrix/vendor/dagre (diagram layout)
  optional  opencc (Simplified-drift fix), agent CLIs (claude / gemini / codex / copilot / agy)
--fix creates .env from .env.example, installs the hook, pip-installs Python packages,
      runs `npm ci` for dagre and `playwright install chromium`.
--check-key makes one request to Groq's model list to prove the key works.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FIX = "--fix" in sys.argv
rows: list[tuple[str, str, str]] = []


def row(level: str, name: str, ok: bool, hint: str = "") -> bool:
    rows.append(("OK" if ok else level, name, "" if ok else hint))
    return ok


def has_module(m: str) -> bool:
    try:
        __import__(m)
        return True
    except ImportError:
        return False


def pip(*pkgs: str) -> None:
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", *pkgs])


def env_value(key: str) -> str:
    env = REPO / ".env"
    if not env.exists():
        return ""
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith(key + "=") or line.strip().startswith(key + " ="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def main() -> int:
    row("FAIL", f"python {sys.version.split()[0]} >= 3.10", sys.version_info >= (3, 10), "install Python 3.10+")
    try:                                     # macOS privacy (TCC): Desktop/Documents need Terminal access
        probe = REPO / ".gsn_write_probe"
        probe.write_text("x"); probe.unlink()
        row("FAIL", "repo folder writable", True)
    except OSError:
        row("FAIL", "repo folder writable", False,
            "macOS: System Settings → Privacy & Security → Files and Folders (or Full Disk Access) → allow your terminal")

    if not has_module("requests") and FIX:
        pip("requests")
    row("FAIL", "python: requests", has_module("requests"), "pip install -r requirements.txt")
    row("FAIL", "ffmpeg", bool(shutil.which("ffmpeg")), "macOS: brew install ffmpeg · Windows: winget install ffmpeg · Linux: apt install ffmpeg")

    env, example = REPO / ".env", REPO / ".env.example"
    if not env.exists() and FIX and example.exists():
        shutil.copyfile(example, env)
        os.chmod(env, 0o600)
    row("FAIL", ".env exists (gitignored)", env.exists(), "cp .env.example .env  (or: python3 gsn.py doctor --fix)")
    key = env_value("GROQ_API_KEY")
    row("FAIL", "GROQ_API_KEY set in .env", bool(key), "README §1: create a key at console.groq.com → API Keys, paste it into .env")
    if key and "--check-key" in sys.argv and has_module("requests"):
        import requests
        try:
            r = requests.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=20)
            row("FAIL", "GROQ_API_KEY accepted by Groq", r.status_code == 200, f"HTTP {r.status_code} — key wrong or revoked")
        except Exception as e:  # network problems are reported, not fatal
            row("WARN", "GROQ_API_KEY accepted by Groq", False, f"network: {e}")

    hooks = subprocess.run(["git", "config", "core.hooksPath"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    if hooks != ".githooks" and FIX and (REPO / ".githooks/pre-commit").exists():
        subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=REPO)
        hooks = ".githooks"
    row("FAIL", "pre-commit secret scan hook", hooks == ".githooks", "python3 gsn.py doctor --fix")

    if not has_module("playwright") and FIX:
        pip("playwright")
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])
    row("WARN", "phase 6: playwright (page gates)", has_module("playwright"),
        "pip install playwright && python3 -m playwright install chromium")
    dagre = REPO / "matrix/vendor/dagre/node_modules/dagre"
    if not dagre.exists() and FIX and shutil.which("npm"):
        subprocess.run(["npm", "ci", "--ignore-scripts", "--silent"], cwd=REPO / "matrix/vendor/dagre")
    row("WARN", "phase 6: node + dagre (diagram layout; fallback layout without it)",
        bool(shutil.which("node")) and dagre.exists(), "install Node.js, then python3 gsn.py doctor --fix")

    if not has_module("opencc") and FIX:
        pip("opencc-python-reimplemented")
    row("WARN", "optional: opencc (Simplified-drift fix, Phase 2 glyph check)", has_module("opencc"),
        "pip install opencc-python-reimplemented")
    clis = [c for c in ("claude", "gemini", "codex", "copilot", "agy") if shutil.which(c)]
    row("WARN", f"agent CLI available ({', '.join(clis) or 'none'})", bool(clis),
        "install at least one: Claude Code, Gemini CLI, Codex CLI, Copilot CLI or Antigravity (README §4)")

    width = max(len(r[1]) for r in rows)
    for level, name, hint in rows:
        print(f"{level:4}  {name:<{width}}  {hint}")
    bad = sum(1 for r in rows if r[0] == "FAIL")
    print(f"\ndoctor: {len(rows) - bad}/{len(rows)} ok" + ("" if not bad else " — fix the FAIL lines (try --fix)"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
