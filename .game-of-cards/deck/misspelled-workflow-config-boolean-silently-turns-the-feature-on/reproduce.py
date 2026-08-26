#!/usr/bin/env python3
"""Prove that an unrecognized `workflow` config scalar reads as True.

Two layers of evidence:

1. **Unit** — `_coerce_config_bool` over every scalar `yaml_lite` can hand it,
   printing the coerced value under both defaults. Any value outside
   `{"0","false","no","off"}` (and falsy non-strings) becomes True.
2. **End-to-end** — two throwaway git repos driven through the real CLI:
   `workflow.claim_push: nope` makes `goc status <card> active` attempt a
   `git push` (documented opt-in, default off), and `workflow.auto_commit: of`
   leaves auto-commit running with no warning, while the correctly spelled
   `off` disables it and warns.

Exit 0 = defect gone. Exit 1 = defect present.
"""

from __future__ import annotations

import os
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
sys.path.insert(0, str(ROOT))

from goc._vendor import yaml_lite  # noqa: E402
from goc.engine import _coerce_config_bool  # noqa: E402

#: Scalars a user could plausibly write, paired with what they meant.
#: `None` means "no intent — YAML-canonical, correctly handled".
CASES: list[tuple[str, bool | None]] = [
    ("true", None),
    ("false", None),
    ("True", None),
    ("False", None),
    ("yes", None),
    ("no", None),
    ("on", None),
    ("off", None),
    # Plausible misspellings / near-misses of an intended OFF.
    ("of", False),
    ("n", False),
    ("none", False),
    ("nope", False),
    ("disabled", False),
    ("Disabled", False),
]


def unit_evidence() -> list[str]:
    """Return the misspellings that coerce to True instead of the intended False."""
    print("=== 1. _coerce_config_bool over YAML scalars ===")
    print(f"{'config value':>12} | {'yaml_lite':>12} | {'default=True':>12} | {'default=False':>13}")
    print("-" * 60)
    wrong: list[str] = []
    for raw, intent in CASES:
        parsed = yaml_lite.safe_load(f"workflow:\n  k: {raw}\n")["workflow"]["k"]
        as_true = _coerce_config_bool(parsed, default=True)
        as_false = _coerce_config_bool(parsed, default=False)
        mark = ""
        if intent is False and (as_true is not False or as_false is not False):
            wrong.append(raw)
            mark = "  <-- meant OFF, reads ON"
        print(f"{raw:>12} | {parsed!r:>12} | {str(as_true):>12} | {str(as_false):>13}{mark}")
    print()
    return wrong


def _make_repo(tmp: Path, config: str) -> Path:
    repo = tmp / "repo"
    (repo / ".game-of-cards" / "deck").mkdir(parents=True)
    (repo / ".game-of-cards" / "config.yaml").write_text(config)
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    run = lambda *a: subprocess.run(a, cwd=repo, check=True, capture_output=True, text=True)
    run("git", "init", "-q", ".")
    run("git", "config", "user.email", "probe@example.invalid")
    run("git", "config", "user.name", "probe")
    subprocess.run(
        [sys.executable, "-m", "goc.cli", "new", "probe-card", "--summary", "S", "--gate", "none"],
        cwd=repo, env=env, check=True, capture_output=True, text=True,
    )
    run("git", "add", "-A")
    run("git", "commit", "-qm", "init")
    return repo


def _goc_status(repo: Path, *args: str) -> str:
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    proc = subprocess.run(
        [sys.executable, "-m", "goc.cli", "status", *args],
        cwd=repo, env=env, capture_output=True, text=True,
    )
    return proc.stdout + proc.stderr


def e2e_evidence() -> list[str]:
    """Drive the real CLI; return the observed silent-enable symptoms."""
    print("=== 2. end-to-end through the CLI ===")
    symptoms: list[str] = []

    with tempfile.TemporaryDirectory() as td:
        repo = _make_repo(Path(td), "workflow:\n  claim_push: nope\n")
        out = _goc_status(repo, "probe-card", "active")
        pushed = "push failed" in out or "push" in out.lower()
        print(f"claim_push: nope  -> push attempted: {pushed}   (documented default: off)")
        if pushed:
            symptoms.append("claim_push: nope armed the remote-push path")

    with tempfile.TemporaryDirectory() as td:
        repo = _make_repo(Path(td), "workflow:\n  auto_commit: of\n")
        out = _goc_status(repo, "probe-card", "active")
        committed = "committed" in out
        warned = "auto_commit is disabled" in out
        print(f"auto_commit: of   -> auto-committed: {committed}, warned: {warned}")
        if committed or not warned:
            symptoms.append("auto_commit: of kept auto-commit on, with no warning")

    with tempfile.TemporaryDirectory() as td:
        repo = _make_repo(Path(td), "workflow:\n  auto_commit: off\n")
        out = _goc_status(repo, "probe-card", "active")
        committed = "committed" in out
        warned = "auto_commit is disabled" in out
        print(f"auto_commit: off  -> auto-committed: {committed}, warned: {warned}   (control)")
        if committed or not warned:
            symptoms.append("CONTROL BROKEN: correctly spelled `off` did not disable auto-commit")

    print()
    return symptoms


def main() -> int:
    wrong = unit_evidence()
    symptoms = e2e_evidence()
    if not wrong and not symptoms:
        print("PASS: unrecognized workflow-config scalars no longer read as True.")
        return 0
    print("FAIL: unrecognized workflow-config scalars silently read as True.")
    if wrong:
        print(f"  {len(wrong)} misspelling(s) meant OFF but coerced ON: {', '.join(wrong)}")
    for s in symptoms:
        print(f"  {s}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
