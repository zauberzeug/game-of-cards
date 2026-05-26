"""Reproduce: compute_values amplifies a live card's priority through an
impeded (waiting_on) descendant that is hidden from the pull queue.

Builds a minimal deck `A (low) advances B (high)` and shows that an
`open` B carrying an active impediment overlay (hidden from the queue
by card_is_ready) still amplifies A's GRPW value, whereas a terminal B
correctly does not.

Exits 0 once the defect is fixed (impeded descendants no longer amplify
ancestor value), 1 while the defect is present.
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


def mk(title, contribution, status="open", advances=None,
       waiting_on=None, waiting_until=None):
    fm = {
        "title": title,
        "contribution": contribution,
        "status": status,
        "advances": advances or [],
        "advanced_by": [],
        "human_gate": "none",
        "tags": [],
    }
    if waiting_on is not None:
        fm["waiting_on"] = waiting_on
    if waiting_until is not None:
        fm["waiting_until"] = waiting_until
    return engine.Card(
        title=title, path=None, frontmatter=fm,
        body="", dod_open=0, dod_done=0,
    )


def value_of_A_with(b_card):
    a = mk("A", "low", advances=["B"])
    vals = engine.compute_values([a, b_card])
    return round(vals["A"][0], 3)


def main() -> int:
    b_impeded = mk("B", "high", status="open",
                   waiting_on="external", waiting_until="2027-01-01")
    b_done = mk("B", "high", status="done")
    b_workable = mk("B", "high", status="open")

    a_impeded = value_of_A_with(b_impeded)
    a_done = value_of_A_with(b_done)
    a_workable = value_of_A_with(b_workable)

    b_hidden = not engine.card_is_ready(b_impeded, {"B": b_impeded})

    print(f"B impeded (waiting_until 2027): A.value = {a_impeded}  | B hidden from queue: {b_hidden}")
    print(f"B terminal (done):              A.value = {a_done}")
    print(f"B workable (open, no overlay):  A.value = {a_workable}")

    # Contract: the scheduler axis is live-and-workable only. An impeded,
    # queue-hidden descendant must NOT amplify the ancestor (it should
    # behave like a terminal descendant). A genuinely workable descendant
    # SHOULD still amplify.
    own_rank = engine.CONTRIBUTION_RANK["low"]  # A's bare rank == 1.0

    if not b_hidden:
        print("\nPRECONDITION FAILED: impeded B is not hidden from the queue; "
              "card_is_ready/waiting_impedes changed — revisit this card.")
        return 1

    if a_workable <= own_rank:
        print("\nPRECONDITION FAILED: a workable descendant does not amplify; "
              "value composition changed — revisit this card.")
        return 1

    if a_impeded > own_rank:
        print(f"\nDEFECT PRESENT: impeded-and-hidden descendant amplifies "
              f"A's priority to {a_impeded} (bare rank {own_rank}); it should "
              f"be pruned from the value walk like the terminal descendant "
              f"(which yields {a_done}).")
        return 1

    print(f"\nFIXED: impeded descendant pruned — A.value collapses to its "
          f"bare rank {a_impeded}, matching the terminal case ({a_done}); "
          f"workable descendant still amplifies ({a_workable}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
