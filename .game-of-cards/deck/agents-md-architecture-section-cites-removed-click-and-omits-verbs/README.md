---
title: agents-md-architecture-section-cites-removed-click-and-omits-verbs
summary: "AGENTS.md's `## Code architecture` section is stale on two facts: it calls `goc/cli.py` a \"thin Click entry point\" that \"imports the engine's Click group\", but Click was fully removed for argparse (closed `replace-click-with-argparse`, 2026-05-09); and it lists only 12 of the engine's 16 verbs, omitting `wait`, `repair-edges`, `migrate`, and `migrate-list-style`. Mechanical doc-sync, no code change."
status: done
stage: null
contribution: high
created: "2026-05-27T12:11:31Z"
closed_at: 2026-05-27T13:18:02Z
human_gate: none
advances: []
advanced_by: []
tags: [documentation, api-contract]
definition_of_done: |
  - [x] MECHANICAL: AGENTS.md `goc/cli.py` bullet no longer says "Click"; it describes the argparse wiring (builds the argparse parser via `_build_parser`, bolts on `install`/`upgrade`, adds `--version`).
  - [x] MECHANICAL: AGENTS.md `goc/engine.py` verb list includes `wait`, `repair-edges`, `migrate`, and `migrate-list-style` (or is reworded so it no longer claims an exhaustive "every verb except install/upgrade (...)" list while omitting them).
  - [x] TDD: a check confirms `click` appears in neither `goc/cli.py` nor AGENTS.md's cli bullet, and that every engine subcommand from `goc --help` (minus install/upgrade) is accounted for in the AGENTS.md passage.
  - [x] PROCESS: plugin-asset sync `--check` green and `goc validate` clean after the edit (AGENTS.md is not auto-synced, but verify nothing else drifted).
worker: {who: "claude[bot]", where: main}
---

# AGENTS.md architecture section cites removed Click and omits four verbs

The `## Code architecture` section of `AGENTS.md` makes two claims that
the code falsifies. Both are pure doc drift — the fix edits prose only.

## Location

- `AGENTS.md:116-123` — the `goc/cli.py` and `goc/engine.py` bullets.
- Code of record: `goc/cli.py:1-20`, `goc/engine.py:2326-2525`.

## What's broken

### 1. "Click entry point" — Click was removed

`AGENTS.md:116-118` reads:

> - **`goc/cli.py`** — thin Click entry point. Imports the engine's Click
>   group, bolts on `install` + `upgrade` from `install.py`, and adds
>   `--version`. Wired as `goc = "goc.cli:main"` in `pyproject.toml`.

But `goc/cli.py` is pure `argparse`. Its own module docstring says:

> Builds the argparse parser from engine.py, adds `install` and `upgrade`
> subcommands from install.py, and wires up the `--version` flag.

It imports `_build_parser` from the engine, and `grep -rni click goc/*.py`
returns nothing — Click is gone from the package entirely. The card
`replace-click-with-argparse` (status: done, closed 2026-05-09) removed
Click and dropped it from `pyproject.toml`, but never updated this prose.

### 2. The engine verb list omits four verbs

`AGENTS.md:119-123` claims engine.py implements "every verb except
install/upgrade" and enumerates twelve:

> `new`, `status`, `done`, `attest`, `decide`, `advance`, `unadvance`,
> `move`, `triage`, `show`, `quality-pass`, `validate`

`goc --help` lists sixteen subcommands. Excluding install/upgrade
(which live in `install.py`), the engine registers four more that the
doc omits:

- `wait` (`goc/engine.py:2435`) — set/clear the impediment overlay; central
  to the actively-evolving three-axis "blocked" model.
- `repair-edges` (`goc/engine.py:~2473`) — preview/repair asymmetric edges.
- `migrate` (`goc/engine.py:2516`) — merge legacy `deck/` into `.game-of-cards/deck/`.
- `migrate-list-style` (`goc/engine.py:2523`) — re-emit cards to block-style lists.

The "every verb except install/upgrade (...)" framing asserts an
exhaustive list, so the four omissions make it a falsifiable contradiction
rather than a harmless abbreviation.

## Why it matters

AGENTS.md is the first orientation a cold agent or contributor reads. The
Click claim sends a reader hunting for a Click group that does not exist;
the truncated verb list hides `wait` — the impediment-overlay verb that is
load-bearing for the in-flight `blocked`-status redesign. Doc that
contradicts authoritative behavior is high-contribution rot: the
read-pattern guarantee silently fails when the map disagrees with the
territory.

## Fix

Edit `AGENTS.md:116-123` only:

- Rewrite the `goc/cli.py` bullet to describe the argparse wiring (mirror
  the module docstring): builds the argparse parser via `_build_parser`
  from engine.py, bolts on `install`/`upgrade` from `install.py`, adds
  `--version`.
- Either extend the engine verb list with `wait`, `repair-edges`,
  `migrate`, `migrate-list-style`, or reword so it no longer claims an
  exhaustive enumeration. Recommend listing them — the explicit roster is
  the useful part.

No code change; AGENTS.md is outside the plugin auto-sync, so only the one
file is touched. The marker-bounded GoC block below the architecture
section is untouched (this content lives above the `<!-- BEGIN GOC -->`
marker).
