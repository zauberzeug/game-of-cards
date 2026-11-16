#!/usr/bin/env python3
"""The regression suite runs git under the host's global git config, so common settings break it.

No test module gives git an isolated global config. Every git subprocess a
test starts, directly or through a goc verb that auto-commits, reads the
global `.gitconfig` of whoever runs the suite. A setting that makes git refuse
an operation the fixtures rely on therefore turns the suite red, even though
nothing in goc changed.

This script runs the full suite (`python -m unittest discover -s tests`) once
per global git config, in parallel. Each run gets its own HOME and
XDG_CONFIG_HOME, so the global config is one this script wrote:

  control      an empty global config
  bare-repos   `safe.bareRepository = explicit`, what anthropics/claude-code-action@v1
               writes before every Claude session
  signing      `commit.gpgsign = true` with a signing key that is not available,
               e.g. a dev container that copies `.gitconfig` but not the key agent
  hooks        `core.hooksPath` pointing at a global hooks directory whose
               `pre-commit` refuses, e.g. an org-wide commit policy hook

It prints, per config, how many tests ran, the result line, and the modules
with errors or failures. It takes about as long as the slowest suite run,
roughly two to three minutes.

Exit 0 when every config gives the control's result (fixed), 1 when any config
changes it (the defect fires), 2 when nothing can be measured: the control run
fails by itself, or git is older than 2.38 (which ignores safe.bareRepository).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".game-of-cards").is_dir():
            return p
        p = p.parent
    raise RuntimeError(".game-of-cards/ not found")


ROOT = _repo_root()

REFUSING_HOOK = "#!/bin/sh\necho 'global pre-commit hook refuses this commit' >&2\nexit 1\n"


def _configs(tmp: Path) -> dict[str, str]:
    hooks = tmp / "global-hooks"
    hooks.mkdir()
    (hooks / "pre-commit").write_text(REFUSING_HOOK)
    (hooks / "pre-commit").chmod(0o755)
    return {
        "control": "",
        "bare-repos": "[safe]\n\tbareRepository = explicit\n",
        "signing": "[commit]\n\tgpgsign = true\n[user]\n\tsigningkey = 0000000000000000NOSUCHKEY\n",
        "hooks": f"[core]\n\thooksPath = {hooks}\n",
    }


def _git_version() -> tuple[int, ...]:
    out = subprocess.run(["git", "--version"], capture_output=True, text=True).stdout
    match = re.search(r"(\d+)\.(\d+)", out)
    return tuple(int(part) for part in match.groups()) if match else (0, 0)


def _run_suite(home: Path) -> dict[str, object]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["HOME"] = str(home)
    env["XDG_CONFIG_HOME"] = str(home / ".config")
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=1800,
    )
    ran = re.search(r"^Ran (\d+) tests?", proc.stderr, re.MULTILINE)
    verdict = re.search(r"^(OK.*|FAILED \(.*\))$", proc.stderr, re.MULTILINE)
    broken = sorted({
        match.group(1).split(".")[0]
        for match in re.finditer(r"^(?:ERROR|FAIL): \S+ \(([\w.]+)", proc.stderr, re.MULTILINE)
    })
    return {
        "ran": int(ran.group(1)) if ran else -1,
        "verdict": verdict.group(1) if verdict else "no verdict",
        "modules": broken,
    }


def main() -> int:
    version = _git_version()
    print(f"git {'.'.join(map(str, version))}")
    if version < (2, 38):
        print("Cannot measure: this git ignores safe.bareRepository.")
        return 2

    with tempfile.TemporaryDirectory(prefix="goc-host-git-config-") as tmp_name:
        tmp = Path(tmp_name)
        configs = _configs(tmp)
        homes = {}
        for name, content in configs.items():
            home = tmp / f"home-{name}"
            (home / ".config").mkdir(parents=True)
            (home / ".gitconfig").write_text(content)
            homes[name] = home
        with ThreadPoolExecutor(max_workers=len(homes)) as pool:
            futures = {name: pool.submit(_run_suite, home) for name, home in homes.items()}
            results = {name: future.result() for name, future in futures.items()}

    control = results["control"]
    print(f"full suite (`python -m unittest discover -s tests`), one run per global git config\n")
    changed = []
    for name, result in results.items():
        mark = "" if name == "control" else ("  [same as control]" if result == control else "  [CHANGED]")
        print(f"{name:<11} ran {result['ran']}, {result['verdict']}{mark}")
        modules = result["modules"]
        if modules:
            shown = ", ".join(modules[:6]) + (f", +{len(modules) - 6} more" if len(modules) > 6 else "")
            print(f"{'':<11}   {len(modules)} module(s) with errors or failures: {shown}")
        if name != "control" and result != control:
            changed.append(name)

    print()
    if control["verdict"] != "OK" or control["ran"] <= 0:
        print("Cannot measure: the suite does not pass under an empty global git config.")
        return 2
    if changed:
        print(
            f"DEFECT: {len(changed)} of {len(results) - 1} host git config(s) change the suite's result "
            f"({', '.join(changed)}). The fixtures inherit the host's global git config."
        )
        return 1
    print("Fixed: the suite gives the same result under every host git config tried.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
