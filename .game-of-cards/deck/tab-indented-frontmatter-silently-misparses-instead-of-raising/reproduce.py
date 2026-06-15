"""Reproduce: tab-indented YAML parses silently instead of raising ParseError.

The vendored parser's docstring promises tab indentation raises
ParseError; this script shows it does not. Exits 0 once the defect is
fixed (all three cases raise), 1 while the defect is live.
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

from goc._vendor.yaml_lite import safe_load, ParseError  # noqa: E402

CASES = [
    ("case 1 (nested via tab)", "parent:\n\tchild: v"),
    ("case 2 (sequence via tab)", "items:\n\t- a\n\t- b"),
    ("case 3 (tab+space indent)", "a: 1\n\t  b: 2"),
]

defect_live = False
for label, src in CASES:
    try:
        result = safe_load(src)
        print(f"{label}: {result}   (expected ParseError)")
        defect_live = True
    except ParseError as e:
        print(f"{label}: ParseError — {e}")

if defect_live:
    print("RESULT: FAIL — tab indentation parsed silently")
    sys.exit(1)
print("RESULT: PASS — tab indentation raises ParseError as documented")
sys.exit(0)
