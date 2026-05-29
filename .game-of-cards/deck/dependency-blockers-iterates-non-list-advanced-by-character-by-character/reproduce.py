"""Reproduce: `dependency_blockers` (engine.py:1693) iterates a bare-string
`advanced_by` character-by-character and emits one phantom blocker per
character. `dependency_blocked` then returns True, treating the card as
derived-blocked even though no real upstream titles are referenced.

Same root-cause shape as the recently-fixed `compute_values` walker
(engine.py:1864) and the supersedes/superseded_by cycle walkers
(engine.py:1336, 1395), neither of which has yet been propagated to the
four read-time consumers named in this card's DoD.
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

from goc.engine import Card, dependency_blockers, dependency_blocked

victim = Card(
    title="victim",
    path=Path("/tmp/nonexistent"),
    frontmatter={
        "title": "victim",
        "status": "open",
        "advanced_by": "abc",  # bare-string scalar — the contract says list
    },
    body="",
    dod_open=1,
    dod_done=0,
)

blockers = dependency_blockers(victim, by_title={})
blocked = dependency_blocked(victim, by_title={})

print(f"dependency_blockers returned: {blockers!r}")
print(f"count: {len(blockers)}")
print(f"dependency_blocked returned: {blocked}")
