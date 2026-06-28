"""Reproduce: `_append_marker_block` corrupts user prose that quotes the marker syntax.

Construct a well-formed briefing file that contains:
  1. user-authored prose explaining the marker convention (with literal
     `<!-- BEGIN GOC vX.Y.Z -->` and `<!-- END GOC -->` in backticks), and
  2. a single real `<!-- BEGIN GOC v0.0.23 -->` ... `<!-- END GOC -->` block.

Run `_append_marker_block` against it. The regex matches BOTH the prose
mention AND the real block, and `pattern.sub` rewrites both — corrupting
the user's documentation and producing a duplicate block.

Exits zero only after the fix lands (target: prose preserved verbatim,
real block rewritten in place, file ends with exactly one block).
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

import re

from goc.install import GOC_BEGIN_RE, GOC_END


def main() -> int:
    new_begin = "<!-- BEGIN GOC v0.0.24 -->"
    block_body = "NEW BRIEFING CONTENT"
    block = f"{new_begin}\n{block_body.rstrip()}\n{GOC_END}\n"

    text = (
        "# Project notes\n"
        "\n"
        "The marker block below is rewritten by goc upgrade.\n"
        "\n"
        "Don't edit between the `<!-- BEGIN GOC vX.Y.Z -->` and `<!-- END GOC -->` markers.\n"
        "\n"
        "More user prose here.\n"
        "\n"
        "<!-- BEGIN GOC v0.0.23 -->\n"
        "REAL BRIEFING CONTENT\n"
        "<!-- END GOC -->\n"
        "\n"
        "Footer text.\n"
    )

    # Exact pattern from goc/install.py:1193.
    pattern = re.compile(
        rf"{GOC_BEGIN_RE.pattern}.*?{re.escape(GOC_END)}\n?", re.DOTALL
    )
    matches = list(pattern.finditer(text))
    print(f"# of matches: {len(matches)}")
    for i, m in enumerate(matches):
        print(f"match {i}: span={m.span()}, text={m.group()!r}")

    result = pattern.sub(lambda _: block, text)
    print()
    print("=== AFTER REWRITE ===")
    print(result, end="")

    # Defect assertions: with the bug present, BOTH should be true.
    prose_corrupted = "Don't edit between the `<!-- BEGIN GOC v0.0.24 -->" in result
    block_count = result.count(new_begin)
    duplicated = block_count > 1

    print()
    print(f"defect-A (prose corrupted)       : {prose_corrupted}")
    print(f"defect-B (block duplicated, n={block_count}): {duplicated}")

    if prose_corrupted or duplicated:
        print("DEFECT REPRODUCED — exiting 1")
        return 1

    # After the fix, we expect:
    #   - prose preserved verbatim,
    #   - exactly one real block, with the new content,
    #   - no copy of the new block injected into prose.
    prose_preserved = "Don't edit between the `<!-- BEGIN GOC vX.Y.Z -->`" in result
    one_real_block = block_count == 1
    if prose_preserved and one_real_block:
        print("FIX VERIFIED — exiting 0")
        return 0
    print("UNKNOWN POST-FIX STATE — exiting 1")
    return 1


if __name__ == "__main__":
    sys.exit(main())
