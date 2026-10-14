"""SessionStart hook — brief GoC session primer.

Runs when an agent session starts. If there are active cards in the deck,
prints a one-line reminder so the model can pick up where it left off. Silent
when no cards are in-flight.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
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
# Canonical decimal integer, byte-for-byte the yaml-lite pattern: a leading-zero
# run (`00`, `007`, `0123`) is NOT an integer under YAML 1.2, so the parser keeps
# it as a `str` and `Card.waiting_on` keeps it as a live reason. Matching it here
# would coerce a hand-edited `waiting_on: 007` to absent and announce an impeded
# card as resumable. Pinned to `yaml_lite._INT_RE` by
# `tests/test_waiting_on_int_mirror.py`.
_INT_RE = re.compile(r"^-?(0|[1-9][0-9]*)$")


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


# The line `worktree_deck: shared` as the engine's yaml_lite reads it: the bare
# or quoted word, then at most a whitespace-led trailing comment.
_SHARED_DECK_LINE_RE = re.compile(
    r"""worktree_deck:[ \t]+(?:shared|"shared"|'shared')(?:[ \t]+#.*)?$"""
)


def _detect_worktree_common_root(cwd: Path) -> Path | None:
    """Return the primary working tree root if `cwd` is inside a linked git
    worktree, else None. Mirror of `goc.engine._detect_worktree_common_root`:
    there `git rev-parse --git-common-dir` differs from `--git-dir`.
    """
    try:
        r_git = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True, text=True, cwd=str(cwd), timeout=5,
        )
        r_common = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, cwd=str(cwd), timeout=5,
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        # No git, or a hook-input cwd that is gone or not a directory.
        return None
    if r_git.returncode != 0 or r_common.returncode != 0:
        return None
    git_dir = r_git.stdout.strip()
    common_dir = r_common.stdout.strip()
    if git_dir == common_dir:
        return None  # primary working tree, not a worktree
    common_path = Path(common_dir)
    if not common_path.is_absolute():
        common_path = (cwd / common_path).resolve()
    return common_path.parent


def _config_shares_the_deck(text: str) -> bool:
    """Whether a config.yaml text sets `workflow.worktree_deck` to `shared`.

    The engine parses the file with yaml_lite and compares the value to
    `"shared"`. This reads the block layout the config template ships: the
    key one level under the top-level `workflow:` key, with comment lines
    skipped, so the template's commented-out line stays off. A flow-style
    `workflow: {...}` is not read. Where yaml_lite refuses the file, the
    engine leaves the redirect off, and so does this for the refusals within
    reach: a tab in the indentation, a repeated top-level or `workflow` key.
    """
    top_indent: int | None = None
    child_indent: int | None = None
    top_keys: set[str] = set()
    child_keys: set[str] = set()
    in_workflow = False
    shared = False
    for raw in text.splitlines():
        line = raw.rstrip()
        bare = line.lstrip()
        if not bare or bare.startswith("#"):
            continue
        indent = len(line) - len(bare)
        if "\t" in line[:indent]:
            return False
        if top_indent is None:
            top_indent = indent
        key = bare.split(":", 1)[0]
        if indent <= top_indent:
            if key in top_keys:
                return False
            top_keys.add(key)
            in_workflow = re.match(r"workflow:(?:[ \t]+#.*)?$", bare) is not None
            continue
        if not in_workflow:
            continue
        if child_indent is None:
            child_indent = indent
        if indent == child_indent:
            if key in child_keys:
                return False
            child_keys.add(key)
            if key == "worktree_deck":
                shared = _SHARED_DECK_LINE_RE.match(bare) is not None
    return shared


def _shared_worktree_deck_root(cwd: Path) -> Path | None:
    """Return the primary working tree root when `cwd` is in a linked git
    worktree that opted into `worktree_deck: shared`, else None. Mirror of
    `goc.engine._shared_worktree_deck_root`.
    """
    common_root = _detect_worktree_common_root(cwd)
    if common_root is None:
        return None
    # Env var wins without requiring the config to exist yet.
    if os.environ.get("GOC_WORKTREE_DECK", "").lower() == "shared":
        return common_root
    config_path = common_root / ".game-of-cards" / "config.yaml"
    try:
        text = config_path.read_text(encoding="utf-8")
    except (OSError, ValueError):
        return None
    return common_root if _config_shares_the_deck(text) else None


def _find_project_dir(start: str) -> Path:
    """Return the deck root `goc` resolves from `start`.

    A mirror of `goc.engine._resolve_deck_root` — hooks import nothing from
    the package — pinned to it by tests/test_project_root_from_subdirectory.py.
    In a linked git worktree that opted into `worktree_deck: shared` (the
    `GOC_WORKTREE_DECK=shared` env var, or the key in the primary tree's
    config), that is the primary working tree. Otherwise it is the nearest
    ancestor of `start` holding `.game-of-cards/`: the walk never crosses into
    a different git working tree, and falls back to `start` itself when no
    ancestor holds a deck.
    """
    start_path = Path(start).resolve()
    shared_root = _shared_worktree_deck_root(start_path)
    if shared_root is not None:
        return shared_root
    own_tree_root_passed = False
    for candidate in (start_path, *start_path.parents):
        has_git = (candidate / ".git").exists()
        if own_tree_root_passed and has_git:
            break
        if (candidate / ".game-of-cards").is_dir():
            return candidate
        if has_git:
            own_tree_root_passed = True
    return start_path


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
    project_dir = _find_project_dir(_project_dir_from_hook_input())
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
