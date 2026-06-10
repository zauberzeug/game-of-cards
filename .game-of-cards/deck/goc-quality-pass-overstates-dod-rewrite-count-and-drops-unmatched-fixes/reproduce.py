"""Reproduce: goc quality-pass overstates the DoD rewrite count and silently
drops accepted fixes whose `idx` does not map to a real DoD checkbox.

`_apply_dod_rewrite` only mutates a line when an accepted issue's `idx`
falls within the card's `box_indices`. The caller `_apply_verdict_interactive`
unconditionally sets `applied["dod"] = len(accepted_issues)` and prints
"DoD: N item(s) rewritten", regardless of how many lines were actually
written. So an accepted fix with an out-of-range `idx` vanishes with no
signal, while the count and per-card tally claim it was applied.

Run on a clean checkout:
    uv run python .game-of-cards/deck/<title>/reproduce.py
"""

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

from goc import engine  # noqa: E402


CARD_TEXT = """\
---
title: demo-card
summary: "A card with exactly two DoD checkboxes."
status: open
stage: null
contribution: low
created: 2026-06-10
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] item zero
  - [ ] item one
---

# Demo card

Body.
"""


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        card_dir = Path(tmp) / "demo-card"
        card_dir.mkdir()
        readme = card_dir / "README.md"
        readme.write_text(CARD_TEXT)

        card = engine.load_card(card_dir)
        fix_text = "rewritten item five"

        # An LLM verdict that accepts one DoD fix targeting idx 5 — a box that
        # does not exist (the card has only boxes 0 and 1). With auto_yes the
        # issue is "accepted" exactly as an interactive operator pressing 'y'
        # would accept it.
        verdict = {
            "title_verdict": {"ok": True},
            "summary_verdict": {"ok": True},
            "dod_issues": [
                {"idx": 5, "issue": "not verifiable", "fix": fix_text}
            ],
        }

        applied = engine._apply_verdict_interactive(card, verdict, auto_yes=True)

        fm, _ = engine.parse_frontmatter(readme.read_text())
        dod_after = fm.get("definition_of_done") or ""

        reported = applied["dod"]
        fix_landed = fix_text in dod_after
        items_preserved = "item zero" in dod_after and "item one" in dod_after

        print(f"reported applied['dod']           : {reported}")
        print(f"accepted fix text present in DoD  : {fix_landed}")
        print(f"original items preserved          : {items_preserved}")
        print()
        if reported == 1 and not fix_landed and items_preserved:
            print("DEFECT CONFIRMED: caller reported 1 DoD item rewritten, but the")
            print("accepted fix text never landed in the DoD — idx 5 matched no")
            print("checkbox so the fix was silently dropped, and the count was")
            print("overstated. The operator is told a fix they accepted was applied.")
            return 0
        print("Defect not reproduced (code may have been fixed).")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
