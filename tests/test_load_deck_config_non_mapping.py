from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import engine


class LoadDeckConfigNonMappingTest(unittest.TestCase):
    """`load_deck_config()` must coerce a non-mapping / unparseable
    config.yaml to `{}` instead of returning a list/str (or raising).

    A bare-list or scalar `.game-of-cards/config.yaml` parses to a Python
    list/str; returning it unguarded crashed every caller's `.get()` —
    `auto_commit_enabled()` on every mutating verb, `get_skills_source()`
    in `goc validate` / `goc upgrade` — after the target card was already
    mutated on disk but before the auto-commit. Same bug class as the
    guarded canonical-tags loader.
    """

    def _load_with_config(self, text: str) -> dict:
        with tempfile.TemporaryDirectory() as d:
            cfg = Path(d) / "config.yaml"
            cfg.write_text(text)
            with mock.patch.object(engine, "GAME_OF_CARDS_CONFIG_FILE", cfg), \
                    mock.patch.object(
                        engine, "LEGACY_DECK_CONFIG_FILE",
                        Path(d) / "absent.yaml"):
                return engine.load_deck_config()

    def test_bare_list_coerces_to_empty_dict(self):
        self.assertEqual(self._load_with_config("- a\n- b\n"), {})

    def test_scalar_coerces_to_empty_dict(self):
        # A scalar config.yaml also raises a parse error in yaml_lite; the
        # loader must swallow it, not propagate a raw traceback.
        self.assertEqual(self._load_with_config("just a string\n"), {})

    def test_valid_mapping_is_preserved(self):
        self.assertEqual(
            self._load_with_config("skills_source: vendored\n"),
            {"skills_source": "vendored"},
        )

    def test_empty_file_coerces_to_empty_dict(self):
        self.assertEqual(self._load_with_config(""), {})

    def test_get_skills_source_survives_non_mapping_config(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Path(d) / "config.yaml"
            cfg.write_text("- a\n- b\n")
            with mock.patch.object(engine, "GAME_OF_CARDS_CONFIG_FILE", cfg), \
                    mock.patch.object(
                        engine, "LEGACY_DECK_CONFIG_FILE",
                        Path(d) / "absent.yaml"):
                # Would previously raise AttributeError: 'list' has no 'get'.
                self.assertEqual(
                    engine.get_skills_source(), engine.DEFAULT_SKILLS_SOURCE)


if __name__ == "__main__":
    unittest.main()
