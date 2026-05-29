"""Reproduce: `goc attest` reports `advanced-by-closed` PASS on a card
whose every `advanced_by` reference is dangling (points at a title that
does not exist in the deck).

Expected output before the fix:

    passed=True  summary='all 2 closed'
    FAIL: defect reproduced — attest reports PASS on a card with zero
          real upstreams.

Expected after the fix: the function returns `passed=False` with a
message naming the missing upstream titles, and this script exits zero.
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

frontmatter = {
    "status": "active",
    "contribution": "medium",
    "human_gate": "none",
    "advanced_by": ["nonexistent-upstream-a", "nonexistent-upstream-b"],
}
card = engine.Card(
    title="dummy",
    path=Path("/tmp/dummy"),
    frontmatter=frontmatter,
    body="",
    dod_open=0,
    dod_done=0,
)
# all_cards contains only the dummy itself — both upstream titles are
# absent, i.e. dangling references.
passed, summary = engine._run_derived_check(
    {"name": "advanced-by-closed"},
    card,
    [card],
    "2026-05-29",
)
print(f"passed={passed}  summary={summary!r}")

if passed and "closed" in summary:
    print(
        "FAIL: defect reproduced — attest reports PASS on a card with "
        "zero real upstreams."
    )
    sys.exit(1)

print("OK: defect no longer fires.")
sys.exit(0)
