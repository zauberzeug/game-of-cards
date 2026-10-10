---
title: card-with-non-utf-8-bytes-crashes-validate-and-every-deck-view-without-naming-it
summary: "A card README whose bytes do not decode (one Latin-1 byte such as 0xE9 is enough) crashes goc validate, the bare queue, --json, --board, triage and show with a raw UnicodeDecodeError traceback that names no card. load_card and validate_deck_directories catch only FrontmatterError, and UnicodeDecodeError is a ValueError that escapes it, so the one-broken-card-does-not-blank-the-queue design never engages and nothing tells the user which card to fix. Fixed: engine.read_card_text now routes decode failures into FrontmatterError, so the existing warn-and-skip, ERROR and exit-2 diagnostic paths name the card."
status: done
stage: null
contribution: medium
created: "2026-10-10T04:49:33Z"
closed_at: "2026-10-10T04:56:54Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — `validate`, the bare queue, `--json`, `--board`, `triage` and `show bad-bytes` each finish without a traceback and name the undecodable card; `validate` exits non-zero and the deck views still list the healthy card
  - [x] TDD: a regression test in `tests/` drives those commands against a scratch deck holding a card with one undecodable byte (UTF-8 mode forced) and fails against the pre-fix engine
  - [x] MECHANICAL: the deck-wide README reads in `goc/engine.py` (`load_card`, `validate_deck_directories`, `_cmd_migrate_list_style`) go through one helper that raises `FrontmatterError` naming the codec, byte and offset; `_cmd_show` still prints the card, with U+FFFD marking each undecodable byte, and warns on stderr
  - [x] MECHANICAL: plugin mirrors regenerated — `python scripts/sync_plugin_assets.py --check` is clean
  - [x] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass
worker: {who: "claude[bot]", where: main}
---

# A card whose bytes do not decode crashes validate and every deck view without naming the card

## Location

- `goc/engine.py:256` (`read_card_text`): the helper the fix added. It
  turns `UnicodeDecodeError` into `FrontmatterError`.
- Readers now routed through it, each a bare `readme.read_text()`
  before: `load_card` (`:1094`), `validate_deck_directories` (`:1448`),
  `_cmd_show` (`:7281`) and `_cmd_migrate_list_style` (`:7493`).
- Handlers that catch only `FrontmatterError`: `load_all_cards`
  (`:1126`), `load_card_or_exit` (`:1155`) and
  `validate_deck_directories` (`:1449`).

## What was broken

The deck is built so one broken card cannot take the rest down.
`load_all_cards` says so:

```python
        except FrontmatterError as exc:
            # Don't let one broken card blank the whole queue — surface a
            # warning per card and skip. `goc validate` reports authoritatively.
```

`validate_deck_directories` turns the same exception into an `ERROR:`
line naming the directory, and `load_card_or_exit` turns it into an
exit-2 diagnostic. All three key on `FrontmatterError`, the exception
`load_card`'s docstring promises for a corrupt card.

A README whose bytes did not decode never reached that exception.
`readme.read_text()` raised `UnicodeDecodeError` before
`parse_frontmatter` ran. That is a `ValueError` but not a
`FrontmatterError`, so it passed every handler and ended the process.
The traceback showed `pathlib` frames and the byte offset, but never the
file. `show`'s own comment promises the opposite for the card you most
want to see: "`show` stays read-everything (the broken card is the one
you most want to inspect)".

## Empirical evidence

`reproduce.py` builds a scratch deck holding a healthy card and a card
whose summary carries one Latin-1 byte (0xE9). It forces Python's UTF-8
mode so the byte is undecodable on any host. Before the fix (engine as
of 3dfedc8b):

```
[FAIL] goc validate: exit 1; traceback (UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9 in position 34: invalid continuation byte); never names the bad card
[FAIL] goc (bare queue): exit 1; traceback (UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9 in position 34: invalid continuation byte); never names the bad card; drops the healthy card
[FAIL] goc --json: exit 1; traceback (UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9 in position 34: invalid continuation byte); never names the bad card; drops the healthy card
[FAIL] goc --board: exit 1; traceback (UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9 in position 34: invalid continuation byte); never names the bad card; drops the healthy card
[FAIL] goc triage: exit 1; traceback (UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9 in position 34: invalid continuation byte); never names the bad card
[FAIL] goc show bad-bytes: exit 1; traceback (UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9 in position 34: invalid continuation byte); never names the bad card
6 of 6 commands mishandle a card whose bytes do not decode.
```

After the fix:

```
[OK]   goc validate: exit 1
[OK]   goc (bare queue): exit 0
[OK]   goc --json: exit 0
[OK]   goc --board: exit 0
[OK]   goc triage: exit 0
[OK]   goc show bad-bytes: exit 0
Every command names the undecodable card and keeps working.
```

Each now names the card with the codec's reason, for example
`ERROR: bad-bytes: README.md is not decodable text: 'utf-8' codec can't
decode byte 0xe9 in position 34: invalid continuation byte`. Verbs that
load only a healthy card (`show healthy-card`, `status healthy-card
active`, `new`) were never affected.

## Why it matters

- **Nothing names the culprit.** In a deck of hundreds of cards, the
  traceback gives a byte offset with no file, so finding the card takes
  a hand-written scan. `goc validate` is the tool meant to answer that
  question, and it crashes too.
- **One card stops all deck work.** The queue, the board and triage all
  die, along with every pull-card gate built on `goc --json`. Today that
  gate also fails open on a crash
  ([pull-card-workflow-launches-agents-when-goc-itself-fails-to-count-the-queue](../pull-card-workflow-launches-agents-when-goc-itself-fails-to-count-the-queue/)),
  and this card was the real engine failure that card's evidence used.
- **Reachability.** An editor that saves in Latin-1 or cp1252, a pasted
  binary fragment, or a merge tool can write such bytes. So can goc
  itself. 17 of the 18 `write_text` calls in `goc/engine.py` pass no
  `encoding=`, so cards are written in the host's default encoding
  ([goc-crashes-on-hosts-whose-default-encoding-is-not-utf-8](../goc-crashes-on-hosts-whose-default-encoding-is-not-utf-8/)).
  A goc run on a cp1252 host writes an em-dash as byte 0x97, and every
  UTF-8 host that reads the card afterwards crashes.

## Fix

The decode failure now takes the exception every handler already
catches, through one helper beside `parse_frontmatter`:

```python
def read_card_text(readme: Path) -> str:
    try:
        return readme.read_text()
    except UnicodeDecodeError as exc:
        raise FrontmatterError(f"README.md is not decodable text: {exc}") from exc
```

- `load_card` and `validate_deck_directories` read through it. The
  queue, `--json`, `--board`, `triage`, `repair-edges` and
  `quality-pass` now warn and skip the card. `validate` prints
  `ERROR: <dir>: README.md is not decodable text: ...` and exits 1.
  `status`, `done` and `wait` on the card exit 2 through
  `load_card_or_exit`, naming the path and the reason.
- `_cmd_migrate_list_style` reads through it inside its existing `try`,
  so the deck-wide rewrite warns, continues, and leaves the card's bytes
  untouched.
- `_cmd_show` keeps its read-everything contract. On the helper's error
  it prints `p.read_text(errors="replace")`, with U+FFFD marking each
  bad byte, and warns with the reason on stderr. `show` never writes, so
  the replacement cannot destroy bytes.
- `tests/test_undecodable_card_readme.py` drives all of these against a
  scratch deck with UTF-8 mode forced. All six tests fail against the
  pre-fix engine and pass now.

The helper does not pick a codec. Which encoding goc reads cards in is
the open decision on
[goc-crashes-on-hosts-whose-default-encoding-is-not-utf-8](../goc-crashes-on-hosts-whose-default-encoding-is-not-utf-8/).
Whatever that card settles, a byte sequence that does not decode can
only be rejected, never repaired, so this behaviour holds either way.
The parked BOM and CRLF cards
([bom-prefixed-card-readme-silently-vanishes-from-every-deck-view](../bom-prefixed-card-readme-silently-vanishes-from-every-deck-view/),
[cards-with-windows-line-endings-vanish-from-the-deck-as-unterminated](../cards-with-windows-line-endings-vanish-from-the-deck-as-unterminated/))
choose between tolerating and rejecting text that decodes fine. That is
a question this card does not touch.

## Out of scope

The SessionStart hook reads cards with its own loop, catches only
`OSError`, and crashes on the same card. It is filed separately as
[session-start-hook-crashes-on-a-card-whose-bytes-do-not-decode](../session-start-hook-crashes-on-a-card-whose-bytes-do-not-decode/).

## Artifacts

- reproduce.py
