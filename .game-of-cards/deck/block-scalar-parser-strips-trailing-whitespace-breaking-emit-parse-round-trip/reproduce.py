"""Reproduce: block-scalar content lines lose trailing whitespace on round-trip.

The frontmatter emitter writes `definition_of_done` (always) and any
multiline string field (e.g. `summary`) as a literal block scalar, preserving
each content line verbatim including trailing whitespace. The vendored
yaml-lite parser rstrips every block-scalar content line, so a value emitted by
goc does NOT survive being parsed back by goc. Because goc rewrites frontmatter
on most verbs (status, advance, done, ...), this silently mutates card data.

Run: uv run python deck/<this-card>/reproduce.py
Exits zero once the round-trip preserves trailing whitespace on block content.
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

from goc.engine import emit_frontmatter, parse_frontmatter  # noqa: E402

# A DoD whose first item ends in a Markdown hard-break (two trailing spaces).
dod = "- [ ] item with hard break  \n- [ ] second item"
fm = {"title": "x", "definition_of_done": dod}

text = emit_frontmatter(fm) + "\nbody\n"
back, _body = parse_frontmatter(text)

orig = fm["definition_of_done"]
# Block-scalar clip mode adds one trailing newline; that is expected and not
# the bug under test. Normalize only that single trailing newline before
# comparing, so the assertion isolates the per-line trailing-whitespace loss.
got = back["definition_of_done"]
got_normalized = got[:-1] if got.endswith("\n") and not orig.endswith("\n") else got

print("emitted frontmatter:")
print(emit_frontmatter(fm))
print("orig DoD:", repr(orig))
print("got  DoD:", repr(got_normalized))

ok = orig == got_normalized
print()
print("ROUND-TRIP PRESERVES TRAILING WHITESPACE:", ok)

if not ok:
    print(
        "\nFAIL: emitter wrote the trailing two spaces but the parser stripped "
        "them.\nThe emit->parse round-trip is not closed for block-scalar content."
    )
    sys.exit(1)

print("\nPASS: block-scalar content survives the emit->parse round-trip.")
sys.exit(0)
