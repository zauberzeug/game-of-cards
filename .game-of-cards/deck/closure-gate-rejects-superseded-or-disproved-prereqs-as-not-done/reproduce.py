"""Reproduce: the `advanced-by-closed` closure gate counts a superseded or
disproved upstream prereq as "not done", while every other predicate over
the same `advanced_by` edge (dependency_blockers / the scheduler prune)
treats it as resolved.

Run: uv run python .game-of-cards/deck/closure-gate-rejects-superseded-or-disproved-prereqs-as-not-done/reproduce.py
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


def make_card(title: str, status: str, advanced_by=None) -> engine.Card:
    fm = {
        "title": title,
        "status": status,
        "advanced_by": advanced_by or [],
        "advances": [],
        "human_gate": "none",
        "contribution": "medium",
    }
    return engine.Card(
        title=title,
        path=Path(f"/nonexistent/{title}"),
        frontmatter=fm,
        body="",
        dod_open=0,
        dod_done=0,
    )


def closure_gate(card: engine.Card, all_cards: list) -> tuple[bool, str]:
    # Invoke the REAL engine closure check so the reproducer tracks the
    # shipped code, not a copy.
    return engine._run_derived_check(
        {"name": "advanced-by-closed"}, card, all_cards, "2026-05-27"
    )


def main() -> int:
    print(f"TERMINAL_STATUSES = {sorted(engine.TERMINAL_STATUSES)}\n")

    failures = 0
    for upstream_status in ("superseded", "disproved", "done"):
        upstream = make_card("X-upstream", upstream_status)
        downstream = make_card("Y-downstream", "open", advanced_by=["X-upstream"])
        all_cards = [upstream, downstream]
        by_title = {c.title: c for c in all_cards}

        blockers = engine.dependency_blockers(downstream, by_title)
        gate_ok, gate_msg = closure_gate(downstream, all_cards)

        print(f"upstream X status = {upstream_status!r}")
        print(f"  dependency_blockers(Y) = {blockers}  (empty => display says 'awaiting: nothing')")
        print(f"  closure gate(Y)        = {gate_ok}  ({gate_msg})")

        # The defect: when X is terminal-but-not-done, the advisory predicate
        # says resolved (no blockers) but the closure gate says not done.
        advisory_resolved = not blockers
        if advisory_resolved and not gate_ok:
            print("  >>> INCONSISTENT: display says resolved, closure gate blocks\n")
            failures += 1
        else:
            print("  consistent\n")

    if failures:
        print(f"DEFECT CONFIRMED: {failures} terminal status(es) treated as resolved by "
              f"dependency_blockers but rejected by the closure gate.")
        return 1
    print("No inconsistency (defect fixed).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
