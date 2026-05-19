#!/usr/bin/env python3
"""Rewrite all static version literals to a release version.

Called by `.github/workflows/release.yml` at build time. The git tag is the
single source of truth for the release version; this script propagates that
value into every static literal that ships:

  - goc/__init__.py (`__version__`)
  - openclaw-plugin/package.json (`version`)
  - openclaw-plugin/package-lock.json (top-level `version` + `packages[""].version`)
  - claude-plugin/.claude-plugin/plugin.json (`version`)
  - codex-plugin/.codex-plugin/plugin.json (`version`)
  - .claude-plugin/marketplace.json (`metadata.version`)
  - .game-of-cards/deck/.goc-version (full-file dogfood sentinel)
  - AGENTS.md (`<!-- BEGIN GOC v… -->` dogfood marker)

Plugin-payload mirrors (`claude-plugin/goc/__init__.py`,
`codex-plugin/goc/__init__.py`, `openclaw-plugin/goc/__init__.py`) are NOT
touched here — they are byte-mirrored from `goc/__init__.py` by
`scripts/sync_plugin_assets.py`, which the workflow runs immediately after this
script.

The two dogfood surfaces (`.goc-version` and the `AGENTS.md` marker) are this
repo's own consumer-copy of what `goc install` writes into a fresh repo. They
are checked by `tests/test_version_surfaces.py` against the static
`__version__` literal, so they must move in lockstep with the publish-channel
manifests.

Usage:
    python3 scripts/release_rewrite_versions.py X.Y.Z

The rewrite is surgical: each match is anchored on enough surrounding context
that bumping a real release version cannot collide with unrelated `"version"`
fields (e.g. transitive-dep entries inside package-lock.json). The script
fails loudly on any expected-vs-actual mismatch — versions are too important
to silently no-op.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _replace(path: Path, pattern: str, replacement: str, expected: int) -> None:
    text = path.read_text()
    new_text, count = re.subn(pattern, replacement, text, flags=re.MULTILINE)
    if count != expected:
        rel = path.relative_to(ROOT)
        sys.exit(
            f"ERROR: {rel}: expected {expected} replacement(s), made {count}. "
            f"Pattern: {pattern!r}"
        )
    path.write_text(new_text)


def rewrite_all(version: str) -> None:
    # goc/__init__.py — `__version__ = "..."` Python literal.
    _replace(
        ROOT / "goc" / "__init__.py",
        r'^__version__\s*=\s*"[^"]+"$',
        f'__version__ = "{version}"',
        expected=1,
    )

    # openclaw-plugin/package.json — top-level `"version": "..."`.
    _replace(
        ROOT / "openclaw-plugin" / "package.json",
        r'^(\s+"version":\s*")[^"]+(")',
        rf"\g<1>{version}\g<2>",
        expected=1,
    )

    # openclaw-plugin/package-lock.json — both `"version"` keys for OUR package.
    # The lockfile has many `"version"` keys (one per dependency); we anchor on
    # the preceding `"name": "game-of-cards"` so we only touch our two entries.
    _replace(
        ROOT / "openclaw-plugin" / "package-lock.json",
        r'("name":\s*"game-of-cards",\s*\n\s+"version":\s*")[^"]+(")',
        rf"\g<1>{version}\g<2>",
        expected=2,
    )

    # claude-plugin/.claude-plugin/plugin.json — top-level `"version": "..."`.
    _replace(
        ROOT / "claude-plugin" / ".claude-plugin" / "plugin.json",
        r'^(\s+"version":\s*")[^"]+(")',
        rf"\g<1>{version}\g<2>",
        expected=1,
    )

    # codex-plugin/.codex-plugin/plugin.json — top-level `"version": "..."`.
    _replace(
        ROOT / "codex-plugin" / ".codex-plugin" / "plugin.json",
        r'^(\s+"version":\s*")[^"]+(")',
        rf"\g<1>{version}\g<2>",
        expected=1,
    )

    # .claude-plugin/marketplace.json — single `metadata.version`.
    _replace(
        ROOT / ".claude-plugin" / "marketplace.json",
        r'^(\s+"version":\s*")[^"]+(")',
        rf"\g<1>{version}\g<2>",
        expected=1,
    )

    # .game-of-cards/deck/.goc-version — dogfood sentinel, just the bare
    # version literal followed by a trailing newline. Full-file write.
    (ROOT / ".game-of-cards" / "deck" / ".goc-version").write_text(f"{version}\n")

    # AGENTS.md — dogfood marker block opener `<!-- BEGIN GOC v… -->`.
    # CLAUDE.md uses the IMPORT-marker form (no version literal), so only
    # AGENTS.md needs rewriting here. `goc install` writes both.
    #
    # Pattern anchors on both line-start (the marker is always at column 0
    # because `_append_marker_block` writes it as a block opener) AND a real
    # semver triple, so prose mentions of the marker syntax — e.g. the
    # placeholder `<!-- BEGIN GOC vX.Y.Z -->` inside backticks in the
    # docstring above — are not rewritten.
    _replace(
        ROOT / "AGENTS.md",
        r"^<!-- BEGIN GOC v\d+\.\d+\.\d+ -->$",
        f"<!-- BEGIN GOC v{version} -->",
        expected=1,
    )


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: release_rewrite_versions.py X.Y.Z", file=sys.stderr)
        return 2
    rewrite_all(argv[1])
    print(f"rewrote version literals to {argv[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
