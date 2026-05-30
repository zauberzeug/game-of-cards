"""Demonstrates `_apply_dod_rewrite` silently unchecking a previously-checked
DoD item when the LLM's `fix` payload is bare text (no checkbox prefix), as
the documented `_QUALITY_PROMPT_TEMPLATE` schema instructs it to be.

Run: `uv run python .game-of-cards/deck/<title>/reproduce.py`
Exits non-zero (prints the offending diff) until the bug is fixed.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc.engine import _apply_dod_rewrite, load_card  # noqa: E402


CARD_TEXT = """---
title: demo-card
summary: "demo summary"
status: open
stage: null
contribution: medium
created: 2026-05-30
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] item zero was already done
  - [ ] item one is open
---

# demo body
"""


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    card_dir = tmp / "demo-card"
    card_dir.mkdir()
    readme = card_dir / "README.md"
    readme.write_text(CARD_TEXT)

    card = load_card(card_dir)
    print("BEFORE DoD:")
    print(card.frontmatter["definition_of_done"])

    # LLM-shaped verdict: targets the *checked* box (idx 0) with a bare-text
    # rewrite — exactly what `_QUALITY_PROMPT_TEMPLATE` (engine.py:2937)
    # documents as the contract: `fix: "rewrite..."`, no checkbox prefix.
    issues = [
        {"idx": 0, "issue": "vague wording", "fix": "item zero meets metric Y across N trials"},
    ]
    _apply_dod_rewrite(card, issues)

    after_text = readme.read_text()
    print("\nAFTER README:")
    print(after_text)

    # The previously-checked `[x]` must survive the rewrite. If it does not,
    # the rewriter has silently erased attested completion.
    if "- [x] item zero meets metric Y across N trials" in after_text:
        print("PASS: checked state preserved across DoD rewrite")
        return 0
    if "- [ ] item zero meets metric Y across N trials" in after_text:
        print(
            "FAIL: previously-checked `[x]` was silently flipped to `[ ]` "
            "by _apply_dod_rewrite (engine.py:3082)",
        )
        return 1
    print("FAIL: unexpected DoD shape after rewrite — see AFTER README dump above")
    return 1


if __name__ == "__main__":
    sys.exit(main())
