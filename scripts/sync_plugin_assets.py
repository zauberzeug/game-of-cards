#!/usr/bin/env python3
"""Sync plugin payloads + dogfood self-host copies from goc/ and goc/templates/.

Run by pre-commit before every commit. When goc/ or goc/templates/ changes,
this script regenerates:

  - the Claude Code plugin payload under claude-plugin/
  - the Codex plugin payload under codex-plugin/
  - the OpenClaw plugin payload's bundled engine under openclaw-plugin/goc/
  - this repo's own dogfood self-host copy under .claude/skills/ + .claude/hooks/
    and .codex/skills/

and stages the changes so they're included in the same commit — no manual
edit-both-copies required. The dogfood targets are this repo's consumer-copy
of what `goc install` writes into a fresh repo; keeping them auto-synced
means editing only `goc/templates/skills/foo/SKILL.md` is enough — the
.claude/ mirror picks it up on commit, and CI's `--check` mode catches any
drift before it lands.

Usage:
    python scripts/sync_plugin_assets.py          # sync + git-add (pre-commit mode)
    python scripts/sync_plugin_assets.py --check  # dry-run, exit 1 if out of sync (CI mode)
"""

from __future__ import annotations

import argparse
import filecmp
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from goc.install import (  # noqa: E402
    CODEX_GOC_COMMAND_RESOLVER,
    _frontmatter_value,
    deck_hook_scripts,
    skill_for_agent,
)


SyncPair = tuple[Path, Path, frozenset[str], frozenset[str]]
"""(src, dst, excludes, preserve_files).

excludes: paths (relative to src) that live in src but must NOT be mirrored
to dst — if they're accidentally present in dst, the sync deletes them.
preserve_files: paths (relative to dst) that live only in dst and must NOT
be deleted by the sync — typically files written by `goc install` from a
different template path, or generated state that has no src counterpart.
"""


def _build_sync_pairs() -> list[SyncPair]:
    """Compute (src, dst, excludes, preserve_files) pairs by deriving the hook list from templates/hooks/.

    Plugin-specific files NOT touched by this sync (`claude-plugin/bin/`,
    `claude-plugin/pyproject.toml`, `codex-plugin/.codex-plugin/plugin.json`,
    `codex-plugin/bin/`, `openclaw-plugin/index.ts`, `openclaw-plugin/package.json`,
    `openclaw-plugin/skills/`, etc.) are not in the pair list and stay untouched.
    The hand-maintained `hooks.json` inside `claude-plugin/hooks/` and
    `codex-plugin/hooks/` sits inside a synced directory, so it is protected
    via `preserve_files` instead.

    The flat hook mirrors (`claude-plugin/hooks/`, `codex-plugin/hooks/`,
    `.claude/hooks/`) are directory syncs of `templates/hooks/` — NOT per-file
    pairs enumerated from the current template set — so a renamed or retired
    hook template is pruned from the mirrors and `--check` flags a stale copy.

    The bundled engine in `claude-plugin/goc/` refuses `--local-skills` and
    `--keep-local-skills` (see `_is_plugin_context` in goc/install.py), so it
    never reads `templates/skills/`. That path is excluded from the
    `goc → claude-plugin/goc` deep mirror; hook scripts are NOT excluded so
    the bundled engine can derive its hook list from `templates/hooks/`.

    The OpenClaw plugin reimplements every deck hook in TypeScript inside
    `openclaw-plugin/index.ts`, so its deep mirror also excludes
    `templates/hooks/*.py` (in addition to `templates/skills/`).

    The dogfood self-host targets (`.claude/skills/`, `.claude/hooks/`) use
    the same skill set as the Claude plugin payload, plus a one-off file
    sync for `goc/templates/bootstrap/_goc-bootstrap.sh` →
    `.claude/skills/_goc-bootstrap.sh`. That bootstrap file is preserved
    during the directory sync (`preserve_files`) so the dir-sync doesn't
    delete it before the file-sync re-creates it.
    """
    templates = ROOT / "goc" / "templates"
    hook_names = deck_hook_scripts(templates)

    pairs: list[SyncPair] = []

    # --- Claude plugin payload ---
    # Exclude non-Claude host complements (e.g. `codex-kickoff`,
    # `openclaw-kickoff`) from the Claude plugin's skill set. They live in
    # templates/skills/ as the source of truth, but the Claude plugin must
    # never ship them.
    skills_src = templates / "skills"
    non_claude_skills = frozenset(
        p.name
        for p in skills_src.iterdir()
        if p.is_dir() and not skill_for_agent(p.name, "claude")
    )
    pairs.append(
        (
            templates / "skills",
            ROOT / "claude-plugin" / "skills",
            non_claude_skills,
            frozenset(),
        )
    )
    pairs.append(
        (
            templates / "hooks",
            ROOT / "claude-plugin" / "hooks",
            frozenset(),
            # `hooks.json` is hand-maintained plugin config (event → command
            # mapping) with no src counterpart — the dir-sync must not prune it.
            frozenset({"hooks.json"}),
        )
    )
    pairs.append(
        (
            ROOT / "goc",
            ROOT / "claude-plugin" / "goc",
            frozenset({"templates/skills"}),
            frozenset(),
        )
    )

    # --- Codex plugin payload ---
    # Skills use Codex frontmatter normalization and are synced by the
    # specialized codex-skill tree functions below. Hook scripts and the bundled
    # engine are byte mirrors.
    pairs.append(
        (
            templates / "hooks",
            ROOT / "codex-plugin" / "hooks",
            frozenset(),
            frozenset({"hooks.json"}),
        )
    )
    pairs.append(
        (
            ROOT / "goc",
            ROOT / "codex-plugin" / "goc",
            frozenset({"templates/skills"}),
            frozenset(),
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
            frozenset(),
        )
    )

    # --- Dogfood self-host: this repo's own consumer-copy of `goc install` ---
    # Without this block, .claude/skills/ and .claude/hooks/ drift silently
    # whenever templates change; with it, pre-commit + CI catch the drift on
    # the spot.
    pairs.append(
        (
            templates / "skills",
            ROOT / ".claude" / "skills",
            non_claude_skills,
            # `_goc-bootstrap.sh` is written by `goc install` from
            # `templates/bootstrap/_goc-bootstrap.sh` (a different src path
            # than templates/skills/). Preserve it during the dir sync; a
            # separate single-file sync pair below keeps it current.
            # `tune-cadence/SKILL.md` is a repo-local Claude Code dev skill
            # (wraps scripts/set_cadence.py) with no template source and
            # ships to no consumer — preserve it so the dir sync doesn't
            # delete it as "not in src".
            frozenset({"_goc-bootstrap.sh", "tune-cadence/SKILL.md"}),
        )
    )
    pairs.append(
        (
            templates / "bootstrap" / "_goc-bootstrap.sh",
            ROOT / ".claude" / "skills" / "_goc-bootstrap.sh",
            frozenset(),
            frozenset(),
        )
    )
    pairs.append(
        (
            templates / "hooks",
            ROOT / ".claude" / "hooks",
            frozenset(),
            frozenset(),
        )
    )

    # Codex dogfood skills use the Codex frontmatter transform, so they are
    # synced by the specialized codex-skill tree functions below. The bootstrap
    # still comes from templates/bootstrap/.
    pairs.append(
        (
            templates / "bootstrap" / "_goc-bootstrap.sh",
            ROOT / ".codex" / "skills" / "_goc-bootstrap.sh",
            frozenset(),
            frozenset(),
        )
    )

    return pairs


SYNC_PAIRS: list[SyncPair] = _build_sync_pairs()

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


def _sync_dir(
    src: Path,
    dst: Path,
    excludes: frozenset[str] = frozenset(),
    preserve_files: frozenset[str] = frozenset(),
) -> list[Path]:
    """Copy src → dst, remove dst-only files. Return changed dst paths.

    Subpaths listed in `excludes` (relative to src) are NOT mirrored from
    src to dst, and any such path that exists in dst is actively removed
    (so excluded leftovers can't linger in the payload).

    Subpaths listed in `preserve_files` (relative to dst) are LEFT ALONE
    in dst — neither copied from src (which is expected not to have them)
    nor removed. This is for files that exist in dst by virtue of a
    different source path (e.g. `_goc-bootstrap.sh`, written from
    `templates/bootstrap/`, lives in `.claude/skills/` but isn't part of
    `templates/skills/`).
    """
    changed: list[Path] = []

    # Remove files in dst that no longer exist in src OR are now excluded.
    # `preserve_files` short-circuits both branches.
    if dst.exists():
        for item in sorted(dst.rglob("*")):
            if _skip(item) or item.is_dir():
                continue
            rel = item.relative_to(dst)
            if rel.as_posix() in preserve_files:
                continue
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

    # Prune directories left empty because their source was renamed or removed.
    # Without this, a dst skill dir whose template vanished lingers as an empty
    # orphan: git does not track empty dirs, so the auto-stage commits "cleanly"
    # while the stale dir persists and ships in any wheel/tarball copy of the
    # payload. Walk depth-first (reverse sort) so nested empties collapse
    # bottom-up; rmdir is self-guarding (fails on non-empty), and the src-exists
    # guard preserves dirs that legitimately mirror an empty src dir.
    if dst.exists():
        for item in sorted(dst.rglob("*"), reverse=True):
            if not item.is_dir() or _skip(item):
                continue
            rel = item.relative_to(dst)
            if (src / rel).exists() and not _excluded(rel, excludes):
                continue
            try:
                item.rmdir()
            except OSError:
                pass

    return changed


def _sync_file(src: Path, dst: Path) -> list[Path]:
    if not dst.exists() or not filecmp.cmp(src, dst, shallow=False):
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return [dst]
    return []


def _codex_skill_text(src: Path, *, skill_name: str) -> str:
    text = src.read_text()
    if not text.startswith("---\n"):
        return text
    try:
        _, frontmatter, body = text.split("---", 2)
    except ValueError:
        return text
    name = _frontmatter_value(frontmatter, "name") or skill_name
    description = _frontmatter_value(frontmatter, "description")
    codex_frontmatter = "\n".join(
        (
            "---",
            f"name: {name}",
            f"description: {json.dumps(description, ensure_ascii=False)}",
            "---",
        )
    )
    return codex_frontmatter + CODEX_GOC_COMMAND_RESOLVER + body


def _sync_codex_skill_tree(dst: Path, *, preserve_files: frozenset[str] = frozenset()) -> list[Path]:
    src = ROOT / "goc" / "templates" / "skills"
    eligible = {
        p.name for p in src.iterdir() if p.is_dir() and skill_for_agent(p.name, "codex")
    }
    changed: list[Path] = []
    dst.mkdir(parents=True, exist_ok=True)

    if dst.exists():
        for item in sorted(dst.rglob("*")):
            if _skip(item) or item.is_dir():
                continue
            rel = item.relative_to(dst)
            if rel.as_posix() in preserve_files:
                continue
            if not rel.parts or rel.parts[0] not in eligible or not (src / rel).exists():
                item.unlink()
                changed.append(item)

    for src_item in sorted(src.rglob("*")):
        if _skip(src_item) or src_item.is_dir():
            continue
        rel = src_item.relative_to(src)
        if rel.parts[0] not in eligible:
            continue
        dst_item = dst / rel
        dst_item.parent.mkdir(parents=True, exist_ok=True)
        if src_item.name == "SKILL.md":
            expected = _codex_skill_text(src_item, skill_name=rel.parts[0])
            if not dst_item.exists() or dst_item.read_text() != expected:
                dst_item.write_text(expected)
                changed.append(dst_item)
        else:
            # Non-SKILL.md siblings copy byte-for-byte (matching `goc install`,
            # the OpenClaw porter, and the Claude dir-sync) so a CRLF or
            # otherwise text-round-trip-sensitive asset is not LF-normalized.
            if not dst_item.exists() or dst_item.read_bytes() != src_item.read_bytes():
                shutil.copy2(src_item, dst_item)
                changed.append(dst_item)

    # Prune empty orphan dirs (a skill dir whose source was removed or made
    # ineligible). Same rationale as `_sync_dir`: git masks empty dirs so they
    # rot silently in the payload otherwise.
    if dst.exists():
        for item in sorted(dst.rglob("*"), reverse=True):
            if not item.is_dir() or _skip(item):
                continue
            rel = item.relative_to(dst)
            if rel.parts and rel.parts[0] in eligible and (src / rel).exists():
                continue
            try:
                item.rmdir()
            except OSError:
                pass

    return changed


def _check_codex_skill_tree(dst: Path, *, preserve_files: frozenset[str] = frozenset()) -> list[Path]:
    src = ROOT / "goc" / "templates" / "skills"
    eligible = {
        p.name for p in src.iterdir() if p.is_dir() and skill_for_agent(p.name, "codex")
    }
    out: list[Path] = []

    for src_item in sorted(src.rglob("*")):
        if _skip(src_item) or src_item.is_dir():
            continue
        rel = src_item.relative_to(src)
        if rel.parts[0] not in eligible:
            continue
        dst_item = dst / rel
        if src_item.name == "SKILL.md":
            expected = _codex_skill_text(src_item, skill_name=rel.parts[0])
            if not dst_item.exists() or dst_item.read_text() != expected:
                out.append(dst_item)
        else:
            # Siblings compared by bytes so install-vs-mirror newline skew is
            # CI-detectable (matching the byte-exact sync above).
            if not dst_item.exists() or dst_item.read_bytes() != src_item.read_bytes():
                out.append(dst_item)

    if dst.exists():
        for dst_item in sorted(dst.rglob("*")):
            if _skip(dst_item):
                continue
            rel = dst_item.relative_to(dst)
            if dst_item.is_dir():
                is_orphan = (
                    not rel.parts
                    or rel.parts[0] not in eligible
                    or not (src / rel).exists()
                )
                if is_orphan and not any(dst_item.iterdir()):
                    out.append(dst_item)
                continue
            if rel.as_posix() in preserve_files:
                continue
            if not rel.parts or rel.parts[0] not in eligible or not (src / rel).exists():
                out.append(dst_item)

    return out


def _compute_changes() -> list[Path]:
    changed: list[Path] = []
    for src, dst, excludes, preserve_files in SYNC_PAIRS:
        if src.is_dir():
            changed.extend(_sync_dir(src, dst, excludes, preserve_files))
        else:
            changed.extend(_sync_file(src, dst))
    changed.extend(
        _sync_codex_skill_tree(
            ROOT / "codex-plugin" / "skills",
            preserve_files=frozenset({"_goc-bootstrap.sh"}),
        )
    )
    changed.extend(_sync_file(
        ROOT / "goc" / "templates" / "bootstrap" / "_goc-bootstrap.sh",
        ROOT / "codex-plugin" / "skills" / "_goc-bootstrap.sh",
    ))
    changed.extend(
        _sync_codex_skill_tree(
            ROOT / ".codex" / "skills",
            preserve_files=frozenset({"_goc-bootstrap.sh"}),
        )
    )
    return changed


def _check_changes() -> list[Path]:
    """Return list of dst paths that differ from src, without modifying anything."""
    out: list[Path] = []
    for src, dst, excludes, preserve_files in SYNC_PAIRS:
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
                    if _skip(dst_item):
                        continue
                    rel = dst_item.relative_to(dst)
                    if dst_item.is_dir():
                        # An empty dir with no src counterpart (or an excluded
                        # one) is an orphan the sync should have pruned. Flag it
                        # so CI fails — rglob skips dirs by default, which is the
                        # blind spot that let empty orphans ship silently.
                        is_orphan = _excluded(rel, excludes) or not (src / rel).exists()
                        if is_orphan and not any(dst_item.iterdir()):
                            out.append(dst_item)
                        continue
                    if rel.as_posix() in preserve_files:
                        continue
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
    out.extend(_check_codex_skill_tree(
        ROOT / "codex-plugin" / "skills",
        preserve_files=frozenset({"_goc-bootstrap.sh"}),
    ))
    codex_bootstrap_src = ROOT / "goc" / "templates" / "bootstrap" / "_goc-bootstrap.sh"
    codex_bootstrap_dst = ROOT / "codex-plugin" / "skills" / "_goc-bootstrap.sh"
    if not codex_bootstrap_dst.exists() or not filecmp.cmp(
        codex_bootstrap_src,
        codex_bootstrap_dst,
        shallow=False,
    ):
        out.append(ROOT / "codex-plugin" / "skills" / "_goc-bootstrap.sh")
    out.extend(
        _check_codex_skill_tree(
            ROOT / ".codex" / "skills",
            preserve_files=frozenset({"_goc-bootstrap.sh"}),
        )
    )
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
            print("ERROR: sync targets are out of sync with goc/ + goc/templates/:")
            for p in diffs:
                print(f"  {p.relative_to(ROOT)}")
            print("Fix: run `python scripts/sync_plugin_assets.py` and commit the result.")
            return 1
        print("OK — plugin payloads + dogfood self-host copies match goc/ and goc/templates/ byte-for-byte.")
        return 0

    changed = _compute_changes()
    if changed:
        rel = [str(p.relative_to(ROOT)) for p in changed]
        subprocess.run(["git", "add", "--"] + rel, check=True, cwd=ROOT)
        print(f"sync-plugin-assets: synced {len(changed)} file(s), staged for commit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
