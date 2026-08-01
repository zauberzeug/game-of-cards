#!/usr/bin/env python3
"""Show that site/llms.txt gates a live install channel behind a pending publish.

`site/llms.txt` is the file LLMs ingest (llmstxt.org convention) to learn how
to recommend Game of Cards. Its `## Install (OpenClaw)` section still says the
ClawHub install works only "Once the plugin is published" and that until then
the reader should build from source — while README.md, ABOUT.md, goc.md and
site/index.html all print the same `openclaw skills install game-of-cards`
command with no such caveat.

The check is offline and deterministic: it compares the repo's own surfaces
against each other. Live-registry confirmation (ClawHub serves the package at
the current release) is recorded in the card README rather than asserted here,
so the exit code does not depend on network access.

Exits 1 while llms.txt still gates the channel; exits 0 once it presents the
ClawHub install the way its four sibling surfaces already do.
"""

from __future__ import annotations

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

LLMS_TXT = Path("site/llms.txt")

# Phrases that assert the OpenClaw channel is not installable yet. Each is a
# claim about publish state, not a style preference — that is what makes the
# check narrow enough to stay green after the fix.
PENDING_PUBLISH_MARKERS = (
    "Once the plugin is published",
    "Until publish lands",
)

# Surfaces that already present the ClawHub install as live and unconditional.
SIBLING_SURFACES = (
    Path("README.md"),
    Path("ABOUT.md"),
    Path("goc.md"),
    Path("site/index.html"),
)

INSTALL_COMMAND = "openclaw skills install game-of-cards"


def main() -> int:
    llms = (ROOT / LLMS_TXT).read_text(encoding="utf-8")
    stale = [m for m in PENDING_PUBLISH_MARKERS if m in llms]

    live = []
    for rel in SIBLING_SURFACES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        if INSTALL_COMMAND in text and not any(
            m in text for m in PENDING_PUBLISH_MARKERS
        ):
            live.append(rel)

    if not stale:
        print(f"[OK] {LLMS_TXT} carries no pending-publish caveat")
        print(f"     {len(live)}/{len(SIBLING_SURFACES)} sibling surfaces agree "
              f"the ClawHub install is live")
        return 0

    print(f"[FAIL] {LLMS_TXT} gates a live install channel behind a pending publish")
    for marker in stale:
        for lineno, line in enumerate(llms.splitlines(), start=1):
            if marker in line:
                print(f"       {LLMS_TXT}:{lineno}: {line.strip()}")
    print(f"       contradicted by {len(live)} surface(s) that print "
          f"{INSTALL_COMMAND!r} with no caveat:")
    for rel in live:
        print(f"         - {rel}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
