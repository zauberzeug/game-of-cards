"""Reproduce: yaml_lite silently absorbs an over-indented block-sequence item.

A `- item` line indented MORE than its surrounding sequence is neither
faithfully parsed nor rejected by goc._vendor.yaml_lite — it is silently
absorbed as a same-level item. The mapping analogue was fixed in 119cf31
(over-indented mapping lines now raise ParseError); the block-sequence
loop never got the same guard.

Exit code is 0 once the defect is fixed (the over-indented item raises
ParseError), non-zero while the defect is present.
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

from goc._vendor.yaml_lite import ParseError, safe_load  # noqa: E402

SEQ = "advances:\n  - first-target\n      - second-target\ncontribution: high\n"
MAP = "status: open\n    rogue: value\n"

defect_present = False

print("Case — over-indented block-sequence item:")
print(f"  input: {SEQ!r}")
try:
    got = safe_load(SEQ)
    print(f"  yaml_lite: {got}   (second-target WRONGLY absorbed as a same-level item)")
    defect_present = True
except ParseError as e:
    print(f"  yaml_lite: raises ParseError ({e}) — correct")
print()

print("For contrast — the mapping analogue already raises (fixed in 119cf31):")
print(f"  input: {MAP!r}")
try:
    got = safe_load(MAP)
    print(f"  yaml_lite: {got}   (UNEXPECTED — mapping guard regressed)")
    defect_present = True
except ParseError as e:
    print(f"  yaml_lite: raises ParseError ({e}) — correct")
print()

if defect_present:
    print("DEFECT CONFIRMED: yaml_lite silently absorbs the over-indented sequence item; it does not raise.")
    sys.exit(1)

print("FIXED: the over-indented block-sequence item raises ParseError.")
sys.exit(0)
