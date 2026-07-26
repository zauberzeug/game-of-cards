"""Reproduce: a symlinked card directory is listed and validated as a
first-class card, while every title-addressed verb rejects it as an
"invalid card title".

Exits non-zero while the surfaces disagree; exits 0 once they agree.
"""
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

    # Author a real card elsewhere, then symlink it into the deck.
    assert goc("new", "sym-card").returncode == 0
    elsewhere = tmp / "elsewhere-card"
    (deck / "sym-card").rename(elsewhere)
    (deck / "sym-card").symlink_to(elsewhere)

    listing = goc("--status", "all")
    listed = "sym-card" in listing.stdout
    validate = goc("validate")
    validated = validate.returncode == 0 and "sym-card" in validate.stdout
    show = goc("show", "sym-card")
    print(f"listed by queue: {listed}")
    print(f"validate says OK: {validated}")
    print(f"goc show sym-card exit={show.returncode}: {show.stderr.strip()!r}")

    verbs_accept = show.returncode == 0
    if (listed or validated) and not verbs_accept:
        failures.append(
            "read/validate surfaces treat sym-card as first-class while "
            "title-addressed verbs reject it"
        )

if failures:
    print("\n[FAIL] defect fires:")
    for f in failures:
        print(" -", f)
    sys.exit(1)
print("\n[OK] surfaces agree")
