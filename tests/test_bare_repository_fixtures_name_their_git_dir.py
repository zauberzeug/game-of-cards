"""Regression guard: a test that reads a bare repository must pass where git refuses to discover one.

`anthropics/claude-code-action@v1` writes `safe.bareRepository = explicit` into
the global git config before every Claude session, and every autonomous
workflow in this repo runs that action. Under that setting git refuses a bare
repository it finds through the working directory: the caller has to name it,
with `--git-dir` or `GIT_DIR`. Two modules here read their scratch bare remote
by running git inside it, so inside every bot session both errored in
`setUpClass`, their 7 tests never ran, and the suite a bot runs to tick its DoD
reported `FAILED (errors=2)`
(`regression-suite-is-red-in-bot-runs-whose-git-refuses-implicit-bare-repositories`).

CI does not run under the action, so CI never saw it. This guard brings the
setting to CI. It runs every other `tests/` module that creates a bare
repository (it passes `--bare` or `--mirror`) in a child process whose HOME
holds only a `.gitconfig` setting `safe.bareRepository = explicit`, and
requires each module to run every test it defines and pass. HOME is the one
channel that reaches the fixtures' git: they drop every `GIT_*` variable before
they run it. The harness is fed the pre-fix fixture shape and the fixed one, to
prove the setting reaches git in the child and that a class whose `setUpClass`
dies is caught.

A module, or a helper it imports, could still move HOME or GIT_CONFIG_GLOBAL
on import, for instance to isolate the suite from the host's git config. Its
tests would then pass without the setting, and so would this guard. So the
child also asks git, once the module is imported, which `safe.bareRepository`
it sees, and anything but `explicit` fails the module: an isolated config has
to carry the setting itself.

The fix this guard asks for is the one the action documents: name the bare
repository with `--git-dir`. Do not opt out with `-c safe.bareRepository=all`,
which turns off the protection the action turned on.
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
TESTS = ROOT / "tests"
HARDENED_GITCONFIG = "[safe]\n\tbareRepository = explicit\n"

# `git init --bare`, `git clone --bare` and `git clone --mirror` create a bare repository.
_CREATES_BARE = re.compile(r"--(?:bare|mirror)\b")

# Runs one module the way `unittest discover -s tests` imports it (its directory
# first on sys.path) and writes to the JSON file named by argv[3] how many tests
# it defines, how many ran, and the `safe.bareRepository` git sees once the module
# is imported. The runner reports to stderr; stdout stays the tests'.
_CHILD = """\
import json, os, subprocess, sys, unittest
sys.path.insert(0, sys.argv[1])
suite = unittest.defaultTestLoader.loadTestsFromName(sys.argv[2])
defined = suite.countTestCases()
setting = subprocess.run(
    ["git", "config", "--get", "safe.bareRepository"],
    cwd=os.path.dirname(sys.argv[3]), capture_output=True, text=True,
).stdout.strip()
result = unittest.TextTestRunner(stream=sys.stderr).run(suite)
with open(sys.argv[3], "w", encoding="utf-8") as out:
    json.dump({"defined": defined, "ran": result.testsRun, "ok": result.wasSuccessful(), "setting": setting}, out)
"""

# The fixture shape this guard exists for, and its fix: a class that reads a bare
# repository in setUpClass, found through the working directory or named. The
# prelude runs on import.
_FIXTURE = """\
import os
import subprocess
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
{prelude}

class BareFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        remote = HERE / "{name}.git"
        subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", *{args}, "rev-parse", "--is-bare-repository"], cwd=remote, check=True, capture_output=True)

    def test_reads_the_remote(self):
        pass
"""


def bare_repository_modules() -> list[str]:
    """Every other `tests/` module that creates a bare repository, by module name."""
    me = Path(__file__).resolve()
    return sorted(
        path.stem
        for path in TESTS.glob("test_*.py")
        if path.resolve() != me and _CREATES_BARE.search(path.read_text(encoding="utf-8"))
    )


def hardened_env(home: Path) -> dict[str, str]:
    """The caller's environment with HOME moved to `home` and every GIT_* variable dropped."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env["HOME"] = str(home)
    env["XDG_CONFIG_HOME"] = str(home / ".config")
    return env


def run_module(directory: Path, module: str, env: dict[str, str], scratch: Path) -> tuple[dict | None, str]:
    """Run one module in a child process: (what it defined and ran, or None if it crashed; its stderr)."""
    report = scratch / f"{module}.json"
    proc = subprocess.run(
        [sys.executable, "-c", _CHILD, str(directory), module, str(report)],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=600,
    )
    outcome = json.loads(report.read_text(encoding="utf-8")) if report.is_file() else None
    return outcome, proc.stderr


def shortfall(outcome: dict | None) -> str | None:
    """None when the module ran every test it defines and passed under the setting, else what fell short."""
    if outcome is None:
        return "crashed before reporting a result"
    if outcome["setting"] != "explicit":
        return f"safe.bareRepository was {outcome['setting'] or 'unset'} for git once the module was imported"
    if outcome["ok"] and outcome["ran"] == outcome["defined"]:
        return None
    return f"ran {outcome['ran']} of {outcome['defined']} tests, {'OK' if outcome['ok'] else 'FAILED'}"


def _git_version() -> tuple[int, int]:
    out = subprocess.run(["git", "--version"], capture_output=True, text=True).stdout
    match = re.search(r"(\d+)\.(\d+)", out)
    return (int(match.group(1)), int(match.group(2))) if match else (0, 0)


class BareRepositoryFixturesNameTheirGitDirTest(unittest.TestCase):
    scratch: Path
    env: dict[str, str]

    @classmethod
    def setUpClass(cls) -> None:
        if not (ROOT / ".git").exists():
            raise unittest.SkipTest("not a git checkout (sdist/wheel test run): a module that needs one skips")
        if shutil.which("git") is None:
            raise unittest.SkipTest("git is not installed")
        if _git_version() < (2, 38):
            raise unittest.SkipTest("git before 2.38 ignores safe.bareRepository")
        tmp = tempfile.TemporaryDirectory(prefix="goc-explicit-bare-")
        cls.addClassCleanup(tmp.cleanup)
        cls.scratch = Path(tmp.name)
        home = cls.scratch / "home"
        (home / ".config").mkdir(parents=True)
        (home / ".gitconfig").write_text(HARDENED_GITCONFIG, encoding="utf-8")
        cls.env = hardened_env(home)

    def test_every_bare_repository_module_runs_all_its_tests_and_passes(self) -> None:
        modules = bare_repository_modules()
        self.assertTrue(modules, "no other tests/ module passes --bare or --mirror: the scan found nothing to run")
        failures = []
        for module in modules:
            outcome, stderr = run_module(TESTS, module, self.env, self.scratch)
            fell_short = shortfall(outcome)
            if fell_short:
                tail = "\n".join(f"      {line}" for line in stderr.strip().splitlines()[-12:])
                failures.append(f"  tests/{module}.py: {fell_short}\n{tail}")
        if failures:
            self.fail(
                "under `safe.bareRepository = explicit`, which claude-code-action@v1 sets for every"
                " session, these modules do not run every test they define and pass. Name the bare"
                " repository with --git-dir wherever git runs inside it; do not opt out with"
                " -c safe.bareRepository=all. A module that gives git a config of its own on import"
                " must set safe.bareRepository = explicit in it:\n" + "\n".join(failures)
            )

    def test_the_harness_catches_the_pre_fix_shape_and_a_lost_setting_and_passes_the_fix(self) -> None:
        fixtures = self.scratch / "fixtures"
        fixtures.mkdir()
        isolate_on_import = (
            'os.environ["HOME"] = str(HERE)\n'
            'os.environ["XDG_CONFIG_HOME"] = str(HERE / ".config")\n'
            'os.environ["GIT_CONFIG_NOSYSTEM"] = "1"'
        )
        shapes = {
            "found_through_cwd": ("", "[]"),
            "named_with_git_dir": ("", '["--git-dir=."]'),
            # The pre-fix shape again, behind an import that gives git a config
            # without the setting: its test passes, so only the setting check sees it.
            "isolated_on_import": (isolate_on_import, "[]"),
        }
        verdicts = {}
        for name, (prelude, args) in shapes.items():
            source = _FIXTURE.format(prelude=prelude, name=name, args=args)
            (fixtures / f"{name}.py").write_text(source, encoding="utf-8")
            outcome, _stderr = run_module(fixtures, name, self.env, self.scratch)
            verdicts[name] = shortfall(outcome)
        self.assertEqual(
            verdicts,
            {
                "found_through_cwd": "ran 0 of 1 tests, FAILED",
                "named_with_git_dir": None,
                "isolated_on_import": "safe.bareRepository was unset for git once the module was imported",
            },
            "the hardened HOME must make git refuse a bare repository found through the working"
            " directory and accept one named with --git-dir, and a module that drops the setting on"
            " import must be caught; otherwise the module runs above prove nothing",
        )


if __name__ == "__main__":
    unittest.main()
