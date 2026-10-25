---
title: goc-attest-mutates-log-md-on-already-closed-cards
summary: "`goc attest` never read a card's status: run on a `done` / `disproved` / `superseded` card it appended a fresh `## Closure verification (<today>)` block to the closed card's `log.md` — recording a spurious `log-md-closure-entry` FAIL on any day after the closure, or, when every check passed, exiting 0 with advice to `goc done` a card already closed. `_cmd_attest` now calls the shared `_refuse_terminal_mutation` helper before it loads any check, so a closed card is refused with exit 2, its `log.md` untouched, and the message names the post-close amendment path that works."
status: done
stage: null
contribution: medium
created: "2026-05-29T18:08:20Z"
closed_at: "2026-10-25T04:39:43Z"
human_gate: none
advances:
  - terminal-status-guard-missing-across-mutation-verbs
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [x] PROCESS: decision recorded in `## Decision required` — guard `goc attest` against terminal targets (the sibling-consistent option), allow with a "re-attest is a no-op echo of the original" semantic, or split (re-attest passes by reading the already-recorded block instead of mutating). — decided 2026-10-22 via the parent epic: option 1, refuse outright.
  - [x] TDD: `reproduce.py` exits zero — running `goc attest` against a closed card no longer mutates `log.md` (or behaves per the recorded decision). — both scenarios (a config with `log-md-closure-entry`, and one whose checks all pass on the closed card) exit 2 with `log.md` byte-identical; the pre-fix engine appended a block in both, and the all-pass run exited 0 with the `Next: goc done` hint. The reproducer returned 0 on its defect-present branch and was rewritten to the 0/1/2 contract. `tests/test_terminal_status_guard.py` pins the refusal in CI.
  - [x] MECHANICAL: `_cmd_attest` in `goc/engine.py` refuses terminal targets through the parent epic's shared `_refuse_terminal_mutation` helper (decided 2026-10-22), with an error message naming the replacement path (re-open is forbidden; file a new card). — the helper runs right after `load_card_or_exit`; its message names the post-close amendment path (a new card, pointed to from the closed card's log.md).
  - [x] MECHANICAL: the misleading `Next: goc done <title> to close once all DoD items are ticked.` print at `engine.py:5890` is dropped on terminal-card paths (or removed entirely if the guard short-circuits before it runs). — the guard exits before it on every terminal path; the test asserts the hint is absent there and still printed for a live card.
  - [x] PROCESS: `uv run goc validate` clean; full regression suite green. — `goc validate` exit 0 with no errors; 1371 tests OK.
worker: {who: "claude[bot]", where: main}
---

# `goc attest` mutates `log.md` on already-closed cards

## Location

`goc/engine.py` — `_cmd_attest`, which loaded the card, ran the
configured layer-2 / layer-3 checks and appended the `## Closure
verification` block to `log.md` without ever reading `card.status`.

## What was broken

A `done`, `disproved` or `superseded` card took the attestation write
exactly as a live one would:

```python
    card = load_card_or_exit(card_dir, title)
    config = load_deck_config()
    # ... runs every configured check ...
    log_path.write_text((existing.rstrip() + "\n\n" + block) if existing.strip() else block)
    print(f"\nWrote attestation to {log_path}")

    if any_failed:
        print("\nERROR: attestation has failures; finish-card will block closure.", file=sys.stderr)
        sys.exit(2)
    print("\nAttestation OK.")
    print(f"Next: goc done {title} to close once all DoD items are ticked.")
```

`_cmd_done` and `_cmd_status` refuse terminal targets inline, and
`_cmd_wait` adopted the shared `_refuse_terminal_mutation` guard on
2026-10-24
([goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard](../goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard/)).
`attest` was the member of the family with no guard at all.
(`_cmd_decide`, whose guard from
[goc-decide-accepts-decisions-on-already-closed-cards](../goc-decide-accepts-decisions-on-already-closed-cards/)
the filing compared against, has since swapped its refusal for a
terminal gate-repair path.)

## Empirical evidence

First observed 2026-05-29 on `main`: `goc attest dummy-closed-card
--non-interactive`, run against a card closed cleanly on 2026-01-02,
exited 2 after appending this to the closed card's `log.md`:

```
## Closure verification (2026-05-29T18:09:09Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 1/1 ticked
- [ ] log-md-closure-entry FAIL — no '## 2026-05-29 — Closure' section
```

The historical record then read as if attestation had re-failed months
after the closure.

`reproduce.py` (this directory) is the canonical reproducer. It runs
`goc attest` against a `done` card in two throwaway decks: one whose
config includes `log-md-closure-entry`, and one whose checks all pass
on the closed card. On `main` before the fix (2026-10-25) both runs
appended a verification block, and the second also exited 0 and told
the caller to `goc done` the already-closed card. After the fix both
exit 2 with `log.md` byte-identical and the terminal refusal on
stderr. Exit codes: 0 = defect no longer fires, 1 = defect fires,
2 = harness or precondition broken.

## Why it matters

Three concrete harms:

1. **Log vandalism on a closed card.** A reader scanning a closed
   card's `log.md` expects the entries to date-sort chronologically
   from open → closure. A stray late-dated `## Closure verification`
   block tells the reader that closure was re-litigated, which it
   wasn't. The card-as-record axis (`Skill(card-schema)` "Deck as
   scheduler vs deck as record") relies on closed-card history being
   stable.

2. **False `FAIL` markers on a year-old closure.** The `log-md-closure-entry`
   derived check requires a `## <today> — Closure` heading in `log.md`.
   That heading only matches on the day the card actually closes — so
   re-attesting any closed card on a later date always records a
   spurious `FAIL` for that check, contradicting the card's terminal
   status. Where no such check is configured, the run instead passes
   and advises closing a card that is already closed.

3. **Reachability path.** This is not a theoretical defect. The
   methodology hands agents a sequence: `attest` runs before `done`.
   An agent driven by `pull-card` or `/loop` can easily land on a
   card that was already closed by a parallel session (the soft
   `status: active` lock isn't a hard one) and run `attest` on it
   reflexively. `goc done` would have refused; `goc attest` accepted.

## Decision

*Resolved 2026-10-22T05:17:58Z:* Decided via parent terminal-status-guard-missing-across-mutation-verbs: option 1, refuse outright — the terminal guard runs at the top of _cmd_attest and writes nothing

*Reasoning:* The maintainer approved the parent's recommended bundle in a human session on 2026-10-22, which resolves exactly this card's question; implement through the parent's shared _refuse_terminal_mutation helper, whose message is written fresh because _cmd_decide has stopped refusing terminal cards

## Fix

Applied 2026-10-25 per the decision:

- **Guard.** `_cmd_attest` calls `_refuse_terminal_mutation(card,
  "attest")` right after `load_card_or_exit` — before any check runs
  or `log.md` is opened, and ahead of the empty-config and all-skipped
  refusals, so a closed card is refused for being closed rather than
  for whatever its config lacks. The shared message names the card,
  its terminal status, the verb and the forward path that works on a
  closed card: file a new card and point to it from the closed card's
  log.md with a dated post-close amendment (`Skill(finish-card)`
  "After closure"). The fix sketch's inline message proposed
  `goc status <old> superseded --by <new>`, which `_cmd_status`
  refuses for every terminal card.
- **Hint.** The `Next: goc done <title>` print needed no change of its
  own: the guard exits before it on every terminal path.
- **Help.** `goc attest --help` now says the verb runs a live card's
  closure checks.
- **Tests.** `tests/test_terminal_status_guard.py` gains
  `test_attest_refuses_every_terminal_status` (exit 2, card directory
  byte-identical, no `Next: goc done` hint) and a live-card control
  that still records the block and prints the hint. The fixture's
  scratch `config.yaml` now turns auto-commit off, replacing the
  `--no-commit` that `_goc` appended to every call: `attest`, like
  `move` and `quality-pass`, rejects that flag as an unknown argument
  with the same exit 2 the guard uses. The config also lists checks
  every probe card passes, so an unguarded verb visibly writes and
  exits 0. Against the pre-fix engine the attest test fails for all
  three terminal statuses.
