"""Reproduce: `goc quality-pass --status all --llm --yes` mutates summary
and DoD on terminal-status (done) cards.

Two-card deck:
  - card-a: open, has a jargon title and weak summary (legitimate rewrite target)
  - card-b: done, has a jargon title and weak summary (must NOT be mutated)

A stub `_run_sonnet_quality_pass` returns a verdict that proposes a summary
rewrite and a DoD rewrite for both cards. With `--yes`, both would be auto-applied.

Post-fix contract: the done card's `summary` and `definition_of_done` survive
unchanged. Pre-fix: both fields are silently overwritten on disk.

Exit 0 — fix in place; exit 1 — defect still present (done card mutated).
"""
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


REPO_ROOT = _repo_root()
sys.path.insert(0, str(REPO_ROOT))


CARD_A_OPEN = """---
title: card-a-open
summary: ""
status: open
stage: null
contribution: medium
created: "2026-05-29T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] fix the thing
---

# card-a-open

body.
"""


CARD_B_DONE = """---
title: card-b-done
summary: "ORIGINAL DONE SUMMARY"
status: done
stage: null
contribution: medium
created: "2026-05-29T00:00:00Z"
closed_at: "2026-05-29T01:00:00Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] original-done-dod-item
---

# card-b-done

body.
"""


STUB_VERDICTS = [
    {
        "title": "card-a-open",
        "title_verdict": {"ok": True},
        "summary_verdict": {"ok": False, "reason": "jargon", "rewrite": "REWRITTEN OPEN SUMMARY"},
        "dod_issues": [{"idx": 0, "issue": "jargon", "fix": "- [ ] rewritten-open-dod-item"}],
    },
    {
        "title": "card-b-done",
        "title_verdict": {"ok": True},
        "summary_verdict": {"ok": False, "reason": "jargon", "rewrite": "REWRITTEN DONE SUMMARY"},
        "dod_issues": [{"idx": 0, "issue": "jargon", "fix": "- [x] rewritten-done-dod-item"}],
    },
]


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        deck_dir = tmp_path / ".game-of-cards" / "deck"
        deck_dir.mkdir(parents=True)
        (tmp_path / "pyproject.toml").write_text("# stub\n")

        (deck_dir / "card-a-open").mkdir()
        (deck_dir / "card-a-open" / "README.md").write_text(CARD_A_OPEN)
        (deck_dir / "card-a-open" / "log.md").write_text("")

        (deck_dir / "card-b-done").mkdir()
        (deck_dir / "card-b-done" / "README.md").write_text(CARD_B_DONE)
        (deck_dir / "card-b-done" / "log.md").write_text("")

        os.chdir(tmp_path)
        # Force engine module to re-resolve DECK_DIR against the temp tree.
        for mod_name in list(sys.modules):
            if mod_name == "goc" or mod_name.startswith("goc."):
                del sys.modules[mod_name]

        from goc import engine

        engine._run_sonnet_quality_pass = lambda _prompt: STUB_VERDICTS

        args = SimpleNamespace(
            status_flag="all",
            llm=True,
            limit=None,
            dry_run=False,
            auto_yes=True,
        )
        try:
            engine._cmd_quality_pass(args)
        except SystemExit:
            pass

        done_readme = (deck_dir / "card-b-done" / "README.md").read_text()
        open_readme = (deck_dir / "card-a-open" / "README.md").read_text()

        print("--- card-b-done (terminal) README.md ---")
        print(done_readme)
        print("--- card-a-open README.md ---")
        print(open_readme)

        done_summary_mutated = "REWRITTEN DONE SUMMARY" in done_readme
        done_dod_mutated = "rewritten-done-dod-item" in done_readme
        open_summary_mutated = "REWRITTEN OPEN SUMMARY" in open_readme

        print()
        print(f"done card summary mutated:    {done_summary_mutated}")
        print(f"done card DoD mutated:        {done_dod_mutated}")
        print(f"open card summary mutated:    {open_summary_mutated}  (sanity: expected True)")

        if done_summary_mutated or done_dod_mutated:
            print("\nFAIL: defect present — terminal-status card was mutated.")
            return 1
        print("\nPASS: terminal-status card survived quality-pass --llm --yes.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
