"""Proof: the create-card skill description promises a reproduce.py stub,
but `goc new` (engine._cmd_new) writes only README.md and log.md.

Run: uv run python .game-of-cards/deck/<this-card>/reproduce.py
Exits 0 when the defect is gone (description no longer promises an
auto-scaffolded reproduce.py stub); exits 1 while the drift stands.
"""

import re
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
sys.path.insert(0, str(ROOT))

import goc.engine as engine

# The shipped description (source-of-truth template).
DESC = (ROOT / "goc" / "templates" / "skills" / "create-card" / "SKILL.md").read_text()
DESC_LINE = next(line for line in DESC.splitlines() if line.startswith("description:"))

# Match the stale promise: reproduce.py named as a `goc new` scaffold deliverable.
PROMISES_STUB = bool(re.search(r"reproduce\.py\s+stub", DESC_LINE, re.IGNORECASE))


def _files_goc_new_writes() -> list[str]:
    """Run _cmd_new into a throwaway deck and return the created file set."""
    with tempfile.TemporaryDirectory() as td:
        deck = Path(td) / "deck"
        deck.mkdir()
        # Point the engine's module-level deck globals at the temp tree.
        engine.DECK_DIR = deck
        engine.DECK_ROOT = Path(td)
        engine.REPO_ROOT = Path(td)
        title = "throwaway-bug-card-for-reproduce-proof"

        class Args:
            pass

        a = Args()
        a.title = title
        a.contribution = "low"
        a.gate = "none"
        a.tags = ["bug"]
        a.worker = None
        a.allow_jargon = False
        a.commit = False
        a.no_commit = True
        a.advances_wire = []
        a.advanced_by_wire = []
        engine._cmd_new(a)
        return sorted(p.name for p in (deck / title).iterdir())


written = _files_goc_new_writes()
stub_present = "reproduce.py" in written

print(f"description claims reproduce.py stub : {PROMISES_STUB}")
print(f"goc new --tag bug wrote files        : {written}")
print(f"reproduce.py present after goc new    : {stub_present}")

if PROMISES_STUB and not stub_present:
    print(
        "DEFECT CONFIRMED: description promises a reproduce.py stub that "
        "goc new never writes."
    )
    sys.exit(1)

print("OK: description no longer overstates goc new's scaffold output.")
sys.exit(0)
