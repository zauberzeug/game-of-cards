"""Demonstrate that the yaml-lite block-scalar parser collapses a
whitespace-only content line, breaking the emit->parse round-trip.

The goc frontmatter emitter writes a multiline `summary` (and always
`definition_of_done`) as a literal block scalar, preserving each content
line verbatim. A line that is all whitespace (indent + interior spaces)
should survive a parse-back. It does not: the parser rstrips every line
to test for blankness and, on a whitespace-only line, appends "" --
dropping the spaces past the block indent.

Exits 0 when the round-trip is lossless (defect fixed), 1 while the
defect fires.
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

import goc.engine as e  # noqa: E402

# A multiline value whose middle line is whitespace-only (3 spaces).
value = "first line\n   \nthird line"

fm = {
    "title": "x",
    "summary": value,
    "status": "open",
    "contribution": "medium",
    "human_gate": "none",
    "tags": ["bug"],
    "advances": [],
    "advanced_by": [],
}

text = e.emit_frontmatter(fm)
parsed, _body = e.parse_frontmatter(text)
roundtripped = parsed.get("summary")

print("=== emitted frontmatter ===")
print(text)
print("=== round-trip of summary ===")
print("in :", repr(value))
print("out:", repr(roundtripped))
print("match:", value == roundtripped)

if value != roundtripped:
    print(
        "\nDEFECT: whitespace-only content line collapsed to empty; "
        "the spaces past the block indent were dropped."
    )
    sys.exit(1)

print("\nOK: block-scalar round-trip is lossless.")
sys.exit(0)
