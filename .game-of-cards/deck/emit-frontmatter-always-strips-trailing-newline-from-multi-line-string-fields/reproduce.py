"""Reproduce: emit_frontmatter always uses the strip indicator (`|-`) for
multi-line string fields, so an authored clip block (`summary: |`, which the
parser reads back WITH a trailing newline) is flipped to `|-` and loses its
trailing newline on the first re-emit. The on-disk indicator changes and the
parsed value mutates even though no verb touched the field.

Exits 0 when the round-trip is faithful (bug fixed); exits 1 while the bug
fires.
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

from goc import engine as e  # noqa: E402

# A card authored the natural way: a multi-line summary as a clip block. This
# is exactly what `goc new` / create-card produce and what humans write.
authored = """---
title: x
summary: |
  line one
  line two
status: open
---

body
"""

fm, body = e.parse_frontmatter(authored)
print("authored summary (parsed):", repr(fm["summary"]))

reemitted = e.emit_frontmatter(fm, body=body)
fm2, _ = e.parse_frontmatter(reemitted)
print("re-emitted summary (parsed):", repr(fm2["summary"]))

indicator_flipped = "summary: |-" in reemitted and "summary: |" in authored
newline_dropped = fm["summary"] != fm2["summary"]

print("indicator flipped | -> |-:", indicator_flipped)
print("trailing newline dropped:", newline_dropped)

# A value that genuinely has no trailing newline must keep emitting `|-`
# (strip) so the fix does not over-correct in the other direction.
no_nl = {"title": "y", "summary": "alpha\nbeta", "status": "open"}
out_no_nl = e.emit_frontmatter(no_nl, body="\nbody\n")
fm3, _ = e.parse_frontmatter(out_no_nl)
no_nl_faithful = fm3["summary"] == no_nl["summary"]
print("no-trailing-newline value round-trips faithfully:", no_nl_faithful)

if indicator_flipped or newline_dropped or not no_nl_faithful:
    print("\nFAIL: emit_frontmatter mutates an authored multi-line string field.")
    sys.exit(1)

print("\nPASS: multi-line string fields round-trip faithfully both ways.")
sys.exit(0)
