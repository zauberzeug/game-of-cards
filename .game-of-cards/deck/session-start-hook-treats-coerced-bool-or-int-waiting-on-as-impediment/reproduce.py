"""Reproduce: session-start hook over-fires "impeded" for parser-coerced
bool/int `waiting_on` values that the engine resolves to None.

The engine's `Card.waiting_on` property gates on `isinstance(v, str)`, so a
`waiting_on` value the yaml-lite parser coerces to bool/int (`false`, `true`,
`yes`, `no`, `42`) resolves to None — the card is NOT impeded. The two hook
re-implementations keep the raw token string (`"false"`) and, since the
just-closed sibling widened them to "any non-empty reason impedes", report the
card impeded. Engine and hooks disagree.

Run: uv run python .game-of-cards/deck/<this-card>/reproduce.py
Exits 0 when the divergence is gone (fix applied); 1 while it reproduces.
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

from goc import engine  # noqa: E402

# Load the hook module from its template path (the shipped source of truth).
_HOOK_PATH = ROOT / "goc" / "templates" / "hooks" / "deck_session_start.py"
_spec = importlib.util.spec_from_file_location("_goc_session_start", _HOOK_PATH)
_hook = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(_hook)


CARD = """---
title: demo-card
status: active
contribution: medium
human_gate: none
waiting_on: {value}
tags: []
---

# Demo

## Definition of Done
- [ ] x
"""

# Every value the yaml-lite parser coerces away from `str`.
COERCED_VALUES = ["false", "true", "yes", "no", "42"]


def main() -> int:
    diverged = []
    with tempfile.TemporaryDirectory() as td:
        deck = Path(td) / ".game-of-cards" / "deck"
        for i, value in enumerate(COERCED_VALUES):
            card_dir = deck / f"card-{i}"
            card_dir.mkdir(parents=True)
            readme = card_dir / "README.md"
            readme.write_text(CARD.format(value=value), encoding="utf-8")

            card = engine.load_card(card_dir)
            engine_impeded = engine.waiting_impedes(card)
            hook_impeded = _hook._is_impeded(readme)

            print(
                f"waiting_on: {value!r:>8} | "
                f"engine.waiting_impedes={engine_impeded!s:>5} | "
                f"hook._is_impeded={hook_impeded!s:>5} | "
                f"card.waiting_on={card.waiting_on!r}"
            )
            if engine_impeded != hook_impeded:
                diverged.append(value)

    print()
    if diverged:
        print(
            "DIVERGENCE: hook reports impeded but engine does not for "
            f"coerced values {diverged}. Defect reproduces."
        )
        return 1
    print("No divergence: engine and hook agree across coerced values. Fixed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
