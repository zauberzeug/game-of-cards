#!/usr/bin/env python3
"""Reproduce: sync_plugin_assets.py leaves orphaned hook files and --check passes.

Bug: hook mirrors are single-file sync pairs enumerated from the CURRENT
template set (`for name in hook_names:`), so when a hook template under
goc/templates/hooks/ is renamed or removed, the retired file is never pruned
from the flat hook mirrors (claude-plugin/hooks/, codex-plugin/hooks/,
.claude/hooks/) and `--check` reports OK because it only compares pair-listed
paths. The deep mirrors (claude-plugin/goc/templates/hooks/) are dir-syncs and
prune correctly, so the payload becomes internally inconsistent.

This script drives the real sync in-tree with a temp hook template, cleaning
up after itself. Exits 0 when the bug is FIXED (stale hook files pruned from
all flat mirrors, --check FAILs while one remains, hooks.json survives),
non-zero when the bug is present.
"""

from __future__ import annotations

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
SYNC = ROOT / "scripts" / "sync_plugin_assets.py"

TEMP_NAME = "zzz_temp_reproduce_hook.py"
FLAT_MIRRORS = [
    "claude-plugin/hooks",
    "codex-plugin/hooks",
    ".claude/hooks",
]
DEEP_MIRRORS = [
    "claude-plugin/goc/templates/hooks",
    "codex-plugin/goc/templates/hooks",
]


def run_sync(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SYNC), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def cleanup(src_hook: Path) -> None:
    if src_hook.exists():
        src_hook.unlink()
    for m in FLAT_MIRRORS + DEEP_MIRRORS:
        f = ROOT / m / TEMP_NAME
        if f.exists():
            f.unlink()


def main() -> int:
    src_hook = ROOT / "goc" / "templates" / "hooks" / TEMP_NAME
    cleanup(src_hook)  # start clean even if a prior run aborted

    failures: list[str] = []
    try:
        # 1. Create a temp hook template and sync it into the mirrors.
        src_hook.write_text('"""temp reproduce hook — safe to delete."""\n')
        run_sync()
        for m in FLAT_MIRRORS + DEEP_MIRRORS:
            if not (ROOT / m / TEMP_NAME).exists():
                print(f"UNEXPECTED setup: {m}/{TEMP_NAME} was not synced")
                cleanup(src_hook)
                return 1

        # 2. Remove the source hook (the rename/retire scenario) and re-sync.
        #    A fixed sync prunes the stale copy from every flat mirror.
        src_hook.unlink()
        run_sync()
        for m in FLAT_MIRRORS:
            if (ROOT / m / TEMP_NAME).exists():
                failures.append(f"stale {m}/{TEMP_NAME} survives the sync")
        for m in DEEP_MIRRORS:
            if (ROOT / m / TEMP_NAME).exists():
                failures.append(f"deep mirror {m}/{TEMP_NAME} not pruned (regression)")

        # 3. Non-synced plugin files in the same dirs must survive.
        for hooks_json in ("claude-plugin/hooks/hooks.json", "codex-plugin/hooks/hooks.json"):
            if not (ROOT / hooks_json).exists():
                failures.append(f"{hooks_json} was deleted by the sync (over-eager prune)")

        # 4. --check must FAIL while a stale hook file remains in a flat mirror.
        planted = ROOT / "claude-plugin" / "hooks" / TEMP_NAME
        planted.write_text('"""planted stale hook."""\n')
        check = run_sync("--check")
        if check.returncode == 0:
            failures.append(
                "--check exits 0 while a stale hook file sits in claude-plugin/hooks/"
            )
        planted.unlink()

        # 5. After cleanup, --check on the untouched tree must pass again.
        check = run_sync("--check")
        if check.returncode != 0:
            failures.append(
                "--check fails on a clean tree after the scenario "
                f"(leftover state?):\n{check.stdout}{check.stderr}"
            )
    finally:
        cleanup(src_hook)

    if failures:
        print("DEFECT PRESENT:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("FIXED: orphaned hook files are pruned and --check flags stale ones.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
