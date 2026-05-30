"""Demonstrate that filecmp.dircmp (used by goc/engine.py:1185 in
validate_plugin_mirror_parity) reports two same-length, same-mtime,
content-different files as identical, while filecmp.cmp(shallow=False)
(used by scripts/sync_plugin_assets.py) correctly reports them as
different.

Run: uv run python .game-of-cards/deck/validate-plugin-mirror-parity-uses-shallow-filecmp-missing-content-drift/reproduce.py
"""

from __future__ import annotations

import filecmp
import os
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


sys.path.insert(0, str(_repo_root()))


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        left = Path(tmp) / "src"
        right = Path(tmp) / "dst"
        left.mkdir()
        right.mkdir()

        # Same length, different content. Identical mtime to mimic a fresh
        # checkout, where every working-tree file is stamped at checkout time.
        (left / "file.txt").write_text("hello world")
        (right / "file.txt").write_text("HELLO WORLD")
        stamp = 1_735_689_600  # 2025-01-01T00:00:00Z, arbitrary fixed value
        os.utime(left / "file.txt", (stamp, stamp))
        os.utime(right / "file.txt", (stamp, stamp))

        cmp = filecmp.dircmp(str(left), str(right))
        deep = filecmp.cmp(left / "file.txt", right / "file.txt", shallow=False)

        print("filecmp.dircmp (used by goc/engine.py:1185):")
        print(f"  diff_files: {cmp.diff_files}")
        print(f"  same_files: {cmp.same_files}")
        print("filecmp.cmp(shallow=False) (used by scripts/sync_plugin_assets.py):")
        print(f"  {deep}")

        if cmp.diff_files == [] and cmp.same_files == ["file.txt"] and deep is False:
            print(
                "verdict: dircmp says identical, deep cmp says different — "
                "engine\n         tripwire silently misses content drift in "
                "the plugin mirrors."
            )
            return 1  # defect present
        print("verdict: defect not reproduced (unexpected).")
        return 0


if __name__ == "__main__":
    sys.exit(main())
