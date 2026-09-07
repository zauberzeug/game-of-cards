"""Regression: `goc upgrade` must migrate a stale pre-commit goc-validate
stanza even when the repo is already at the current version.

`upgrade()`'s same-version "nothing to do" short-circuit used to return
before `_append_precommit_hook` ran, so a legacy `files: ^deck/.*$` glob
(predating the deck move to `.game-of-cards/deck/`) survived — leaving
the frontmatter-drift pre-commit hook silently matching no card path.
The fix adds a `pending_precommit_refresh` signal that defeats the
short-circuit only when a real drifted stanza needs fixing; a pristine,
already-current repo still takes the no-op path.

The same path now also carries the `files:` -> `always_run: true` migration
(`installed-pre-commit-hook-never-fires-on-anything-outside-the-deck-folder`),
so the assertions here compare against `PRE_COMMIT_HOOK` itself rather than a
literal glob that has to be edited every time the stanza evolves.

`pending_precommit_refresh` — and the `_precommit_refresh_pending` predicate
behind it — are gone as of
`goc-upgrade-cannot-repair-a-damaged-install-at-the-same-version`: the guard
now reads the upgrade write plan, which asks `_append_precommit_hook` itself
whether it would change the file. The two behavioral cases below are the
contract that survived the mechanism swap; the probe that replaced the
predicate is exercised directly at the bottom of this module.
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


@contextlib.contextmanager
def _engine_config_at(repo: Path):
    """Point the engine's config lookup at *repo*, as a fresh CLI process would.

    `goc.engine` resolves `GAME_OF_CARDS_CONFIG_FILE` once at import time from
    the then-current directory. Every real `goc` invocation is its own process,
    so that constant always matches the repo being operated on; an in-process
    test that chdir's into a temp repo inherits whichever directory imported
    the engine first, which would make `effective_skills_source()` — and so
    `upgrade()`'s vendored/plugin decision — depend on test ordering.
    """

    from goc import engine

    saved = (engine.GAME_OF_CARDS_CONFIG_FILE, engine.LEGACY_DECK_CONFIG_FILE)
    engine.GAME_OF_CARDS_CONFIG_FILE = repo / ".game-of-cards" / "config.yaml"
    engine.LEGACY_DECK_CONFIG_FILE = repo / ".claude" / "config.yaml"
    try:
        yield
    finally:
        engine.GAME_OF_CARDS_CONFIG_FILE, engine.LEGACY_DECK_CONFIG_FILE = saved


class UpgradePrecommitRefreshAtSameVersionTest(unittest.TestCase):
    def test_same_version_upgrade_migrates_stale_precommit_glob(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            with _chdir(repo), _engine_config_at(repo):
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
        self.assertIn(
            goc_install.PRE_COMMIT_HOOK, after, msg="current stanza missing after migration"
        )

    def test_pristine_current_repo_still_short_circuits(self) -> None:
        """A repo already current with an up-to-date pre-commit stanza takes
        the unchanged 'nothing to do' no-op path."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            with _chdir(repo), _engine_config_at(repo):
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

    def test_precommit_probe_reports_every_pending_case_and_writes_nothing(self) -> None:
        """`_append_precommit_hook(probe=True)` is the pure check that gates the guard.

        It answers for the whole branch tree the write takes, not just the
        drifted-stanza branch the retired `_precommit_refresh_pending` covered
        — an absent config and a config with no GoC stanza are pending work
        too, and skipping them is what left a deleted `.pre-commit-config.yaml`
        unrepairable.
        """
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            cfg = repo / ".pre-commit-config.yaml"

            # No .git → never pending.
            cfg.write_text(LEGACY_PRECOMMIT)
            self.assertFalse(goc_install._append_precommit_hook(cfg, probe=True))

            (repo / ".git").mkdir()
            # Drifted stanza → pending, and the probe leaves it drifted.
            self.assertTrue(goc_install._append_precommit_hook(cfg, probe=True))
            self.assertEqual(LEGACY_PRECOMMIT, cfg.read_text())

            # Current stanza → not pending (the write would be byte-identical).
            cfg.write_text("repos:\n" + goc_install.PRE_COMMIT_HOOK)
            self.assertFalse(goc_install._append_precommit_hook(cfg, probe=True))

            # Absent file / no goc-validate stanza → pending, nothing written.
            cfg.unlink()
            self.assertTrue(goc_install._append_precommit_hook(cfg, probe=True))
            self.assertFalse(cfg.exists())
            cfg.write_text("repos: []\n")
            self.assertTrue(goc_install._append_precommit_hook(cfg, probe=True))
            self.assertEqual("repos: []\n", cfg.read_text())


if __name__ == "__main__":
    unittest.main()
