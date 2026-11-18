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
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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
    """The hooks import nothing from the package, so their deck-root
    resolution is a mirror of the engine's: the shared-deck worktree redirect,
    then the walk. Pin the walk over the layouts of
    tests/test_subdirectory_deck_resolution.py and the redirect over a linked
    worktree with and without the opt-in."""

    HOOK_NAMES = ("deck_session_start", "pattern_generalization_check", "deck_prompt_router")

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

    def linked_worktree(self) -> Path:
        """A linked worktree of `self.repo`, whose committed config carries the
        template's commented-out `worktree_deck` line. The checkout holds its
        own `.game-of-cards/`, so the walk alone stops there."""
        self.init_repo(self.repo)
        (self.repo / ".game-of-cards" / "deck").mkdir(parents=True)
        config = self.repo / ".game-of-cards" / "config.yaml"
        config.write_text("workflow:\n  auto_commit: true\n  # worktree_deck: shared\n")
        self.git(self.repo, "add", ".game-of-cards/config.yaml")
        self.git(self.repo, "commit", "-q", "-m", "fixture")
        linked = self.tmp / "linked"
        self.git(self.repo, "worktree", "add", "-q", "-b", "feature", str(linked))
        (linked / "src" / "pkg").mkdir(parents=True)
        return linked

    def test_hook_walks_agree_with_the_engine_in_a_linked_worktree(self) -> None:
        linked = self.linked_worktree()
        config = self.repo / ".game-of-cards" / "config.yaml"
        hooks = {name: _load_hook(name) for name in self.HOOK_NAMES}

        def agree(case: str, expected: Path) -> None:
            for start in (linked, linked / "src" / "pkg"):
                engine_root = engine._resolve_deck_root(start)
                self.assertEqual(expected, engine_root, msg=f"fixture drift: {case} at {start}")
                for name, hook in hooks.items():
                    with self.subTest(hook=name, case=case, start=str(start.relative_to(self.tmp))):
                        self.assertEqual(engine_root, hook._find_project_dir(str(start)))

        with mock.patch.dict(os.environ):
            os.environ.pop("GOC_WORKTREE_DECK", None)
            agree("no opt-in", linked)
            os.environ["GOC_WORKTREE_DECK"] = "Shared"
            agree("env opt-in", self.repo)
            del os.environ["GOC_WORKTREE_DECK"]
            config.write_text("workflow:\n  auto_commit: true\n  worktree_deck: shared\n")
            agree("config opt-in", self.repo)

    def test_hook_config_reading_agrees_with_the_engine(self) -> None:
        """The hooks read `workflow.worktree_deck` without yaml_lite. Pin their
        reading to the engine's over the shapes the opt-in can take."""
        template_file = ROOT / "goc" / "templates" / "game_of_cards" / "config.yaml"
        template = template_file.read_text(encoding="utf-8")
        uncommented = template.replace("  # worktree_deck: shared", "  worktree_deck: shared", 1)
        self.assertNotEqual(template, uncommented, msg="the template lost its shared line")
        configs = {
            "template as shipped": (template, False),
            "template line uncommented": (uncommented, True),
            "double-quoted": ('workflow:\n  worktree_deck: "shared"\n', True),
            "single-quoted, comments": ("workflow:  # c\n  worktree_deck: 'shared'  # c\n", True),
            "among other keys": (
                "layer_2_project_dod:\n  - name: x\n    kind: automated\n"
                "workflow:\n  auto_commit: true\n  worktree_deck: shared\n"
                "hooks:\n  pattern_generalization_check: false\n", True),
            "indented document": ("  workflow:\n    worktree_deck: shared\n", True),
            "hash without a space": ("workflow:\n  worktree_deck: shared#x\n", False),
            "hash inside quotes": ('workflow:\n  worktree_deck: "shared # x"\n', False),
            "other case": ("workflow:\n  worktree_deck: Shared\n", False),
            "other value": ("workflow:\n  worktree_deck: isolated\n", False),
            "empty value": ("workflow:\n  worktree_deck:\n", False),
            "space before the colon": ("workflow:\n  worktree_deck : shared\n", False),
            "top level": ("worktree_deck: shared\n", False),
            "under another key": ("hooks:\n  worktree_deck: shared\n", False),
            "under a longer key": ("workflows:\n  worktree_deck: shared\n", False),
            "nested deeper": ("workflow:\n  nested:\n    worktree_deck: shared\n", False),
            "second workflow block": (template + "workflow:\n  worktree_deck: shared\n", False),
            "repeated key": (
                "workflow:\n  worktree_deck: shared\n  worktree_deck: shared\n", False),
            "tab indentation": ("workflow:\n\tworktree_deck: shared\n", False),
        }
        # Every reader is told cwd sits in a linked worktree of `primary`, so
        # the config text alone decides.
        primary = self.tmp / "primary"
        config = primary / ".game-of-cards" / "config.yaml"
        config.parent.mkdir(parents=True)
        hooks = {name: _load_hook(name) for name in self.HOOK_NAMES}

        def shared_root(module) -> Path | None:
            with mock.patch.object(module, "_detect_worktree_common_root", return_value=primary):
                return module._shared_worktree_deck_root(self.repo)

        with mock.patch.dict(os.environ):
            os.environ.pop("GOC_WORKTREE_DECK", None)
            for case, (text, shared) in configs.items():
                config.write_text(text, encoding="utf-8")
                engine_root = shared_root(engine)
                self.assertEqual(primary if shared else None, engine_root,
                                 msg=f"fixture drift: {case}")
                for name, hook in hooks.items():
                    with self.subTest(hook=name, case=case):
                        self.assertEqual(engine_root, shared_root(hook))

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

    def test_hooks_in_a_shared_deck_worktree_read_the_primary_deck_and_config(self) -> None:
        linked = self.linked_worktree()
        config = self.repo / ".game-of-cards" / "config.yaml"
        config.write_text(
            "workflow:\n  auto_commit: true\n  worktree_deck: shared\n"
            "hooks:\n  pattern_generalization_check: true\n"
        )
        self.assert_ok(self.goc(linked, "new", CARD, "--summary", "Fixture card.",
                                "--gate", "none", "--no-commit"))
        self.assert_ok(self.goc(linked, "status", CARD, "active", "--no-commit"))
        self.assertFalse((linked / ".game-of-cards" / "deck" / CARD).exists(),
                         msg="fixture: goc must write the card to the primary deck")

        def hook(name: str, **payload: str) -> subprocess.CompletedProcess:
            return subprocess.run(
                [sys.executable, str(HOOKS / f"{name}.py")],
                input=json.dumps({"cwd": str(linked / "src" / "pkg"), **payload}),
                env=self.env, capture_output=True, text=True,
            )

        self.assertIn(CARD, hook("deck_session_start", hook_event_name="SessionStart").stdout)
        # The linked checkout's own config leaves the Stop hook off; the
        # primary's, which goc reads, turns it on.
        transcript = self.tmp / "transcript.jsonl"
        transcript.write_text(json.dumps(
            {"role": "assistant", "content": [{"type": "tool_use", "name": "Edit", "input": {}}]}
        ) + "\n")
        r = hook("pattern_generalization_check", hook_event_name="Stop",
                 transcript_path=str(transcript))
        self.assertEqual(2, r.returncode, msg=r.stderr)


class PrimaryCheckoutIsNotALinkedWorktreeTest(_Fixture):
    """From a subdirectory of the primary checkout git prints `--git-dir`
    absolute and `--git-common-dir` relative. Compared as printed, the two
    differed, so every such subdirectory read as a linked worktree and the
    shared-deck opt-in sent it to the git top level
    (shared-deck-mode-treats-primary-checkout-subdirectories-as-linked-worktrees)."""

    def test_only_a_linked_worktree_reports_a_primary_root(self) -> None:
        self.init_repo(self.repo)
        self.git(self.repo, "commit", "-q", "--allow-empty", "-m", "init")
        linked = self.tmp / "linked"
        self.git(self.repo, "worktree", "add", "-q", "--detach", str(linked))
        (linked / "src" / "pkg").mkdir(parents=True)
        readers = {"engine": engine}
        readers.update((name, _load_hook(name)) for name in HookProjectDirWalkTest.HOOK_NAMES)
        cases = {
            self.repo: None,
            self.sub: None,
            linked: self.repo,
            linked / "src" / "pkg": self.repo,
        }
        for start, expected in cases.items():
            for name, module in readers.items():
                with self.subTest(reader=name, start=str(start.relative_to(self.tmp))):
                    self.assertEqual(expected, module._detect_worktree_common_root(start))

    def test_new_beside_a_nested_deck_files_into_it_under_the_config_opt_in(self) -> None:
        self.init_repo(self.repo)
        service = self.repo / "service"
        for root in (self.repo, service):
            (root / ".game-of-cards" / "deck").mkdir(parents=True)
        (self.repo / ".game-of-cards" / "config.yaml").write_text(
            "workflow:\n  auto_commit: false\n  worktree_deck: shared\n"
        )
        self.assert_ok(self.goc(service, "new", CARD, "--summary", "Fixture card.", "--no-commit"))
        self.assertTrue((service / ".game-of-cards" / "deck" / CARD).is_dir())
        self.assertFalse((self.repo / ".game-of-cards" / "deck" / CARD).exists())

    def test_install_in_a_subdirectory_scaffolds_it_under_the_env_opt_in(self) -> None:
        self.init_repo(self.repo)
        env = _env(self.home, GOC_WORKTREE_DECK="shared")
        self.assert_ok(self.goc(self.sub, "install", "--agents", "codex", env=env))
        self.assertTrue((self.sub / ".game-of-cards" / "deck").is_dir())
        self.assertFalse((self.repo / ".game-of-cards").exists())


class BareCloneHasNoPrimaryWorkingTreeTest(_Fixture):
    """Shared mode reads the deck from the primary working tree, taken to be
    the parent of git's common directory. A bare clone has no primary working
    tree: its common directory is the bare repository, whose parent is a plain
    folder. goc looked for the deck there, reported a missing deck naming the
    worktree it never searched, and ignored the opt-in in the worktree's own
    config (shared-worktree-deck-finds-no-deck-when-the-repository-is-a-bare-clone).
    Shared mode now stays off in such a layout, the walk finds the worktree's
    own deck, and goc says why."""

    CONFIG = "workflow:\n  auto_commit: false\n  worktree_deck: shared\n"

    def source(self) -> Path:
        src = self.tmp / "src"
        src.mkdir()
        self.init_repo(src)
        self.git(src, "commit", "-q", "--allow-empty", "-m", "init")
        return src

    def add_worktree(self, git_dir: Path, path: Path) -> Path:
        """A linked worktree of `git_dir` holding its own deck and the config
        opt-in. `--git-dir` names a bare repository explicitly, as a host with
        `safe.bareRepository=explicit` requires."""
        self.git(self.tmp, f"--git-dir={git_dir}", "worktree", "add", "-q",
                 "-b", path.name, str(path))
        (path / ".game-of-cards" / "deck").mkdir(parents=True)
        (path / ".game-of-cards" / "config.yaml").write_text(self.CONFIG)
        (path / "src" / "pkg").mkdir(parents=True)
        return path

    def layouts(self) -> dict[str, tuple[Path, Path]]:
        """Layout name -> (git common directory, linked worktree)."""
        src = self.source()
        layouts = {}
        # `git clone --bare … repo.git`, the card's layout.
        bare = self.tmp / "repo.git"
        self.git(self.tmp, "clone", "-q", "--bare", str(src), str(bare))
        layouts["repo.git"] = (bare, self.add_worktree(bare, self.tmp / "wt-feat"))
        # A `.bare` repository behind a `.git` gitfile, worktrees beside it.
        folder = self.tmp / "dotbare"
        folder.mkdir()
        dotbare = folder / ".bare"
        self.git(self.tmp, "clone", "-q", "--bare", str(src), str(dotbare))
        (folder / ".git").write_text("gitdir: ./.bare\n")
        layouts[".bare"] = (dotbare, self.add_worktree(dotbare, folder / "feat"))
        # A bare repository cloned as `.git`: the name alone would pass.
        project = self.tmp / "project"
        dotgit = project / ".git"
        self.git(self.tmp, "clone", "-q", "--bare", str(src), str(dotgit))
        layouts["bare .git"] = (dotgit, self.add_worktree(dotgit, project / "feat"))
        # Not bare, but the git directory sits apart from its primary checkout.
        gitdir = self.tmp / "separate-gitdir"
        self.git(self.tmp, "init", "-q", f"--separate-git-dir={gitdir}", str(self.tmp / "work"))
        self.git(self.tmp / "work", "-c", "user.name=probe", "-c",
                 "user.email=probe@example.invalid", "-c", "commit.gpgsign=false",
                 "commit", "-q", "--allow-empty", "-m", "init")
        layouts["separate git dir"] = (gitdir, self.add_worktree(gitdir, self.tmp / "sep-linked"))
        return layouts

    def readers(self) -> dict:
        readers = {"engine": engine}
        readers.update((name, _load_hook(name)) for name in HookProjectDirWalkTest.HOOK_NAMES)
        return readers

    def test_no_reader_finds_a_primary_and_every_walk_stays_in_the_worktree(self) -> None:
        readers = self.readers()
        for layout, (common_dir, worktree) in self.layouts().items():
            for start in (worktree, worktree / "src" / "pkg"):
                where = f"{layout}: {start.relative_to(self.tmp)}"
                for name, module in readers.items():
                    with self.subTest(reader=name, start=where):
                        self.assertIsNone(module._detect_worktree_common_root(start))
                for case, env in (("config opt-in", {}), ("env opt-in", {"GOC_WORKTREE_DECK": "shared"})):
                    with mock.patch.dict(os.environ):
                        os.environ.pop("GOC_WORKTREE_DECK", None)
                        os.environ.update(env)
                        self.assertEqual(worktree, engine._resolve_deck_root(start),
                                         msg=f"engine, {case}, {where}")
                        for name, hook in readers.items():
                            if hook is engine:
                                continue
                            with self.subTest(hook=name, case=case, start=where):
                                self.assertEqual(worktree, hook._find_project_dir(str(start)))

    def test_the_engine_says_why_the_shared_deck_is_off(self) -> None:
        for layout, (common_dir, worktree) in self.layouts().items():
            with mock.patch.dict(os.environ):
                os.environ.pop("GOC_WORKTREE_DECK", None)
                warning = engine._unshareable_worktree_deck_warning(worktree, worktree)
                self.assertIsNotNone(warning, msg=f"{layout}: the config opt-in is dropped silently")
                self.assertIn(str(worktree / ".game-of-cards" / "config.yaml"), warning)
                self.assertIn(str(common_dir), warning)
                if layout == "separate git dir":
                    self.assertIn("is not the .git directory of a working tree", warning)
                else:
                    self.assertIn("is a bare repository, so this layout has no primary "
                                  "working tree", warning)
                os.environ["GOC_WORKTREE_DECK"] = "shared"
                warning = engine._unshareable_worktree_deck_warning(worktree, worktree)
                self.assertIn("GOC_WORKTREE_DECK=shared is ignored", warning or "")
                # Without any opt-in the per-worktree deck is what was asked for.
                del os.environ["GOC_WORKTREE_DECK"]
                (worktree / ".game-of-cards" / "config.yaml").write_text("workflow: {}\n")
                self.assertIsNone(engine._unshareable_worktree_deck_warning(worktree, worktree),
                                  msg=layout)

    def test_goc_files_and_lists_in_the_worktree_deck_and_names_the_bare_repository(self) -> None:
        src = self.source()
        bare = self.tmp / "repo.git"
        self.git(self.tmp, "clone", "-q", "--bare", str(src), str(bare))
        worktree = self.add_worktree(bare, self.tmp / "wt-feat")
        for case, extra in (("config opt-in", {}), ("env opt-in", {"GOC_WORKTREE_DECK": "shared"})):
            env = _env(self.home, **extra)
            card = f"card-{len(extra)}"
            created = self.goc(worktree / "src" / "pkg", "new", card, "--summary",
                               "Fixture card.", "--gate", "none", "--no-commit", env=env)
            listed = self.goc(worktree, "--status", "all", env=env)
            for verb, r in (("new", created), ("--status all", listed)):
                with self.subTest(case=case, verb=verb):
                    self.assert_ok(r)
                    self.assertNotIn(engine.MISSING_DECK_PHRASE, r.stderr)
                    self.assertIn(f"{bare} is a bare repository, so this layout has no "
                                  "primary working tree", r.stderr)
            self.assertTrue((worktree / ".game-of-cards" / "deck" / card).is_dir(), msg=case)
            self.assertIn(card, listed.stdout, msg=case)
        self.assertEqual([], sorted(p.name for p in self.tmp.glob(".game-of-cards")),
                         msg="goc must not scaffold the folder holding the bare repository")

    def test_a_primary_checkout_keeps_the_shared_deck_and_names_it_when_missing(self) -> None:
        """The control: with a primary working tree shared mode applies and
        says nothing. When the primary has no deck the notice names the
        primary goc searched, not the linked worktree, which holds a deck."""
        self.init_repo(self.repo)
        self.git(self.repo, "commit", "-q", "--allow-empty", "-m", "init")
        linked = self.tmp / "linked"
        self.git(self.repo, "worktree", "add", "-q", "-b", "feature", str(linked))
        (linked / ".game-of-cards" / "deck").mkdir(parents=True)
        env = _env(self.home, GOC_WORKTREE_DECK="shared")

        r = self.goc(linked, "--status", "all", env=env)
        self.assert_ok(r)
        self.assertNotIn("is ignored", r.stderr)
        self.assertIn(f"no Game of Cards deck found in the primary working tree {self.repo} ",
                      r.stderr)
        self.assertNotIn(str(linked), r.stderr)

        (self.repo / ".game-of-cards" / "deck").mkdir(parents=True)
        r = self.goc(linked, "--status", "all", env=env)
        self.assert_ok(r)
        self.assertEqual("", r.stderr)


if __name__ == "__main__":
    unittest.main()
