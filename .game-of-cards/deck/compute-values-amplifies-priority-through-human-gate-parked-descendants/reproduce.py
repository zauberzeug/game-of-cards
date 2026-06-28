"""Reproduce: `compute_values` amplifies priority through human_gate-parked descendants.

Builds three minimal two-card decks where `A (medium) advances B (high)`, varying
B's gate state, and prints the resulting value(A) from `compute_values`. The
defect is visible by comparing:

- B parked at `human_gate: decision`  → A.value amplified (defect)
- B impeded by `waiting_on: external` → A.value pruned (fixed by closed sibling)
- B ready (`human_gate: none`)        → A.value amplified (correct)

The defect: the gated row should equal the impeded row when the
"live-AND-workable" scheduler-axis principle is extended to the third
`card_is_ready` gate (`human_gate != "none"`). Today it equals the ready row.

Exit status:
- 0 — the defect is gone (gated == impeded; the gate prune was added).
- 1 — the defect is present (gated == ready; the prune still leaks the gate axis).
"""
from __future__ import annotations

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

from goc.engine import Card, compute_values  # noqa: E402


def _mk(title: str, *, contribution: str, gate: str = "none",
        advances: list[str] | None = None, waiting_on: str | None = None) -> Card:
    fm: dict = {
        "title": title,
        "status": "open",
        "contribution": contribution,
        "human_gate": gate,
        "advances": advances or [],
        "advanced_by": [],
        "tags": [],
        "definition_of_done": "- [ ] X\n",
    }
    if waiting_on:
        fm["waiting_on"] = waiting_on
    return Card(
        title=title,
        path=Path(f"/tmp/{title}"),
        frontmatter=fm,
        body="",
        dod_open=1,
        dod_done=0,
    )


def main() -> int:
    deck_gated = [
        _mk("A", contribution="medium", advances=["B"]),
        _mk("B", contribution="high", gate="decision"),
    ]
    deck_impeded = [
        _mk("A", contribution="medium", advances=["B"]),
        _mk("B", contribution="high", waiting_on="external"),
    ]
    deck_ready = [
        _mk("A", contribution="medium", advances=["B"]),
        _mk("B", contribution="high"),
    ]

    v_gated = compute_values(deck_gated)["A"]
    v_impeded = compute_values(deck_impeded)["A"]
    v_ready = compute_values(deck_ready)["A"]

    print(f"A.value (B parked at human_gate=decision)  = {v_gated[0]:.2f}   path={v_gated[1]}")
    print(f"A.value (B impeded by waiting_on=external) = {v_impeded[0]:.2f}   path={v_impeded[1]}")
    print(f"A.value (B ready)                          = {v_ready[0]:.2f}   path={v_ready[1]}")
    print()

    own_rank = 3.0  # CONTRIBUTION_RANK["medium"]
    amplified = 9.3  # 3.0 + 0.7 * 9.0  (γ · rank("high"))

    if v_gated[0] == own_rank and v_impeded[0] == own_rank:
        print("PASS: gate-parked descendants no longer amplify ancestor priority.")
        return 0

    if v_gated[0] == amplified and v_ready[0] == amplified:
        print(
            "FAIL: a gate-parked descendant amplifies its ancestor's priority "
            "identically to a ready descendant. The third `card_is_ready` axis "
            "(`human_gate != \"none\"`) is not honored by the scheduler walk; "
            "see `goc/engine.py:2083` and `goc/engine.py:2311`."
        )
        return 1

    print(f"UNEXPECTED: gated={v_gated[0]} impeded={v_impeded[0]} ready={v_ready[0]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
