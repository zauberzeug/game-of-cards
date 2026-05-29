"""Reproduce: find_half_edges substring-matches a non-list inverse.

Builds an in-memory two-card deck where `acard.advances = [bcard]` is a
proper list and `bcard.advanced_by = "<substring-of-acard>"` is a bare
string. `find_half_edges` should report the asymmetric edge; instead it
returns an empty list because `"acard" in "acard-suffix-..."` is a
substring hit.

Run: `uv run python deck/<title>/reproduce.py`
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

from goc.engine import Card, find_half_edges  # noqa: E402


def _make_card(title: str, frontmatter: dict) -> Card:
    fm = {"title": title, **frontmatter}
    return Card(
        title=title,
        path=Path(f"/virtual/{title}/README.md"),
        frontmatter=fm,
        body="",
        dod_open=0,
        dod_done=0,
    )


def main() -> int:
    acard = _make_card(
        "acard",
        {"advances": ["bcard"], "advanced_by": []},
    )
    bcard = _make_card(
        "bcard",
        {"advances": [], "advanced_by": "acard-suffix-that-contains-acard"},
    )

    edges = find_half_edges([acard, bcard])
    print(f"half-edges found: {len(edges)}")
    for e in edges:
        print(f"  {e.message}")

    # Ground truth: bcard.advanced_by is a bare string, not a list, so the
    # symmetric reverse edge does NOT exist. find_half_edges SHOULD return
    # one entry for the acard→bcard direction.
    if len(edges) == 0:
        print("DEFECT: substring match silently passed the inner check.")
        print("Expected: 1 half-edge for acard.advances=[bcard] (reverse missing).")
        print("Actual:   0 half-edges (the 'acard' substring matches the bare string).")
        return 0
    print("Fix landed: half-edge correctly reported.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
