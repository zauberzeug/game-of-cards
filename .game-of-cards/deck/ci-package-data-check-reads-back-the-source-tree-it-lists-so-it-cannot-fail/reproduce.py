#!/usr/bin/env python3
"""Does any CI gate notice a wheel that ships no skill templates?

ci.yml installs the package editable (`uv pip install -e .`), then its
`Verify package data ships templates` step lists the skills under
`goc/templates/skills` and checks that each one exists under
`files('goc.templates')`. Under an editable install that is the same
directory, so the step reads back the list it just made.

This script copies the working tree into a scratch git repo, adds a
wheel-level `exclude = ["goc/templates/skills"]` to its pyproject.toml, and
runs ci.yml's steps there verbatim, in CI's order, under a fresh activated
venv: `Install package`, `Run regression tests`, and `Verify package data
ships templates` while ci.yml still has it. It then builds the distribution
the way release.yml does (`uv build`: the sdist, then the wheel from the
sdist) and counts the wheel's `SKILL.md` members.

A test that fails under the exclude is attributed to it only if it passes
once the exclude is reverted, so an environment-dependent failure is not
mistaken for a gate noticing.

Verdict:
- the wheel still ships skills: the exclude did not take, and the hypothesis
  is disproved (exit 2);
- the wheel ships none and no gate fails because of it: CI is blind (exit 1);
- some gate fails because of it: CI notices (exit 0). The package-data step's
  own result is printed either way. While it passes under a skill-less wheel
  it is still a check that cannot fail, which is a ci.yml edit only a human
  can push.

Usage: reproduce.py   (takes a couple of minutes: it runs the whole suite)
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import zipfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
CI_YML = ROOT / ".github" / "workflows" / "ci.yml"
REQUIRED_STEPS = ("Install package", "Run regression tests")
PACKAGE_DATA_STEP = "Verify package data ships templates"
WHEEL_TABLE = "[tool.hatch.build.targets.wheel]\n"
EXCLUDE = 'exclude = ["goc/templates/skills"]\n'


def step_body(workflow: str, name: str) -> str:
    """The `run:` script of the step called `name`, dedented like YAML does."""
    lines = workflow.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)- name: (.+?)\s*$", line)
        if not m or m.group(2) != name:
            continue
        key_indent = len(m.group(1)) + 2
        for j in range(i + 1, len(lines)):
            cur = lines[j]
            if cur.strip() and len(cur) - len(cur.lstrip()) < key_indent:
                break
            run = re.match(rf"^\s{{{key_indent}}}run:\s*(.*)$", cur)
            if not run:
                continue
            if run.group(1) not in ("|", "|-", ">"):
                return run.group(1) + "\n"
            block = []
            for nxt in lines[j + 1:]:
                if nxt.strip() and len(nxt) - len(nxt.lstrip()) <= key_indent:
                    break
                block.append(nxt)
            return textwrap.dedent("\n".join(block)).strip("\n") + "\n"
        raise RuntimeError(f"step {name!r} has no run: block")
    raise RuntimeError(f"step {name!r} not found in {CI_YML}")


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout


def scratch_copy(dest: Path) -> None:
    """Tracked plus untracked-but-not-ignored files, committed to a new repo."""
    listed = git("ls-files", "-z", "--cached", "--others", "--exclude-standard", cwd=ROOT)
    for rel in sorted(set(filter(None, listed.split("\0")))):
        src = ROOT / rel
        if not src.is_file():
            continue  # deleted in the working tree
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest / rel)
    git("init", "-q", cwd=dest)
    git("add", "-A", cwd=dest)
    git("-c", "user.name=reproduce", "-c", "user.email=reproduce@example.invalid",
        "commit", "-q", "-m", "scratch", cwd=dest)


def ci_env(scratch: Path) -> dict[str, str]:
    """What setup-uv's activate-environment leaves behind, minus the git tags."""
    venv = scratch / ".venv"
    env = {k: v for k, v in os.environ.items() if k not in ("VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT")}
    env["VIRTUAL_ENV"] = str(venv)
    env["PATH"] = f"{venv / 'bin'}{os.pathsep}{env.get('PATH', '')}"
    # The scratch repo has no tags, so pin what hatch-vcs derives between
    # releases: a dev build after the `__version__` literal. The install tests
    # compare the installed version against older ones; 0.0.0 would fail them.
    literal = re.search(r'^__version__ = "([^"]+)"$',
                        (scratch / "goc" / "__init__.py").read_text(encoding="utf-8"), re.MULTILINE)
    env["SETUPTOOLS_SCM_PRETEND_VERSION"] = f"{literal.group(1)}.post1.dev0"
    env["UV_NO_PROGRESS"] = "1"
    return env


def run_step(body: str, scratch: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    # GitHub runs an unspecified-shell step on Linux as `bash -e {0}`.
    return subprocess.run(["bash", "-e", "-c", body], cwd=scratch, env=env,
                          capture_output=True, text=True)


def failing_tests(output: str) -> list[str]:
    """Loadable ids of the failed tests. 3.11+ prints `FAIL: m (mod.Class.m)`,
    3.10 `FAIL: m (mod.Class)`, and a fixture error `ERROR: setUpClass (mod.Class)`."""
    ids = set()
    for name, where in re.findall(r"^(?:FAIL|ERROR): (\S+) \(([\w.]+)\)", output, re.MULTILINE):
        fixture = name in ("setUpClass", "tearDownClass", "setUpModule", "tearDownModule")
        ids.add(where if fixture or where.endswith("." + name) else f"{where}.{name}")
    return sorted(ids)


def tail(text: str, n: int = 6) -> str:
    return "\n".join("    " + line for line in text.strip().splitlines()[-n:])


def main() -> int:
    if shutil.which("uv") is None:
        print("uv is not on PATH", file=sys.stderr)
        return 3
    workflow = CI_YML.read_text(encoding="utf-8")
    bodies = {name: step_body(workflow, name) for name in REQUIRED_STEPS}
    if f"- name: {PACKAGE_DATA_STEP}\n" in workflow:
        bodies[PACKAGE_DATA_STEP] = step_body(workflow, PACKAGE_DATA_STEP)
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp) / "repo"
        scratch.mkdir()
        scratch_copy(scratch)
        pyproject = scratch / "pyproject.toml"
        original = pyproject.read_text(encoding="utf-8")
        if WHEEL_TABLE not in original:
            print(f"pyproject.toml has no {WHEEL_TABLE.strip()} table", file=sys.stderr)
            return 3
        pyproject.write_text(original.replace(WHEEL_TABLE, WHEEL_TABLE + EXCLUDE), encoding="utf-8")

        env = ci_env(scratch)
        subprocess.run(["uv", "venv", "-q", "--python", sys.executable, str(scratch / ".venv")],
                       cwd=scratch, env=env, check=True)
        results = {name: run_step(body, scratch, env) for name, body in bodies.items()}

        dist = Path(tmp) / "dist"
        build = subprocess.run(["uv", "build", "--out-dir", str(dist)], cwd=scratch, env=env,
                               capture_output=True, text=True)
        wheels = sorted(dist.glob("*.whl"))
        if build.returncode != 0 or len(wheels) != 1:
            print(f"uv build failed:\n{tail(build.stderr, 20)}", file=sys.stderr)
            return 3
        members = zipfile.ZipFile(wheels[0]).namelist()
        shipped = sorted(m for m in members if re.fullmatch(r"goc/templates/skills/[^/]+/SKILL\.md", m))
        source = sorted(p.parent.name for p in (scratch / "goc/templates/skills").glob("*/SKILL.md"))

        install = results["Install package"]
        if install.returncode != 0:
            print(f"`Install package` failed:\n{tail(install.stderr, 20)}", file=sys.stderr)
            return 3

        suite = results["Run regression tests"]
        suite_out = suite.stdout + suite.stderr
        ran = re.search(r"^Ran (\d+) tests?", suite_out, re.MULTILINE)
        under_exclude = failing_tests(suite_out)

        step = results.get(PACKAGE_DATA_STEP)

        # Control: revert the exclude, re-run whatever failed.
        pyproject.write_text(original, encoding="utf-8")
        environmental = []
        if under_exclude:
            # `discover -s tests` puts tests/ on sys.path; the ids need it too.
            control = subprocess.run(
                [str(scratch / ".venv" / "bin" / "python"), "-m", "unittest", *under_exclude],
                cwd=scratch, env={**env, "PYTHONPATH": str(scratch / "tests")},
                capture_output=True, text=True)
            environmental = failing_tests(control.stdout + control.stderr)
        attributable = [t for t in under_exclude if t not in environmental]
        step_noticed = (step is not None and step.returncode != 0
                        and run_step(bodies[PACKAGE_DATA_STEP], scratch, env).returncode == 0)

    print(f"wheel built under the exclude ships {len(shipped)} of {len(source)} SKILL.md "
          f"({wheels[0].name})")
    print(f"`Run regression tests`: exit {suite.returncode}, "
          f"{ran.group(1) if ran else '?'} tests, {len(under_exclude)} failing")
    for t in attributable:
        print(f"    fails because of the exclude: {t}")
    for t in environmental:
        print(f"    fails without the exclude too (not counted): {t}")
    if step is None:
        print(f"`{PACKAGE_DATA_STEP}`: no longer in ci.yml")
    else:
        print(f"`{PACKAGE_DATA_STEP}`: exit {step.returncode}")
        print(tail(step.stdout, 1))

    if shipped:
        print("\nDISPROVED: the exclude did not drop the skills from the wheel.")
        return 2
    if step is not None and not step_noticed:
        print("\nThe package-data step passes while the wheel ships no skills: it cannot fail.")
    if attributable or step_noticed:
        print("CI notices: a gate fails because the wheel ships no skills.")
        return 0
    print("CI IS BLIND: the wheel ships no skills and no gate fails.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
