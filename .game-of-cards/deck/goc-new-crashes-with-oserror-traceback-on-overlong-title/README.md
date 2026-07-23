---
title: goc-new-crashes-with-oserror-traceback-on-overlong-title
summary: "No title gate in `goc new` (antipattern guard, schema `title_pattern` regex, `resolve_card_dir`) bounds title length, so a valid-slug title longer than the filesystem's 255-byte name limit passes every guard and crashes with an uncaught `OSError: [Errno 36] File name too long` traceback at `card_dir.exists()` — instead of the CLI's clean `ERROR:` + exit 2 contract. `goc move <old> <overlong-new>` shares the unguarded path. Needs a small decision: guard bound (filesystem 255 vs a conservative editorial cap) and guard location."
status: open
stage: null
contribution: low
created: "2026-07-23T01:11:06Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] PROCESS: decision recorded — length bound and guard location (see "## Decision required")
  - [ ] TDD: `reproduce.py` exits zero — `goc new` with a 300-char valid-slug title prints a clean `ERROR:` line and exits 2, no traceback, deck untouched
  - [ ] TDD: regression test under tests/ covers overlong titles on both `goc new` and `goc move`
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` green; `uv run goc validate` passes
---

# goc new crashes with a raw OSError traceback on an overlong title

## Location

`goc/engine.py:5479-5490` (`cmd_new`):

```python
    card_dir = resolve_card_dir(title)
    if card_dir.exists():          # <- OSError raised here, before any guard output
        ...
    card_dir.mkdir(parents=True)
```

None of the three title gates bounds length: `_check_title_antipatterns`
(engine.py:5385), the schema `title_pattern` regex check (engine.py:5475
— `^[a-z0-9][a-z0-9-]*[a-z0-9]$` matches any length), and
`resolve_card_dir` (engine.py:1020).

## What's broken

The CLI's error contract for bad input is a clean `ERROR: ...` line on
stderr and exit 2 (as every neighboring guard in `cmd_new` does). A
title that is a perfectly valid slug but longer than the filesystem's
255-byte filename limit passes every guard, then blows up inside
pathlib:

```
$ goc new $(python3 -c "print('a'*300)")
  ...
  File ".../pathlib.py", line 842, in stat
    return os.stat(self, follow_symlinks=follow_symlinks)
OSError: [Errno 36] File name too long: '/tmp/gocprobe/.game-of-cards/deck/aaa...'
```

(verified live in a scratch deck; the crash fires at `card_dir.exists()`,
so no partial state is created — the defect is the contract violation,
not data corruption). `goc move <old> <overlong-new>` funnels through
the same unguarded `resolve_card_dir` + filesystem path.

## Why it matters

Agents generate titles programmatically (audit hunters, porters,
migration tools); a summary-length string pasted as a title is an easy
mistake, and the raw traceback reads as an engine crash rather than
user error — the exact failure shape the CLI's guard layer exists to
prevent. Adjacent precedent:
[trailing-newline-title-passes-guards-and-scaffolds-unaddressable-card-dir](../trailing-newline-title-passes-guards-and-scaffolds-unaddressable-card-dir/)
covers a different character-level gap in the same guard stack; no
existing card covers length.

## Decision required

Two small picks:

1. **Bound.** (a) The real filesystem limit — reject titles whose
   UTF-8 byte length exceeds 255 (precise, but OS-dependent in
   principle); or (b) a conservative editorial cap (e.g. 120 chars)
   justified by readability — every existing card title is well under
   100 chars, and a title approaching 255 bytes is unusable in tables
   anyway. **Recommendation: (b)** — an editorial cap doubles as a
   quality guard and makes the limit self-documenting.
2. **Location.** Add the check to `_check_title_antipatterns` (shared
   by `goc new` and validate's title sweep) or as a standalone guard in
   `cmd_new` + `cmd_move` next to the `title_pattern` check.
   **Recommendation:** the standalone guard next to `title_pattern`,
   so `goc move`'s new-title path is covered explicitly and existing
   decks with hypothetical long titles don't start failing validate.

## Fix (after decision)

A ~4-line guard in `cmd_new` and `cmd_move`:

```python
if len(title.encode()) > TITLE_MAX_BYTES:
    print(f"ERROR: title exceeds {TITLE_MAX_BYTES} bytes (got {len(title.encode())})", file=sys.stderr)
    sys.exit(2)
```

plus the regression test from the DoD.
