"""Demonstrate that goc query flags accept invalid input / contradictory
compositions silently (exit 0, no diagnostic), one probe per catalogued
instance.

Exits non-zero while any probe shows the silent behavior; exits zero once
every probe either hard-errors or emits a diagnostic naming the problem
(fix-shape neutral: an exit-2 error and a stderr WARN both count).

Run: uv run python .game-of-cards/deck/<this-card>/reproduce.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()


def goc(*flags: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    env.pop("GOC_WORKER", None)
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *flags],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )


def check(name: str, flags: list[str], token: str, extra_guard=None) -> bool:
    """A probe is GUARDED when it exits non-zero OR its stderr mentions
    `token` (the offending flag/value), OR `extra_guard(stdout)` accepts
    the output. Otherwise the defect fires."""
    r = goc(*flags)
    diagnosed = r.returncode != 0 or token in r.stderr
    if not diagnosed and extra_guard is not None:
        diagnosed = extra_guard(r.stdout)
    verdict = "OK  (guarded)" if diagnosed else "FAIL (silent, exit 0)"
    print(f"[{verdict}] goc {' '.join(flags)}")
    if not diagnosed:
        first = next((l for l in r.stdout.splitlines() if l.strip()), "<no stdout>")
        print(f"         exit={r.returncode}  stdout[0]={first[:70]!r}")
    return diagnosed


def _is_json(stdout: str) -> bool:
    try:
        json.loads(stdout)
        return True
    except ValueError:
        return False


failures = 0
failures += not check(
    "advances-unknown", ["--advances", "no-such-card-xyz-reproduce"],
    "no-such-card-xyz-reproduce")
failures += not check(
    "advanced-by-unknown", ["--advanced-by", "no-such-card-xyz-reproduce"],
    "no-such-card-xyz-reproduce")
failures += not check(
    "json-vs-board", ["--json", "--board"], "--board", extra_guard=_is_json)
failures += not check(
    "open-vs-closed-since", ["--status", "open", "--closed-since", "7d"],
    "--closed-since")
failures += not check(
    "waiting-vs-closed-since", ["--waiting", "--closed-since", "24h"],
    "--closed-since")

print()
print("contrast (per-flag guards that DO exist):")
r = goc("--tag", "no-such-tag")
print(f"  goc --tag no-such-tag           -> exit={r.returncode} "
      f"stderr={r.stderr.splitlines()[-1][:60]!r}" if r.stderr else "")
r = goc("--done", "--status", "open")
print(f"  goc --done --status open        -> exit={r.returncode} "
      f"stderr={r.stderr.splitlines()[-1][:60]!r}" if r.stderr else "")

print()
if failures:
    print(f"DEFECT: {failures}/5 query-flag probes silently return "
          f"wrong/empty output with exit 0")
    sys.exit(1)
print("all probes guarded — defect no longer fires")
