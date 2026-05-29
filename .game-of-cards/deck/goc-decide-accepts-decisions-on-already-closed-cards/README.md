---
title: goc-decide-accepts-decisions-on-already-closed-cards
summary: "`goc decide` only guards on `human_gate != 'none'`, never on `status in TERMINAL_STATUSES`. A closed card (`done` / `disproved` / `superseded`) whose gate was left raised by `goc done` is silently mutated — a `## Decision` section is appended to the closed README, `human_gate` is lowered to `none`, and the success line announces `any agent can now claim this card`. Mirrors the existing guards in `_cmd_done` (engine.py:3244) and `_cmd_status` (engine.py:3983)."
status: active
stage: null
contribution: medium
created: "2026-05-29T15:27:59Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: a regression test in `tests/` exercises `goc decide <closed-card>` and asserts a non-zero exit + an unchanged README.
  - [ ] MECHANICAL: `_cmd_decide` (engine.py:4548) rejects cards whose `status` is in `TERMINAL_STATUSES`, with an error message that mirrors `_cmd_done` (engine.py:3244-3250) and `_cmd_status` (engine.py:3983-3989).
  - [ ] TDD: `reproduce.py` exits zero (defect no longer fires — the script asserts non-zero exit from `goc decide` and an unchanged README on the closed fixture).
  - [ ] MECHANICAL: `uv run goc validate` is clean.
  - [ ] PROCESS: cross-link the existing sibling card `goc-done-marks-cards-done-without-clearing-or-checking-human-gate` in this card's log.md and consider whether a shared terminal-status guard helper is warranted (decline if two call-sites is too small; note the decision in log.md either way).
worker: {who: "claude[bot]", where: main}
---

# `goc decide` accepts decisions on already-closed cards

## Location

`goc/engine.py:4548` — `_cmd_decide` only checks `t.human_gate == "none"`,
not `t.status in TERMINAL_STATUSES`.

## What's broken

`_cmd_decide` (engine.py:4548-4598) opens with a single guard:

```python
t = load_card_or_exit(card_dir, title)
if t.human_gate == "none":
    print(
        f"ERROR: {title}: gate already 'none' (no decision pending)",
        file=sys.stderr,
    )
    sys.exit(2)
```

There is no companion guard on `t.status`. The two peer mutation verbs
that *do* protect terminal cards are explicit:

`_cmd_done` (engine.py:3244-3250):

```python
if prior in TERMINAL_STATUSES:
    print(
        f"ERROR: {title}: status is {prior!r} (terminal); "
        f"use the supersede/disprove workflow — 'done' cannot overwrite terminal states",
        file=sys.stderr,
    )
    sys.exit(2)
```

`_cmd_status` (engine.py:3983-3989):

```python
if prior in TERMINAL_STATUSES:
    print(
        f"ERROR: {title}: status is {prior!r} (terminal);"
        f" terminal cards cannot be moved backward through `goc status`",
        file=sys.stderr,
    )
    sys.exit(2)
```

`_cmd_decide` lacks that pattern. The resulting side effects on a closed
card are visible — not silent — but they ARE wrong:

1. A `## Decision` section is appended to the closed README via
   `replace_or_append_decision` (engine.py:4568).
2. `human_gate` is rewritten from `decision` / `session` to `none`
   (engine.py:4570).
3. A `## <ts>: decision recorded` block is appended to `log.md`
   (engine.py:4586-4591).
4. The success line printed to the user is:
   `Next: gate lowered to none — any agent can now claim this card. goc to see the queue.`
   — which is straight-up false: the card is `status: done` and is not
   pullable. `pull-card` / `next-card` filter out terminal status; the
   user reading this line is given an incorrect promise.

## Reachability path

This bug is reachable through the gap documented by the open sibling
card [goc-done-marks-cards-done-without-clearing-or-checking-human-gate](../goc-done-marks-cards-done-without-clearing-or-checking-human-gate/):
`goc done` closes a card without clearing or rejecting a raised
`human_gate`. So a card can land at `status: done` with
`human_gate: decision` still set — a state the deck reaches today, not
hypothetically. Once in that state, any subsequent `goc decide <title>
--decision X --because Y` succeeds and produces the misleading "any
agent can now claim this card" output.

Two ways into the state empirically:

- A card is filed with `--gate decision`, gets claimed and worked, then
  `goc done` closes it before the decision was formally recorded
  (the gate-clear gap of the sibling card).
- A previously-resolved decision card is re-routed forward via
  `goc status superseded --by`, which closes the card but `goc decide`
  has no terminal-status guard to refuse the legacy decision-recording
  attempt that follows.

## Empirical evidence

Repro on a sandbox deck with one fixture card (`status: done`,
`human_gate: decision`), running the locally-installed `goc`:

```
$ goc decide sample-card --decision "go" --because "irrelevant on a done card" --no-commit
sample-card: decision recorded; gate decision → none
Next: gate lowered to none — any agent can now claim this card. goc to see the queue.
```

After the call, the fixture's README contains:

```
status: done
closed_at: "2026-05-15T00:00:00Z"
human_gate: none
...

## Decision

*Resolved 2026-05-29T15:26:53Z:* go

*Reasoning:* irrelevant on a done card
```

`reproduce.py` (sibling file in this card directory) reproduces this in
an isolated temporary deck and exits non-zero today; once the guard
lands, the script will exit zero (the assertion flips: `goc decide`
must reject, not accept).

## Why it matters

1. The closed READMEs of the deck are part of the **record axis** — a
   cold reader walks closed cards to reconstruct decision history
   (AGENTS.md "Deck as scheduler vs deck as record"). Allowing
   post-closure mutation of the `## Decision` block undermines that
   read-pattern: the recorded decision can be silently rewritten
   without a `superseded_by` link, leaving no forward routing pointer
   the way `goc status superseded --by` provides.
2. The misleading user message ("any agent can now claim this card")
   actively encourages the wrong follow-up. An autonomous puller
   reading this is told the card is pullable; the queue filter then
   silently hides it because `status: done`, but the operator now has
   an inconsistent mental model.
3. This is the *second* instance of the gate-vs-terminal-status family
   (the first is the sibling card on `goc done`). Two instances is
   below the four-instance threshold for filing the architectural
   meta-fix, but they do suggest a shared
   `_refuse_on_terminal_status(t, verb)` helper would centralize the
   guard pattern. The DoD's PROCESS item leaves that judgement to the
   pull session.

## Fix

Add a terminal-status guard at the head of `_cmd_decide`, mirroring the
peer verbs:

```python
def _cmd_decide(args):
    ...
    t = load_card_or_exit(card_dir, title)
    if t.status in TERMINAL_STATUSES:
        print(
            f"ERROR: {title}: status is {t.status!r} (terminal); "
            f"`goc decide` records a *pending* decision — terminal cards "
            f"cannot be re-decided. To replace a recorded decision, file "
            f"a new card and link it via `goc status <old> superseded --by <new>`.",
            file=sys.stderr,
        )
        sys.exit(2)
    if t.human_gate == "none":
        ...
```

The order matters: a terminal card with `human_gate: decision` should
surface the terminal violation (the deeper issue), not the
"gate-already-none" framing (which would mask the real problem). The
error message points the user at supersession as the documented forward
path, mirroring the routing pointer enforced by
`superseded-status-without-by-leaves-no-forward-routing-pointer`.

The fix does NOT depend on the sibling `goc done` card landing first;
this guard makes the closed-card-with-raised-gate state unreachable from
`goc decide` regardless of how the card got into that state. The two
cards are siblings, not a sequence.
