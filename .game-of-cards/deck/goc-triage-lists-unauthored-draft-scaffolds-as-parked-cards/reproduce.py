"""Reproduce: `goc triage` leaks unauthored draft scaffolds that every
other listing surface hides.

A card filed by `goc new <title> --gate decision` is `open` +
`human_gate: decision` + `draft: true`. The canonical `filter_cards`
path (queue / --status / board / json) hides it via `card_is_draft`;
`_cmd_triage` (engine.py:5965) hand-rolls its own filter that omits the
draft exclusion, so it surfaces the scaffold as a parked card.

Exits non-zero while the defect is present (triage leaks the draft),
zero once `_cmd_triage` consults `card_is_draft`.
"""

import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc.engine import Card, card_is_draft, filter_cards  # noqa: E402

# The exact shape `goc new <title> --gate decision` produces.
card = Card(
    title="draft-card-needs-a-decision",
    path=Path("draft-card-needs-a-decision"),
    frontmatter={
        "title": "draft-card-needs-a-decision",
        "status": "open",
        "human_gate": "decision",
        "draft": True,
        "contribution": "medium",
        "created": "2026-06-30",
    },
    body="",
    dod_open=0,
    dod_done=0,
)

print(f"card_is_draft: {card_is_draft(card)} | status: {card.status} | gate: {card.human_gate}")

# Canonical listing path (queue / board / json) — hides drafts.
via_filter = [c.title for c in filter_cards([card], status="open", human_gate="decision")]
print(f"filter_cards (queue/board/json) shows: {via_filter}")

# `_cmd_triage` candidate filter, engine.py:5965 — current behavior.
# Mirror whatever the engine does so this tracks the real code: the fix
# adds `and not card_is_draft(t)` to that comprehension.
import inspect  # noqa: E402

from goc import engine  # noqa: E402

triage_src = inspect.getsource(engine._cmd_triage)
triage_excludes_drafts = "card_is_draft" in triage_src.split("def aged_days")[0]

via_triage = [
    c.title
    for c in [card]
    if c.status == "open"
    and c.human_gate != "none"
    and (not card_is_draft(c) if triage_excludes_drafts else True)
]
print(f"triage filter (engine.py:_cmd_triage) shows: {via_triage}")

if via_triage:
    print("\nFAIL: triage surfaces an unauthored draft that filter_cards hides.")
    sys.exit(1)

print("\nPASS: triage hides the draft, consistent with every other surface.")
sys.exit(0)
