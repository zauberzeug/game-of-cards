"""Reproduce: mutate_frontmatter_field over-consumes a blank line (and any
indented line after it) when mutating a FLAT field that is immediately
followed by a structural blank line.

Exit 0 when the defect fires (current buggy behavior), 1 once it is fixed.
Run: uv run python deck/mutate-frontmatter-field-over-consumes-blank-line-after-a-flat-field/reproduce.py
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

from goc.engine import mutate_frontmatter_field  # noqa: E402

defect_fired = False

# CASE 1 — flat field `status` followed by a structural blank line.
case1 = "---\ntitle: foo\nstatus: open\n\nhuman_gate: none\n---\nbody\n"
out1 = mutate_frontmatter_field(case1, "status", "active")
print("CASE1 blank-line loss:")
print(repr(out1))
blank_preserved = "\n\n" in out1
print("blank line preserved:", blank_preserved)
if not blank_preserved:
    defect_fired = True
print()

# CASE 2 — flat field `worker` followed by blank line then an indented line.
case2 = "---\ntitle: foo\nworker: bob\n\n  stray: indented\nhuman_gate: none\n---\nbody\n"
out2 = mutate_frontmatter_field(case2, "worker", "alice")
print("CASE2 indented-line loss:")
print(repr(out2))
stray_preserved = "stray" in out2
print("stray line preserved:", stray_preserved)
if not stray_preserved:
    defect_fired = True
print()

# CONTROL — block field with internal blank line must KEEP its tail
# (the sibling card's invariant; a correct fix must not regress this).
block = (
    "---\n"
    "title: foo\n"
    "definition_of_done: |\n"
    "  - [ ] first\n"
    "\n"
    "  - [ ] second\n"
    "status: open\n"
    "---\nbody\n"
)
out3 = mutate_frontmatter_field(block, "definition_of_done", "- [ ] only\n")
print("CONTROL block-field tail:")
print(repr(out3))
tail_kept = "status: open" in out3
print("block tail (status) preserved:", tail_kept)
print()

if defect_fired:
    print("DEFECT FIRED: flat-field mutation deleted a blank/indented line it did not own.")
    sys.exit(0)
print("OK: flat-field mutation preserved surrounding lines.")
sys.exit(1)
