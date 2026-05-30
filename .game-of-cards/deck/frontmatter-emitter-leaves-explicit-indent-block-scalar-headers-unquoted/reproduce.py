"""Reproduce: explicit-indent block-scalar headers (`|2`, `|3`, `|10`,
`|2-`, `|2+`) emitted bare by `emit_frontmatter` are silently parsed
back as empty strings — the parser reads the bare token as a literal
block scalar with the indicated indent and empty content.

Exits 0 if every probe value survives the emit -> parse round-trip
unchanged (defect fixed). Exits 1 otherwise (defect fires).
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

PROBES = ["|2", "|3", "|2-", "|2+", "|10"]

failures = 0
for value in PROBES:
    fm = {"title": "foo", "summary": value}
    emitted = emit_frontmatter(fm)
    summary_line = next(
        line for line in emitted.splitlines() if line.startswith("summary:")
    )
    parsed, _ = parse_frontmatter(emitted)
    got = parsed.get("summary")
    print(f"=== {value!r} ===")
    print(f"  emitted line: {summary_line!r}")
    if got == value:
        print(f"  round-trip OK: {got!r}")
    else:
        print(f"  round-trip got: {got!r} (lost original value)")
        failures += 1

sys.exit(1 if failures else 0)
