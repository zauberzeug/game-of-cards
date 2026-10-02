"""Regression guard: goc.md's vendored -> plugin switch recipe must do what it says.

`goc.md` § "Coexistence with the repo-local harness" is the consumer-facing
page that tells a vendored repo how to move to the Claude Code plugin. It used
to say: delete `.claude/skills/`, `.claude/hooks/` and the GoC settings entries
by hand. That took every skill the repo kept there, and because it never
touched `skills_source`, the next `goc upgrade` re-vendored all of it
(`cli-reference-plugin-switch-recipe-deletes-user-skills-and-the-next-upgrade-reverts-it`).

A recipe is an instruction the reader executes, so no derive-from-tree check
can tell whether it works — running it can. These tests read the numbered
steps out of the section and run them against a scratch `--local-skills`
install that also holds a skill, a hook script and settings of the repo's own.
The section's two warnings (hand-deleting gets re-vendored; the plugin's
bundled engine leaves GoC's skill directories behind) are run against the same
fixture and compared both ways, so a behavior change on either side turns the
build red instead of leaving the page wrong again.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc.install import GOC_CLAUDE_HOOKS, _strip_goc_settings_entries, skill_for_agent  # noqa: E402

GOC_MD = ROOT / "goc.md"
SECTION = "### Coexistence with the repo-local harness"
BUNDLED_ENGINE_ROOT = ROOT / "claude-plugin"

GOC_SKILLS = sorted(
    p.name
    for p in (ROOT / "goc" / "templates" / "skills").iterdir()
    if p.is_dir() and skill_for_agent(p.name, "claude")
)
GOC_HOOK_SCRIPTS = sorted(
    m.group(1) for cmd in GOC_CLAUDE_HOOKS.values() if (m := re.search(r"(\.claude/hooks/[\w.-]+\.py)", cmd))
)
GOC_COMMANDS = set(GOC_CLAUDE_HOOKS.values())

# What the fixture repo owns itself, beside the vendored GoC layout.
USER_SKILL = Path(".claude/skills/my-own-skill/SKILL.md")
USER_HOOK = Path(".claude/hooks/my_hook.py")
USER_COMMAND = "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/my_hook.py"
USER_PERMISSIONS = {"allow": ["Bash(make:*)"]}

_STEP = re.compile(r"^\d+\. (.+)$", re.MULTILINE)
_SET_STEP = re.compile(r"Set `(\w+): (\w+)` in `([^`]+)`")


def _section() -> str:
    text = GOC_MD.read_text()
    start = text.index(SECTION)
    end = text.find("\n## ", start + len(SECTION))
    return text[start : end if end != -1 else len(text)]


def _goc(repo: Path, *args: str, stdin: str = "", engine_root: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=repo,
        env={**os.environ, "PYTHONPATH": str(engine_root)},
        input=stdin,
        text=True,
        capture_output=True,
        check=False,
    )


def _settings(repo: Path) -> dict:
    path = repo / ".claude" / "settings.json"
    return json.loads(path.read_text()) if path.is_file() else {}


def _commands(repo: Path) -> list[str]:
    return [
        h.get("command")
        for groups in _settings(repo).get("hooks", {}).values()
        for group in groups
        for h in group.get("hooks", [])
    ]


def _pin(repo: Path) -> str | None:
    m = re.search(r"^skills_source:\s*(\S+)", (repo / ".game-of-cards" / "config.yaml").read_text(), re.MULTILINE)
    return m.group(1) if m else None


def _goc_layout(repo: Path) -> dict[str, list[str]]:
    """Every piece of the vendored GoC layout still on disk, by kind."""
    return {
        "skill dirs": [name for name in GOC_SKILLS if (repo / ".claude" / "skills" / name).is_dir()],
        "bootstrap": [rel for rel in [".claude/skills/_goc-bootstrap.sh"] if (repo / rel).is_file()],
        "hook scripts": [rel for rel in GOC_HOOK_SCRIPTS if (repo / rel).is_file()],
        "settings entries": sorted(c for c in _commands(repo) if c in GOC_COMMANDS),
    }


class PluginSwitchRecipeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._tmp.cleanup)
        fixture = Path(cls._tmp.name) / "fixture"
        fixture.mkdir()
        result = _goc(fixture, "install", "--local-skills", "--agents", "claude")
        if result.returncode:
            raise RuntimeError(f"goc install --local-skills failed:\n{result.stdout}\n{result.stderr}")
        (fixture / USER_SKILL).parent.mkdir(parents=True)
        (fixture / USER_SKILL).write_text("---\nname: my-own-skill\ndescription: the repo's own\n---\n")
        (fixture / USER_HOOK).write_text("# a hook script the repo owns\n")
        settings = _settings(fixture)
        settings["permissions"] = USER_PERMISSIONS
        settings["hooks"]["PreToolUse"] = [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": USER_COMMAND}]}
        ]
        (fixture / ".claude" / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")
        cls.fixture = fixture

    def _repo(self) -> Path:
        repo = Path(self._tmp.name) / self.id().rsplit(".", 1)[-1]
        shutil.copytree(self.fixture, repo)
        return repo

    def _run_documented_steps(self, repo: Path, *, engine_root: Path = ROOT) -> None:
        steps = _STEP.findall(_section())
        ran = []
        for step in steps:
            set_step = _SET_STEP.match(step)
            if set_step:
                key, value, rel = set_step.groups()
                path = repo / rel
                text, n = re.subn(rf"^{key}:.*$", f"{key}: {value}", path.read_text(), flags=re.MULTILINE)
                path.write_text(text if n else f"{text.rstrip()}\n{key}: {value}\n")
                ran.append("set")
            elif "`goc upgrade`" in step:
                stdin = "y\n" if "answer `y`" in step else ""
                result = _goc(repo, "upgrade", stdin=stdin, engine_root=engine_root)
                self.assertEqual(0, result.returncode, msg=f"{step!r}:\n{result.stdout}\n{result.stderr}")
                ran.append("upgrade")
            else:
                self.fail(f"goc.md's switch recipe has a step this guard cannot run: {step!r}. Teach it.")
        self.assertIn("set", ran, msg="goc.md's switch recipe no longer sets skills_source as a numbered step.")
        self.assertIn("upgrade", ran, msg="goc.md's switch recipe no longer runs goc upgrade as a numbered step.")

    def _assert_repo_owned_files_intact(self, repo: Path) -> None:
        self.assertTrue((repo / USER_SKILL).is_file(), msg="the switch deleted a skill the repo owns")
        self.assertTrue((repo / USER_HOOK).is_file(), msg="the switch deleted a hook script the repo owns")
        self.assertIn(USER_COMMAND, _commands(repo), msg="the switch dropped a settings hook entry the repo owns")
        self.assertEqual(USER_PERMISSIONS, _settings(repo).get("permissions"), msg="the switch rewrote the repo's settings")

    def test_fixture_matches_the_vendored_install_the_section_describes(self) -> None:
        described = re.search(r"`skills_source: (\w+)` pinned", _section())
        self.assertIsNotNone(described, msg="goc.md no longer says which skills_source a vendored install pins.")
        self.assertEqual(described.group(1), _pin(self.fixture))
        layout = _goc_layout(self.fixture)
        self.assertEqual(GOC_SKILLS, layout["skill dirs"])
        self.assertEqual(GOC_HOOK_SCRIPTS, layout["hook scripts"])
        self.assertEqual(sorted(GOC_COMMANDS), layout["settings entries"])

    def test_documented_switch_ends_in_plugin_mode_and_keeps_the_repos_own_files(self) -> None:
        repo = self._repo()
        self._run_documented_steps(repo)

        self.assertEqual("plugin", _pin(repo))
        self.assertEqual({kind: [] for kind in _goc_layout(repo)}, _goc_layout(repo))
        self._assert_repo_owned_files_intact(repo)

        # The switch has to survive the routine upgrade goc.md recommends.
        routine = _goc(repo, "upgrade")
        self.assertEqual(0, routine.returncode, msg=routine.stdout + routine.stderr)
        self.assertEqual("plugin", _pin(repo))
        self.assertEqual({kind: [] for kind in _goc_layout(repo)}, _goc_layout(repo))
        self._assert_repo_owned_files_intact(repo)

    def test_section_does_not_tell_the_reader_to_delete_the_skills_dir(self) -> None:
        self.assertNotRegex(
            _section(),
            re.compile(r"(?<![\w-])(?:remove|delete|rm -rf) `?\.claude/skills/?`?", re.IGNORECASE),
            msg=(
                "goc.md tells the reader to delete .claude/skills/, which takes the "
                "repo's own skills with it and does not survive the next goc upgrade. "
                "Point at the numbered switch instead."
            ),
        )

    def test_hand_delete_warning_matches_what_upgrade_does(self) -> None:
        repo = self._repo()
        shutil.rmtree(repo / ".claude" / "skills")
        shutil.rmtree(repo / ".claude" / "hooks")
        _strip_goc_settings_entries(repo / ".claude" / "settings.json")
        result = _goc(repo, "upgrade")
        self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)

        layout = _goc_layout(repo)
        revendored = _pin(repo) == "vendored" and all(
            layout[kind] for kind in ("skill dirs", "hook scripts", "settings entries")
        )
        warns = bool(re.search(r"hand-delete `\.claude/skills/`[^.]*\.[^.]*re-vendors", _section()))
        self.assertEqual(
            warns,
            revendored,
            msg=(
                "goc.md warns that a hand-deleted vendored layout is re-vendored by the next goc upgrade, but it was not; drop the warning."
                if warns
                else "goc upgrade re-vendors a hand-deleted vendored layout, and goc.md no longer warns the reader."
            ),
        )

    @unittest.skipUnless((BUNDLED_ENGINE_ROOT / "goc").is_dir(), "no bundled plugin engine in this tree")
    def test_bundled_engine_caveat_matches_its_cleanup(self) -> None:
        repo = self._repo()
        self._run_documented_steps(repo, engine_root=BUNDLED_ENGINE_ROOT)

        left_behind = _goc_layout(repo)["skill dirs"]
        self._assert_repo_owned_files_intact(repo)
        warns = "standalone `goc`" in _section()
        self.assertEqual(
            warns,
            bool(left_behind),
            msg=(
                "goc.md says to run the switch with the standalone goc because the plugin's bundled engine "
                "leaves GoC's skill directories behind, but it now removes them; drop the caveat."
                if warns
                else f"the plugin's bundled engine leaves GoC skill dirs {left_behind} behind on the documented "
                "switch, and goc.md no longer tells the reader to run it with the standalone goc."
            ),
        )


if __name__ == "__main__":
    unittest.main()
