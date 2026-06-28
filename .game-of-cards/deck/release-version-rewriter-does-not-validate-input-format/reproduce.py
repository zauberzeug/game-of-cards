"""Demonstrate that `scripts/release_rewrite_versions.py` mutates seven
files before its only format-validating regex (AGENTS.md) fails out.

Snapshots the seven target files, runs the rewriter with a malformed
version, asserts each target was mutated, then restores the snapshots
so the working tree is unchanged.

Run from anywhere:

    uv run python .game-of-cards/deck/release-version-rewriter-does-not-validate-input-format/reproduce.py
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
sys.path.insert(0, str(ROOT))

TARGETS = [
    ROOT / "goc" / "__init__.py",
    ROOT / "openclaw-plugin" / "package.json",
    ROOT / "openclaw-plugin" / "package-lock.json",
    ROOT / "claude-plugin" / ".claude-plugin" / "plugin.json",
    ROOT / "codex-plugin" / ".codex-plugin" / "plugin.json",
    ROOT / ".claude-plugin" / "marketplace.json",
    ROOT / ".game-of-cards" / "deck" / ".goc-version",
]
AGENTS_MD = ROOT / "AGENTS.md"

MALFORMED_VERSION = "1.0"  # missing the .Z segment — caught only by AGENTS.md regex


def main() -> int:
    # Snapshot every file the rewriter might touch.
    snapshot = {p: p.read_bytes() for p in TARGETS + [AGENTS_MD]}

    try:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "release_rewrite_versions.py"),
                MALFORMED_VERSION,
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

        mutated = []
        unchanged = []
        for p in TARGETS + [AGENTS_MD]:
            now = p.read_bytes()
            (mutated if now != snapshot[p] else unchanged).append(
                p.relative_to(ROOT)
            )

        print(f"--- script exit code: {result.returncode}")
        print("--- script stderr ---")
        print(result.stderr.rstrip() or "(empty)")
        print()
        print(f"--- mutated files ({len(mutated)}) ---")
        for p in mutated:
            print(f"  {p}")
        print(f"--- unchanged files ({len(unchanged)}) ---")
        for p in unchanged:
            print(f"  {p}")
        print()

        # Verdict: the defect is "no input format validation." A correctly
        # guarded rewriter refuses a malformed version with a non-zero exit
        # code AND zero file mutations. Repo convention: exit 0 == post-fix.
        total_files = len(TARGETS) + 1   # +1 for AGENTS.md
        if result.returncode != 0 and len(mutated) == 0:
            print(
                "VERDICT: post-fix. Rewriter rejected malformed input before "
                "writing any file. exit 0."
            )
            return 0
        if result.returncode == 0 and len(mutated) == total_files:
            print(
                f"VERDICT: pre-fix. Rewriter exited 0 (silent success) after "
                f"mutating ALL {total_files} target files with malformed input "
                f"{MALFORMED_VERSION!r}. exit 1."
            )
            return 1
        print(
            f"VERDICT: partial. Rewriter exited {result.returncode} after "
            f"mutating {len(mutated)} of {total_files} files. exit 1."
        )
        return 1

    finally:
        # Always restore the snapshots so the working tree is unchanged.
        for p, original in snapshot.items():
            p.write_bytes(original)


if __name__ == "__main__":
    sys.exit(main())
