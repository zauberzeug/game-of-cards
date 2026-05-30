#!/usr/bin/env python3
"""Reproduce the autonomous-commit-bypass gap.

Two assertions, both of which must FAIL before the fix and PASS after:

  A. `.github/workflows/pull-card.yml` invokes `pre-commit` somewhere
     (either `pre-commit install` before the agent step, or an explicit
     `pre-commit run` / `goc validate` after the agent step).

  B. `uv run goc validate` exits 0 on the current deck (no orphan tag
     drift from prior bot commits that escaped the missing gate).

The script returns the same exit code as the assertions: 0 if both
pass (post-fix), 1 if either fails (current state).
"""
from __future__ import annotations

import re
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


def assert_pull_card_invokes_pre_commit(root: Path) -> tuple[bool, str]:
    """Assertion A: the workflow has some pre-commit / goc-validate gate."""
    wf = root / ".github" / "workflows" / "pull-card.yml"
    text = wf.read_text()
    # Match any of the legitimate gate forms.
    patterns = [
        r"\bpre-commit\s+install\b",
        r"\bpre-commit\s+run\b",
        r"\bgoc\s+validate\b",
    ]
    found = [p for p in patterns if re.search(p, text)]
    if found:
        return True, f"FOUND pre-commit/validate invocation(s) in pull-card.yml: {found}"
    return False, (
        "MISSING: pull-card.yml has no `pre-commit install`, "
        "`pre-commit run`, or `goc validate` step. The bot's "
        "`git commit` runs no .pre-commit-config.yaml gate."
    )


def assert_goc_validate_clean(root: Path) -> tuple[bool, str]:
    """Assertion B: `uv run goc validate` exits 0 on the current deck."""
    result = subprocess.run(
        ["uv", "run", "goc", "validate"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True, "goc validate: clean"
    # Surface up to 3 error lines for diagnosis. `goc validate` writes
    # ERROR/WARN lines to stderr; stdout carries the per-card OK summary.
    combined = (result.stdout + "\n" + result.stderr).splitlines()
    errors = [line for line in combined if line.startswith("ERROR:")][:3]
    return False, "goc validate FAILED (sample):\n  " + "\n  ".join(errors)


def main() -> int:
    root = _repo_root()
    a_ok, a_msg = assert_pull_card_invokes_pre_commit(root)
    b_ok, b_msg = assert_goc_validate_clean(root)
    print(f"[A] pull-card.yml runs pre-commit/validate: {'PASS' if a_ok else 'FAIL'}")
    print(f"    {a_msg}")
    print(f"[B] goc validate clean on current deck:    {'PASS' if b_ok else 'FAIL'}")
    print(f"    {b_msg}")
    return 0 if (a_ok and b_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
