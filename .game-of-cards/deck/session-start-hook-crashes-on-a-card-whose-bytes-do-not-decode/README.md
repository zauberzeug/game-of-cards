---
title: session-start-hook-crashes-on-a-card-whose-bytes-do-not-decode
summary: "The SessionStart hook (goc/templates/hooks/deck_session_start.py, shipped in the Claude Code and Codex plugin payloads and the vendored install) reads every card's README with encoding='utf-8' but catches only OSError, so one card holding bytes that do not decode makes the hook exit 1 with a UnicodeDecodeError traceback. No reminder prints at all, so the session starts without the active, parked and impeded card lists the hook exists to show."
status: open
stage: null
contribution: medium
created: "2026-10-10T04:51:12Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — with an undecodable card in the deck, the hook exits 0 and still prints the active card's reminder
  - [ ] TDD: a regression test in `tests/test_session_start_hook.py` runs the hook against a deck holding an undecodable card and fails against today's hook
  - [ ] MECHANICAL: the four README readers in `goc/templates/hooks/deck_session_start.py` (`_card_status`, `_card_human_gate`, `_card_waiting_on`, `_card_waiting_until`) treat a decode failure the way they treat an unreadable file
  - [ ] MECHANICAL: mirrors regenerated — `python scripts/sync_plugin_assets.py --check` is clean
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass
---

# The SessionStart hook crashes on a card whose bytes do not decode

## Location

`goc/templates/hooks/deck_session_start.py`, mirrored into
`claude-plugin/hooks/`, `codex-plugin/hooks/` and `.claude/hooks/`:

- `:111-115` (`_card_status`), `:126-130` (`_card_human_gate`),
  `:141-157` (`_card_waiting_on`), `:186-190` (`_card_waiting_until`).
  Each reads with `readme.read_text(encoding="utf-8")` inside
  `except OSError:`.
- `:322-328` (`main`): calls `_card_status(readme)` for every card in
  the deck, whatever its status.

## What's broken

Each reader's docstring promises a quiet fallback, for example
`_card_status`: "Return the frontmatter `status` value, or None if
unreadable." The handler only covers `OSError`. A README whose bytes
are not UTF-8 raises `UnicodeDecodeError`, which is a `ValueError`, so
it escapes the reader and `main`, and the hook exits 1.

`main` asks every card for its status before it filters to active
cards. So one undecodable card anywhere in the deck, at any status,
stops the hook before it prints anything.

## Empirical evidence

`reproduce.py` builds a deck holding one active gate-free card and one
open card whose summary carries a Latin-1 byte (0xE9). It then pipes
the hook the JSON Claude Code sends. At HEAD:

```
hook exit: 1
stdout: ''
stderr (last line): UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9 in position 34: invalid continuation byte
[FAIL] one undecodable card stops the hook before it prints any reminder.
```

## Why it matters

The hook is how a new session learns that cards are already claimed,
parked or impeded. Without it, an agent can claim work another session
holds. A failing hook is also noisy: the host reports a hook error at
every session start, in every consuming repo with such a card, until
someone finds the card by hand. The traceback names no file.

The engine had the same gap at its deck-wide reads
([card-with-non-utf-8-bytes-crashes-validate-and-every-deck-view-without-naming-it](../card-with-non-utf-8-bytes-crashes-validate-and-every-deck-view-without-naming-it/)).
How such bytes reach a card, including goc itself writing cp1252 bytes
on a non-UTF-8 host, is covered there.

## Fix

Widen the four handlers to `except (OSError, UnicodeDecodeError):`.
The readers already return `None` / `"none"` for an unreadable file,
so `main` skips the card the way it skips a missing README, and the
reminders for every readable card still print. Re-run
`python scripts/sync_plugin_assets.py` so the three mirrors pick up the
template.

The hook reimplements engine frontmatter logic, which is the subject
of the decision-gated
[session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting](../session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting/).
This fix does not depend on that decision: whichever way it goes, a
hook must not crash on one card.

OpenClaw is unaffected. Its TypeScript port reads with Node's
`readFile(readme, "utf8")` (`openclaw-plugin/index.ts:314`), which
substitutes U+FFFD instead of throwing (checked with Node: the bytes
`caf\xe9` read back as `"caf�"`).

## Artifacts

- reproduce.py
