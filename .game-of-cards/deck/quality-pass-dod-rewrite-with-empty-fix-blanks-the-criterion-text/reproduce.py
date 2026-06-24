"""Reproduce: an empty `fix` on an accepted DoD issue blanks the criterion text.

`_apply_dod_rewrite` promises "Other items preserved verbatim" but rewrites a
targeted line to the literal "- [ ] " when the issue's `fix` is empty, silently
destroying the criterion. Exits non-zero while the defect fires, zero once fixed.
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

README = (
    "---\n"
    "title: tmp-card\n"
    "status: open\nstage: null\ncontribution: low\n"
    'created: "2026-06-21T00:00:00Z"\nclosed_at: null\nhuman_gate: none\n'
    "advances: []\nadvanced_by: []\ntags: [bug]\n"
    "definition_of_done: |\n"
    "  - [ ] TDD: regression test proves the fix\n"
    "  - [ ] implement the guard\n"
    "---\n\n# tmp-card\n"
)


def main() -> int:
    with tempfile.TemporaryDirectory() as d:
        cd = Path(d) / "tmp-card"
        cd.mkdir()
        (cd / "README.md").write_text(README)
        card = Card(title="tmp-card", path=cd, frontmatter={}, body="", dod_open=2, dod_done=0)
        fm0, _ = parse_frontmatter((cd / "README.md").read_text())
        before = fm0["definition_of_done"].splitlines()
        print("BEFORE:", before)

        # An LLM verdict that flags item 0 but supplies an empty replacement.
        _apply_dod_rewrite(card, [{"idx": 0, "fix": ""}])

        fm1, _ = parse_frontmatter((cd / "README.md").read_text())
        after = fm1["definition_of_done"].splitlines()
        print("AFTER :", after)

        if after[0].strip() == "- [ ]":
            print("FAIL: item 0 criterion text was blanked by an empty fix")
            return 1
        if after[0] != before[0]:
            print(f"FAIL: item 0 changed unexpectedly: {after[0]!r}")
            return 1
        print("OK: empty fix left the criterion verbatim")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
