"""Reproduce: yaml_lite drops a same-indent block sequence and then
silently truncates every frontmatter key that follows it.

YAML permits a block-sequence whose `- item` lines sit at the SAME
indentation as the parent mapping key:

    advanced_by:
    - upstream-card

PyYAML parses this as {'advanced_by': ['upstream-card']}. The vendored
yaml_lite requires sequence items to be *strictly more* indented than
the key, so it (a) resolves the value to None and (b) leaves the
un-indented `- item` line to abort the enclosing block mapping, dropping
every subsequent key. The card silently loses its dependency edges,
tags, and Definition-of-Done.

Run: uv run python deck/<this-card>/reproduce.py
Exits 0 when the bug is FIXED (same-indent sequences parse correctly),
1 while the bug is present.
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

DOC = """title: example
advanced_by:
- upstream-card
tags:
- bug
- infra
definition_of_done: |
  - [ ] do the thing
"""

EXPECTED = {
    "title": "example",
    "advanced_by": ["upstream-card"],
    "tags": ["bug", "infra"],
    "definition_of_done": "- [ ] do the thing\n",
}

result = yaml_lite.safe_load(DOC)

print("Input frontmatter (same-indent block sequences, valid YAML):")
print(DOC)
print("yaml_lite.safe_load result:")
for k, v in result.items():
    print(f"  {k!r}: {v!r}")
print()

missing = [k for k in EXPECTED if k not in result]
wrong = {k: result.get(k) for k in EXPECTED if k in result and result[k] != EXPECTED[k]}

print(f"Keys lost entirely: {missing}")
print(f"Keys with wrong value: {sorted(wrong)}")
print()

if not missing and not wrong:
    print("PASS: same-indent block sequences parse correctly.")
    sys.exit(0)

print("FAIL: same-indent block sequence dropped and frontmatter truncated.")
print("  - 'advanced_by' resolves to None instead of ['upstream-card']")
print("  - 'tags' and 'definition_of_done' vanish from the dict entirely")
print("  -> card loses its dependency edges, tags, and DoD on every read.")
sys.exit(1)
