"""Demonstrate session-start hook drift from engine on malformed bare waiting_until.

Defect: when a card has no `waiting_on` and a present-but-unparseable
`waiting_until`, the engine's `waiting_impedes` returns True (safety
backstop) while the hook's `_is_impeded` returns False — meaning the
hook announces the card as resumable while the queue hides it.

Run via: uv run python .game-of-cards/deck/<this-card>/reproduce.py
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

from goc import engine  # type: ignore  # noqa: E402


def _load_hook_module():
    hook_path = ROOT / "goc" / "templates" / "hooks" / "deck_session_start.py"
    spec = importlib.util.spec_from_file_location("_deck_session_start", hook_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CARD_FRONTMATTER = """---
title: hypothetical-bare-deferral-with-garbage-date
summary: ""
status: active
stage: null
contribution: low
created: "2026-05-29"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] placeholder
waiting_until: "2026-99-99"
---

# placeholder
"""


def main() -> int:
    hook = _load_hook_module()

    with tempfile.TemporaryDirectory() as tmp:
        readme = Path(tmp) / "README.md"
        readme.write_text(CARD_FRONTMATTER, encoding="utf-8")

        hook_verdict = hook._is_impeded(readme)

    card = engine.Card(
        title="hypothetical-bare-deferral-with-garbage-date",
        path=Path("/tmp/fake"),
        frontmatter={
            "status": "active",
            "human_gate": "none",
            "waiting_on": None,
            "waiting_until": "2026-99-99",
        },
        body="# placeholder\n",
        dod_open=1,
        dod_done=0,
    )
    engine_verdict = engine.waiting_impedes(card)

    print(f"engine.waiting_impedes  -> {engine_verdict}")
    print(f"hook._is_impeded        -> {hook_verdict}")
    print()

    if engine_verdict and not hook_verdict:
        print("DEFECT FIRES: engine hides the card from queues, hook announces it as resumable.")
        return 0
    print("Defect did not fire — engine and hook agree.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
