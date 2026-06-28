"""Reproduce: the frontmatter emitter drops a leading whitespace-only line.

A block-scalar value whose first line is whitespace-only (e.g. "   ") loses
that line's interior spaces on emit->parse, because `_emit_block_field` only
emits an explicit indent indicator (`|2`) when the first NON-BLANK content
line is indented. The leading whitespace-only line is skipped by that
selection, so the parser collapses it to "" while block_indent is still None.

Exits 0 when every case round-trips losslessly; exits 1 (and prints the
failures) while the defect is present.
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

# Each value is multi-line so it routes through _emit_block_field.
CASES = [
    "   \nsecond line",   # leading whitespace-only line (the defect)
    "  \n   \nbody",      # multiple leading blank/whitespace-only lines
    "first\n   \nthird",  # interior whitespace-only line (already fixed)
    "  indented\nplain",  # first non-blank line indented (already fixed)
]

failures = []
for val in CASES:
    text = engine.emit_frontmatter({"summary": val})
    data, _ = engine.parse_frontmatter(text)
    got = data["summary"]
    status = "OK  " if got == val else "FAIL"
    print(f"{status} {val!r} -> {got!r}")
    if got != val:
        failures.append((val, got))

if failures:
    print(f"\n{len(failures)} case(s) lost content on emit->parse round-trip")
    sys.exit(1)
print("\nall block-scalar leading/interior whitespace cases round-trip")
sys.exit(0)
