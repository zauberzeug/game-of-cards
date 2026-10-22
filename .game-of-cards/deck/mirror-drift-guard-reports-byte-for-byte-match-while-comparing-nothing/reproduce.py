#!/usr/bin/env python3
"""The plugin-mirror drift guard passes while comparing nothing.

Exports the repo into a directory whose name contains `.pyc` (e.g. `.pycharm`),
corrupts a mirrored file and deletes a mirrored hook, then asks the guard.
A working guard reports drift; today it reports a byte-for-byte match.

Exits 0 once the guard detects the injected drift under such a path.
"""

from __future__ import annotations

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


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="goc-pycpath-"))
    try:
        # A real-world directory name that contains the ".pyc" fragment.
        repo = work / ".pycharm" / "checkout"
        repo.mkdir(parents=True)
        archive = subprocess.run(
            ["git", "archive", "HEAD"], cwd=ROOT, capture_output=True, check=True,
        ).stdout
        subprocess.run(["tar", "-x", "-C", str(repo)], input=archive, check=True)

        script = repo / "scripts" / "sync_plugin_assets.py"
        drifted = repo / "claude-plugin" / "skills" / "deck" / "SKILL.md"
        deleted = repo / "claude-plugin" / "hooks" / "deck_session_start.py"

        base = subprocess.run(
            [sys.executable, str(script), "--check"], cwd=repo,
            capture_output=True, text=True,
        )
        print(f"baseline   : exit={base.returncode} :: {base.stdout.strip().splitlines()[-1]}")

        with drifted.open("a") as fh:
            fh.write("\nDRIFTED CONTENT\n")
        deleted.unlink()

        after = subprocess.run(
            [sys.executable, str(script), "--check"], cwd=repo,
            capture_output=True, text=True,
        )
        last = (after.stdout.strip().splitlines() or ["(no output)"])[-1]
        print(f"after drift: exit={after.returncode} :: {last}")

        sync = subprocess.run(
            [sys.executable, str(script)], cwd=repo, capture_output=True, text=True,
        )
        # The extracted fixture is not a git repo, so the script's closing
        # `git add` of the synced paths fails AFTER the files are written:
        # empty stdout here means "nothing staged", not "nothing done". The
        # `after sync` line below is what distinguishes a no-op from a repair.
        print(f"sync run   : exit={sync.returncode} :: "
              f"{sync.stdout.strip() or '(no stdout — git add fails outside a repo)'}")

        still_drifted = "DRIFTED CONTENT" in drifted.read_text()
        still_missing = not deleted.exists()
        print(f"after sync : content still drifted={still_drifted}, "
              f"hook still missing={still_missing}")

        if after.returncode == 0:
            print("\n[FAIL] --check reported success with a corrupted mirror and a "
                  "deleted hook: the guard compared nothing.")
            return 1
        print("\n[OK] the guard detects drift under a checkout path containing '.pyc'.")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
