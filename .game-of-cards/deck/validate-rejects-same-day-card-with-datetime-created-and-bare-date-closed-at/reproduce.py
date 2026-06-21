#!/usr/bin/env python3
"""Reproduce: validate flags a same-day card with datetime `created` + bare-date `closed_at`.

Exits non-zero while the defect is live (false-positive ordering error on a
same-day card), zero once the ordering check compares at day granularity when
either operand is a bare date — while still rejecting genuine inversions.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from goc import engine


_SCHEMA = engine.load_schema()


def _card(created, closed_at):
    fm = {
        "title": "demo",
        "status": "done",
        "stage": None,
        "contribution": "medium",
        "created": created,
        "closed_at": closed_at,
        "human_gate": "none",
        "advances": [],
        "advanced_by": [],
        "tags": [],
        "definition_of_done": "- [x] done\n",
    }
    return engine.Card(
        title="demo",
        path=Path("demo"),
        frontmatter=fm,
        body="# demo\n",
        dod_open=0,
        dod_done=1,
    )


def ordering_errors(created, closed_at):
    errs = engine.validate_card(_card(created, closed_at), _SCHEMA, {"demo"})
    return [e for e in errs if "predates created" in e]


# 1. The false positive: datetime created, same-day bare-date closed.
same_day_dt_created = ordering_errors("2026-06-10T20:00:00Z", "2026-06-10")
# 2. Inverse mix the predecessor's comment claims to handle.
same_day_dt_closed = ordering_errors("2026-06-10", "2026-06-10T20:00:00Z")
# 3. Genuine inversion: closed a strictly-earlier day than created.
earlier_day = ordering_errors("2026-06-10T20:00:00Z", "2026-06-09")
# 4. Genuine both-datetime intra-day inversion (predecessor's case).
intra_day = ordering_errors("2026-06-10T20:00:00Z", "2026-06-10T08:00:00Z")

print(f"same-day (datetime created, bare-date closed): {same_day_dt_created}")
print(f"same-day (bare-date created, datetime closed): {same_day_dt_closed}")
print(f"earlier-day bare-date closed (must reject):    {earlier_day}")
print(f"both-datetime intra-day inversion (must reject): {intra_day}")

ok = (
    not same_day_dt_created  # must be accepted
    and not same_day_dt_closed  # must be accepted
    and earlier_day  # must be rejected
    and intra_day  # must be rejected
)

if ok:
    print("\nPASS: same-day mixed-granularity accepted; genuine inversions rejected")
    sys.exit(0)
print("\nFAIL: defect live — same-day card spuriously rejected as closed-before-created")
sys.exit(1)
