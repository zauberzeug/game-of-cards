from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from goc import install  # noqa: E402


class UpgradeBriefingTargetPickerTest(unittest.TestCase):
    """`_resolve_upgrade_briefing_target` advertises a 1-based `Pick [1-N]`
    prompt. Because the selection used `found[int(raw) - 1]`, Python negative
    indexing let `0` resolve to the last candidate and negatives wrap around,
    silently selecting the wrong briefing home instead of aborting. The picker
    must bounds-check and route out-of-range input into the existing abort
    branch (`sys.exit(2)`).
    """

    FOUND = ("AGENTS.md", "CLAUDE.md", "CLAUDE.local.md")

    def _run_picker(self, raw: str):
        orig_stdin = sys.stdin
        orig_detect = install._detect_briefing_targets_on_disk
        orig_stdout = sys.stdout
        sys.stdin = io.StringIO(raw + "\n")
        sys.stdout = io.StringIO()  # silence the picker's prompt output
        install._detect_briefing_targets_on_disk = lambda target: self.FOUND
        try:
            return install._resolve_upgrade_briefing_target(
                Path("."), explicit_target=None, dry_run=False
            )
        finally:
            sys.stdin = orig_stdin
            sys.stdout = orig_stdout
            install._detect_briefing_targets_on_disk = orig_detect

    def test_zero_aborts(self) -> None:
        with self.assertRaises(SystemExit) as cm:
            self._run_picker("0")
        self.assertEqual(cm.exception.code, 2)

    def test_negative_aborts(self) -> None:
        with self.assertRaises(SystemExit) as cm:
            self._run_picker("-1")
        self.assertEqual(cm.exception.code, 2)

    def test_out_of_range_positive_aborts(self) -> None:
        with self.assertRaises(SystemExit) as cm:
            self._run_picker("99")
        self.assertEqual(cm.exception.code, 2)

    def test_in_range_selection_still_works(self) -> None:
        self.assertEqual(self._run_picker("2"), "CLAUDE.md")

    def test_empty_defaults_to_first(self) -> None:
        self.assertEqual(self._run_picker(""), "AGENTS.md")


if __name__ == "__main__":
    unittest.main()
