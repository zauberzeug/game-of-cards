"""Prove `goc upgrade` silently relocates a gitignored CLAUDE.local.md
briefing home into checked-in AGENTS.md on a fresh clone.

The briefing home chosen at install time is persisted nowhere;
`_resolve_upgrade_briefing_target` re-detects it by grepping on-disk
files for the GoC marker block (`_detect_briefing_targets_on_disk`).
A repo installed with `--briefing-target CLAUDE.local.md` — the home
GoC's own help text describes as gitignored — leaves only the pointer
evidence `@CLAUDE.local.md` inside the checked-in CLAUDE.md. On a fresh
clone the gitignored file is absent, the resolver finds zero marker
blocks and falls back to AGENTS.md, and `_sync_claude_import` then
rewrites CLAUDE.md's import to `@AGENTS.md` — reversing the user's
explicit keep-it-out-of-the-repo configuration without a prompt and
producing a commit-ready diff that publishes the briefing.

Exits non-zero while the silent relocation fires; exits zero once the
resolver honors the surviving `@CLAUDE.local.md` evidence (or refuses
to proceed without a prompt).
"""

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
sys.path.insert(0, str(ROOT))

from goc.install import (  # noqa: E402
    _resolve_upgrade_briefing_target,
    _sync_claude_import,
)

with tempfile.TemporaryDirectory() as td:
    clone = Path(td)
    # Fresh clone of a repo installed with --briefing-target CLAUDE.local.md:
    # the gitignored home is absent; the checked-in pointer survives.
    (clone / "CLAUDE.md").write_text("@CLAUDE.local.md\n")

    resolved = _resolve_upgrade_briefing_target(
        clone, explicit_target=None, dry_run=False
    )
    _sync_claude_import(clone, resolved)
    claude_md = (clone / "CLAUDE.md").read_text().strip()

print(f"resolved briefing home: {resolved}")
print(f"CLAUDE.md after upgrade sync: {claude_md!r}")

if resolved != "CLAUDE.local.md" or claude_md != "@CLAUDE.local.md":
    print(
        "DEFECT: upgrade on a fresh clone relocates the gitignored "
        "CLAUDE.local.md briefing into checked-in AGENTS.md and retargets "
        "the CLAUDE.md import"
    )
    sys.exit(1)

print("OK: resolver honors the surviving @CLAUDE.local.md pointer")
