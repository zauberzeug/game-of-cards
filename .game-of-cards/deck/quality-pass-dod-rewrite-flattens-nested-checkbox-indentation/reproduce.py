"""Reproduce: `_apply_dod_rewrite` flattens a nested DoD checkbox to column 0.

A verdict targeting a nested `  - [ ]` sub-item should keep its original
indentation after the rewrite. Before the fix, the sub-item is de-indented
to the top level.

Run: uv run python deck/quality-pass-dod-rewrite-flattens-nested-checkbox-indentation/reproduce.py
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

from goc.engine import Card, _apply_dod_rewrite, parse_frontmatter  # noqa: E402

DOD = "- [ ] TDD: top-level criterion\n  - [ ] sub-criterion under it\n- [x] already-done item\n"

README = (
    "---\n"
    "title: tmp-card\n"
    "status: open\n"
    "stage: null\n"
    "contribution: low\n"
    'created: "2026-06-21T00:00:00Z"\n'
    "closed_at: null\n"
    "human_gate: none\n"
    "advances: []\n"
    "advanced_by: []\n"
    "tags: [bug]\n"
    "definition_of_done: |\n"
    "  - [ ] TDD: top-level criterion\n"
    "    - [ ] sub-criterion under it\n"
    "  - [x] already-done item\n"
    "---\n\n# tmp-card\n"
)


def main() -> int:
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
            dod_done=1,
        )
        # Verdict targets box index 1 — the nested sub-criterion.
        _apply_dod_rewrite(card, [{"idx": 1, "fix": "sub-criterion reworded to be measurable"}])
        fm, _ = parse_frontmatter((card_dir / "README.md").read_text())
        new_dod = fm["definition_of_done"]
        target_line = new_dod.splitlines()[1]

        print("Rewritten DoD line for the nested sub-item:")
        print(repr(target_line))
        preserved = target_line.startswith("  - [ ]")
        print(f"\nIndentation preserved: {preserved}")
        if preserved:
            print("PASS: nested sub-item kept its two-space indent")
            return 0
        print("FAIL: nested sub-item was flattened to column 0")
        return 1


if __name__ == "__main__":
    sys.exit(main())
