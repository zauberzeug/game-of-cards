"""Proof that the vendored YAML parser implements YAML block-scalar chomping
as a three-way choice (clip / strip / keep), not a clip-vs-strip boolean.

Inspection in the card suspected `|+` (keep) was collapsed onto bare `|`
(clip). Running it shows the inverse: keep was already correct, but BOTH
clip and strip retained trailing blank lines that they are supposed to chomp.
The fix is the same either way — a real three-way chomp — and this script
asserts the full YAML 1.1/1.2 contract for all three indicators.

YAML chomping (trailing blank lines after content `a`):
  |   clip  -> "a\n"      one trailing newline, blank lines dropped
  |-  strip -> "a"        no trailing newline, blank lines dropped
  |+  keep  -> "a\n\n\n"  final newline + every trailing blank line preserved

Run: uv run python .game-of-cards/deck/yaml-lite-keep-chomping-indicator-treated-as-clip/reproduce.py
Exits 0 when chomping is correct (fix present), 1 when the bug is present.
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

from goc._vendor.yaml_lite import safe_load  # noqa: E402


def chomp(indicator: str) -> str:
    # Block scalar `a` followed by two trailing blank lines, then a sibling key
    # so the trailing blanks are unambiguously inside the scalar's region.
    doc = f"x: {indicator}\n  a\n\n\nb: 2\n"
    return safe_load(doc)["x"]


cases = [
    ("|", "clip", "a\n"),
    ("|-", "strip", "a"),
    ("|+", "keep", "a\n\n\n"),
]

print("Block-scalar chomping (content 'a' + two trailing blank lines):")
ok = True
for indicator, label, expected in cases:
    got = chomp(indicator)
    passed = got == expected
    ok = ok and passed
    flag = "ok" if passed else "WRONG"
    print(f"  {indicator:2} {label:5} expected={expected!r:12} got={got!r:12} {flag}")

# Keep and clip must be DISTINCT — that distinction is the whole point.
distinct = chomp("|+") != chomp("|")
print(f"\n|+ (keep) distinct from | (clip)? {distinct}")
ok = ok and distinct

# Sibling key still parses (trailing blanks consumed by the scalar, not leaked).
sibling = safe_load("x: |+\n  a\n\n\nb: 2\n").get("b")
print(f"sibling key after block scalar parses? b={sibling!r}")
ok = ok and sibling == 2

print(f"\nCHOMPING CORRECT (three-way clip/strip/keep): {ok}")
sys.exit(0 if ok else 1)
