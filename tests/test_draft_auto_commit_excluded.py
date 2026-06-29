"""Regression: `_git_auto_commit` excludes draft cards by default (Option C).

An unauthored scaffold must never reach shared state through goc's automatic
commit path — that is the dedup/supersede race the draft state guards against.
The explicit `goc new --commit` path opts out (exclude_draft=False) so a wired
filing commits the new card with its edge writes atomically (no half-edge).
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


def _write_card(deck: Path, title: str, *, draft: bool, authored: bool) -> Path:
    d = deck / title
    d.mkdir(parents=True)
    lines = [
        "---",
        f"title: {title}",
        "status: open",
        "contribution: medium",
        'created: "2026-01-01T00:00:00Z"',
        "human_gate: none",
        "tags: [story]",
    ]
    if draft:
        lines.append("draft: true")
    lines.append("definition_of_done: |")
    lines.append("  - [x] MECHANICAL: done" if authored else "  - [ ] (replace with real criteria)")
    lines += ["---", "", f"# {title}", "", "Real body." if authored else "(write the design doc here)", ""]
    (d / "README.md").write_text("\n".join(lines))
    (d / "log.md").write_text("")
    return d


class DraftAutoCommitExcludedTest(unittest.TestCase):
    def _seed_repo(self, tmp: Path):
        _run(["git", "init", "-q", "-b", "main"], cwd=tmp)
        _run(["git", "config", "user.email", "test@example.com"], cwd=tmp)
        _run(["git", "config", "user.name", "Test"], cwd=tmp)
        deck = tmp / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)
        return deck

    def _committed_paths(self, tmp: Path) -> list[str]:
        result = _run(["git", "show", "--name-only", "--format=", "HEAD"], cwd=tmp)
        return sorted(ln for ln in result.stdout.splitlines() if ln.strip())

    def _with_patched_engine(self, tmp: Path, fn):
        from goc import engine
        orig_root, orig_dir = engine.DECK_ROOT, engine.DECK_DIR
        try:
            engine.DECK_ROOT = tmp
            engine.DECK_DIR = tmp / ".game-of-cards" / "deck"
            return fn(engine)
        finally:
            engine.DECK_ROOT, engine.DECK_DIR = orig_root, orig_dir

    def test_draft_excluded_live_card_committed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            deck = self._seed_repo(tmp)
            draft_dir = _write_card(deck, "draft-card", draft=True, authored=False)
            live_dir = _write_card(deck, "live-card", draft=False, authored=True)
            _run(["git", "add", "."], cwd=tmp)
            _run(["git", "commit", "-q", "-m", "seed"], cwd=tmp)
            # Mutate both, then auto-commit both dirs.
            (draft_dir / "README.md").write_text(
                (draft_dir / "README.md").read_text() + "\nmutated\n"
            )
            (live_dir / "README.md").write_text(
                (live_dir / "README.md").read_text() + "\nmutated\n"
            )
            ok = self._with_patched_engine(
                tmp,
                lambda e: e._git_auto_commit([draft_dir, live_dir], "deck: batch"),
            )
            self.assertTrue(ok)
            committed = self._committed_paths(tmp)
            self.assertIn(".game-of-cards/deck/live-card/README.md", committed)
            self.assertNotIn(".game-of-cards/deck/draft-card/README.md", committed)
            # the draft mutation is still pending in the working tree
            status = _run(["git", "status", "--porcelain"], cwd=tmp).stdout
            self.assertIn("draft-card/README.md", status)

    def test_all_draft_targets_commit_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            deck = self._seed_repo(tmp)
            draft_dir = _write_card(deck, "draft-card", draft=True, authored=False)
            _run(["git", "add", "."], cwd=tmp)
            _run(["git", "commit", "-q", "-m", "seed"], cwd=tmp)
            (draft_dir / "README.md").write_text(
                (draft_dir / "README.md").read_text() + "\nmutated\n"
            )
            ok = self._with_patched_engine(
                tmp, lambda e: e._git_auto_commit([draft_dir], "deck: draft only")
            )
            self.assertFalse(ok, "a draft-only commit set must be a no-op")

    def test_exclude_draft_false_commits_the_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            deck = self._seed_repo(tmp)
            draft_dir = _write_card(deck, "draft-card", draft=True, authored=False)
            _run(["git", "add", "."], cwd=tmp)
            _run(["git", "commit", "-q", "-m", "seed"], cwd=tmp)
            (draft_dir / "README.md").write_text(
                (draft_dir / "README.md").read_text() + "\nmutated\n"
            )
            ok = self._with_patched_engine(
                tmp,
                lambda e: e._git_auto_commit(
                    [draft_dir], "deck: new draft-card", exclude_draft=False
                ),
            )
            self.assertTrue(ok, "exclude_draft=False must commit the draft (goc new --commit path)")
            self.assertIn(".game-of-cards/deck/draft-card/README.md", self._committed_paths(tmp))


if __name__ == "__main__":
    unittest.main()
