"""Reproduce: _remove_from_list_field rewrites a bare-string edge field as a per-character list.

Exits 0 once the defect is fixed (either via per-site guard in
_remove_from_list_field or via upstream coercion in parse_frontmatter).
Exits 1 while the defect fires.
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

from goc.engine import (  # noqa: E402
    _remove_from_list_field,
    parse_frontmatter,
)


PARENT_TEXT = """---
title: parent
status: open
contribution: medium
created: "2026-01-01T00:00:00Z"
closed_at: null
human_gate: none
advances: othercard
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] placeholder
---

# parent
"""


def main() -> int:
    fm_before, _ = parse_frontmatter(PARENT_TEXT)
    cur_before = fm_before.get("advances")
    print(f"parent advances before: {cur_before!r} (type: {type(cur_before).__name__})")
    print("running _remove_from_list_field(parent_text, 'advances', 'othercard')")

    try:
        rewritten = _remove_from_list_field(PARENT_TEXT, "advances", "othercard")
    except ValueError as exc:
        print(f"raised ValueError as expected: {exc}")
        print()
        print("PASS: the bare-string scalar was rejected at the guard.")
        return 0

    fm_after, _ = parse_frontmatter(rewritten)
    cur_after = fm_after.get("advances")
    print(f"parent advances after:  {cur_after!r} (type: {type(cur_after).__name__})")
    print()

    if isinstance(cur_after, list) and len(cur_after) > 1 and all(isinstance(c, str) and len(c) == 1 for c in cur_after):
        print("FAIL: bare-string 'advances: othercard' was rewritten as a character-list "
              "instead of being removed or rejected.")
        return 1

    if cur_after == [] or cur_after is None:
        print("PASS: the bare-string scalar 'othercard' was removed as the matching edge.")
        return 0

    if cur_after == "othercard":
        print("PASS: the bare-string scalar was left untouched (no early-exit corruption).")
        return 0

    print("UNEXPECTED: write-back produced a shape the test did not anticipate; treating as fail.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
