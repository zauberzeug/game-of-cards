#!/usr/bin/env python3
"""Sync plugin payloads from goc/ and goc/templates/ to claude-plugin/ and openclaw-plugin/.

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
sys.path.insert(0, str(ROOT))

from goc.install import deck_hook_scripts  # noqa: E402


def _build_sync_pairs() -> list[tuple[Path, Path, frozenset[str]]]:
    """Compute (src, dst, excludes) pairs by deriving the hook list from templates/hooks/.

    Plugin-specific files NOT touched by this sync (`claude-plugin/hooks/hooks.json`,
    `claude-plugin/bin/`, `claude-plugin/pyproject.toml`, `openclaw-plugin/index.ts`,
    `openclaw-plugin/package.json`, `openclaw-plugin/skills/`, etc.) are not in
    the pair list and stay untouched.

    The bundled engine in `claude-plugin/goc/` refuses `--local-skills` and
    `--keep-local-skills` (see `_is_plugin_context` in goc/install.py), so it
    never reads `templates/skills/`. That path is excluded from the
    `goc → claude-plugin/goc` deep mirror; hook scripts are NOT excluded so
    the bundled engine can derive its hook list from `templates/hooks/`.

    The OpenClaw plugin reimplements every deck hook in TypeScript inside
    `openclaw-plugin/index.ts`, so its deep mirror also excludes
    `templates/hooks/*.py` (in addition to `templates/skills/`).
    """
    templates = ROOT / "goc" / "templates"
    hook_names = deck_hook_scripts(templates)

    pairs: list[tuple[Path, Path, frozenset[str]]] = []

    # --- Claude plugin payload ---
    # Exclude OpenClaw-only host complements (e.g. `openclaw-kickoff`) from
    # the Claude plugin's skill set. They live in templates/skills/ as the
    # source of truth, but the Claude plugin must never ship them.
    skills_src = templates / "skills"
    openclaw_only_skills = frozenset(
        p.name
        for p in skills_src.iterdir()
        if p.is_dir() and p.name.startswith("openclaw-")
    )
    pairs.append(
        (templates / "skills", ROOT / "claude-plugin" / "skills", openclaw_only_skills)
    )
    for name in hook_names:
        pairs.append(
            (
                templates / "hooks" / name,
                ROOT / "claude-plugin" / "hooks" / name,
                frozenset(),
            )
        )
    pairs.append(
        (
            ROOT / "goc",
            ROOT / "claude-plugin" / "goc",
            frozenset({"templates/skills"}),
        )
    )

    # --- OpenClaw plugin payload ---
    # Engine only — skills are hand-ported, hooks are TypeScript ports
    # in openclaw-plugin/index.ts.
    pairs.append(
        (
            ROOT / "goc",
            ROOT / "openclaw-plugin" / "goc",
            frozenset({"templates/skills"})
            | frozenset(f"templates/hooks/{name}" for name in hook_names),
        )
    )

    return pairs


SYNC_PAIRS: list[tuple[Path, Path, frozenset[str]]] = _build_sync_pairs()

_SKIP_FRAGMENTS = ("__pycache__", ".pyc")


def _excluded(rel: Path, excludes: frozenset[str]) -> bool:
    """True if `rel` is, or lives under, any excluded subpath."""
    if not excludes:
        return False
    parts = rel.as_posix()
    for ex in excludes:
        if parts == ex or parts.startswith(ex + "/"):
            return True
    return False


def _skip(path: Path) -> bool:
    s = str(path)
    return any(frag in s for frag in _SKIP_FRAGMENTS)


def _sync_dir(src: Path, dst: Path, excludes: frozenset[str] = frozenset()) -> list[Path]:
    """Copy src → dst, remove dst-only files. Return changed dst paths.

    Subpaths listed in `excludes` (relative to src) are skipped in both
    directions: they are never copied from src and never removed from dst —
    so an excluded path that exists in dst (but not src) is left alone, and
    an excluded path that exists in src (but not dst) is not mirrored.
    Excluded paths in dst that are *files* (e.g. stale leftovers) are removed
    so the dst tree can shrink as the exclusion list grows.
    """
    changed: list[Path] = []

    # Remove files in dst that no longer exist in src OR are now excluded.
    if dst.exists():
        for item in sorted(dst.rglob("*")):
            if _skip(item) or item.is_dir():
                continue
            rel = item.relative_to(dst)
            if _excluded(rel, excludes):
                item.unlink()
                changed.append(item)
                continue
            if not (src / rel).exists():
                item.unlink()
                changed.append(item)

    # Copy src → dst (new or changed files only), respecting excludes.
    for src_item in sorted(src.rglob("*")):
        if _skip(src_item):
            continue
        rel = src_item.relative_to(src)
        if _excluded(rel, excludes):
            continue
        dst_item = dst / rel
        if src_item.is_dir():
            dst_item.mkdir(parents=True, exist_ok=True)
        else:
            dst_item.parent.mkdir(parents=True, exist_ok=True)
            if not dst_item.exists() or not filecmp.cmp(src_item, dst_item, shallow=False):
                shutil.copy2(src_item, dst_item)
                changed.append(dst_item)

    # Prune empty excluded directories so they don't linger in the payload.
    if dst.exists():
        for ex in excludes:
            ex_dir = dst / ex
            if ex_dir.is_dir():
                # Walk depth-first and remove anything left.
                for item in sorted(ex_dir.rglob("*"), reverse=True):
                    if item.is_file():
                        item.unlink()
                        changed.append(item)
                    elif item.is_dir():
                        try:
                            item.rmdir()
                        except OSError:
                            pass
                try:
                    ex_dir.rmdir()
                except OSError:
                    pass

    return changed


def _sync_file(src: Path, dst: Path) -> list[Path]:
    if not dst.exists() or not filecmp.cmp(src, dst, shallow=False):
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return [dst]
    return []


def _compute_changes() -> list[Path]:
    changed: list[Path] = []
    for src, dst, excludes in SYNC_PAIRS:
        if src.is_dir():
            changed.extend(_sync_dir(src, dst, excludes))
        else:
            changed.extend(_sync_file(src, dst))
    return changed


def _check_changes() -> list[Path]:
    """Return list of dst paths that differ from src, without modifying anything."""
    out: list[Path] = []
    for src, dst, excludes in SYNC_PAIRS:
        if src.is_dir():
            for src_item in sorted(src.rglob("*")):
                if _skip(src_item) or src_item.is_dir():
                    continue
                rel = src_item.relative_to(src)
                if _excluded(rel, excludes):
                    continue
                dst_item = dst / rel
                if not dst_item.exists() or not filecmp.cmp(src_item, dst_item, shallow=False):
                    out.append(dst_item)
            if dst.exists():
                for dst_item in sorted(dst.rglob("*")):
                    if _skip(dst_item) or dst_item.is_dir():
                        continue
                    rel = dst_item.relative_to(dst)
                    if _excluded(rel, excludes):
                        # An excluded path lingering in dst means the payload
                        # is stale — flag it so CI can fail until it is pruned.
                        out.append(dst_item)
                        continue
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
