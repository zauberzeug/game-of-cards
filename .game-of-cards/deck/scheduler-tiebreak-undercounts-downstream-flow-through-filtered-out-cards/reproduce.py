"""Reproduce: sort_default's tiebreak undercounts live downstream flow when
the downstream cards are filtered out of the sorted subset.

Two equal-value open cards (A advances two live cards, X advances one) should
order A-before-X by the near-term-flow tiebreak. When the live downstream
targets are hidden by a status filter, the buggy subset-scoped tiebreak scores
both at 0 and falls through to age, inverting the order.

Exits 0 when the order is correct (A first), 1 when the bug fires (X first).
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

from goc import engine  # noqa: E402


def mk(title, status, contrib, advances, created):
    fm = {
        "status": status,
        "contribution": contrib,
        "advances": advances,
        "human_gate": "none",
        "created": created,
    }
    return engine.Card(
        title=title, path=None, frontmatter=fm, body="", dod_open=0, dod_done=0
    )


def main() -> int:
    A = mk("a-open-two-live", "open", "medium",
           ["h-active-high", "l-active-low"], "2026-01-02")
    X = mk("x-open-one-live", "open", "medium",
           ["h-active-high"], "2026-01-01")
    H = mk("h-active-high", "active", "high", [], "2026-01-01")
    L = mk("l-active-low", "active", "low", [], "2026-01-01")
    full = [A, X, H, L]

    values = engine.compute_values(full)
    print("values:", {t: round(values[t][0], 1) for t in values})

    # Simulate `goc --status open`: filter to the open subset, sort with
    # full-deck values (exactly as _cmd_default does).
    open_subset = [c for c in full if c.status == "open"]
    order = [c.title for c in engine.sort_default(open_subset, values=values)]
    print("order:", order)

    full_by_title = {c.title: c for c in full}

    def live_direct(t):
        n = 0
        for dest in t.frontmatter.get("advances") or []:
            dc = full_by_title.get(dest)
            if dc and engine.card_is_workable_for_scheduler(dc):
                n += 1
        return n

    print("live_direct full deck -> A:", live_direct(A), "X:", live_direct(X))

    expected = ["a-open-two-live", "x-open-one-live"]
    if order == expected:
        print("PASS: higher-live-flow card (A) ranked first")
        return 0
    print(f"FAIL: expected {expected}, got {order} "
          "(live downstream cards filtered out -> tiebreak collapsed to 0)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
