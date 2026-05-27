"""Reproduce: sort_default's near-term-flow tiebreak counts closed/impeded
advances edges that the value walk (compute_values) deliberately prunes.

Two open `medium` cards with identical computed value: card-x advances two
`done` cards; card-y advances nothing. The tiebreak's stated purpose is
"more direct downstream cards = unblock more flow now" — but card-x's
downstream is fully closed and unblocks zero flow. A correct tiebreak (one
that mirrors the value-walk prune at engine.py:1751) would treat them as
equal and break only on `created`. The current code ranks card-x ahead
purely on its closed-edge count.
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

from goc.engine import Card, compute_values, sort_default  # noqa: E402


def mk(title, status, advances, created):
    fm = {
        "title": title,
        "status": status,
        "contribution": "medium",
        "advances": advances,
        "advanced_by": [],
        "tags": [],
        "human_gate": "none",
        "created": created,
    }
    return Card(title=title, path=None, frontmatter=fm, body="", dod_open=0, dod_done=0)


def main() -> int:
    # card-y is OLDER, so a created-only tiebreak would put it first.
    d1 = mk("d1", "done", [], "2026-01-01T00:00:00Z")
    d2 = mk("d2", "done", [], "2026-01-01T00:00:00Z")
    x = mk("card-x", "open", ["d1", "d2"], "2026-01-02T00:00:00Z")  # downstream all done
    y = mk("card-y", "open", [], "2026-01-01T00:00:00Z")            # no downstream, older

    deck = [d1, d2, x, y]
    values = compute_values(deck)
    vx = round(values.get("card-x", (0.0, []))[0], 3)
    vy = round(values.get("card-y", (0.0, []))[0], 3)

    order = [c.title for c in sort_default([y, x], values=values)]

    print(f"computed value  card-x={vx}  card-y={vy}  (equal: {vx == vy})")
    print(f"queue order     {order}")
    print(f"older card      card-y (2026-01-01) vs card-x (2026-01-02)")
    print()

    if vx != vy:
        print("INCONCLUSIVE: values differ; test setup invalid")
        return 2

    if order[0] == "card-x":
        print("DEFECT CONFIRMED: card-x ranks first despite all its advances")
        print("edges being `done` (zero live flow to unblock), and despite")
        print("card-y being older. The tiebreak counted closed edges that the")
        print("value walk at engine.py:1751 prunes from the scheduler axis.")
        return 0

    print("NO DEFECT: card-y (older, no closed-edge inflation) ranks first")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
