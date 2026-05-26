"""Reproduce: emit_frontmatter does not quote string values that the
vendored parser coerces to int / None / bool, so they lose their type
on a single emit->parse round-trip.

Exit 0 == every string value round-trips unchanged (defect fixed).
Exit 1 == at least one string value changed type (defect fires).
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

# String values the vendored parser coerces: ints, null-variants,
# case-variant booleans. Each is a legitimate free-form string field value.
cases = ["123", "02", "-5", "~", "NULL", "Null",
         "True", "TRUE", "Yes", "NO", "FALSE", "2026-01-01"]

failures = 0
for s in cases:
    fm = {"title": "t", "summary": s}
    text = engine.emit_frontmatter(fm, body="")
    back, _ = engine.parse_frontmatter(text)
    got = back.get("summary")
    ok = got == s and type(got) is str
    flag = "OK  " if ok else "LOSS"
    if not ok:
        failures += 1
    print(f"{flag}: summary={s!r:14} -> {got!r} ({type(got).__name__})")

print()
if failures:
    print(f"DEFECT: {failures}/{len(cases)} string values changed type on round-trip")
    sys.exit(1)
print("OK: every string value round-tripped unchanged")
sys.exit(0)
