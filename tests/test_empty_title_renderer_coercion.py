from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import engine  # noqa: E402


BARE_TITLE_CARD = (
    "---\n"
    "title:\n"  # bare title -> parses to None
    "status: open\n"
    "stage: null\n"
    "contribution: medium\n"
    "created: \"2026-01-01\"\n"
    "closed_at: null\n"
    "human_gate: none\n"
    "advances: []\n"
    "advanced_by: []\n"
    "tags: [bug]\n"
    "definition_of_done: |\n"
    "  - [ ] PROCESS: fixture\n"
    "---\n\n"
    "Body.\n"
)


def _write_card(cwd: Path, dirname: str, text: str) -> Path:
    card_dir = cwd / ".game-of-cards" / "deck" / dirname
    card_dir.mkdir(parents=True)
    (card_dir / "README.md").write_text(text)
    (card_dir / "log.md").write_text("")
    return card_dir


def _run_validate(cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", "validate", "--quiet"],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


class EmptyTitleRendererCoercionTest(unittest.TestCase):
    """A bare `title:` parses to None with the key present, so the old
    `fm.get("title", card_dir.name)` returned None (the default only applies
    when the key is absent). That None then crashed `render_table` /
    `render_board` for the WHOLE deck via `_display_width`, defeating the
    one-broken-card-doesn't-blank-the-queue design of `load_all_cards`.
    `title` is now coerced to the dir name, mirroring the sibling
    status/contribution/human_gate properties — while `goc validate` still
    flags the malformed title from the raw `fm["title"]`."""

    def test_bare_title_coerces_to_dir_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            card_dir = _write_card(Path(tmp), "card-with-empty-title", BARE_TITLE_CARD)
            card = engine.load_card(card_dir)
            self.assertIsNotNone(card)
            self.assertEqual(card.title, "card-with-empty-title")

    def test_bare_title_renders_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _write_card(cwd, "card-with-empty-title", BARE_TITLE_CARD)
            saved = engine.DECK_DIR
            try:
                engine.DECK_DIR = cwd / ".game-of-cards" / "deck"
                cards = engine.load_all_cards()
                # Neither renderer should raise on the None-title card.
                table = engine.render_table(cards, verbose=0, no_color=True)
                board = engine.render_board(cards, max_rows=20, no_color=True)
            finally:
                engine.DECK_DIR = saved
            self.assertIn("card-with-empty-title", table)
            self.assertIn("card-with-empty-title", board)

    def test_validate_still_flags_the_malformed_title(self) -> None:
        # Coercion protects only the renderers; the malformed title must still
        # be reported by `goc validate`, which reads the raw `fm["title"]`.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _write_card(cwd, "card-with-empty-title", BARE_TITLE_CARD)
            result = _run_validate(cwd)
            self.assertNotEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertIn("title:", result.stderr)


if __name__ == "__main__":
    unittest.main()
