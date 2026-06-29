"""Regression: `goc upgrade` must migrate a stale pre-commit goc-validate
glob even when the repo is already at the current version.

`upgrade()`'s same-version "nothing to do" short-circuit used to return
before `_append_precommit_hook` ran, so a legacy `files: ^deck/.*$` glob
(predating the deck move to `.game-of-cards/deck/`) survived — leaving
the frontmatter-drift pre-commit hook silently matching no card path.
The fix adds a `pending_precommit_refresh` signal that defeats the
short-circuit only when a real drifted stanza needs fixing; a pristine,
already-current repo still takes the no-op path.
"""

from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import install as goc_install  # noqa: E402

LEGACY_GLOB = "files: ^deck/.*$"
NEW_GLOB = "files: ^\\.game-of-cards/deck/.*$"

LEGACY_PRECOMMIT = (
    "repos:\n"
    "  - repo: local\n"
    "    hooks:\n"
    "      - id: goc-validate\n"
    "        name: goc validate\n"
    "        entry: goc validate\n"
    "        language: system\n"
    "        pass_filenames: false\n"
    "        files: ^deck/.*$\n"
)


@contextlib.contextmanager
def _chdir(path: Path):
    prev = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


def _quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        fn(*args, **kwargs)
    return buf.getvalue()


class UpgradePrecommitRefreshAtSameVersionTest(unittest.TestCase):
    def test_same_version_upgrade_migrates_stale_precommit_glob(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            with _chdir(repo):
                _quiet(goc_install.install)
                (repo / ".git").mkdir(exist_ok=True)
                precommit = repo / ".pre-commit-config.yaml"
                precommit.write_text(LEGACY_PRECOMMIT)
                # Same version → the short-circuit is what gates behavior.
                (repo / ".game-of-cards" / "deck" / ".goc-version").write_text(
                    goc_install.__version__ + "\n"
                )

                _quiet(goc_install.upgrade)

                after = precommit.read_text()

        self.assertNotIn(LEGACY_GLOB, after, msg="stale glob was not migrated")
        self.assertIn(NEW_GLOB, after, msg="migrated glob missing")

    def test_pristine_current_repo_still_short_circuits(self) -> None:
        """A repo already current with an up-to-date pre-commit stanza takes
        the unchanged 'nothing to do' no-op path."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            with _chdir(repo):
                _quiet(goc_install.install)
                (repo / ".git").mkdir(exist_ok=True)
                precommit = repo / ".pre-commit-config.yaml"
                # Current (non-stale) stanza — refresh would be a no-op.
                precommit.write_text("repos:\n" + goc_install.PRE_COMMIT_HOOK)
                before = precommit.read_text()
                (repo / ".game-of-cards" / "deck" / ".goc-version").write_text(
                    goc_install.__version__ + "\n"
                )

                out = _quiet(goc_install.upgrade)

                after = precommit.read_text()

        self.assertIn("nothing to do", out)
        self.assertEqual(before, after)

    def test_precommit_refresh_pending_pure_check(self) -> None:
        """_precommit_refresh_pending is true only for a real drifted stanza."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            cfg = repo / ".pre-commit-config.yaml"

            # No .git → never pending.
            cfg.write_text(LEGACY_PRECOMMIT)
            self.assertFalse(goc_install._precommit_refresh_pending(cfg))

            (repo / ".git").mkdir()
            # Drifted stanza → pending.
            self.assertTrue(goc_install._precommit_refresh_pending(cfg))

            # Current stanza → not pending (would be a byte-identical no-op).
            cfg.write_text("repos:\n" + goc_install.PRE_COMMIT_HOOK)
            self.assertFalse(goc_install._precommit_refresh_pending(cfg))

            # Absent file / no goc-validate stanza → not pending.
            cfg.unlink()
            self.assertFalse(goc_install._precommit_refresh_pending(cfg))
            cfg.write_text("repos: []\n")
            self.assertFalse(goc_install._precommit_refresh_pending(cfg))


if __name__ == "__main__":
    unittest.main()
