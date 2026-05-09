"""SessionStart hook — brief GoC session primer.

Runs when Claude Code starts a new session. If there are active cards in the
deck, prints a one-line reminder so the model can pick up where it left off.
Silent when no cards are in-flight.
"""

from __future__ import annotations

import os
import re
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


def main() -> int:
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    deck_dir = Path(project_dir) / ".game-of-cards" / "deck"
    if not deck_dir.is_dir():
        legacy = Path(project_dir) / "deck"
        if legacy.is_dir():
            deck_dir = legacy
        else:
            return 0

    active_cards = []
    for card_dir in sorted(deck_dir.iterdir()):
        if not card_dir.is_dir():
            continue
        readme = card_dir / "README.md"
        if not readme.is_file():
            continue
        if _card_status(readme) == "active":
            active_cards.append(card_dir.name)

    if active_cards:
        cards_str = ", ".join(active_cards)
        print(f"[GoC] Active card(s): {cards_str} — resume or close before starting new work.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
