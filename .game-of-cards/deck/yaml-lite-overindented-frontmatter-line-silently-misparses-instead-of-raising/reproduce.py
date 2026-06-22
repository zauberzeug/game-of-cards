"""Reproduce: yaml_lite silently mis-parses over-indented frontmatter lines.

A line indented MORE than its surrounding mapping is neither faithfully
parsed nor rejected by goc._vendor.yaml_lite — it is silently mangled.
PyYAML raises (Case 1) or folds (Case 2). The vendored parser does
neither: it promotes a nested key to top level (Case 1) or truncates
every following key (Case 2).

Exit code is 0 once the defect is fixed (both cases raise ParseError),
non-zero while the defect is present.
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

CASE1 = "status: open\n  human_gate: decision\n"
CASE2 = "summary: hello\n  world\nstatus: open\n"

defect_present = False

print("Case 1 — over-indented mapping key:")
print(f"  input: {CASE1!r}")
try:
    got = safe_load(CASE1)
    print(f"  yaml_lite: {got}   (human_gate WRONGLY promoted to top level)")
    defect_present = True
except ParseError as e:
    print(f"  yaml_lite: raises ParseError ({e}) — correct")
print("  PyYAML:    raises ScannerError")
print()

print("Case 2 — over-indented bare continuation:")
print(f"  input: {CASE2!r}")
try:
    got = safe_load(CASE2)
    print(f"  yaml_lite: {got}   (world dropped AND status:open silently truncated)")
    defect_present = True
except ParseError as e:
    print(f"  yaml_lite: raises ParseError ({e}) — correct")
print("  PyYAML:    {'summary': 'hello world', 'status': 'open'}")
print()

if defect_present:
    print("DEFECT CONFIRMED: yaml_lite silently mis-parses; neither raises.")
    sys.exit(1)

print("FIXED: both over-indent cases raise ParseError.")
sys.exit(0)
