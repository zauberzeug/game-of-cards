"""Reproduce: `goc status <card> superseded` accepts no `--by` and the result
passes `goc validate` with no `superseded_by` field set.

The defect lives at two surfaces of the engine:

  - `goc/engine.py:_cmd_status` does not require `--by` when
    `new_status == "superseded"`.
  - `goc/engine.py:validate_card` only enforces `superseded_by ->
    status: superseded`, not the inverse.

Both together let a card reach the terminal `superseded` state with no
forward routing pointer, breaking the deck-as-record axis described in
AGENTS.md (the supersession link is supposed to be set atomically with
the status flip).

This reproducer:
  1. Creates a throwaway deck in a temp dir.
  2. Files a card and flips it open -> active -> superseded with NO --by.
  3. Asserts the resulting frontmatter has status: superseded and an
     empty / missing superseded_by.
  4. Runs `goc validate` and asserts it exits 0 (the bug — should be
     non-zero).

Exit code 0 means the defect is present (current behavior).
Exit code 1 means the fix has landed and the orphan transition is rejected.
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


REPO_ROOT = _repo_root()


def run_goc(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "--project", str(REPO_ROOT), "goc", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        sandbox = Path(td)
        # Minimal git env so goc's auto-commit doesn't error fatally on missing
        # identity. We're not relying on git here; the test just needs the
        # filesystem mutations.
        env = os.environ.copy()
        env.setdefault("GIT_AUTHOR_NAME", "Repro")
        env.setdefault("GIT_AUTHOR_EMAIL", "repro@example.invalid")
        env.setdefault("GIT_COMMITTER_NAME", "Repro")
        env.setdefault("GIT_COMMITTER_EMAIL", "repro@example.invalid")
        subprocess.run(["git", "init", "-q"], cwd=sandbox, env=env, check=True)

        install = subprocess.run(
            ["uv", "run", "--project", str(REPO_ROOT), "goc", "install", "--local-skills"],
            cwd=sandbox,
            env=env,
            capture_output=True,
            text=True,
            input="y\ny\ny\n",
        )
        if install.returncode != 0:
            print("FAIL: goc install failed:", install.stderr, file=sys.stderr)
            return 2

        title = "demo-card"
        new = subprocess.run(
            ["uv", "run", "--project", str(REPO_ROOT), "goc", "new", title],
            cwd=sandbox,
            env=env,
            capture_output=True,
            text=True,
        )
        if new.returncode != 0:
            print("FAIL: goc new failed:", new.stderr, file=sys.stderr)
            return 2

        active = subprocess.run(
            ["uv", "run", "--project", str(REPO_ROOT), "goc", "status", title, "active"],
            cwd=sandbox,
            env=env,
            capture_output=True,
            text=True,
        )
        if active.returncode != 0:
            print("FAIL: goc status active failed:", active.stderr, file=sys.stderr)
            return 2

        # The defect: no --by argument here.
        superseded = subprocess.run(
            ["uv", "run", "--project", str(REPO_ROOT), "goc", "status", title, "superseded"],
            cwd=sandbox,
            env=env,
            capture_output=True,
            text=True,
        )

        card_path = sandbox / ".game-of-cards" / "deck" / title / "README.md"
        body = card_path.read_text() if card_path.exists() else ""
        validate = subprocess.run(
            ["uv", "run", "--project", str(REPO_ROOT), "goc", "validate"],
            cwd=sandbox,
            env=env,
            capture_output=True,
            text=True,
        )

        print("=" * 64)
        print("CLI exit code for `goc status <c> superseded` (no --by):",
              superseded.returncode)
        print()
        print("Resulting frontmatter snippet:")
        for line in body.splitlines()[:14]:
            print("  ", line)
        print()
        print("`goc validate` exit code:", validate.returncode)
        print("`goc validate` stdout tail:")
        for line in (validate.stdout or "").splitlines()[-3:]:
            print("  ", line)
        print("=" * 64)

        status_is_superseded = "\nstatus: superseded" in body
        superseded_by_is_missing_or_empty = (
            "\nsuperseded_by:" not in body
            or "\nsuperseded_by: []" in body
        )
        validate_clean = validate.returncode == 0

        defect_present = (
            superseded.returncode == 0
            and status_is_superseded
            and superseded_by_is_missing_or_empty
            and validate_clean
        )

        if defect_present:
            print("DEFECT REPRODUCED:")
            print("  - CLI accepted `goc status <c> superseded` with no --by")
            print("  - Card has status: superseded and no superseded_by link")
            print("  - `goc validate` reports OK (asymmetric check)")
            return 0
        print("FIXED: the orphan supersession state is no longer reachable.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
