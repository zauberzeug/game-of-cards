"""Reproducer: SessionStart hook `_is_impeded` vs engine `waiting_impedes`.

The engine treats an elapsed `waiting_until` as re-surfacing the card even
when a `waiting_on` reason is set (engine.py:1763-1765 / 1797-1798). The
hook short-circuits on `waiting_on` and never inspects `waiting_until`, so
Case A diverges.
"""

from __future__ import annotations

import importlib.util
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

from goc import engine

spec = importlib.util.spec_from_file_location(
    "deck_session_start", ROOT / "goc/templates/hooks/deck_session_start.py"
)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


def scenario(label: str, frontmatter: str) -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        card_dir = Path(tmp) / "test-card"
        card_dir.mkdir()
        readme = card_dir / "README.md"
        readme.write_text(f"---\n{frontmatter}\n---\nbody\n", encoding="utf-8")

        hook_says = hook._is_impeded(readme)
        card = engine.load_card(card_dir)
        engine_says = engine.waiting_impedes(card)

        diverged = hook_says != engine_says
        print(label)
        print(f"  hook  _is_impeded     : {hook_says}")
        print(f"  engine waiting_impedes: {engine_says}")
        print(f"  DIVERGED               : {diverged}")
        print()
        return diverged


BASE = (
    "title: test-card\nstatus: active\nhuman_gate: none\n"
    "advances: []\nadvanced_by: []\ntags: []\n"
    "contribution: medium\ncreated: 2026-05-29"
)

div_a = scenario(
    "Case A: waiting_on=external, waiting_until=2000-01-01 (ELAPSED)",
    f"{BASE}\nwaiting_on: external\nwaiting_until: 2000-01-01",
)
div_b = scenario(
    "Case B: waiting_on=external, waiting_until=2099-01-01 (FUTURE)",
    f"{BASE}\nwaiting_on: external\nwaiting_until: 2099-01-01",
)
div_c = scenario(
    "Case C: waiting_on=external only",
    f"{BASE}\nwaiting_on: external",
)
div_d = scenario(
    "Case D: waiting_until=2000-01-01 only (ELAPSED)",
    f"{BASE}\nwaiting_until: 2000-01-01",
)

# Defect signature: Case A diverges, B/C/D agree.
assert div_a, "Expected Case A to diverge (hook over-reports impediment)"
assert not div_b, "Case B should agree (both impeded)"
assert not div_c, "Case C should agree (both impeded)"
assert not div_d, "Case D should agree (both not impeded)"

print("Defect reproduced: only Case A diverges (elapsed waiting_until + waiting_on).")
