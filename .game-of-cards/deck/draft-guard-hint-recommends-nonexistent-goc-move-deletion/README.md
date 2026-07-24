---
title: draft-guard-hint-recommends-nonexistent-goc-move-deletion
summary: "The draft-scaffold refusal in _cmd_status (goc status <draft> superseded/disproved) tells the agent to 'delete it with goc move' — but goc move is strictly a rename (old_title new_title both required); no deletion verb exists. Following the hint verbatim exits 2 with an argparse usage error, exactly when an autonomous agent wants to discard an unauthored duplicate scaffold, inviting improvised rm -rf on deck state. Ships in all four engine copies."
status: open
stage: null
contribution: low
created: "2026-07-24T01:31:14Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, documentation, api-contract]
definition_of_done: |
  - [ ] PROCESS: remedy wording decided (option A/B/C in "Decision required") and gate lowered to none
  - [ ] TDD: reproduce.py exits zero — every remedy named in the refusal message is an executable CLI invocation (or an explicit manual procedure), verified by actually running it
  - [ ] MECHANICAL: hint text updated in goc/engine.py and plugin engine mirrors resynced
---

# Draft-guard refusal hint recommends a `goc move` deletion that does not exist

## Location

- `goc/engine.py:5298-5307` — the draft-scaffold refusal inside `_cmd_status`:

  ```python
  f"draft state guards against. Author it first (then `goc publish {title}` or "
  f"`goc status {title} active`), or delete it with `goc move`.",
  ```

- `goc/engine.py:3613` — `goc move` is a rename verb:
  `subparsers.add_parser("move", help="Rename a title and rewrite known cross-references.")`
  with two required positionals (`old_title new_title`); the executor is
  `git mv`/`shutil.move` plus cross-reference rewrite. No deletion mode,
  no deletion verb anywhere in the CLI.

## What's broken

The refusal fires exactly when an agent wants to discard an unauthored
duplicate scaffold (`goc status <draft> superseded --by <other>`). The
shipped remedy — ``delete it with `goc move` `` — is unexecutable:

```
$ goc move my-draft
usage: goc move [-h] [--allow-jargon] [--dry-run] old_title new_title
goc move: error: the following arguments are required: new_title
```

An autonomous agent that follows printed hints verbatim hits exit 2 and
then improvises — typically `rm -rf` on deck state, the failure mode this
guard exists to prevent. The wrong hint ships in all four engine copies
(source plus claude/codex/openclaw plugin mirrors, which auto-sync from
`goc/engine.py`).

## Empirical evidence

`reproduce.py` (sibling file) scaffolds a throwaway deck, triggers the
refusal, and executes the hinted remedy verbatim:

```
[1] refusal stderr contains: "or delete it with `goc move`."
[2] hinted remedy `goc move <draft>` -> exit 2: the following arguments are required: new_title
[FAIL] refusal hint names a deletion remedy the CLI cannot execute
```

## Why it matters

Reachability: any dedup/supersede automation that races card authoring —
`goc new` scaffold → second agent spots the duplicate → `goc status <draft>
superseded --by <canonical>` → refusal with the broken hint. Same genus as
[legacy-deck-repos-cannot-reach-canonical-layout-by-following-printed-hints](../legacy-deck-repos-cannot-reach-canonical-layout-by-following-printed-hints/)
(printed hint is unexecutable), different verb/surface — the deck's
precedent is one card per hint surface.

## Decision required

What should the discard remedy in the refusal say?

- **Option A — drop the clause.** End the hint after the publish/claim
  remedies. Honest, but leaves the "I really do want to discard this
  scaffold" reader with no guidance.
- **Option B — name the manual procedure.** E.g. "or remove the scaffold
  directory (`git rm -r .game-of-cards/deck/<title>`)". Executable today;
  puts a destructive shell command in a printed hint.
- **Option C — add a real discard verb** (e.g. `goc discard <draft>`,
  guarded to drafts only) and point the hint at it. Cleanest long-term;
  new surface area, and interacts with the open draft-gating meta cards.
