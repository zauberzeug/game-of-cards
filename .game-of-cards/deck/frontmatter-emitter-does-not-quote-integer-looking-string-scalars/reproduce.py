"""Proof that the frontmatter emitter does not quote integer-looking string
scalars, so they round-trip through emit -> parse as `int` (not `str`) and
then fail `goc validate`.

Scope note: the vendored parser only coerces strings matching `^-?\\d+$` to
int. Dates (`^\\d{4}-\\d{2}-\\d{2}$`) and floats are returned as strings, so
they round-trip fine — they are shown below as controls. The defect is
integer-looking scalars only.

Run: uv run python .game-of-cards/deck/frontmatter-emitter-does-not-quote-integer-looking-string-scalars/reproduce.py
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

from goc.engine import _yaml_inline, _emit_worker  # noqa: E402
from goc._vendor import yaml_lite  # noqa: E402


def roundtrips(value):
    emitted = _yaml_inline(value)
    parsed = yaml_lite.safe_load("x: " + emitted)["x"]
    ok = parsed == value and type(parsed) is type(value)
    print(f"  input={value!r:14} emitted={emitted!r:14} parsed={parsed!r} ({type(parsed).__name__})  round-trips={ok}")
    return ok


print("CORRUPTED — integer-looking string scalars:")
corrupted = [not roundtrips(v) for v in ("123", "007", "-3")]

print("\nCONTROLS — round-trip correctly (NOT part of this defect):")
for v in ("2026-01-01", "1.5", "rodja"):
    roundtrips(v)

print("\nRealistic worker claim — `where` from a numeric branch name (e.g. issue branch '123'):")
emitted = _emit_worker({"who": "rodja", "where": "123"})
print(f"  emitted worker value: {emitted}")
parsed = yaml_lite.safe_load("worker: " + emitted)["worker"]
print(f"  parsed worker: {parsed}")
where_ok = isinstance(parsed.get("where"), str)
print(f"  where is str? {where_ok}  ->  card would fail validate with \"worker: 'where' must be a string\": {not where_ok}")

print()
bug_present = any(corrupted) or not where_ok
print(f"BUG PRESENT (integer-looking strings do not round-trip): {bug_present}")
sys.exit(0 if bug_present else 1)
