"""Regression: the upgrade write plan must carry the skill-tree prune.

`_sync_skill_tree(replace_skills=True)` `shutil.rmtree`s each *eligible*
(current-GoC-template) skill directory before recopying it, so a file inside a
GoC-owned skill dir that the templates no longer ship — the shape any release
retiring a skill asset leaves in a vendored consumer — is deleted by
`goc upgrade`. That deletion used to be invisible to `_plan_upgrade_writes`,
which enumerated one entry per *template* file and so had nothing to derive a
destination-only orphan from. One omission, two consequences:

1. `goc upgrade --dry-run` printed a write count that excluded the deletion and
   named it on no line, then the real run removed a file the preview never
   mentioned.
2. `upgrade()` reads its "already at goc X — nothing to do" verdict off that
   same plan, so at the *same* version the stale file survived — while the
   identical damage was repaired at any other sentinel value.

The fix plans the prune: `_sync_skill_tree(probe=True)` returns the paths its
wipe-and-recopy would delete, and `_plan_skill_prunes` turns each into a
`skill-prune` `PlannedWrite` with action `delete`. `_print_plan` and
`plan_has_effect` needed no change — which is the point of the plan-derived
design the predecessor card
`goc-upgrade-cannot-repair-a-damaged-install-at-the-same-version` installed.

Card: `upgrade-write-plan-omits-the-skill-tree-prune-from-dry-run-and-no-op-verdict`.
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

# A GoC-owned skill dir, and a file inside it the current templates do not ship.
SKILL_DIR = Path(".claude") / "skills" / "deck"
STALE = SKILL_DIR / "reference-v1.md"


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
    the then-current directory, so an in-process test that chdir's into a temp
    repo would otherwise inherit whichever directory imported the engine first
    — making `effective_skills_source()`, and so `upgrade()`'s vendored/plugin
    decision, depend on test ordering.
    """

    from goc import engine

    saved = (engine.GAME_OF_CARDS_CONFIG_FILE, engine.LEGACY_DECK_CONFIG_FILE)
    engine.GAME_OF_CARDS_CONFIG_FILE = repo / ".game-of-cards" / "config.yaml"
    engine.LEGACY_DECK_CONFIG_FILE = repo / ".claude" / "config.yaml"
    try:
        yield
    finally:
        engine.GAME_OF_CARDS_CONFIG_FILE, engine.LEGACY_DECK_CONFIG_FILE = saved


def _install_vendored(repo: Path) -> None:
    """Vendored install in a git repo, pinned to the running engine version."""

    (repo / ".git").mkdir(exist_ok=True)
    with _chdir(repo), _engine_config_at(repo):
        _quiet(goc_install.install, local_skills=True)
    _pin_sentinel(repo, goc_install.__version__)


def _pin_sentinel(repo: Path, version: str) -> None:
    (repo / ".game-of-cards" / "deck" / ".goc-version").write_text(version + "\n")


def _plant_stale(repo: Path) -> Path:
    stale = repo / STALE
    stale.write_text("guidance the current templates no longer ship\n")
    return stale


def _upgrade_plan(repo: Path) -> list[goc_install.PlannedWrite]:
    return goc_install._plan_upgrade_writes(
        repo,
        goc_install._templates_root(),
        ("claude",),
        local_skills_agents=frozenset({"claude"}),
    )


def _prunes(repo: Path) -> list[goc_install.PlannedWrite]:
    return [w for w in _upgrade_plan(repo) if w.kind == "skill-prune"]


def _effecting(plan_output: str) -> int:
    """The dry-run headline's effecting count (`_print_plan` omits it at 100%)."""

    headline = next(ln for ln in plan_output.splitlines() if "writes planned" in ln)
    match = re.search(r"\((\d+) effecting\)", headline)
    return int(match.group(1)) if match else int(re.search(r"(\d+) writes planned", headline).group(1))


class UpgradePlanCarriesTheSkillPruneTest(unittest.TestCase):
    def test_plan_is_prune_free_when_the_tree_matches_the_templates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _install_vendored(repo)

            self.assertEqual([], _prunes(repo))

    def test_plan_emits_an_effecting_delete_for_an_orphan_in_a_goc_skill_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _install_vendored(repo)
            stale = _plant_stale(repo)

            prunes = _prunes(repo)

            self.assertEqual([stale], [w.path for w in prunes])
            self.assertEqual("delete", prunes[0].action)
            self.assertNotIn(prunes[0].action, goc_install._NO_OP_ACTIONS)
            self.assertEqual("harness", prunes[0].category)
            self.assertTrue(stale.is_file(), msg="planning deleted the file")

    def test_plan_leaves_orphans_in_user_owned_skill_dirs_alone(self) -> None:
        """The executor never rmtrees a non-eligible dir, so the plan must not
        promise to — the inverse defect of the one this card fixes."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _install_vendored(repo)
            mine = repo / ".claude" / "skills" / "my-tool"
            mine.mkdir(parents=True)
            (mine / "SKILL.md").write_text("# My custom tool\n")

            self.assertEqual([], _prunes(repo))

    def test_plugin_mode_plans_no_prune(self) -> None:
        """Plugin-mode upgrade skips the skill tree entirely (`guidance_only`),
        so nothing is pruned and nothing may be planned."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _install_vendored(repo)
            _plant_stale(repo)

            plan = goc_install._plan_upgrade_writes(
                repo,
                goc_install._templates_root(),
                ("claude",),
                local_skills_agents=frozenset(),
            )

            self.assertEqual([], [w for w in plan if w.kind == "skill-prune"])


class SameVersionUpgradeRepairsTheSkillTreeTest(unittest.TestCase):
    def test_bare_upgrade_at_the_same_version_removes_the_stale_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _install_vendored(repo)
            stale = _plant_stale(repo)

            with _chdir(repo), _engine_config_at(repo):
                out = _quiet(goc_install.upgrade)

            self.assertNotIn("nothing to do", out)
            self.assertFalse(stale.exists())
            self.assertTrue((repo / SKILL_DIR / "SKILL.md").is_file())

    def test_undamaged_repo_at_the_same_version_still_short_circuits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _install_vendored(repo)

            with _chdir(repo), _engine_config_at(repo):
                out = _quiet(goc_install.upgrade)

            self.assertIn("nothing to do", out)


class DryRunNamesTheDeletionTest(unittest.TestCase):
    def test_dry_run_lists_the_deletion_and_counts_it_as_effecting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _install_vendored(repo)
            # An older sentinel so the preview prints a plan rather than the
            # same-version no-op — the reader this defect misled at any version.
            _pin_sentinel(repo, "0.0.1")

            with _chdir(repo), _engine_config_at(repo):
                baseline = _quiet(goc_install.upgrade, dry_run=True)
                stale = _plant_stale(repo)
                preview = _quiet(goc_install.upgrade, dry_run=True)

            self.assertNotIn(str(STALE), baseline)
            self.assertIn(f"delete {STALE}", preview)
            self.assertEqual(_effecting(baseline) + 1, _effecting(preview))
            self.assertTrue(stale.is_file(), msg="dry-run performed the deletion")

    def test_dry_run_and_real_run_agree_on_the_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _install_vendored(repo)
            stale = _plant_stale(repo)

            with _chdir(repo), _engine_config_at(repo):
                preview = _quiet(goc_install.upgrade, dry_run=True)
                self.assertTrue(stale.is_file(), msg="dry-run wrote to disk")
                _quiet(goc_install.upgrade)

            self.assertIn(f"delete {STALE}", preview)
            self.assertFalse(stale.exists())


class SkillTreeProbeTest(unittest.TestCase):
    def test_probe_reports_the_orphans_the_real_sync_deletes_and_writes_nothing(self) -> None:
        """The plan and the deletion come from one call, so they cannot drift."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _install_vendored(repo)
            stale = _plant_stale(repo)
            templates = goc_install._templates_root()
            skills_dst = repo / ".claude" / "skills"

            probed = goc_install._sync_skill_tree(
                templates, skills_dst, "claude", replace_skills=True, probe=True
            )
            self.assertEqual([stale], probed)
            self.assertTrue(stale.is_file(), msg="probe touched the filesystem")

            deleted = goc_install._sync_skill_tree(
                templates, skills_dst, "claude", replace_skills=True
            )

            self.assertEqual(probed, deleted)
            self.assertFalse(stale.exists())
            self.assertEqual(
                [], goc_install._sync_skill_tree(
                    templates, skills_dst, "claude", replace_skills=True, probe=True
                )
            )

    def test_probe_without_replace_skills_reports_nothing(self) -> None:
        """`goc install` copies without wiping, so it deletes — and plans — nothing."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _install_vendored(repo)
            _plant_stale(repo)

            self.assertEqual(
                [],
                goc_install._sync_skill_tree(
                    goc_install._templates_root(),
                    repo / ".claude" / "skills",
                    "claude",
                    probe=True,
                ),
            )


if __name__ == "__main__":
    unittest.main()
