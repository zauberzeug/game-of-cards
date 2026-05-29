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
from datetime import date, datetime, timezone
from pathlib import Path

_FRONTMATTER_RE = re.compile(r"^---\n(.*?\n)---\n", re.DOTALL)
_IMPEDED_WAITING_ON = frozenset({"external", "resource", "deferred"})
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ISO_DATETIME_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


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
            return line.split(":", 1)[1].strip().strip('"').strip("'")
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
            val = line.split(":", 1)[1].strip().strip('"').strip("'")
            return val or "none"
    return "none"


def _card_waiting_on(readme: Path) -> str | None:
    """Return the frontmatter `waiting_on` value, or None if absent/blank."""
    try:
        text = readme.read_text(encoding="utf-8")
    except OSError:
        return None
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    for line in m.group(1).splitlines():
        if line.startswith("waiting_on:"):
            val = line.split(":", 1)[1].strip().strip('"').strip("'")
            return val or None
    return None


def _card_waiting_until(readme: Path) -> str | None:
    """Return the frontmatter `waiting_until` raw value, or None if absent."""
    try:
        text = readme.read_text(encoding="utf-8")
    except OSError:
        return None
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    for line in m.group(1).splitlines():
        if line.startswith("waiting_until:"):
            val = line.split(":", 1)[1].strip().strip('"').strip("'")
            return val or None
    return None


def _parse_waiting_until(value: str) -> datetime | None:
    """Parse `waiting_until` into a UTC instant, or None if unparseable.

    Mirrors `goc.engine._waiting_until_instant`: a bare date
    `YYYY-MM-DD` becomes midnight UTC of that day, so date-only
    deferrals clear at the start of their named day; a datetime
    `YYYY-MM-DDTHH:MM:SSZ` is honored at full precision so a same-day
    future timestamp does not collapse to "today" and clear early. The
    hook re-implements the engine helper (rather than importing it) so
    it has no package dependency and runs from any working tree shape.
    """
    if _ISO_DATETIME_UTC_RE.match(value):
        try:
            return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            return None
    if _ISO_DATE_RE.match(value):
        try:
            d = date.fromisoformat(value)
        except ValueError:
            return None
        return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return None


def _is_impeded(readme: Path) -> bool:
    """Card carries an active impediment overlay.

    Mirrors `goc.engine.waiting_impedes` across the four-cell
    `waiting_on` × `waiting_until` matrix at full UTC timestamp
    precision (matching `engine._waiting_until_instant`):

    - `waiting_on` set, no `waiting_until` → impeded (open-ended wait).
    - `waiting_on` set, future `waiting_until` → impeded.
    - `waiting_on` set, elapsed `waiting_until` → NOT impeded
      (elapsed wait resurfaces the card; engine contract).
    - no `waiting_on`, future `waiting_until` → impeded (deferred wait).
    - no `waiting_on`, elapsed `waiting_until` → NOT impeded.

    Date-level coarseness does NOT suffice for the datetime-shape
    values the engine accepts since the `_waiting_until_instant`
    extension: a same-day future `YYYY-MM-DDTHH:MM:SSZ` is impeded by
    the engine, and a date-truncated comparison would round it to
    today and clear the wait early.
    """
    reason = _card_waiting_on(readme)
    until = _card_waiting_until(readme)
    until_dt = _parse_waiting_until(until) if until else None
    until_future = until_dt is not None and until_dt > datetime.now(tz=timezone.utc)
    if reason in _IMPEDED_WAITING_ON:
        # Elapsed waiting_until resurfaces the card even with a reason set.
        if until_dt is not None and not until_future:
            return False
        return True
    return until_future


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
    parked_gate = []
    impeded = []
    for card_dir in sorted(deck_dir.iterdir()):
        if not card_dir.is_dir():
            continue
        readme = card_dir / "README.md"
        if not readme.is_file():
            continue
        if _card_status(readme) != "active":
            continue
        gate = _card_human_gate(readme)
        if _is_impeded(readme):
            impeded.append(card_dir.name)
        elif gate != "none":
            parked_gate.append(card_dir.name)
        else:
            resumable.append(card_dir.name)

    if resumable:
        cards_str = ", ".join(resumable)
        print(f"[GoC] Active card(s): {cards_str} — resume or close before starting new work.")
    if parked_gate:
        cards_str = ", ".join(parked_gate)
        print(f"[GoC] Parked active card(s) (awaiting human): {cards_str} — agent cannot resume.")
    if impeded:
        cards_str = ", ".join(impeded)
        print(f"[GoC] Impeded active card(s) (waiting_on): {cards_str} — agent cannot resume.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
