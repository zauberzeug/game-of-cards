#!/usr/bin/env python3
"""Reproduce: a same-indent block-mapping key with no space after the colon
silently truncates the document instead of raising.

Exits non-zero while the defect is present (the malformed line is swallowed),
exits zero once the parser raises ParseError as it already does for the
analogous tab / over-indent / block-sequence cases.
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

FAILURES = []

# Case 1: colon with no following space, mid-document — drops the bad line AND
# every key below it.
doc1 = "title: foo\nstatus:open\ncontribution: medium"
try:
    out = safe_load(doc1)
    FAILURES.append(
        f"colon-no-space mid-document did NOT raise; returned {out!r} "
        "(expected ParseError; 'status:open' and 'contribution' silently dropped)"
    )
    print(f"DEFECT: safe_load({doc1!r}) -> {out!r}")
except ParseError:
    print(f"OK: safe_load({doc1!r}) raised ParseError")

# Case 2: minimal shape.
doc2 = "a: 1\nb:2\nc: 3"
try:
    out = safe_load(doc2)
    FAILURES.append(
        f"colon-no-space minimal did NOT raise; returned {out!r} (expected ParseError)"
    )
    print(f"DEFECT: safe_load({doc2!r}) -> {out!r}")
except ParseError:
    print(f"OK: safe_load({doc2!r}) raised ParseError")

# Control: the analogous over-indent case already raises (loud-fail posture).
try:
    safe_load("a: 1\n  b: 2")
    FAILURES.append("control over-indent did NOT raise (parser posture regression)")
except ParseError:
    print("OK (control): over-indented line raises ParseError")

if FAILURES:
    print("\nFAILED:")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)

print("\nAll checks passed: malformed same-indent mapping lines fail loud.")
sys.exit(0)
