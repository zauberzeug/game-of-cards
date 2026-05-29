"""SessionStart hook — brief GoC session primer.

Runs when an agent session starts. If there are active cards in the deck,
prints a one-line reminder so the model can pick up where it left off. Silent
when no cards are in-flight.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

_FRONTMATTER_RE = re.compile(r"^---\n(.*?\n)---\n", re.DOTALL)


def _card_status(readme: Path) -> str | None:
    """Return the frontmatter `status` value, or None if unreadable."""
    try:
        text = readme.read_text(encoding="utf-8")
    except OSError:
        return None
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    for line in m.group(1).splitlines():
        if line.startswith("status:"):
            return line.split(":", 1)[1].strip()
    return None


def _card_human_gate(readme: Path) -> str:
    """Return the frontmatter `human_gate` value, defaulting to 'none'."""
    try:
        text = readme.read_text(encoding="utf-8")
    except OSError:
        return "none"
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return "none"
    for line in m.group(1).splitlines():
        if line.startswith("human_gate:"):
            val = line.split(":", 1)[1].strip()
            return val or "none"
    return "none"


def _project_dir_from_hook_input() -> str:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        data = {}
    if isinstance(data, dict) and data.get("cwd"):
        return str(data["cwd"])
    return (
        os.environ.get("CLAUDE_PROJECT_DIR")
        or os.environ.get("CODEX_PROJECT_DIR")
        or "."
    )


def main() -> int:
    project_dir = _project_dir_from_hook_input()
    deck_dir = Path(project_dir) / ".game-of-cards" / "deck"
    if not deck_dir.is_dir():
        legacy = Path(project_dir) / "deck"
        if legacy.is_dir():
            deck_dir = legacy
        else:
            return 0

    resumable = []
    parked = []
    for card_dir in sorted(deck_dir.iterdir()):
        if not card_dir.is_dir():
            continue
        readme = card_dir / "README.md"
        if not readme.is_file():
            continue
        if _card_status(readme) != "active":
            continue
        if _card_human_gate(readme) == "none":
            resumable.append(card_dir.name)
        else:
            parked.append(card_dir.name)

    if resumable:
        cards_str = ", ".join(resumable)
        print(f"[GoC] Active card(s): {cards_str} — resume or close before starting new work.")
    if parked:
        cards_str = ", ".join(parked)
        print(f"[GoC] Parked active card(s) (awaiting human): {cards_str} — agent cannot resume.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
