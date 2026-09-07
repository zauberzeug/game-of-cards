"""Regression: `goc upgrade` must repair a damaged install at the same version.

`upgrade()`'s "already at goc X — nothing to do" short-circuit used to be a
version comparison plus a hand-maintained allowlist of `pending_*` signals.
Four repair steps living below the `return` had no signal on that allowlist
(`_sync_agent_harness`, `_sync_game_of_cards_config`, `_sync_methodology_blocks`
and the *absent-config* half of `_append_precommit_hook`), so a repo whose
vendored skills, `.game-of-cards/` stubs, pre-commit stanza or AGENTS.md marker
block were deleted could never be re-synced — while `goc install` in that same
repo exited 1 naming `goc upgrade` as the remedy.

The fix derives the verdict from `_plan_upgrade_writes`, the same plan
`--dry-run` prints, with every write labelled by asking its executor (in probe
mode) whether it would change anything. The tests below pin all three halves of
that contract: the four repairs happen, the pristine no-op survives byte-exact,
and the guard reads the plan rather than a list of remembered signals.

Card: `goc-upgrade-cannot-repair-a-damaged-install-at-the-same-version`.
"""

from __future__ import annotations

import contextlib
import io
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import install as goc_install  # noqa: E402
from goc.install import PlannedWrite  # noqa: E402


@contextlib.contextmanager
def _chdir(path: Path):
    prev = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


def _quiet(fn, *args, **kwargs) -> str:
    with contextlib.redirect_stdout(io.StringIO()) as out:
        with contextlib.redirect_stderr(io.StringIO()):
            fn(*args, **kwargs)
    return out.getvalue()


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


def _install_current(repo: Path) -> None:
    """Vendored install in a git repo, pinned to the running engine version."""

    (repo / ".git").mkdir(exist_ok=True)
    with _chdir(repo), _engine_config_at(repo):
        _quiet(goc_install.install, local_skills=True)
    (repo / ".game-of-cards" / "deck" / ".goc-version").write_text(
        goc_install.__version__ + "\n"
    )


def _snapshot(repo: Path) -> dict[str, tuple[bytes, int]]:
    """Bytes and mtime of every tracked file, so a "no-op" can be proven byte-exact."""

    snap: dict[str, tuple[bytes, int]] = {}
    for path in sorted(repo.rglob("*")):
        if not path.is_file() or ".git" in path.relative_to(repo).parts:
            continue
        snap[str(path.relative_to(repo))] = (path.read_bytes(), path.stat().st_mtime_ns)
    return snap


def _destroy_marker_block(agents_md: Path) -> None:
    agents_md.write_text(
        re.sub(
            r"(<!-- BEGIN GOC [^>]*-->\n).*?(<!-- END GOC -->)",
            r"\1(block destroyed)\n\2",
            agents_md.read_text(),
            flags=re.S,
        )
    )


class UpgradeRepairsDamagedInstallTest(unittest.TestCase):
    """Each of the four repairs the old allowlist skipped, one test apiece."""

    def test_restores_deleted_vendored_skill_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _install_current(repo)
            skill = repo / ".claude" / "skills" / "deck"
            self.assertTrue(skill.is_dir(), msg="fixture did not vendor skills")
            for asset in sorted(skill.rglob("*"), reverse=True):
                asset.unlink() if asset.is_file() else asset.rmdir()
            skill.rmdir()

            with _chdir(repo), _engine_config_at(repo):
                _quiet(goc_install.upgrade)

            self.assertTrue((skill / "SKILL.md").is_file())

    def test_scaffolds_absent_project_state_stub(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _install_current(repo)
            stub = repo / ".game-of-cards" / "canonical-tags.md"
            stub.unlink()

            with _chdir(repo), _engine_config_at(repo):
                _quiet(goc_install.upgrade)

            self.assertTrue(stub.is_file())

    def test_regenerates_destroyed_marker_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _install_current(repo)
            agents_md = repo / "AGENTS.md"
            _destroy_marker_block(agents_md)

            with _chdir(repo), _engine_config_at(repo):
                _quiet(goc_install.upgrade)

            self.assertNotIn("(block destroyed)", agents_md.read_text())
            self.assertIn(goc_install.GOC_END, agents_md.read_text())

    def test_appends_absent_precommit_stanza(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _install_current(repo)
            precommit = repo / ".pre-commit-config.yaml"
            self.assertTrue(precommit.is_file(), msg="fixture did not write the stanza")
            precommit.unlink()

            with _chdir(repo), _engine_config_at(repo):
                _quiet(goc_install.upgrade)

            self.assertTrue(precommit.is_file())
            self.assertIn("id: goc-validate", precommit.read_text())

    def test_preserves_diverged_user_owned_stub_while_repairing(self) -> None:
        """The repair must not reopen the overwrite-authored-content defect."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _install_current(repo)
            authored = repo / ".game-of-cards" / "domain-vocabulary.md"
            authored.write_text("# my vocabulary\n\nhand-written, do not touch\n")
            (repo / ".game-of-cards" / "canonical-tags.md").unlink()

            with _chdir(repo), _engine_config_at(repo):
                _quiet(goc_install.upgrade)

            self.assertEqual(
                "# my vocabulary\n\nhand-written, do not touch\n", authored.read_text()
            )
            self.assertTrue((repo / ".game-of-cards" / "canonical-tags.md").is_file())


class UpgradeNoOpIsPreservedTest(unittest.TestCase):
    def test_pristine_repo_prints_nothing_to_do_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _install_current(repo)
            before = _snapshot(repo)

            with _chdir(repo), _engine_config_at(repo):
                out = _quiet(goc_install.upgrade)

            self.assertEqual(f"already at goc {goc_install.__version__} — nothing to do.\n", out)
            self.assertEqual(before, _snapshot(repo), msg="no-op upgrade touched files")

    def test_second_bare_upgrade_after_a_repair_is_a_no_op(self) -> None:
        """The repair run converges: nothing stays permanently pending."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _install_current(repo)
            (repo / ".game-of-cards" / "canonical-tags.md").unlink()

            with _chdir(repo), _engine_config_at(repo):
                _quiet(goc_install.upgrade)
                after_repair = _snapshot(repo)
                out = _quiet(goc_install.upgrade)

            self.assertIn("nothing to do", out)
            self.assertEqual(after_repair, _snapshot(repo))


class UpgradeGuardReadsThePlanTest(unittest.TestCase):
    def test_synthetic_pending_write_defeats_the_short_circuit(self) -> None:
        """A pending write no `pending_*` predicate names still defeats the guard.

        This is the forward guarantee: the next repair added to `upgrade()`
        cannot silently rejoin the skipped set, because the guard reads the
        plan rather than a list of signals somebody has to remember to extend.
        """
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _install_current(repo)

            real_plan = goc_install._plan_upgrade_writes

            def _plan_with_synthetic_pending(*args, **kwargs):
                writes = real_plan(*args, **kwargs)
                return [
                    *writes,
                    PlannedWrite(
                        "shared",
                        "create",
                        repo / "some-future-repair",
                        "project-state",
                        kind="future-repair",
                    ),
                ]

            goc_install._plan_upgrade_writes = _plan_with_synthetic_pending
            try:
                with _chdir(repo), _engine_config_at(repo):
                    out = _quiet(goc_install.upgrade)
            finally:
                goc_install._plan_upgrade_writes = real_plan

            self.assertNotIn("nothing to do", out)
            self.assertIn("goc upgrade complete", out)

    def test_plan_reports_absent_precommit_config_as_pending_append(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _install_current(repo)
            templates = goc_install._templates_root()
            precommit = repo / ".pre-commit-config.yaml"

            def _precommit_action() -> str:
                writes = goc_install._plan_upgrade_writes(
                    repo,
                    templates,
                    ("claude",),
                    local_skills_agents=frozenset({"claude"}),
                )
                return next(w.action for w in writes if w.path == precommit)

            self.assertEqual("unchanged", _precommit_action())
            precommit.unlink()
            self.assertEqual("append", _precommit_action())

    def test_plan_labels_a_current_harness_file_unchanged_and_a_deleted_one_sync(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _install_current(repo)
            templates = goc_install._templates_root()
            skill = repo / ".claude" / "skills" / "deck" / "SKILL.md"

            def _skill_action() -> str:
                writes = goc_install._plan_upgrade_writes(
                    repo,
                    templates,
                    ("claude",),
                    local_skills_agents=frozenset({"claude"}),
                )
                return next(w.action for w in writes if w.path == skill)

            self.assertEqual("unchanged", _skill_action())
            skill.unlink()
            self.assertEqual("sync", _skill_action())


class UpgradeDryRunAgreesWithRealRunTest(unittest.TestCase):
    def test_pristine_repo_dry_run_reports_the_same_no_op(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _install_current(repo)
            before = _snapshot(repo)

            with _chdir(repo), _engine_config_at(repo):
                preview = _quiet(goc_install.upgrade, dry_run=True)
                real = _quiet(goc_install.upgrade)

            self.assertIn("nothing to do", preview)
            self.assertEqual(preview, real)
            self.assertEqual(before, _snapshot(repo))

    def test_damaged_repo_dry_run_reports_the_work_the_real_run_performs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _install_current(repo)
            stub = repo / ".game-of-cards" / "canonical-tags.md"
            stub.unlink()
            before = _snapshot(repo)

            with _chdir(repo), _engine_config_at(repo):
                preview = _quiet(goc_install.upgrade, dry_run=True)
                self.assertEqual(before, _snapshot(repo), msg="dry-run wrote to disk")
                real = _quiet(goc_install.upgrade)

            self.assertNotIn("nothing to do", preview)
            self.assertIn("create .game-of-cards/canonical-tags.md", preview)
            self.assertNotIn("nothing to do", real)
            self.assertTrue(stub.is_file())


if __name__ == "__main__":
    unittest.main()
