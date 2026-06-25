"""Reproduce: emit_frontmatter drops trailing blank lines from multi-line
string fields because it never selects the `|+` (keep) chomp indicator.

A multi-line string value ending in a *blank line* (two-or-more trailing
newlines) is emitted with bare `|` (clip), which the parser reads back with
exactly one trailing newline — silently discarding the blank line(s) on the
first frontmatter re-emit by any mutation verb (goc wait / decide / advance /
migrate-list-style). The vendored parser already supports `|+`; only the emit
side never picks it.

The values below carry a following field (`status`/`tags`) so the multi-line
field is bounded by a sibling key — the realistic frontmatter shape, since a
multi-line `summary` is never the last frontmatter field. (A keep block placed
immediately before the closing `---` hits a *separate* parse-boundary defect in
FRONTMATTER_RE + safe_load that this card does not address.)

Exits 0 when the round-trip is faithful for every case (defect fixed);
exits 1 while the defect fires.
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

from goc.engine import emit_frontmatter, parse_frontmatter  # noqa: E402

# Each value is a realistic multi-line `summary:` that ends in a blank line.
CASES = [
    "foo\n\n",
    "first line\nsecond line\n\n",
    "para one\n\npara two\n\n",
    "x\n\n\n",  # two trailing blank lines
    "  indented first line\nmore\n\n",  # forces the |2+ explicit-indent + keep
]

failures = []
for value in CASES:
    # `status`/`tags` follow `summary`, so the block is bounded by a sibling
    # key — exactly how a real card's frontmatter is shaped.
    fm = {"title": "x", "summary": value, "status": "open", "tags": ["bug"]}
    text = emit_frontmatter(fm)
    parsed, _body = parse_frontmatter(text)
    back = parsed.get("summary")
    ok = back == value
    print(f"{value!r:40} -> {back!r:40} {'OK' if ok else 'LOST'}")
    if not ok:
        failures.append((value, back))

print()
if failures:
    print(f"FAIL: {len(failures)}/{len(CASES)} multi-line values lost trailing blank lines on round-trip")
    print("Emitted frontmatter for the first failing case:")
    print(emit_frontmatter({"title": "x", "summary": failures[0][0], "status": "open"}))
    sys.exit(1)

print(f"OK: all {len(CASES)} values round-trip faithfully")
sys.exit(0)
