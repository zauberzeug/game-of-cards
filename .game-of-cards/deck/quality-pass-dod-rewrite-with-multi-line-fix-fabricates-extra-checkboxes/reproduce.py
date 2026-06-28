#!/usr/bin/env python3
"""Reproduce: a multi-line quality-pass `fix` fabricates an extra DoD checkbox.

`_apply_dod_rewrite` replaces ONE DoD item by index. An LLM-authored `fix`
(from `claude --model sonnet ... --output-format json`) can contain a newline.
When it does, the single item becomes multiple physical lines on re-emit, and
any line shaped like `- [ ]` is counted as a fabricated checkbox.

Run: `uv run python .game-of-cards/deck/<this-card>/reproduce.py`
Expected (buggy): box count grows from 2 to 3.
Expected (fixed): box count stays 2.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from goc.engine import Card, _apply_dod_rewrite, count_dod_boxes, parse_frontmatter

README = (
    "---\n"
    "title: tmp-card\n"
    "status: open\n"
    "stage: null\n"
    "contribution: low\n"
    'created: "2026-06-28T00:00:00Z"\n'
    "closed_at: null\n"
    "human_gate: none\n"
    "advances: []\n"
    "advanced_by: []\n"
    "tags: [bug]\n"
    "definition_of_done: |\n"
    "  - [ ] first criterion\n"
    "  - [ ] second criterion\n"
    "---\n\n# tmp-card\n"
)


def main() -> None:
    with tempfile.TemporaryDirectory() as d:
        card_dir = Path(d) / "tmp-card"
        card_dir.mkdir()
        (card_dir / "README.md").write_text(README)
        card = Card(
            title="tmp-card",
            path=card_dir,
            frontmatter={},
            body="",
            dod_open=2,
            dod_done=0,
        )
        # An LLM `fix` that wraps onto a second line shaped like a checkbox.
        _apply_dod_rewrite(
            card,
            [{"idx": 0, "fix": "rewritten first\n- [ ] sneaky injected"}],
        )
        fm, _ = parse_frontmatter((card_dir / "README.md").read_text())
        dod = fm["definition_of_done"]
        open_boxes, done_boxes = count_dod_boxes(dod)
        print("DoD after rewrite:")
        print(dod)
        print(f"open boxes: {open_boxes} (contract: 2)  done boxes: {done_boxes}")
        if open_boxes != 2:
            print("BUG: a single-item rewrite fabricated an extra checkbox.")
        else:
            print("OK: box count preserved by the rewrite.")


if __name__ == "__main__":
    main()
