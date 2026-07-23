#!/usr/bin/env python3
"""Prove mutate_frontmatter_field's field-absent append truncates a final
`|+` keep block scalar.

FRONTMATTER_RE deliberately captures the blank-line run before the closing
`---` in group(2) so a final keep scalar retains its trailing blank line
(engine.py:155-160). The append branch (engine.py:487-488) splices the new
`field: value` line between group(1) and that blank run, so after the write
the blank run belongs to the new flat field (where yaml_lite ignores it)
instead of the keep scalar — the scalar reads back one blank line short,
and validate passes before AND after.

Reachable via `goc status <title> active` on a worker-less card
(_auto_populate_worker → mutate_frontmatter_field(text, "worker", ...),
engine.py:5221) and via closed_at stamping on a hand-authored card lacking
the key (engine.py:4270, 5310).

Exits 0 iff the defect fires (data loss observed).
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

from goc.engine import mutate_frontmatter_field, parse_frontmatter  # noqa: E402

# A card whose LAST frontmatter field is a |+ keep scalar whose value ends
# with a blank line — exactly the shape FRONTMATTER_RE's group(2) exists to
# protect — and which has no `worker` field yet.
text = "---\ntitle: t\nsummary: |+\n  ends with a blank line.\n\n---\nbody\n"

before, _ = parse_frontmatter(text)
print(f"summary before mutation: {before['summary']!r}")

mutated = mutate_frontmatter_field(text, "worker", "{who: probe, where: main}")
print(f"mutated file:\n{mutated}")

after, _ = parse_frontmatter(mutated)
print(f"summary after mutation:  {after['summary']!r}")

if before["summary"] == after["summary"]:
    print("NOT REPRODUCED: keep scalar survived the field-absent append")
    sys.exit(1)

assert before["summary"].endswith("\n\n") and not after["summary"].endswith("\n\n")
print("DEFECT REPRODUCED: appended field wedged inside the keep scalar's "
      "trailing blank run; scalar silently lost its final newline")
