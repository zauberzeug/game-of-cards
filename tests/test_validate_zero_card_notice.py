"""`goc validate` must say when it validated no cards — regression guard for
`goc-validate-reports-a-clean-pass-when-it-validated-no-cards`.

Every signal `_cmd_validate` emits is per-card (`OK  <title>` / `ERROR:`), so a
run that walked zero cards used to write nothing at all and exit 0 — byte-identical
to a clean pass over a real deck. That silence is a false green wherever DECK_DIR
resolved somewhere unintended: `goc install` writes a `pass_filenames: false`
pre-commit hook, so the hook (and CI) inherits whatever deck the cwd produced and
never learns which one it checked.

The three states are asserted together so they cannot drift back into each other,
and the exit codes are pinned alongside the text: the notice must not turn an
empty deck into a failure (`goc install` → `goc validate` is the sequence
Skill(kickoff) walks a new user through), and must not mask a real error.
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

CARD = """---
title: {title}
summary: "Summary for {title}."
status: open
stage: null
contribution: medium
created: "2026-08-01T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] TDD: something
---

# {title}
"""

BROKEN_CARD = CARD.replace("contribution: medium", "contribution: gigantic")


class ValidateZeroCardNoticeTest(unittest.TestCase):
    """A card-less run states its outcome; a card-bearing run is untouched."""

    def run_validate(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", "validate", *args],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def write_card(self, repo: Path, title: str, body: str = CARD) -> None:
        card_dir = repo / ".game-of-cards" / "deck" / title
        card_dir.mkdir(parents=True, exist_ok=True)
        (card_dir / "README.md").write_text(body.format(title=title), encoding="utf-8")
        (card_dir / "log.md").write_text("", encoding="utf-8")

    def test_scaffolded_but_empty_deck_states_the_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".game-of-cards" / "deck").mkdir(parents=True)
            r = self.run_validate(repo)
            self.assertEqual(0, r.returncode, r.stderr)
            self.assertIn("validated 0 cards", r.stderr)

    def test_missing_deck_states_the_outcome_and_names_the_path(self) -> None:
        """The dangerous case: nothing on disk, and the old code said nothing."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            r = self.run_validate(repo)
            self.assertEqual(0, r.returncode, r.stderr)
            self.assertIn("validated 0 cards", r.stderr)
            # Naming the searched path is what separates "the deck is empty"
            # from "I am standing in the wrong tree".
            self.assertIn(str(repo / ".game-of-cards" / "deck"), r.stderr)

    def test_card_bearing_deck_is_unchanged(self) -> None:
        """The other half of the contract — a real run must not gain the notice."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.write_card(repo, "alpha")
            r = self.run_validate(repo)
            self.assertEqual(0, r.returncode, r.stderr)
            self.assertIn("OK  alpha", r.stdout)
            self.assertNotIn("validated 0 cards", r.stderr)

    def test_the_three_states_are_distinguishable(self) -> None:
        """The defect itself: empty, missing and populated rendered identically."""
        with tempfile.TemporaryDirectory() as tmp:
            populated = Path(tmp) / "populated"
            self.write_card(populated, "alpha")
            empty = Path(tmp) / "empty"
            (empty / ".game-of-cards" / "deck").mkdir(parents=True)
            missing = Path(tmp) / "missing"
            missing.mkdir()

            renders = [
                self.run_validate(p).stdout + self.run_validate(p).stderr
                for p in (populated, empty, missing)
            ]
            self.assertEqual(3, len(set(renders)), renders)
            for render in renders:
                self.assertNotEqual("", render)

    def test_notice_survives_quiet_while_ok_lines_do_not(self) -> None:
        """`--quiet` is where the false green is worst: silence IS its success."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            r = self.run_validate(repo, "--quiet")
            self.assertEqual(0, r.returncode, r.stderr)
            self.assertIn("validated 0 cards", r.stderr)

            populated = Path(tmp) / "populated"
            self.write_card(populated, "alpha")
            q = self.run_validate(populated, "--quiet")
            self.assertEqual(0, q.returncode, q.stderr)
            self.assertNotIn("OK  alpha", q.stdout)

    def test_notice_goes_to_stderr_leaving_stdout_untouched(self) -> None:
        """Warnings already use stderr; stdout stays what OK-line consumers parse."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            r = self.run_validate(repo)
            self.assertEqual("", r.stdout)
            self.assertIn("validated 0 cards", r.stderr)

    def test_a_real_error_still_exits_nonzero(self) -> None:
        """The notice must not be reachable in a way that masks a failure."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.write_card(repo, "alpha", BROKEN_CARD)
            r = self.run_validate(repo)
            self.assertEqual(1, r.returncode, r.stderr)
            self.assertNotIn("validated 0 cards", r.stderr)


if __name__ == "__main__":
    unittest.main()
