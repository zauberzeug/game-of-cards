"""Reproduce: every install that vendors `.codex/skills/` without vendoring
Claude pins `skills_source: plugin`, and that Claude-only value switches off
the parity check for the vendored Codex tree too.

`install()` (goc/install.py) pins
`"vendored" if "claude" in local_skills_agents else "plugin"`, while
`_should_use_local_skills` vendors Codex on every install. So a codex-only
install, a default `claude,codex` install, and even a codex-only
`--local-skills` install all write `skills_source: plugin` beside a real
vendored `.codex/skills/`. `validate_skill_dir_parity()` (goc/engine.py)
returns `[]` before it looks at either tree when the effective source is
`plugin`, so a GoC skill deleted from `.codex/skills/` never surfaces in
`goc validate`. When the drift goes unreported, the script flips the pin to
`vendored` and checks again: the same check then reports the missing skill,
which shows the pin is what hides it.

Each scenario installs into a fresh temp repo with HOME pointed at an empty
directory and CLAUDE_PLUGIN_ROOT unset, so no Claude plugin is present.

Exit codes: 0 = defect no longer fires, 1 = defect fires, 2 = harness or
precondition broken.

Run on a clean checkout:
    uv run python .game-of-cards/deck/codex-only-install-pins-skills-source-to-plugin-skipping-parity-check/reproduce.py
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
DRIFTED_SKILL = "pull-card"
PARITY_PROBE = "import json; from goc.engine import validate_skill_dir_parity as v; print(json.dumps(v()))"
SCENARIOS = (
    ("codex-only", ("--agents", "codex")),
    ("claude,codex default", ("--agents", "claude,codex")),
    ("codex-only --local-skills", ("--agents", "codex", "--local-skills")),
)


class HarnessError(Exception):
    pass


def _env(home: Path) -> dict[str, str]:
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
    env["HOME"] = str(home)
    env.pop("CLAUDE_PLUGIN_ROOT", None)
    return env


def _run(cwd: Path, home: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd,
        env=_env(home),
        text=True,
        capture_output=True,
        check=False,
    )


def _parity(repo: Path, home: Path) -> list[str]:
    probe = _run(repo, home, "-c", PARITY_PROBE)
    if probe.returncode != 0:
        raise HarnessError(f"parity probe failed:\n{probe.stderr}")
    return json.loads(probe.stdout)


def _validate_reports_drift(repo: Path, home: Path) -> tuple[bool, int]:
    result = _run(repo, home, "-m", "goc.cli", "validate", "--quiet")
    reported = result.returncode != 0 and DRIFTED_SKILL in result.stdout + result.stderr
    return reported, result.returncode


def _pin(repo: Path) -> str:
    config = (repo / ".game-of-cards" / "config.yaml").read_text()
    match = re.search(r"^skills_source:[ \t]*(\S+)", config, re.MULTILINE)
    return match.group(1) if match else "(unset)"


def _scenario(label: str, install_args: tuple[str, ...]) -> bool:
    """Return True when the defect fires for this install shape."""
    print(f"[{label}] goc install {' '.join(install_args)}")
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td) / "consumer"
        home = Path(td) / "home"
        repo.mkdir()
        home.mkdir()
        installed = _run(repo, home, "-m", "goc.cli", "install", *install_args)
        if installed.returncode != 0:
            raise HarnessError(f"install exited {installed.returncode}:\n{installed.stderr}")

        codex_skill = repo / ".codex" / "skills" / DRIFTED_SKILL
        if not (codex_skill / "SKILL.md").is_file():
            print("  .codex/skills/ is not vendored by this install; nothing can drift there.")
            return False
        if (home / ".claude" / "plugins").exists():
            raise HarnessError("a Claude plugin directory exists under the isolated HOME")
        print(f"  skills_source pinned: {_pin(repo)}")
        print(f"  .codex/skills/{DRIFTED_SKILL}/SKILL.md vendored: True")
        clean, clean_exit = _validate_reports_drift(repo, home)
        if clean or clean_exit != 0:
            raise HarnessError(f"goc validate is not clean right after install (exit {clean_exit})")

        shutil.rmtree(codex_skill)
        reported, exit_code = _validate_reports_drift(repo, home)
        print(f"  after deleting .codex/skills/{DRIFTED_SKILL}/: parity validator -> {_parity(repo, home)!r}")
        print(f"  goc validate exit: {exit_code}; drift reported: {reported}")
        if reported:
            return False

        config_path = repo / ".game-of-cards" / "config.yaml"
        config_path.write_text(
            re.sub(r"^skills_source:.*$", "skills_source: vendored", config_path.read_text(), flags=re.MULTILINE)
        )
        corrected = _parity(repo, home)
        print(f"  same drift with skills_source: vendored: parity validator -> {corrected!r}")
        if not any(DRIFTED_SKILL in e for e in corrected):
            raise HarnessError("the parity check misses the drift even with the vendored pin")
        return True


try:
    fired = [label for label, args in SCENARIOS if _scenario(label, args)]
except HarnessError as exc:
    print(f"HARNESS BROKEN: {exc}")
    sys.exit(2)
print()
if fired:
    print(
        "DEFECT REPRODUCED: a GoC skill deleted from the vendored .codex/skills/ goes unreported "
        f"by goc validate after these installs: {', '.join(fired)}. The skills_source pin "
        "(Claude-only) switches off the Codex tree's parity check."
    )
    sys.exit(1)
print("No defect: drift in a vendored .codex/skills/ is reported after every install shape.")
sys.exit(0)
