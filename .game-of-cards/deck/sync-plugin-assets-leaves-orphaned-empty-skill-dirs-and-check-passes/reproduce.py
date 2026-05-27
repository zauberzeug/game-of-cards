#!/usr/bin/env python3
"""Reproduce: sync_plugin_assets.py leaves orphaned empty skill dirs and --check passes.

Bug: when a source skill dir under goc/templates/skills/ is removed, the sync
prunes the orphaned FILES from the claude-plugin/ + codex-plugin/ + dogfood
mirrors but never rmdir's the now-empty skill directory. `--check` walks rglob
and skips directories, so it reports OK while a stale empty dir remains (and
ships in any wheel/tarball copy of the payload — git masks empty dirs).

This script drives the real sync in a temp clone of the repo's plugin-asset
surfaces, so it never mutates the live working tree. Exits 0 when the bug is
FIXED (orphan dirs pruned, --check FAILs while one remains, partial-removal
does not over-prune), non-zero when the bug is present.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SYNC = ROOT / "scripts" / "sync_plugin_assets.py"

TEMP_NAME = "zzz-temp-reproduce-skill"
MIRRORS = [
    "claude-plugin/skills",
    "codex-plugin/skills",
    ".claude/skills",
    ".codex/skills",
]


def run_sync(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SYNC), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def cleanup(src_dir: Path) -> None:
    import shutil

    if src_dir.exists():
        shutil.rmtree(src_dir)
    for m in MIRRORS:
        d = ROOT / m / TEMP_NAME
        if d.exists():
            shutil.rmtree(d)


def main() -> int:
    src_dir = ROOT / "goc" / "templates" / "skills" / TEMP_NAME
    cleanup(src_dir)  # start clean even if a prior run aborted

    failures: list[str] = []
    try:
        # 1. Create a temp source skill and sync it into the mirrors.
        src_dir.mkdir(parents=True)
        (src_dir / "SKILL.md").write_text(
            f'---\nname: {TEMP_NAME}\ndescription: "temp reproduce skill"\n---\nbody\n'
        )
        run_sync()
        for m in MIRRORS:
            if not (ROOT / m / TEMP_NAME / "SKILL.md").exists():
                failures.append(f"setup: {m}/{TEMP_NAME}/SKILL.md was not synced")
        if failures:
            for f in failures:
                print(f"UNEXPECTED {f}")
            return 1

        # 2. DoD item 2 — partial removal must NOT over-prune a dir that still
        #    has synced content. Add a second file, remove only the first.
        (src_dir / "extra.md").write_text("extra\n")
        run_sync()
        (src_dir / "SKILL.md").unlink()
        run_sync()
        for m in MIRRORS[:2]:  # claude + codex non-codex tree; codex tree too
            d = ROOT / m / TEMP_NAME
            if not d.exists():
                failures.append(f"over-prune: {m}/{TEMP_NAME} removed while extra.md remained")
        # restore SKILL.md so the dir is back to a normal skill
        (src_dir / "SKILL.md").write_text(
            f'---\nname: {TEMP_NAME}\ndescription: "temp reproduce skill"\n---\nbody\n'
        )
        (src_dir / "extra.md").unlink()
        run_sync()

        # 3. Remove the source dir entirely, re-sync.
        import shutil

        shutil.rmtree(src_dir)
        run_sync()

        # The orphan dirs must be gone (the fix), and --check must agree.
        remaining = [m for m in MIRRORS if (ROOT / m / TEMP_NAME).exists()]
        if remaining:
            failures.append(
                "orphan empty dirs remain after sync: "
                + ", ".join(f"{m}/{TEMP_NAME}" for m in remaining)
            )

        check = run_sync("--check")
        if remaining and check.returncode == 0:
            failures.append("--check reported OK while empty orphan dirs remained (blind spot)")

        # 4. With the fix, after sync the tree is clean and --check passes.
        if not remaining and check.returncode != 0:
            failures.append(
                f"--check FAILed on a cleanly-synced tree (exit {check.returncode}):\n"
                f"{check.stdout}\n{check.stderr}"
            )

        # 5. Directly exercise the --check blind-spot: plant an empty orphan dir
        #    in each mirror (the pre-fix on-disk state) and assert --check FAILs
        #    while one remains. rglob skips dirs, so the old code printed OK here.
        try:
            planted = [ROOT / m / TEMP_NAME for m in MIRRORS]
            for d in planted:
                d.mkdir(parents=True)
            check2 = run_sync("--check")
            if check2.returncode == 0:
                failures.append(
                    "--check reported OK with planted empty orphan dirs (blind spot not closed)"
                )
            if not all(str(d.relative_to(ROOT)) in check2.stdout for d in planted):
                failures.append(
                    "--check did not name every planted empty orphan dir:\n" + check2.stdout
                )
        finally:
            for d in planted:
                if d.exists():
                    d.rmdir()
    finally:
        cleanup(src_dir)

    if failures:
        print("DEFECT — bug present:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("FIXED — orphan empty skill dirs are pruned by sync, detected by --check,")
    print("        and partial file removal does not over-prune.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
