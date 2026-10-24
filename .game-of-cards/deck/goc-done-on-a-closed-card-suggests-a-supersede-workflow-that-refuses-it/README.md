---
title: goc-done-on-a-closed-card-suggests-a-supersede-workflow-that-refuses-it
summary: "goc done and goc done --bundle refuse a disproved or superseded card with 'use the supersede/disprove workflow', but goc status refuses every terminal card, so the advice sends the user to a second refusal. Route both refusals through the shared _refuse_terminal_mutation helper, which names the post-close amendment path that does work."
status: open
stage: null
contribution: low
created: "2026-10-24T05:07:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero (defect no longer fires) — `goc done` and `goc done --bundle` refuse a `disproved` / `superseded` card without naming the supersede/disprove workflow, and name the post-close amendment path instead.
  - [ ] MECHANICAL: `_cmd_done` and `_cmd_done_bundle` in `goc/engine.py` route their non-`done` terminal branch through `_refuse_terminal_mutation(t, "done")`; the `already done` branches keep their current behavior (single: exit 0, closed_at unchanged; bundle: exit 2).
  - [ ] TDD: `tests/test_terminal_status_guard.py` covers both `done` paths for both non-`done` terminal statuses, and the guard-ordering tests in `tests/test_close_terminal_gate_guard.py` stay green.
  - [ ] PROCESS: the closed predecessor `done-command-overwrites-terminal-cards`, whose DoD contracted the old wording, gets a dated post-close amendment in its log.md pointing here.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` green; `uv run goc validate` clean.
---

# `goc done` on a closed card suggests a supersede workflow that refuses it

## Location

`goc/engine.py` — `_cmd_done` and `_cmd_done_bundle`, the branch that
refuses a card whose status is already `disproved` or `superseded`.

## What's broken

Both closing paths refuse a non-`done` terminal card with advice to use
another workflow:

```python
if prior in TERMINAL_STATUSES:
    print(
        f"ERROR: {title}: status is {prior!r} (terminal); "
        f"use the supersede/disprove workflow — 'done' cannot overwrite terminal states",
        file=sys.stderr,
    )
    sys.exit(2)
```

(`_cmd_done_bundle` prints the same advice with `--bundle cannot
overwrite terminal states`.) The supersede/disprove workflow is
`goc status <card> superseded --by <new>` or `goc status <card>
disproved`, and `_cmd_status` refuses every terminal card:

```python
if prior in TERMINAL_STATUSES:
    print(
        f"ERROR: {title}: status is {prior!r} (terminal);"
        f" terminal cards cannot be moved backward through `goc status`",
        ...
```

So the advice points at a second refusal. The refusal itself is
correct; only the advice is wrong. The wording dates from
[done-command-overwrites-terminal-cards](../done-command-overwrites-terminal-cards/),
whose DoD asked for a message telling the user "to use the appropriate
supersede/disprove workflow instead of closing". `goc status` learned to
refuse terminal cards on the same day (2026-05-05), in
[status-command-reopens-terminal-cards](../status-command-reopens-terminal-cards/),
so the two contracts have contradicted each other from the start.

## Empirical evidence

`reproduce.py` output on `main` (2026-10-24):

```
goc done disproved-card (disproved): exit 2
  ERROR: disproved-card: status is 'disproved' (terminal); use the supersede/disprove workflow — 'done' cannot overwrite terminal states
goc done --bundle disproved-card (disproved): exit 2
  ERROR: disproved-card: status is 'disproved' (terminal); use the supersede/disprove workflow — --bundle cannot overwrite terminal states
goc done superseded-card (superseded): exit 2
  ERROR: superseded-card: status is 'superseded' (terminal); use the supersede/disprove workflow — 'done' cannot overwrite terminal states
goc done --bundle superseded-card (superseded): exit 2
  ERROR: superseded-card: status is 'superseded' (terminal); use the supersede/disprove workflow — --bundle cannot overwrite terminal states

goc status disproved-card superseded --by live-card: exit 2
  ERROR: disproved-card: status is 'disproved' (terminal); terminal cards cannot be moved backward through `goc status`
goc status superseded-card disproved: exit 2
  ERROR: superseded-card: status is 'superseded' (terminal); terminal cards cannot be moved backward through `goc status`

[DEFECT] goc done on a disproved card names no working forward path
[DEFECT] goc done --bundle on a disproved card names no working forward path
[DEFECT] goc done on a superseded card names no working forward path
[DEFECT] goc done --bundle on a superseded card names no working forward path
```

Exit codes: 0 = defect no longer fires, 1 = defect fires, 2 = harness
or precondition broken.

## Why it matters

A user or agent who runs `goc done` on a card that is already closed
wants to know what to do instead. Following this advice costs a second
failed command and still leaves no path forward. An agent that trusts
the message may go on to hand-edit the frontmatter to force the
transition. The path that does work is documented in
`Skill(finish-card)` "After closure": file a new card and point to it
from the closed card's log.md with a dated post-close amendment.

## Fix

Replace the inline refusal in both functions with the shared helper
that
[goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard](../goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard/)
introduced: `_refuse_terminal_mutation(t, "done")`. Its message names
the card, the terminal status, the verb and the post-close amendment
path. Leave the `already done` branches as they are. `goc done` on a
`done` card is an idempotent exit 0, and the bundle refuses to re-close
one. Exit code (2) and guard order (terminal check before the DoD
check, per
[done-reports-dod-error-on-terminal-cards-before-status-guard](../done-reports-dod-error-on-terminal-cards-before-status-guard/))
are unchanged.

This is not a fifth child of
[terminal-status-guard-missing-across-mutation-verbs](../terminal-status-guard-missing-across-mutation-verbs/).
That epic is about verbs with no guard; `goc done` has one, and only its
message is wrong. It just reuses the epic's helper.
