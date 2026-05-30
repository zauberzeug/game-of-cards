"""Regression: `goc upgrade` must never overwrite authored project-state.

The 12 user-owned files under `.game-of-cards/` (6 content stubs + 6
workflow hooks) plus the 2 evolving files (`README.md`, `config.yaml`)
all carry authored content in real downstream repos. The bug under fix
was a blind `_copy_tree` over those files on upgrade. This test pins
the unconditional safety guarantee: every file the consumer authored
survives a cross-version upgrade, and the absent-stub scaffolding still
works for new-in-version files.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import install as goc_install  # noqa: E402

USER_OWNED_STUBS = (
    "canonical-tags.md",
    "domain-vocabulary.md",
    "domain-examples.md",
    "file-path-map.md",
    "tooling-conventions.md",
    "documentation-conventions.md",
)
USER_OWNED_HOOKS = (
    "hooks/audit-deck.md",
    "hooks/create-card.md",
    "hooks/decide-card.md",
    "hooks/finish-card.md",
    "hooks/pull-card.md",
    "hooks/refine-deck.md",
)
EVOLVING_FILES = ("README.md", "config.yaml")


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


class UpgradePreservesUserOwnedContentTest(unittest.TestCase):
    def test_all_twelve_user_owned_files_survive_cross_version_upgrade(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            with _chdir(repo):
                _quiet(goc_install.install)

                authored = {}
                for rel in (*USER_OWNED_STUBS, *USER_OWNED_HOOKS):
                    body = f"# authored content for {rel}\n\nsentinel-{rel}\n"
                    (repo / ".game-of-cards" / rel).write_text(body)
                    authored[rel] = body

                # Force a real upgrade pass (versions equal → short-circuits).
                (repo / ".game-of-cards" / "deck" / ".goc-version").write_text("0.0.1\n")

                _quiet(goc_install.upgrade)

                for rel, expected in authored.items():
                    got = (repo / ".game-of-cards" / rel).read_text()
                    self.assertEqual(expected, got, msg=f"clobbered: {rel}")

    def test_diverged_evolving_files_are_preserved(self) -> None:
        """README.md and config.yaml are 'evolving' — engine still preserves them.

        The `Skill(upgrade)` reconciliation pass is the place where upstream
        changes to these files merge into the local copy. The engine itself
        is unconditionally safe: it never blind-copies the template over the
        consumer's bytes. `config.yaml` is the documented exception that the
        engine *targeted*-mutates (only its `skills_source:` key) — the
        consumer's other content must survive that targeted edit.
        """
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            with _chdir(repo):
                _quiet(goc_install.install)

                customized = {}
                for rel in EVOLVING_FILES:
                    body = f"# customized {rel}\n\nlocal-edits\n"
                    (repo / ".game-of-cards" / rel).write_text(body)
                    customized[rel] = body

                (repo / ".game-of-cards" / "deck" / ".goc-version").write_text("0.0.1\n")

                _quiet(goc_install.upgrade)

                # README.md: engine touches nothing → byte-identical survival.
                self.assertEqual(
                    customized["README.md"],
                    (repo / ".game-of-cards" / "README.md").read_text(),
                )
                # config.yaml: engine targeted-mutates the `skills_source` key
                # only. The user's content (header + body) must survive that.
                config_after = (repo / ".game-of-cards" / "config.yaml").read_text()
                self.assertIn("# customized config.yaml", config_after)
                self.assertIn("local-edits", config_after)

    def test_absent_user_owned_file_is_scaffolded_on_upgrade(self) -> None:
        """A new-in-version stub or hook absent on disk must still be scaffolded."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            with _chdir(repo):
                _quiet(goc_install.install)

                # Simulate "this file is new in the current version" by deleting
                # a freshly-scaffolded stub from disk. The upgrade should put it back.
                stub = repo / ".game-of-cards" / "canonical-tags.md"
                hook = repo / ".game-of-cards" / "hooks" / "audit-deck.md"
                stub.unlink()
                hook.unlink()

                (repo / ".game-of-cards" / "deck" / ".goc-version").write_text("0.0.1\n")

                _quiet(goc_install.upgrade)

                self.assertTrue(stub.is_file(), msg="absent stub not scaffolded on upgrade")
                self.assertTrue(hook.is_file(), msg="absent hook not scaffolded on upgrade")

    def test_pristine_user_owned_file_is_left_alone_no_op(self) -> None:
        """A byte-identical (pristine) stub is a no-op — neither rewritten nor mangled."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            with _chdir(repo):
                _quiet(goc_install.install)

                stub = repo / ".game-of-cards" / "canonical-tags.md"
                pristine = stub.read_bytes()
                mtime_before = stub.stat().st_mtime

                (repo / ".game-of-cards" / "deck" / ".goc-version").write_text("0.0.1\n")

                _quiet(goc_install.upgrade)

                self.assertEqual(pristine, stub.read_bytes())
                # Same bytes — the classification was `unchanged`, so the file
                # was not rewritten. mtime is allowed to be equal or unchanged.
                self.assertLessEqual(stub.stat().st_mtime, mtime_before + 5)


class UpgradeDivergenceReportTest(unittest.TestCase):
    def test_upgrade_emits_machine_readable_divergence_report(self) -> None:
        """The `upgrade` skill consumes a JSON report on stdout under a sentinel marker."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            with _chdir(repo):
                _quiet(goc_install.install)

                (repo / ".game-of-cards" / "canonical-tags.md").write_text(
                    "# customized\n"
                )
                (repo / ".game-of-cards" / "README.md").write_text("# customized\n")
                (repo / ".game-of-cards" / "hooks" / "audit-deck.md").unlink()
                (repo / ".game-of-cards" / "deck" / ".goc-version").write_text("0.0.1\n")

                out = _quiet(goc_install.upgrade)

            self.assertIn("GoC project-state divergence report (JSON):", out)

            lines = out.splitlines()
            for idx, line in enumerate(lines):
                if "GoC project-state divergence report (JSON):" in line:
                    payload = json.loads(lines[idx + 1])
                    break
            else:
                self.fail("divergence report sentinel not found in upgrade output")

            self.assertEqual(1, payload["version"])
            self.assertIn("templates_root", payload)
            by_path = {f["path"]: f for f in payload["files"]}

            self.assertEqual("preserved", by_path["canonical-tags.md"]["status"])
            self.assertEqual("user-owned", by_path["canonical-tags.md"]["ownership"])

            self.assertEqual("preserved", by_path["README.md"]["status"])
            self.assertEqual("evolving", by_path["README.md"]["ownership"])

            self.assertEqual("create", by_path["hooks/audit-deck.md"]["status"])
            self.assertEqual("user-owned", by_path["hooks/audit-deck.md"]["ownership"])


class UpgradeDryRunPlanAccuracyTest(unittest.TestCase):
    def test_dry_run_labels_each_project_state_file_with_ownership_aware_action(self) -> None:
        """`_plan_upgrade_writes` reports create / unchanged / preserved per file."""
        from goc.install import _plan_upgrade_writes, _templates_root

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            with _chdir(repo):
                _quiet(goc_install.install)

                (repo / ".game-of-cards" / "canonical-tags.md").write_text("# customized\n")
                (repo / ".game-of-cards" / "hooks" / "audit-deck.md").unlink()

                templates = _templates_root()
                writes = _plan_upgrade_writes(repo, templates, ("claude",))

            actions = {
                str(w.path.relative_to(repo)): w.action
                for w in writes
                if w.category == "project-state"
            }
            self.assertEqual("preserved", actions[".game-of-cards/canonical-tags.md"])
            self.assertEqual("create", actions[".game-of-cards/hooks/audit-deck.md"])
            self.assertEqual("unchanged", actions[".game-of-cards/hooks/finish-card.md"])
            # config.yaml is preserved because install's _write_skills_source
            # diverges it from the shipped template (skills_source: plugin gets
            # added). The plan must surface that as `preserved`, not `sync`.
            self.assertEqual("preserved", actions[".game-of-cards/config.yaml"])


if __name__ == "__main__":
    unittest.main()
