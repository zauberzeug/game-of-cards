"""Reproduce: compute_values inherits value through terminal-status descendants.

An open `low` card A with `advances: [B]` where B is `done high` scores
`1.0 + 0.7*9.0 = 7.3` today, outranking a genuinely-open `medium` (3.0)
purely on the strength of work that is already complete and can no longer
be unblocked.

Decision (2026-05-26): the scheduler axis walks `advances` edges across
*live* cards only (AGENTS.md "deck as scheduler vs record" contract).
Terminal descendants belong to the record axis and must NOT contribute to
the scheduling value.

Exit 0 == A scores its bare rank (1.0, ["self"]) — terminal descendant
          excluded from the scheduler value (defect fixed).
Exit 1 == A inherits B's value (defect fires).
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


def _card(title: str, contribution: str, status: str, advances: list[str]) -> engine.Card:
    return engine.Card(
        title=title,
        path=Path(title),
        frontmatter={
            "title": title,
            "contribution": contribution,
            "status": status,
            "human_gate": "none",
            "advances": advances,
        },
        body="",
        dod_open=0,
        dod_done=0,
    )


failures = 0

# Case 1: open low A → done high B. A must score its bare rank.
a = _card("A", "low", "open", ["B"])
b = _card("B", "high", "done", [])
values = engine.compute_values([a, b])
a_value, a_path = values["A"]
expected = (1.0, ["self"])
ok = (round(a_value, 4), a_path) == expected
print(f"open->done:       A={a_value!r} path={a_path!r}  expected={expected!r}  {'OK' if ok else 'DEFECT'}")
if not ok:
    failures += 1

# Case 2: open low A → superseded high B. Same rule.
a2 = _card("A", "low", "open", ["B"])
b2 = _card("B", "high", "superseded", [])
values2 = engine.compute_values([a2, b2])
a2_value, a2_path = values2["A"]
ok2 = (round(a2_value, 4), a2_path) == expected
print(f"open->superseded: A={a2_value!r} path={a2_path!r}  expected={expected!r}  {'OK' if ok2 else 'DEFECT'}")
if not ok2:
    failures += 1

# Case 3: a live descendant STILL contributes (the fix must not over-prune).
a3 = _card("A", "low", "open", ["B"])
b3 = _card("B", "high", "open", [])
values3 = engine.compute_values([a3, b3])
a3_value, a3_path = values3["A"]
expected3 = (round(1.0 + 0.7 * 9.0, 4), ["B", "self"])
ok3 = (round(a3_value, 4), a3_path) == expected3
print(f"open->open:       A={a3_value!r} path={a3_path!r}  expected={expected3!r}  {'OK' if ok3 else 'DEFECT'}")
if not ok3:
    failures += 1

print()
if failures:
    print(f"DEFECT: {failures}/3 cases wrong — terminal descendants leak into scheduler value")
    sys.exit(1)
print("OK: terminal descendants excluded from scheduler value; live descendants still contribute")
sys.exit(0)
