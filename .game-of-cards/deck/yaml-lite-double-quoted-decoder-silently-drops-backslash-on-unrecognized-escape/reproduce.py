"""Reproduce: yaml-lite's double-quoted decoder silently drops the backslash
on any escape it does not recognize, corrupting the parsed value.

`_parse_double_quoted` knows only four escapes (\\n \\t \\" \\\\). For every
other escape sequence it appends the escaped character WITHOUT the backslash
(the `.get(esc, esc)` fallback at goc/_vendor/yaml_lite.py), so:

  "C:\\Users"  -> "C:Users"   (the \\U is eaten; data lost, no error)
  "a\\rb"      -> "arb"       (\\r dropped instead of decoded or rejected)
  "caf\\u00e9" -> "cafu00e9"  (the \\u escape silently mangled)

This violates the parser's documented fail-loud posture: every other
malformed / unsupported double-quoted input (over-indent, tabs, folded
scalars, unterminated flow collections) raises ParseError rather than
returning a corrupted value. Unrecognized escapes are the lone
silent-corruption holdout in the decoder.

Exit 0 (defect demonstrated) printing the corrupted reads BEFORE the fix.
After the fix the corrupted reads no longer occur (the parser raises
ParseError instead), and this script exits 1.
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


def _load(scalar: str):
    """Parse a double-quoted scalar as the value of key `k`."""
    return safe_load(f"k: {scalar}\n")["k"]


# Each case: (raw double-quoted scalar, the corrupted value the buggy
# decoder returns). All three are silent corruption — no error raised.
CASES = [
    (r'"C:\Users"', "C:Users"),     # \U eaten -> backslash dropped
    (r'"a\rb"', "arb"),             # \r dropped
    (r'"caf\u00e9"', "cafu00e9"),  # \u escape mangled
]

corrupted = []
for raw, expected_bug in CASES:
    try:
        got = _load(raw)
    except ParseError:
        # Post-fix: the decoder fails loud instead of corrupting.
        continue
    if got == expected_bug:
        corrupted.append((raw, got))

print("=== yaml-lite double-quoted unrecognized-escape decode ===")
for raw, got in corrupted:
    print(f"  {raw!r:18} -> {got!r}   (silently corrupted: backslash dropped)")

# Sanity: the four recognized escapes must still decode correctly either way.
assert _load(r'"a\nb"') == "a\nb", "recognized \\n escape regressed"
assert _load(r'"it\"s"') == 'it"s', "recognized \\\" escape regressed"
assert _load(r'"a\\b"') == "a\\b", "recognized \\\\ escape regressed"

if corrupted:
    print(
        f"\nDEFECT PRESENT: {len(corrupted)} unrecognized-escape scalar(s) "
        "silently corrupted (backslash dropped, no error)."
    )
    sys.exit(0)

print("\nNo silent corruption: unrecognized escapes are now rejected (fixed).")
sys.exit(1)
