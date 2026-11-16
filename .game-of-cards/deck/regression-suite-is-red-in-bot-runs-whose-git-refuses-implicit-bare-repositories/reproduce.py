#!/usr/bin/env python3
"""Tests that run git inside a bare remote break where git refuses implicit bare repositories.

`anthropics/claude-code-action@v1` writes `safe.bareRepository = explicit` into
the global git config before every Claude session. With that setting, git
refuses a bare repository it finds through the working directory; a caller has
to name one with `--git-dir`. Every autonomous workflow in this repo runs that
action, and its bot runs the regression suite to tick its DoD box.

This script runs the same targets twice, each time with its own temporary HOME
and XDG_CONFIG_HOME, so the global git config is one this script wrote:

  control   an empty global config
  hardened  `[safe] bareRepository = explicit`, what the action writes

The targets are every module under `tests/` that creates a bare repository,
plus the reproducers of two closed cards that read their bare remote the same
way. A unittest target reports how many tests ran and its result line; a
reproducer reports its exit code and last output line.

Exit 0 when every target behaves the same under both configs (fixed), 1 when
any target diverges (the defect fires), 2 when nothing can be measured: git is
older than 2.38, which ignores the setting, a target is missing, or the control
run itself fails.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".game-of-cards").is_dir():
            return p
        p = p.parent
    raise RuntimeError(".game-of-cards/ not found")


ROOT = _repo_root()
DECK = ROOT / ".game-of-cards" / "deck"
HARDENED = "[safe]\n\tbareRepository = explicit\n"

# Closed cards whose reproducer reads its bare remote by working directory. Each
# exited 0 under an empty global config when it was closed.
CLOSED_CARD_REPRODUCERS = [
    "deck-location-doc-says-claims-push-by-default-and-last-writer-wins",
    "deck-skill-promises-git-merge-settles-claim-races-the-default-config-never-detects",
]


def _git_version() -> tuple[int, ...]:
    out = subprocess.run(["git", "--version"], capture_output=True, text=True).stdout
    match = re.search(r"(\d+)\.(\d+)", out)
    return tuple(int(part) for part in match.groups()) if match else (0, 0)


def _env(home: Path) -> dict[str, str]:
    """The caller's environment with HOME moved and every GIT_* variable dropped."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["HOME"] = str(home)
    env["XDG_CONFIG_HOME"] = str(home / ".config")
    return env


def _bare_remote_test_modules() -> list[str]:
    return sorted(
        f"tests.{path.stem}"
        for path in (ROOT / "tests").glob("test_*.py")
        if "--bare" in path.read_text(encoding="utf-8")
    )


def _run_unittest(module: str, env: dict[str, str]) -> str:
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", module],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=600,
    )
    ran = re.search(r"^Ran (\d+) tests?", proc.stderr, re.MULTILINE)
    verdict = re.search(r"^(OK.*|FAILED \(.*\))$", proc.stderr, re.MULTILINE)
    return f"ran {ran.group(1) if ran else '?'}, {verdict.group(1) if verdict else 'no verdict'}"


def _run_reproducer(card: str, env: dict[str, str]) -> str:
    proc = subprocess.run(
        [sys.executable, str(DECK / card / "reproduce.py")],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=600,
    )
    lines = [line.strip() for line in (proc.stdout + proc.stderr).splitlines() if line.strip()]
    last = lines[-1] if lines else ""
    if len(last) > 70:
        last = last[:67] + "..."
    return f"exit {proc.returncode}: {last}"


def main() -> int:
    version = _git_version()
    print(f"git {'.'.join(map(str, version))}; safe.bareRepository is honored from 2.38")
    if version < (2, 38):
        print("Cannot measure: this git ignores safe.bareRepository.")
        return 2

    modules = _bare_remote_test_modules()
    missing = [card for card in CLOSED_CARD_REPRODUCERS if not (DECK / card / "reproduce.py").is_file()]
    if not modules or missing:
        print(f"Cannot measure: no bare-remote test module found, or reproducer(s) missing: {missing}")
        return 2

    targets = [(module, _run_unittest, module) for module in modules]
    targets += [(f"deck/{card[:40]}.../reproduce.py", _run_reproducer, card) for card in CLOSED_CARD_REPRODUCERS]

    results: dict[str, dict[str, str]] = {}
    with tempfile.TemporaryDirectory(prefix="goc-bare-hardening-") as tmp:
        for name, content in (("control", ""), ("hardened", HARDENED)):
            home = Path(tmp) / name
            (home / ".config").mkdir(parents=True)
            (home / ".gitconfig").write_text(content)
            env = _env(home)
            for label, runner, arg in targets:
                results.setdefault(label, {})[name] = runner(arg, env)

    print("global git config: control = empty; hardened = `[safe] bareRepository = explicit`")
    print()
    width = max(len(label) for label, _, _ in targets)
    diverged = 0
    for label, _, _ in targets:
        control, hardened = results[label]["control"], results[label]["hardened"]
        mark = "same" if control == hardened else "DIVERGES"
        diverged += control != hardened
        print(f"{label:<{width}}  [{mark}]")
        print(f"{'':<{width}}    control:  {control}")
        print(f"{'':<{width}}    hardened: {hardened}")

    # The control must pass outright: a unittest target ends in OK, a reproducer exits 0.
    control_failed = [
        label for label, runner, _ in targets
        if not (
            results[label]["control"].endswith(", OK")
            if runner is _run_unittest
            else results[label]["control"].startswith("exit 0:")
        )
    ]
    print()
    if control_failed:
        print(f"Cannot measure: the control run fails too: {control_failed}")
        return 2
    if diverged:
        print(
            f"DEFECT: {diverged} of {len(targets)} target(s) pass with an empty global git config and fail "
            "under the setting claude-code-action@v1 writes for every session."
        )
        return 1
    print(f"Fixed: all {len(targets)} target(s) behave the same under both global git configs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
