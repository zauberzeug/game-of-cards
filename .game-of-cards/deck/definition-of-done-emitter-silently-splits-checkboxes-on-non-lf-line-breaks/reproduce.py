"""Reproduce: the `definition_of_done` emitter branch silently rewrites
non-LF line breaks into LF, fabricating/destroying checkbox boundaries.

Unlike every other multi-line string field, the DoD branch in
`emit_frontmatter` routes the value unconditionally through
`_emit_block_field`, which splits on `str.splitlines()` and rejoins with
LF. A DoD value carrying a non-LF break (VT/FF/NEL/U+2028/U+2029) is
therefore silently split into extra lines on emit — while the SAME
character in any other multi-line field is refused at the boundary with a
`FrontmatterError`. Splitting a DoD item can fabricate or destroy a
`- [ ]` checkbox, changing the closure count that `goc done` gates on.

Exit zero == defect fixed (DoD with a non-LF break round-trips faithfully
OR is refused like the other fields). Exit non-zero == defect present.
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

from goc.engine import FrontmatterError, emit_frontmatter, parse_frontmatter  # noqa: E402

# A DoD with a vertical-tab (\x0b) inside one authored checkbox item.
# \x0b survives Path.read_text() universal-newline normalization (which
# only collapses \r / \r\n), so it can reach the emitter intact via the
# quality-pass LLM-rewrite applier (_apply_dod_rewrite).
authored = "- [ ] keep this one item\x0bnot two"
fm = {"title": "x", "definition_of_done": authored}

failures = []

# 1. The DoD field must NOT silently rewrite the non-LF break.
try:
    text = emit_frontmatter(fm, body="body")
    fm2, _ = parse_frontmatter(text)
    round_tripped = fm2["definition_of_done"]
    expected = authored  # block style clips one trailing newline; compare core
    if round_tripped.rstrip("\n") != authored.rstrip("\n"):
        failures.append(
            "DoD emitter silently rewrote the non-LF break:\n"
            f"  authored:    {authored!r}\n"
            f"  round-trip:  {round_tripped!r}"
        )
except FrontmatterError:
    # Refusing at the boundary (like every other multi-line field) is the
    # acceptable alternative outcome — not a failure.
    pass

# 2. Consistency check: the same character in `summary` IS refused today.
#    Demonstrates the DoD branch is the lone field exempt from the guard.
try:
    emit_frontmatter({"title": "x", "summary": "a\x0bb"}, body="body")
    print("note: summary no longer refuses non-LF break (guard changed)")
except FrontmatterError:
    pass  # expected: the generic branch guards this

if failures:
    print("DEFECT PRESENT:")
    for f in failures:
        print(f)
    sys.exit(1)

print("OK: DoD emitter handles non-LF line breaks safely "
      "(faithful round-trip or boundary refusal).")
sys.exit(0)
