"""Prove the OpenClaw porter's orphan detection misses asset-only dirs.

Plants openclaw-plugin/skills/zombie-repro-dir/asset.txt (no SKILL.md),
runs `port_skills_to_openclaw.py --check` and a real re-port, then removes
the planted dir (try/finally, so the tree is restored even on error).

Exits 0 when the asset-only dst-only dir is flagged by --check or removed
by the re-port (fixed); exits 1 while it is invisible to both (defect).
"""

import shutil
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


def main() -> int:
    root = _repo_root()
    porter = root / "scripts" / "port_skills_to_openclaw.py"
    zombie = root / "openclaw-plugin" / "skills" / "zombie-repro-dir"
    if zombie.exists():
        print(f"refusing to run: {zombie} already exists")
        return 1
    try:
        zombie.mkdir()
        (zombie / "asset.txt").write_text("stale\n")

        check = subprocess.run(
            [sys.executable, str(porter), "--check"],
            capture_output=True, text=True, cwd=root,
        )
        print(f"--check exit code with asset-only zombie dir present: "
              f"{check.returncode} (expected nonzero)")
        if check.returncode != 0:
            print("OK: --check flags the asset-only orphan")
            return 0

        subprocess.run(
            [sys.executable, str(porter)],
            capture_output=True, text=True, cwd=root, check=True,
        )
        survived = (zombie / "asset.txt").is_file()
        print(f"zombie survived a full re-port: {survived}")
        if not survived:
            print("OK: re-port pruned the asset-only orphan")
            return 0
        print("DEFECT CONFIRMED: asset-only dst-only dir is invisible to "
              "check and prune")
        return 1
    finally:
        shutil.rmtree(zombie, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
