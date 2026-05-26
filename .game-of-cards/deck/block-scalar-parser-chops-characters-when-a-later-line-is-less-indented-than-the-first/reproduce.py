"""Reproduce: block-scalar parser chops characters on a less-indented later line.

`_parse_block_scalar` locks `block_indent` to the FIRST content line's indent,
then admits every following line while `curr > declaration_indent` and slices
it with `raw[block_indent:]`. A later line indented strictly less than the
first content line (but still deeper than the `|` declaration) is therefore
sliced past its leading content — real characters are silently eaten instead
of the block ending (YAML spec) or a parse error being raised.

Per the YAML spec the block scalar's indentation is fixed by its first
non-empty line; a content line less-indented than that cannot belong to the
block. Since it is also over-indented relative to the declaration's parent, it
cannot be a clean sibling either — it is unambiguously malformed. The parser
must NOT silently corrupt: it must either end the block cleanly or raise.

Run: uv run python .game-of-cards/deck/<this-card>/reproduce.py
Exits zero once a less-indented later line no longer eats characters.
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

from goc._vendor import yaml_lite  # noqa: E402

# "    deep line" sets block_indent=4; "  shallow line" sits at indent 2, between
# the declaration indent (0) and block_indent (4). The buggy slice raw[4:] turns
# "  shallow line" into "allow line" — the leading "sh" is eaten.
src = "k: |\n    deep line\n  shallow line\nnext: x\n"

print("input:")
print(repr(src))

try:
    out = yaml_lite.safe_load(src)
except yaml_lite.ParseError as exc:
    print("\nParseError raised:", exc)
    print("\nPASS: malformed indentation rejected instead of silently corrupted.")
    sys.exit(0)

print("\nparsed:", repr(out))

corrupted = isinstance(out, dict) and out.get("k", "").splitlines()[1:2] == ["allow line"]
if corrupted:
    print(
        "\nFAIL: the 'sh' of 'shallow line' was eaten — block_indent slicing "
        "chopped real content off a less-indented line."
    )
    sys.exit(1)

# Did not raise and did not corrupt — the block must have ended cleanly at the
# less-indented line, leaving its content intact (not sliced to "allow line").
k_val = out.get("k", "") if isinstance(out, dict) else ""
if "allow line" in k_val:
    print("\nFAIL: less-indented line was partially absorbed into the block.")
    sys.exit(1)

print("\nPASS: block ended cleanly; no characters were eaten.")
sys.exit(0)
