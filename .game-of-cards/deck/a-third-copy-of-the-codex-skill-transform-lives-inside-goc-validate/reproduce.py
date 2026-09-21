#!/usr/bin/env python3
"""Reproduce: `goc validate`'s Codex skill-mirror check is weaker than the sync script's.

`validate_plugin_mirror_parity` (goc/engine.py) carries a third copy of the
Codex SKILL.md transform and its surrounding mirror walk. That copy missed two
hardening fixes the repo-local `scripts/sync_plugin_assets.py --check` carries:

  1. non-`SKILL.md` siblings are compared with `read_text()`, which applies
     universal-newline translation — so a CRLF sibling in the mirror reads
     identical to its LF source and the drift is invisible;
  2. the orphan walk skips every directory, so an empty mirror subdirectory
     with no source counterpart is never reported.

`goc validate` is the guard that SHIPS; the sync script is repo-local. So the
weaker of the two is the one consuming repos get.

This script builds a throwaway REPO_ROOT-shaped tree (the live working tree is
never touched), plants exactly those two mutations, and runs BOTH guards over
it. Exits 0 when the two agree (bug FIXED), 1 when the engine reports fewer
`codex-plugin/skills` findings than the sync check (bug PRESENT).
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import goc.engine as eng  # noqa: E402
from goc.install import _codex_skill_text  # noqa: E402

SKILL = "foo-skill"
SIBLING = "reference.md"
ORPHAN_DIR = "zzz-orphan-dir"

SKILL_MD = '---\nname: foo-skill\ndescription: "a test skill"\n---\n\n# Foo\n\nbody\n'
SIBLING_TEXT = "alpha\nbeta\n"
HOOK = "# hook\n"
BOOTSTRAP = "#!/bin/sh\nexec goc \"$@\"\n"


def _load_sync():
    """Import scripts/sync_plugin_assets.py without putting scripts/ on sys.path."""
    spec = importlib.util.spec_from_file_location(
        "_goc_sync_assets", ROOT / "scripts" / "sync_plugin_assets.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _build_tree(cwd: Path) -> None:
    """A minimal REPO_ROOT shape whose codex payload is otherwise in sync."""
    src = cwd / "goc" / "templates" / "skills" / SKILL
    src.mkdir(parents=True)
    (src / "SKILL.md").write_text(SKILL_MD)
    (src / SIBLING).write_text(SIBLING_TEXT)

    hooks = cwd / "goc" / "templates" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "deck_prompt_router.py").write_text(HOOK)

    bootstrap = cwd / "goc" / "templates" / "bootstrap"
    bootstrap.mkdir(parents=True)
    (bootstrap / "_goc-bootstrap.sh").write_text(BOOTSTRAP)

    (cwd / "goc" / "__init__.py").write_text("# goc package\n")

    mirror = cwd / "codex-plugin" / "skills" / SKILL
    mirror.mkdir(parents=True)
    # The mirror's SKILL.md is what the transform would produce, so the only
    # findings in play are the two this card is about.
    (mirror / "SKILL.md").write_text(
        _codex_skill_text(src / "SKILL.md", skill_name=SKILL) or SKILL_MD
    )
    (mirror / SIBLING).write_text(SIBLING_TEXT)
    (cwd / "codex-plugin" / "skills" / "_goc-bootstrap.sh").write_text(BOOTSTRAP)

    codex_hooks = cwd / "codex-plugin" / "hooks"
    codex_hooks.mkdir(parents=True)
    (codex_hooks / "deck_prompt_router.py").write_text(HOOK)

    deep = cwd / "codex-plugin" / "goc"
    (deep / "templates" / "hooks").mkdir(parents=True)
    (deep / "templates" / "hooks" / "deck_prompt_router.py").write_text(HOOK)
    (deep / "templates" / "bootstrap").mkdir(parents=True)
    (deep / "templates" / "bootstrap" / "_goc-bootstrap.sh").write_text(BOOTSTRAP)
    (deep / "__init__.py").write_text("# goc package\n")


def _mutate(cwd: Path) -> None:
    """Plant the two drifts the sync check catches."""
    # 1. CRLF sibling: byte-different from its LF source, text-identical.
    sib = cwd / "codex-plugin" / "skills" / SKILL / SIBLING
    sib.write_bytes(SIBLING_TEXT.replace("\n", "\r\n").encode())
    assert sib.read_text() == SIBLING_TEXT, "CRLF sibling must still read text-identical"
    # 2. Empty orphan subdirectory with no source counterpart.
    (cwd / "codex-plugin" / "skills" / ORPHAN_DIR).mkdir()


def _engine_findings(cwd: Path) -> list[str]:
    old = eng.REPO_ROOT
    try:
        eng.REPO_ROOT = cwd
        errors = eng.validate_plugin_mirror_parity()
    finally:
        eng.REPO_ROOT = old
    return [e for e in errors if "codex-plugin/skills" in e]


def _sync_findings(cwd: Path) -> list[str]:
    sync = _load_sync()
    old = sync.ROOT
    try:
        sync.ROOT = cwd
        paths = sync._check_codex_skill_tree(
            cwd / "codex-plugin" / "skills",
            preserve_files=frozenset({"_goc-bootstrap.sh"}),
        )
    finally:
        sync.ROOT = old
    return [str(p.relative_to(cwd)) for p in paths]


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        _build_tree(cwd)

        clean_engine = _engine_findings(cwd)
        clean_sync = _sync_findings(cwd)
        if clean_engine or clean_sync:
            print("UNEXPECTED — the unmutated tree is not in sync:")
            print(f"  engine: {clean_engine}")
            print(f"  sync:   {clean_sync}")
            return 1

        _mutate(cwd)
        engine = _engine_findings(cwd)
        sync = _sync_findings(cwd)

    blob = " ".join(engine)
    misses = []
    if not any(SIBLING in p for p in sync):
        print(f"UNEXPECTED — sync check did not flag the CRLF sibling: {sync}")
        return 1
    if not any(ORPHAN_DIR in p for p in sync):
        print(f"UNEXPECTED — sync check did not flag the empty orphan dir: {sync}")
        return 1
    if SIBLING not in blob:
        misses.append(f"CRLF sibling {SKILL}/{SIBLING} (sync flags it, engine does not)")
    if ORPHAN_DIR not in blob:
        misses.append(f"empty orphan dir {ORPHAN_DIR}/ (sync flags it, engine does not)")

    print("sync check  (scripts/sync_plugin_assets.py):")
    for p in sync:
        print(f"  - {p}")
    print("goc validate (engine.validate_plugin_mirror_parity):")
    for e in engine or ["<no codex-plugin/skills findings>"]:
        print(f"  - {e}")

    if misses:
        print("\nDEFECT — the shipped guard is weaker than the repo-local one:")
        for m in misses:
            print(f"  - {m}")
        return 1

    print("\nFIXED — both guards report the CRLF sibling and the empty orphan dir.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
