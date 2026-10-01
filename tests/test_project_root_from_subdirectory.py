"""Every notion of "the project root" follows the deck walk from a subdirectory.

`_resolve_deck_root` (`goc/engine.py`) walks from cwd to the nearest ancestor
holding `.game-of-cards/`. Before goc-finds-the-deck-from-a-subdirectory-but-
attests-validates-and-installs-there, only `DECK_ROOT` followed it: `REPO_ROOT`,
the installer's target and the hooks' project dir all stayed the current
directory. Run from `src/pkg/`, `goc attest` ran the project's closure checks
there, `goc validate` skipped its vendored skill-parity check, `goc upgrade`
reported no install and `goc install` scaffolded a stray nested deck, and the
session-start hook stayed silent about the active card.

These tests run each root reader from a subdirectory and require the root
run's answer. Under the shared-deck worktree redirect the root is the linked
worktree's own checkout, not the primary tree that holds the deck.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import engine  # noqa: E402

HOOKS = ROOT / "goc" / "templates" / "hooks"
CARD = "fixture-card"

# The closure check's only input is its working directory, printed between
# delimiters so a root path never matches as a prefix of a subdirectory path.
WHERE_CHECK = "import os; print('ran-in:<' + os.getcwd() + '>')"


def _env(home: Path, **extra: str) -> dict:
    env = dict(os.environ, PYTHONPATH=str(ROOT), HOME=str(home))
    for key in ("GOC_WORKER", "GOC_WORKTREE_DECK", "CLAUDE_PROJECT_DIR",
                "CODEX_PROJECT_DIR", "CLAUDE_PLUGIN_ROOT"):
        env.pop(key, None)
    env.update(extra)
    return env


def _load_hook(name: str):
    spec = importlib.util.spec_from_file_location(f"_hook_{name}", HOOKS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Fixture(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self.sub = self.repo / "src" / "pkg"
        self.sub.mkdir(parents=True)
        self.env = _env(self.home)

    def git(self, cwd: Path, *args: str) -> None:
        subprocess.run(["git", *args], cwd=cwd, env=self.env, check=True,
                       capture_output=True, text=True)

    def goc(self, cwd: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-m", "goc.cli", *args], cwd=cwd,
                              env=env or self.env, capture_output=True, text=True)

    def assert_ok(self, r: subprocess.CompletedProcess) -> None:
        self.assertEqual(0, r.returncode, msg=f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}")

    def init_repo(self, root: Path) -> None:
        self.git(root, "init", "-q")
        self.git(root, "config", "user.email", "probe@example.invalid")
        self.git(root, "config", "user.name", "probe")
        self.git(root, "config", "commit.gpgsign", "false")

    def make_deck_with_check(self, root: Path) -> None:
        """A deck whose layer-2 closure check reports the directory it ran in."""
        (root / ".game-of-cards" / "deck").mkdir(parents=True)
        cmd = ", ".join(f'"{part}"' for part in (sys.executable, "-c", WHERE_CHECK))
        (root / ".game-of-cards" / "config.yaml").write_text(
            "layer_2_project_dod:\n"
            "  - name: where-it-ran\n"
            "    kind: automated\n"
            f"    cmd: [{cmd}]\n"
            "layer_3_goc_dod: []\n"
        )
        self.assert_ok(self.goc(root, "new", CARD, "--summary", "Fixture card.",
                                "--gate", "none", "--no-commit"))

    def ran_in(self, r: subprocess.CompletedProcess) -> str:
        out = r.stdout + r.stderr
        self.assertIn("ran-in:<", out, msg=out)
        return out.split("ran-in:<", 1)[1].split(">", 1)[0]


class AttestRunsChecksInTheProjectRootTest(_Fixture):
    def test_attest_from_a_subdirectory_runs_the_check_in_the_project_root(self) -> None:
        self.init_repo(self.repo)
        self.make_deck_with_check(self.repo)

        r = self.goc(self.sub, "attest", CARD, "--non-interactive")
        self.assertEqual(str(self.repo), self.ran_in(r))

    def test_attest_under_shared_deck_mode_runs_in_the_linked_worktree_root(self) -> None:
        self.init_repo(self.repo)
        self.make_deck_with_check(self.repo)
        (self.sub / "mod.py").write_text("VALUE = 1\n")
        self.git(self.repo, "add", "-A")
        self.git(self.repo, "commit", "-q", "-m", "fixture")
        worktree = self.tmp / "linked"
        self.git(self.repo, "worktree", "add", "-q", str(worktree))

        env = _env(self.home, GOC_WORKTREE_DECK="shared")
        r = self.goc(worktree / "src" / "pkg", "attest", CARD, "--non-interactive", env=env)
        self.assertEqual(str(worktree), self.ran_in(r))
        # The deck itself is still the primary tree's: the attestation landed there.
        log = self.repo / ".game-of-cards" / "deck" / CARD / "log.md"
        self.assertIn("where-it-ran", log.read_text())


class InstalledRepoFromSubdirectoryTest(_Fixture):
    def setUp(self) -> None:
        super().setUp()
        self.init_repo(self.repo)
        self.git(self.repo, "commit", "-q", "--allow-empty", "-m", "init")
        self.assert_ok(self.goc(self.repo, "install", "--agents", "claude", "--local-skills"))

    def test_validate_from_a_subdirectory_reports_the_vendored_parity_error(self) -> None:
        shutil.rmtree(self.repo / ".claude" / "skills" / "deck")

        def parity(cwd: Path) -> tuple[int, list[str]]:
            r = self.goc(cwd, "validate")
            lines = (r.stdout + r.stderr).splitlines()
            return r.returncode, [line for line in lines if "missing skills" in line]

        at_root = parity(self.repo)
        self.assertEqual(1, at_root[0])
        self.assertTrue(at_root[1], msg="fixture: the root run must report the missing skill")
        self.assertEqual(at_root, parity(self.sub))

    def test_install_from_a_subdirectory_refuses_and_writes_nothing(self) -> None:
        before = sorted(self.sub.rglob("*"))
        r = self.goc(self.sub, "install")
        self.assertNotEqual(0, r.returncode)
        self.assertIn("already installed", r.stdout + r.stderr)
        self.assertEqual(before, sorted(self.sub.rglob("*")))

    def test_upgrade_from_a_subdirectory_acts_on_the_enclosing_install(self) -> None:
        skill = self.repo / ".claude" / "skills" / "deck" / "SKILL.md"
        skill.unlink()

        r = self.goc(self.sub, "upgrade")
        self.assert_ok(r)
        self.assertTrue(skill.exists(), msg=f"upgrade did not repair the root install:\n{r.stdout}")
        self.assertEqual([], sorted(self.sub.rglob("*")))


class HookProjectDirWalkTest(_Fixture):
    """The hooks import nothing from the package, so their project-dir walk is
    a mirror of the engine's. Pin it over the layouts of
    tests/test_subdirectory_deck_resolution.py."""

    HOOK_NAMES = ("deck_session_start", "pattern_generalization_check")

    def layouts(self) -> list[tuple[Path, Path]]:
        """(start dir, expected root) for each layout."""
        # The canonical consumer shape: a git repo whose root owns the deck.
        (self.repo / ".game-of-cards" / "deck").mkdir(parents=True)
        self.init_repo(self.repo)
        # A nested foreign tree: its own git repo, no deck, inside the host.
        inner = self.repo / "vendor" / "inner"
        (inner / "lib").mkdir(parents=True)
        self.init_repo(inner)
        # No deck anywhere: the walk falls back to the start directory.
        bare = self.tmp / "bare" / "sub"
        bare.mkdir(parents=True)
        return [
            (self.repo, self.repo),
            (self.sub, self.repo),
            (inner, inner),
            (inner / "lib", inner / "lib"),
            (bare, bare),
        ]

    def test_hook_walks_agree_with_the_engine_walk(self) -> None:
        hooks = {name: _load_hook(name) for name in self.HOOK_NAMES}
        for start, expected in self.layouts():
            engine_root = engine._resolve_deck_root(start)
            self.assertEqual(expected, engine_root, msg=f"fixture drift at {start}")
            for name, hook in hooks.items():
                with self.subTest(hook=name, start=str(start.relative_to(self.tmp))):
                    self.assertEqual(engine_root, hook._find_project_dir(str(start)))

    def test_session_start_hook_from_a_subdirectory_names_the_active_card(self) -> None:
        self.init_repo(self.repo)
        self.make_deck_with_check(self.repo)
        self.assert_ok(self.goc(self.repo, "status", CARD, "active", "--no-commit"))
        r = subprocess.run(
            [sys.executable, str(HOOKS / "deck_session_start.py")],
            input='{"hook_event_name": "SessionStart", "cwd": "%s"}' % self.sub,
            env=self.env, capture_output=True, text=True,
        )
        self.assertIn(CARD, r.stdout)


if __name__ == "__main__":
    unittest.main()
