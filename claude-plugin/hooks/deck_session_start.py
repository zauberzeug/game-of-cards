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
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ISO_DATETIME_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
# Mirrors `goc._vendor.yaml_lite._NULL_SET`: explicit YAML null literals that
# resolve to None, so `waiting_on: null` / `~` reads as absent, not a reason.
_NULL_SET = frozenset(("null", "Null", "NULL", "~"))
# Mirrors `goc._vendor.yaml_lite._TRUE_SET` / `_FALSE_SET` / `_INT_RE`: tokens
# the yaml-lite parser coerces away from `str` (to bool / int). The engine's
# `Card.waiting_on` drops a non-`str` value via `isinstance(v, str)`, so the
# `waiting_on` reader must resolve these coerced tokens to None too — see
# `_card_waiting_on`.
_TRUE_SET = frozenset(("true", "True", "TRUE", "yes", "Yes", "YES"))
_FALSE_SET = frozenset(("false", "False", "FALSE", "no", "No", "NO"))
_INT_RE = re.compile(r"^-?\d+$")


def _comment_free_tail(line: str) -> str:
    """Return the inline-comment-free, whitespace-trimmed tail of a
    `key: value` line, with surrounding quotes **preserved**.

    Mirrors the YAML 1.1/1.2 rule for inline comments as the engine's
    vendored parser implements it (`goc._vendor.yaml_lite._strip_comment`):
    a `#` terminates the value only when preceded by whitespace AND it sits
    **outside** a quoted scalar. So `status: active # note` yields
    `'active'`, `status: foo#bar` yields `'foo#bar'` (no preceding space),
    and `status: "done # x"` yields `'"done # x"'` (the `#` is inside the
    quotes, so it is content). The quote tracking only engages for a
    genuinely quoted scalar — one whose value starts with a quote — so a
    lone apostrophe in a bare value (`5 o'clock`) stays ordinary content.
    Keeping the quotes lets callers distinguish a quoted scalar (which the
    yaml-lite parser keeps as a live `str`) from an unquoted token (subject
    to null/bool/int coercion) — the distinction `_card_waiting_on` /
    `_scalar_or_none` need to mirror the engine.
    """
    tail = line.split(":", 1)[1].strip()
    if tail.startswith("#"):
        return ""
    quoted = tail[:1] in ('"', "'")
    in_q: str | None = None
    escaped = False
    for i, c in enumerate(tail):
        if escaped:
            escaped = False
        elif in_q:
            if c == "\\" and in_q == '"':
                escaped = True  # double-quoted YAML escapes the next char
            elif c == in_q:
                in_q = None
        elif quoted and c in ('"', "'"):
            in_q = c
        elif c == "#" and i > 0 and tail[i - 1] in (" ", "\t"):
            return tail[:i].rstrip()
    return tail


def _frontmatter_tail(line: str) -> str:
    """Return the comment-free, quote-stripped tail of a `key: value` line.

    Quote-stripping wrapper over `_comment_free_tail`; the hook
    re-implements YAML parsing for four enum/date fields so it has no
    package dependency, and routing all four readers through this helper
    keeps their treatment of authored inline comments aligned.
    """
    return _comment_free_tail(line).strip('"').strip("'")


def _scalar_or_none(line: str) -> str | None:
    """Tail of a frontmatter scalar, or None for blank / explicit YAML null.

    Mirrors `yaml_lite._NULL_SET` so the hook resolves an *unquoted*
    `key: null`, `~`, `Null`, `NULL` to absent — matching how the engine
    parses the same line. The null coercion is quote-aware: yaml-lite only
    coerces *bare* null literals, so a quoted `key: "null"` stays the live
    string `"null"` (which the engine keeps), and resolving it to absent
    here would diverge from the engine. Without the bare-token guard, the
    raw token (`null`) would survive as a truthy string and `_is_impeded`
    would mistake an absent overlay for a live one.
    """
    raw = _comment_free_tail(line)
    quoted = raw[:1] in ('"', "'")
    value = raw.strip('"').strip("'") if quoted else raw
    if not value:
        return None
    if not quoted and value in _NULL_SET:
        return None
    return value


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
            return _frontmatter_tail(line)
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
            return _frontmatter_tail(line) or "none"
    return "none"


def _card_waiting_on(readme: Path) -> str | None:
    """Return the frontmatter `waiting_on` value, or None if absent/blank.

    Scoped narrowing beyond `_scalar_or_none`: the engine's `Card.waiting_on`
    drops any value the yaml-lite parser would coerce away from `str` via
    `isinstance(v, str)`, so an *unquoted* token in `_NULL_SET` / `_TRUE_SET`
    / `_FALSE_SET` (coerced to None/bool) or matching `_INT_RE` (coerced to
    int) reads as None here too. The coercion is quote-aware: a *quoted*
    `"true"` / `"42"` / `"null"` is parsed as a live `str` the engine keeps,
    so it stays a reason. Only the `waiting_on` reader applies the bool/int
    narrowing — the engine's `waiting_until` property has no `isinstance`
    guard, so `_card_waiting_until` keeps the raw token (its
    unparseable-backstop contract depends on it).
    """
    try:
        text = readme.read_text(encoding="utf-8")
    except OSError:
        return None
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    for line in m.group(1).splitlines():
        if line.startswith("waiting_on:"):
            raw = _comment_free_tail(line)
            quoted = raw[:1] in ('"', "'")
            value = raw.strip('"').strip("'") if quoted else raw
            if not value:
                return None
            # yaml-lite coerces only *unquoted* tokens away from `str`
            # (null/bool -> None/bool, int -> int), all of which the engine's
            # `isinstance(v, str)` guard drops to None. A *quoted* "true" /
            # "42" / "null" stays a live string reason the engine keeps, so
            # coercion must skip it — otherwise the hook reports a card the
            # engine impedes as resumable.
            if not quoted and (
                value in _NULL_SET
                or value in _TRUE_SET
                or value in _FALSE_SET
                or _INT_RE.match(value)
            ):
                return None
            return value
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
            return _scalar_or_none(line)
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

    Mirrors `goc.engine.waiting_impedes` across the full
    `waiting_on` × `waiting_until` matrix at UTC timestamp precision
    (matching `engine._waiting_until_instant`). The engine gates on
    `reason is not None` — any non-None reason (canonical *or* a
    typo'd / hand-edited value that has not yet been through
    `goc validate`) impedes unless `waiting_until` is elapsed:

    - any non-None `waiting_on`, no `waiting_until` → impeded
      (open-ended wait).
    - any non-None `waiting_on`, future `waiting_until` → impeded.
    - any non-None `waiting_on`, elapsed `waiting_until` → NOT impeded
      (elapsed wait resurfaces the card; engine contract).
    - no `waiting_on`, future `waiting_until` → impeded (deferred wait).
    - no `waiting_on`, elapsed `waiting_until` → NOT impeded.
    - present-but-unparseable `waiting_until` with no `waiting_on` →
      impeded (engine's `until_unparseable` backstop: err on the side
      of hiding pre-validate / hand-edited decks).

    Date-level coarseness does NOT suffice for the datetime-shape
    values the engine accepts since the `_waiting_until_instant`
    extension: a same-day future `YYYY-MM-DDTHH:MM:SSZ` is impeded by
    the engine, and a date-truncated comparison would round it to
    today and clear the wait early.
    """
    reason = _card_waiting_on(readme)
    until = _card_waiting_until(readme)
    until_unparseable = False
    until_dt: datetime | None = None
    if until:
        until_dt = _parse_waiting_until(until)
        if until_dt is None:
            until_unparseable = True
    until_future = until_dt is not None and until_dt > datetime.now(tz=timezone.utc)
    if reason is not None:
        # Elapsed waiting_until resurfaces the card even with a reason set.
        if until_dt is not None and not until_future:
            return False
        return True
    if until_dt is None:
        return until_unparseable
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
