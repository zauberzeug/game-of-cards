"""Reproduce: an ISO-shaped but calendar-impossible TIME in `waiting_until`
passes `_is_iso_date` (so `goc validate` green-lights it) yet crashes the
read-time guard `waiting_impedes` with an uncaught ValueError.

Exits 0 once the defect is FIXED (impossible time rejected by the predicate
and `waiting_impedes` returns a bool); exits 1 while the defect is present.
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

from goc import engine
from goc.engine import Card, waiting_impedes

BAD = "2026-05-20T25:61:99Z"  # valid date prefix, impossible time (25:61:99)

predicate = engine._is_iso_date(BAD)
print(f"_is_iso_date({BAD!r})      = {predicate}    (EXPECTED False)")

instant_raised = None
try:
    engine._waiting_until_instant(BAD)
    instant_msg = "returned without raising"
except ValueError as e:
    instant_raised = e
    instant_msg = f"RAISED ValueError: {e}"
print(f"_waiting_until_instant(...)                 -> {instant_msg}")

card = Card(
    title="x",
    path=None,
    frontmatter={
        "title": "x",
        "status": "open",
        "human_gate": "none",
        "waiting_until": BAD,
    },
    body="",
    dod_open=0,
    dod_done=0,
)

impede_raised = None
try:
    result = waiting_impedes(card)
    impede_msg = f"returned {result!r}"
except ValueError as e:
    impede_raised = e
    impede_msg = "RAISED ValueError (EXPECTED a bool)"
print(f"waiting_impedes(card with that until)       -> {impede_msg}")

defect_present = predicate is True or impede_raised is not None

if defect_present:
    print(
        "DEFECT CONFIRMED: validator accepts an impossible time the "
        "read-time guard then crashes on."
    )
    sys.exit(1)

print("FIXED: impossible time rejected by the predicate and waiting_impedes is total.")
sys.exit(0)
