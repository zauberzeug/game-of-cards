#!/usr/bin/env python3
"""Sync plugin payloads from goc/ and goc/templates/ to claude-plugin/.

Run by pre-commit before every commit. When goc/ changes, this script
regenerates the plugin payload files and stages them so they're included
in the same commit — no manual edit-both-copies required.

Usage:
    python scripts/sync_plugin_assets.py          # sync + git-add (pre-commit mode)
    python scripts/sync_plugin_assets.py --check  # dry-run, exit 1 if out of sync (CI mode)
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (src, dst) pairs — src is the source of truth, dst is the generated copy.
# Directory pairs sync the full subtree; file pairs sync a single file.
# Files NOT listed here (claude-plugin/hooks/hooks.json, claude-plugin/bin/,
# claude-plugin/pyproject.toml, etc.) are plugin-specific and never touched.
SYNC_PAIRS: list[tuple[Path, Path]] = [
    (ROOT / "goc" / "templates" / "skills",
     ROOT / "claude-plugin" / "skills"),
    (ROOT / "goc" / "templates" / "hooks" / "deck_prompt_router.py",
     ROOT / "claude-plugin" / "hooks" / "deck_prompt_router.py"),
    (ROOT / "goc" / "templates" / "hooks" / "deck_session_start.py",
     ROOT / "claude-plugin" / "hooks" / "deck_session_start.py"),
    (ROOT / "goc" / "templates" / "hooks" / "pattern_generalization_check.py",
     ROOT / "claude-plugin" / "hooks" / "pattern_generalization_check.py"),
    (ROOT / "goc",
     ROOT / "claude-plugin" / "goc"),
]

_SKIP_FRAGMENTS = ("__pycache__", ".pyc")


def _skip(path: Path) -> bool:
    s = str(path)
    return any(frag in s for frag in _SKIP_FRAGMENTS)


def _sync_dir(src: Path, dst: Path) -> list[Path]:
    """Copy src → dst, remove dst-only files. Return changed dst paths."""
    changed: list[Path] = []

    # Remove files in dst that no longer exist in src.
    if dst.exists():
        for item in sorted(dst.rglob("*")):
            if _skip(item) or item.is_dir():
                continue
            rel = item.relative_to(dst)
            if not (src / rel).exists():
                item.unlink()
                changed.append(item)

    # Copy src → dst (new or changed files only).
    for src_item in sorted(src.rglob("*")):
        if _skip(src_item):
            continue
        rel = src_item.relative_to(src)
        dst_item = dst / rel
        if src_item.is_dir():
            dst_item.mkdir(parents=True, exist_ok=True)
        else:
            dst_item.parent.mkdir(parents=True, exist_ok=True)
            if not dst_item.exists() or not filecmp.cmp(src_item, dst_item, shallow=False):
                shutil.copy2(src_item, dst_item)
                changed.append(dst_item)

    return changed


def _sync_file(src: Path, dst: Path) -> list[Path]:
    if not dst.exists() or not filecmp.cmp(src, dst, shallow=False):
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return [dst]
    return []


def _compute_changes() -> list[Path]:
    changed: list[Path] = []
    for src, dst in SYNC_PAIRS:
        if src.is_dir():
            changed.extend(_sync_dir(src, dst))
        else:
            changed.extend(_sync_file(src, dst))
    return changed


def _check_changes() -> list[Path]:
    """Return list of dst paths that differ from src, without modifying anything."""
    out: list[Path] = []
    for src, dst in SYNC_PAIRS:
        if src.is_dir():
            for src_item in sorted(src.rglob("*")):
                if _skip(src_item) or src_item.is_dir():
                    continue
                rel = src_item.relative_to(src)
                dst_item = dst / rel
                if not dst_item.exists() or not filecmp.cmp(src_item, dst_item, shallow=False):
                    out.append(dst_item)
            if dst.exists():
                for dst_item in sorted(dst.rglob("*")):
                    if _skip(dst_item) or dst_item.is_dir():
                        continue
                    rel = dst_item.relative_to(dst)
                    if not (src / rel).exists():
                        out.append(dst_item)
        else:
            if not dst.exists() or not filecmp.cmp(src, dst, shallow=False):
                out.append(dst)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report out-of-sync files and exit 1 without modifying anything (CI mode).",
    )
    args = parser.parse_args(argv)

    if args.check:
        diffs = _check_changes()
        if diffs:
            print("ERROR: plugin assets are out of sync with goc/:")
            for p in diffs:
                print(f"  {p.relative_to(ROOT)}")
            print("Fix: run `python scripts/sync_plugin_assets.py` and commit the result.")
            return 1
        print("OK — plugin assets match goc/ and goc/templates/ byte-for-byte.")
        return 0

    changed = _compute_changes()
    if changed:
        rel = [str(p.relative_to(ROOT)) for p in changed]
        subprocess.run(["git", "add", "--"] + rel, check=True, cwd=ROOT)
        print(f"sync-plugin-assets: synced {len(changed)} file(s), staged for commit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
