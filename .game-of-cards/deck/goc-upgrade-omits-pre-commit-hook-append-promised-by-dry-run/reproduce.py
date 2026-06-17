"""Reproduce: `goc upgrade` never appends the pre-commit hook its dry-run plan promises.

Steps:
  1. `goc install` in a directory with no `.git` -> hook skipped (expected).
  2. `git init`, then `goc upgrade --dry-run` -> plan lists the pre-commit append.
  3. Real `goc upgrade` -> the file is STILL absent (the bug).

Exits non-zero while the bug is present, zero once the fix lands.
"""

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


REPO = _repo_root()


def _goc(args, cwd):
    return subprocess.run(
        ["uv", "run", "--project", str(REPO), "goc", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as wd:
        wd = Path(wd)
        cfg = wd / ".pre-commit-config.yaml"

        # 1. install without .git -> hook skipped
        _goc(["install", "--agents", "claude", "--local-skills"], wd)
        print(f"after install (no .git): .pre-commit-config.yaml exists = {cfg.exists()}")

        # 2. git init + dry-run plan
        subprocess.run(["git", "init", "-q"], cwd=wd, check=True)
        plan = _goc(["upgrade", "--keep-local-skills", "--dry-run"], wd)
        plan_promises = "append .pre-commit-config.yaml" in plan.stdout
        print(f"dry-run plan promises pre-commit append = {plan_promises}")

        # 3. real upgrade
        _goc(["upgrade", "--keep-local-skills"], wd)
        present_after = cfg.exists() and "id: goc-validate" in cfg.read_text()
        print(f"after real upgrade: hook present = {present_after}")

        if plan_promises and not present_after:
            print("\nFAIL: dry-run plan promised the pre-commit append but the real upgrade did not perform it.")
            return 1
        print("\nOK: dry-run plan and real upgrade agree on the pre-commit hook.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
