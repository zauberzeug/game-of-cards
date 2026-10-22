"""A read view in a repo without a deck names the missing deck.

Before this, `goc` in a fresh repo printed only `No cards match (status: open).`
— the same line an empty queue prints. The skills' `!` preambles run those
views at load time, and their Preflight routes to `Skill(kickoff)` on a fixed
set of phrases, none of which a missing deck produced; an agent that loaded a
skill in a repo without a deck went on to work an empty queue instead of
setting the deck up (release smoke Path B, card
`denied-preamble-block-aborts-skill-load-before-the-preflight-routes-to-kickoff`).

The notice goes to stderr so exit 0 and the `--json` stdout stay as they are,
and it keys on the *resolved* deck, so a legacy `deck/` stays silent.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc.engine import MISSING_DECK_PHRASE  # noqa: E402

PREFLIGHT_SKILLS = sorted(
    path
    for path in (ROOT / "goc" / "templates" / "skills").glob("*/SKILL.md")
    if "## Preflight" in path.read_text(encoding="utf-8")
)


class MissingDeckNoticeTest(unittest.TestCase):
    def run_goc(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        existing = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not existing else f"{ROOT}{os.pathsep}{existing}"
        env.pop("GOC_WORKTREE_DECK", None)
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def repo(self, tmp: str) -> Path:
        root = Path(tmp)
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
        return root

    def test_queue_view_names_the_missing_deck_on_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_goc(self.repo(tmp))
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("No cards match (status: open).", result.stdout.strip())
        self.assertIn(MISSING_DECK_PHRASE, result.stderr)
        self.assertIn("goc install", result.stderr)
        self.assertIn("Skill(kickoff)", result.stderr)

    def test_goc_new_errors_with_the_same_wording(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.repo(tmp)
            notice = self.run_goc(root).stderr.strip()
            refusal = self.run_goc(root, "new", "x", "--summary", "x").stderr.strip()
        self.assertTrue(notice.startswith("goc: "), notice)
        self.assertTrue(refusal.startswith("ERROR: "), refusal)
        self.assertEqual(notice.removeprefix("goc: "), refusal.removeprefix("ERROR: "))

    def test_json_stdout_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_goc(self.repo(tmp), "--ready", "--json")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("[]", result.stdout.strip())
        self.assertIn(MISSING_DECK_PHRASE, result.stderr)

    def test_existing_deck_stays_silent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.repo(tmp)
            (root / ".game-of-cards" / "deck").mkdir(parents=True)
            result = self.run_goc(root)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn(MISSING_DECK_PHRASE, result.stderr)

    def test_legacy_deck_stays_silent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.repo(tmp)
            (root / "deck").mkdir()
            result = self.run_goc(root)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn(MISSING_DECK_PHRASE, result.stderr)

    def test_every_preflight_routes_on_the_notice_phrase(self) -> None:
        # The phrase is the coupling: a Preflight that stops listing it, or a
        # notice that rewords it, leaves a deckless repo unrouted again.
        self.assertGreaterEqual(len(PREFLIGHT_SKILLS), 9, PREFLIGHT_SKILLS)
        missing = [
            str(path.relative_to(ROOT))
            for path in PREFLIGHT_SKILLS
            if f"`{MISSING_DECK_PHRASE}`" not in path.read_text(encoding="utf-8")
        ]
        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
