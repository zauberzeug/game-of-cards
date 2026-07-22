"""Reproduce: goc new accepts a title with a trailing newline and
scaffolds a card directory literally named 'newline-tail\\n'.

Exits non-zero while the defect fires; exits 0 once fixed.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
BAD_TITLE = "newline-tail\n"

failures = []

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    subprocess.run(["git", "init", "-q", str(tmp)], check=True)
    deck = tmp / ".game-of-cards" / "deck"
    deck.mkdir(parents=True)

    def goc(*args):
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=tmp, capture_output=True, text=True,
            env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"},
        )

    new = goc("new", BAD_TITLE)
    print(f"goc new {BAD_TITLE!r} exit={new.returncode} (want 2)")
    if new.returncode == 0:
        entries = os.listdir(deck)
        print(f"deck entries: {entries!r}")
        if BAD_TITLE in entries:
            failures.append(f"card dir literally named {BAD_TITLE!r} exists on disk")
        show = goc("show", BAD_TITLE.strip())
        print(f"goc show {BAD_TITLE.strip()!r} exit={show.returncode} "
              "(card is unaddressable by its visible name)")
        if show.returncode != 0:
            failures.append("visible name does not address the card")
        validate = goc("validate")
        print(f"goc validate exit={validate.returncode} (certifies the malformed title as OK)")
        if validate.returncode == 0:
            failures.append("goc validate reports OK for the trailing-newline title")

if failures:
    print("\n[FAIL] defect fires:")
    for f in failures:
        print(" -", f)
    sys.exit(1)
print("\n[OK] defect no longer fires")
