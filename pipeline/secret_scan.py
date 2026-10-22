#!/usr/bin/env python3
"""secret_scan.py — refuse to commit keys, .env files, raw media or session products.

Runs as the git pre-commit hook (installed by `python3 gsn.py doctor --fix`) and in tests.

  python3 pipeline/secret_scan.py            scan files staged for commit
  python3 pipeline/secret_scan.py --all      scan every tracked + untracked-not-ignored file
Exit 1 when anything is found.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KEY_PATTERNS = {
    "Groq key": r"gsk_[A-Za-z0-9]{20,}",
    "Google API key": r"AIza[0-9A-Za-z\-_]{35}",
    "Anthropic key": r"sk-ant-[A-Za-z0-9\-_]{20,}",
    "OpenAI key": r"sk-(?:proj-)?[A-Za-z0-9]{32,}",
    "GitHub token": r"gh[pousr]_[A-Za-z0-9]{30,}",
    "AWS access key": r"AKIA[0-9A-Z]{16}",
    "private key block": r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----",
    "assigned secret in env syntax": r"(?m)^[A-Z_]*(?:API_KEY|SECRET|TOKEN)[A-Z_0-9]*\s*=\s*['\"]?[A-Za-z0-9_\-]{16,}",
}
FORBIDDEN_PATH = re.compile(
    r"(^|/)\.env($|\.)(?!example$)|(^|/)\.secrets/|(^|/)sessions/(?!README)|(^|/)matrix/(runs|links|vault)/"
    r"|\.(mp3|m4a|wav|aac|flac|ogg|opus|mp4|mov|mkv|webm|m4v|avi)$|(^|/)credentials[^/]*\.json$|\.(pem|key|p12)$", re.I)
ALLOW = {"pipeline/secret_scan.py", "tests/test_secret_scan.py"}   # they contain the patterns themselves


def files(all_files: bool) -> list[str]:
    if all_files:
        out = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=REPO, capture_output=True, text=True).stdout
    else:
        out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"], cwd=REPO,
                             capture_output=True, text=True).stdout
    return [f for f in out.splitlines() if f]


def scan(paths: list[str]) -> list[str]:
    hits = []
    for f in paths:
        if FORBIDDEN_PATH.search(f):
            hits.append(f"{f}: forbidden path (secret, media or session product)")
            continue
        if f in ALLOW:
            continue
        p = REPO / f
        if not p.is_file() or p.stat().st_size > 5_000_000:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for name, pat in KEY_PATTERNS.items():
            m = re.search(pat, text)
            if m:
                line = text[:m.start()].count("\n") + 1
                hits.append(f"{f}:{line}: looks like a {name}")
    return hits


def main() -> int:
    hits = scan(files("--all" in sys.argv))
    for h in hits:
        print("SECRET-SCAN", h)
    if hits:
        print("secret_scan: commit refused. Move secrets to .env (gitignored); media and sessions/ never go to git.")
        return 1
    print("secret_scan: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
