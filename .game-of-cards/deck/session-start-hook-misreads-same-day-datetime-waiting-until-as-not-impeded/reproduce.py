"""Reproducer: SessionStart hook `_is_impeded` vs engine `waiting_impedes` on
the same-day datetime cells of the `waiting_on` × `waiting_until` matrix.

The engine compares `waiting_until` at full UTC timestamp precision since the
datetime-shape extension (`engine._waiting_until_instant`, `engine.py:724-751`;
`waiting_impedes`, `engine.py:1767-1798`). The hook truncates to the leading
10 chars and compares dates only (`deck_session_start.py:107`). When a card
carries a same-day future datetime `waiting_until` (e.g. `<today>T23:59:59Z`
at 09:00Z), the engine reports impeded but the hook reports not-impeded —
the session-start banner frames the card as resumable even though
`goc --ready` won't list it.

This script captures the divergence on three cells:

  Case A: waiting_on set, waiting_until = <today>T23:59:59Z   → DIVERGES
  Case B: waiting_on set, waiting_until = <today>T00:00:00Z   → agrees (elapsed)
  Case C: waiting_until = <today>T23:59:59Z (no reason)       → DIVERGES

Cases A and C are the new shapes the datetime-precision engine extension
introduced; the hook's "date-level coarseness suffices" assumption (carried
forward from commit c191410) breaks for both.

Run via `uv run python deck/<this-card>/reproduce.py`.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
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


# Pick a `waiting_until` strictly in the future-of-now but same UTC civil day.
# If we're already past 23:59:30Z, the case is unreachable today — fall back
# to tomorrow's 23:59:59Z (still a same-day-future scenario when the engine
# evaluates it at "today" = `now`-derived).
now = datetime.now(tz=timezone.utc)
today_iso = now.date().isoformat()
future_same_day = f"{today_iso}T23:59:59Z"
if datetime.strptime(future_same_day, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) <= now:
    # Vanishingly small edge — fall back to a clearly-future same-second offset.
    bumped = (now + timedelta(minutes=1)).replace(microsecond=0)
    future_same_day = bumped.strftime("%Y-%m-%dT%H:%M:%SZ")
midnight_today = f"{today_iso}T00:00:00Z"


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
    f"Case A: waiting_on=external, waiting_until={future_same_day} (FUTURE, same civil day)",
    f"{BASE}\nwaiting_on: external\nwaiting_until: {future_same_day}",
)
div_b = scenario(
    f"Case B: waiting_on=external, waiting_until={midnight_today} (ELAPSED at start of today)",
    f"{BASE}\nwaiting_on: external\nwaiting_until: {midnight_today}",
)
div_c = scenario(
    f"Case C: waiting_until={future_same_day} only (deferred, FUTURE same civil day)",
    f"{BASE}\nwaiting_until: {future_same_day}",
)

# Pre-fix invariant: same-day future datetime diverges in cases A and C.
assert div_a, "Case A should DIVERGE pre-fix (hook says not impeded, engine says impeded)"
assert not div_b, "Case B agrees (both not impeded — elapsed instant resurfaces)"
assert div_c, "Case C should DIVERGE pre-fix (hook says not impeded, engine says impeded)"

print(
    "Pre-fix: same-day future datetime `waiting_until` makes the hook disagree "
    "with the engine on 2 of 3 sampled cells."
)
