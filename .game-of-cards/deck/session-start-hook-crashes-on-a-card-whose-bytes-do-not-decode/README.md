---
title: session-start-hook-crashes-on-a-card-whose-bytes-do-not-decode
summary: "The SessionStart hook (goc/templates/hooks/deck_session_start.py, shipped in the Claude Code and Codex plugin payloads and the vendored install) read every card's README with encoding='utf-8' but caught only OSError, so one card holding bytes that do not decode made the hook exit 1 with a UnicodeDecodeError traceback. No reminder printed at all, so the session started without the active, parked and impeded card lists the hook exists to show. Fixed: the four frontmatter readers now catch UnicodeDecodeError beside OSError, so the hook skips such a card the way it skips an unreadable one, as the engine's deck views do, and still reminds about every readable card."
status: done
stage: null
contribution: medium
created: "2026-10-10T04:51:12Z"
closed_at: "2026-10-14T05:15:38Z"
human_gate: none
advances:
  - session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — with an undecodable card in the deck, the hook exits 0 and still prints the active card's reminder
  - [x] TDD: a regression test in `tests/test_session_start_hook.py` runs the hook against a deck holding an undecodable card and fails against today's hook
  - [x] MECHANICAL: the four README readers in `goc/templates/hooks/deck_session_start.py` (`_card_status`, `_card_human_gate`, `_card_waiting_on`, `_card_waiting_until`) treat a decode failure the way they treat an unreadable file
  - [x] MECHANICAL: mirrors regenerated — `python scripts/sync_plugin_assets.py --check` is clean
  - [x] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass
worker: {who: "claude[bot]", where: main}
---

# The SessionStart hook crashes on a card whose bytes do not decode

## Location

`goc/templates/hooks/deck_session_start.py`, mirrored into
`claude-plugin/hooks/`, `codex-plugin/hooks/` and `.claude/hooks/`, and
into the `goc/templates/hooks/` copy inside both plugin payloads:

- `:114-120` (`_card_status`), `:132-135` (`_card_human_gate`),
  `:159-162` (`_card_waiting_on`), `:192-195` (`_card_waiting_until`).
  Each reads with `readme.read_text(encoding="utf-8")`. The handler was
  `except OSError:` and is now `except (OSError, UnicodeDecodeError):`.
- `:435-441` (`main`): calls `_card_status(readme)` for every card in
  the deck, whatever its status.
- `tests/test_session_start_hook.py:787`
  (`SessionStartHookUndecodableCardTest`): the regression tests.

## What was broken

Each reader's docstring promises a quiet fallback, for example
`_card_status`: "Return the frontmatter `status` value, or None if
unreadable." The handler only covered `OSError`. A README whose bytes
are not UTF-8 raises `UnicodeDecodeError`, which is a `ValueError`, so
it escaped the reader and `main`, and the hook exited 1.

`main` asks every card for its status before it filters to active
cards. So one undecodable card anywhere in the deck, at any status,
stopped the hook before it printed anything.

## Empirical evidence

`reproduce.py` builds a deck holding one active gate-free card and one
open card whose summary carries a Latin-1 byte (0xE9). It then pipes
the hook the JSON Claude Code sends. Before the fix (hook as of
58fdfd19):

```
hook exit: 1
stdout: ''
stderr (last line): UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9 in position 34: invalid continuation byte
[FAIL] one undecodable card stops the hook before it prints any reminder.
```

After the fix:

```
hook exit: 0
stdout: '[GoC] Active card(s): claimed-card — resume or close before starting new work.'
[OK] the hook skips the undecodable card and still reminds about claimed-card.
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

The four handlers now read `except (OSError, UnicodeDecodeError):`. A
card whose bytes do not decode gets the fallback an unreadable file
gets (`None`, or `"none"` for the gate), so `main` skips it the way it
skips a missing README, and the reminders for every readable card
still print. That matches the engine, where `load_all_cards` warns and
skips the same card. The hook says nothing about the skipped card;
`goc validate` names it.

`SessionStartHookUndecodableCardTest` pins both halves:

- `test_readers_treat_undecodable_bytes_like_an_unreadable_file`: each
  reader returns, for an undecodable README, exactly what it returns
  for a README it cannot open. Every field in that README carries a
  non-default value, so a reader that decoded past the bad byte would
  not match.
- `test_undecodable_card_does_not_stop_the_reminder`: `main` exits 0
  and prints the readable active card's reminder while an undecodable
  card sits in the deck.

Against the pre-fix hook, the four reader subtests and the `main` run
all raise `UnicodeDecodeError`.

This card is one more instance of
[session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting](../session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting/)
(it advances that card): the engine's card read learned the corrupt-card
path on 2026-10-10 and the hook's copy did not. The fix did not depend
on that card's decision: whichever way it goes, a hook must not crash
on one card.

OpenClaw is unaffected. Its TypeScript port reads with Node's
`readFile(readme, "utf8")` (`openclaw-plugin/index.ts:314`), which
substitutes U+FFFD instead of throwing (checked with Node: the bytes
`caf\xe9` read back as `"caf�"`).

## Artifacts

- reproduce.py
