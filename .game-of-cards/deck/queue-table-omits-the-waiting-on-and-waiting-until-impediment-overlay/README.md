---
title: queue-table-omits-the-waiting-on-and-waiting-until-impediment-overlay
summary: "The queue table never prints a card's impediment overlay. `render_table` (engine.py:3021-3117) emits no `waiting_on` / `waiting_until` at any verbosity, so an impeded card renders byte-identically to a pullable one at `goc`, `goc -v`, and `goc -vv` — and `goc --waiting`, the view whose only job is surfacing impeded work, cannot say what any listed card waits on or until when. Two closed siblings already added the overlay to the board (⏳) and to `--json`; the human table is the last renderer that hides it."
status: done
stage: null
contribution: medium
created: "2026-07-27T02:08:48Z"
closed_at: "2026-07-27T02:18:23Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — `goc -v`, `goc -vv`, `goc -v --waiting`, and `goc -vv --waiting` all name the impeding card's `waiting_on` reason and `waiting_until` date
  - [x] TDD: a regression test under `tests/` pins the detail line's three shapes (reason + until, reason only, bare `waiting_until` deferral) and asserts no line is emitted for a non-impeded card
  - [x] TDD: a regression test asserts the line's liveness gate matches the `--waiting` filter — no overlay line on a terminal-status card carrying a stale overlay, and none on a draft scaffold
  - [x] MECHANICAL: the detail line sorts above the `awaiting:` advisory in `render_table`, so the hard impediment reads before the advisory dependency hint
  - [x] PROCESS: `uv run python -m unittest discover -s tests` green; `uv run goc validate` clean
worker: {who: "claude[bot]", where: main}
---

# The queue table omits the impediment overlay at every verbosity

## Location

`goc/engine.py:3021-3117` — `render_table`. The verbose detail block
(`engine.py:3084-3116`) emits `why:`, `summary:`, `awaiting:`, `worker:`,
the four relationship fields, and the DoD checklist. It never reads
`waiting_on`, `waiting_until`, or `waiting_impedes`.

The `--waiting` filter that feeds it: `goc/engine.py:3825-3840`.

## What's broken

The three-axis stuck model (see
[blocked-status-conflates-dependency-external-wait-and-deferral](../blocked-status-conflates-dependency-external-wait-and-deferral/))
makes the stored impediment overlay the *hard* "cannot pull" axis:
`card_is_ready` drops any card for which `waiting_impedes` is true, so an
impeded card is silently absent from `goc --ready`, from `Skill(next-card)`,
and from `Skill(pull-card)`'s selection.

Every other surface says so. `render_board` marks it `⏳`
(`engine.py:3283`). `render_json` carries `waiting_on` / `waiting_until`
(and `SLIM_JSON_KEYS` carries them too, `engine.py:3120-3132`). The
session-start hook names the impeded cards by title.

`render_table` — the default view, and the one `Skill(scan-deck)` tells
readers to use (`goc -v` is its "RECOMMENDED DEFAULT") — prints nothing.
The verbose block's neighbours show every other per-card field:

```python
blockers, _ = dependency_advisory(t, by_title, queue_only=True)
if blockers:
    out_lines.append(f"    awaiting: {', '.join(blockers)} (you may start)")
w = t.worker
if w:
    ...
    out_lines.append(f"    {worker_str}")
```

The one line that *is* printed reads `awaiting: <prereq> (you may start)`
— the **advisory** dependency axis, whose parenthetical explicitly says
the card is pullable. So the only "waiting"-shaped text in the verbose
table belongs to the other axis and asserts the opposite of what an
impeded card's state is.

The sharpest consequence is `goc --waiting`, whose entire purpose is
surfacing impeded work:

> `--waiting` — Filter to cards with an active impediment overlay (a
> `waiting_on` reason or an unelapsed `waiting_until`).
> — `goc/engine.py:3476-3478`

It selects the right cards and then renders them through `render_table`,
so the view answers *which* cards are impeded and nothing about *what
by* or *until when* — the two facts a human needs to act. Reading the
reason today requires `goc show <title>` per card, or `goc --json`.

This is the same renderer/predicate divergence two closed siblings
already fixed one surface at a time:

- [board-omits-marker-for-cards-with-active-waiting-overlay](../board-omits-marker-for-cards-with-active-waiting-overlay/)
  — added the board `⏳`.
- [goc-json-omits-the-waiting-on-and-waiting-until-impediment-fields](../goc-json-omits-the-waiting-on-and-waiting-until-impediment-fields/)
  — added the JSON fields; [goc-status-json-slim-omits-waiting-until](../goc-status-json-slim-omits-waiting-until/)
  finished the slim record.

The table is the last renderer left, and it is the one humans read.

## Empirical evidence

`uv run python .game-of-cards/deck/queue-table-omits-the-waiting-on-and-waiting-until-impediment-overlay/reproduce.py`:

```
=== waiting_impedes (the predicate --ready / --waiting / the board use) ===
  impeded-card           impedes=True
  plain-pullable-card    impedes=False

=== render_board OPEN column ===
  impeded-card [h] ⏳
  plain-pullable-card [h]

=== render_json ===
  impeded-card           waiting_on='external' waiting_until='2099-01-01'
  plain-pullable-card    waiting_on=None waiting_until=None

=== render_table ===
  --- goc -vv --- overlay named: False
      TITLE                STATUS  STAGE  CONTR.  VALUE  GATE  ...
      impeded-card         open    -      high      9.0  none  ...
          summary: Blocked on upstream
          - [ ] TDD: a criterion
      plain-pullable-card  open    -      high      9.0  none  ...
          summary: Ready to pull
          - [ ] TDD: a criterion
  --- goc -vv --waiting --- overlay named: False
      TITLE         STATUS  STAGE  CONTR.  VALUE  GATE  ...
      impeded-card  open    -      high      9.0  none  ...
          summary: Blocked on upstream
          - [ ] TDD: a criterion

=== verdict ===
DEFECT: the impediment overlay is invisible in 4 detail-line view(s): goc -v, goc -vv, goc -v --waiting, goc -vv --waiting
  the board marks it ⏳ and --json carries the fields, but no table view names the reason or the date
exit=1
```

After the fix the same reproducer exits 0, and this repo's own deck reads:

```
$ uv run goc -v --waiting
blocked-status-conflates-dependency-external-wait-and-deferral  open  ...  none  ...
    summary: EPIC. `status: blocked` conflates distinct situations. …
    waiting_on: deferred
    awaiting: remove-blocked-from-status-enum-and-migrate-existing-cards (you may start)
```

The two axes now read in the right order on the same card: the hard
`waiting_on: deferred` above the advisory `awaiting: … (you may start)`.

## Why it matters

This repo's own deck reproduces the failure live. Its three
`status: open ∧ human_gate: none` cards are *all* impeded — one on an
upstream issue, two deferred — so `goc --ready` returns zero. But
`goc --status open --human-gate none` renders three rows that look
pullable, with no signal anywhere in the table that they are not:

```
openclaw-subagent-plugin-tools-alsoallow-ignored                open  medium  3.0  none  bug,infra          4/6
blocked-status-conflates-dependency-external-wait-and-deferral  open  medium  3.0  none  epic,api-contract  4/5
remove-blocked-from-status-enum-and-migrate-existing-cards      open  medium  3.0  none  epic,api-contract  2/4
```

A reader has to run a second command (`goc --waiting`) to discover that
the queue is empty, and a third (`goc show` per card) to learn why. The
gap costs more than an extra keystroke: the same predicate divergence
between "looks pullable in a listing" and "`card_is_ready` says no" is
what makes
[pull-card-workflow-launches-agent-sessions-when-the-ready-queue-is-empty](../pull-card-workflow-launches-agent-sessions-when-the-ready-queue-is-empty/)
burn whole agent sessions on an empty queue.

## Fix (applied)

`render_table`'s `verbose >= 1` block emits an overlay detail line above
the `awaiting:` advisory — hard signal above advisory:

```python
overlay = format_waiting_overlay(t)
if overlay:
    out_lines.append(f"    {overlay}")
```

Three shapes, echoing the stored fields (the idiom `goc wait` and
`validate_waiting_overlay` already print):

```
    waiting_on: external (until 2026-12-01)
    waiting_on: external
    waiting_until: 2026-12-01
```

A parseable date renders through `_format_waiting_until_for_message`
(`engine.py:1165`) so a datetime overlay is not flattened to a bare
date — the failure
[waiting-overdue-warning-renders-datetime-as-date-and-floors-elapsed-to-days](../waiting-overdue-warning-renders-datetime-as-date-and-floors-elapsed-to-days/)
fixed for the validator. An *unparseable* one (which `waiting_impedes`
still treats as impeding) is echoed verbatim and labelled
`… — malformed` rather than run through `_date_part`'s 10-character
slice, which would present `2026-05-20xx` as the clean date
`2026-05-20` — the truncation
[waiting-impedes-truncates-malformed-waiting-until-to-a-valid-prefix-date](../waiting-impedes-truncates-malformed-waiting-until-to-a-valid-prefix-date/)
removed from the read guard.

### The liveness gate is shared, not re-inlined

The gate this line needs — `status not in TERMINAL_STATUSES`, not a
draft, `waiting_impedes` — is the live variant that
[waiting-impedes-callers-reimplement-the-terminal-status-liveness-gate-and-drift](../waiting-impedes-callers-reimplement-the-terminal-status-liveness-gate-and-drift/)
documents as re-inlined at ~5 sites in three phrasings, and predicts:
"the next read surface that consults `waiting_impedes` will face the
same choice and can drift the same way." Rather than become that sixth
copy, this card adds `live_impeded(card)` next to `waiting_impedes` and
routes **both** the new table line and the `--waiting` filter — which
had the identical expression inlined verbatim — through it. Net copy
count goes down, not up.

That is a partial landing of the meta-fix's live variant. Still open
there: the board's `card_cell` (whose `live` / `is_draft` locals also
feed the `✎` marker, so it is not a drop-in), `card_is_workable_for_scheduler`,
and the stricter open-only variant used by `card_is_ready` and the
leverage line. The helper-shape decision that card is gated on is
untouched — `live_impeded` can be renamed into whatever
`active_impediment(card, *, queue_only=…)` shape gets picked.

### Scope boundary

The terse verbose-0 table (`goc`, `goc --waiting`) stays one row per
card. It already carries no detail line for `summary`, `awaiting`, or
`worker`, and `Skill(scan-deck)` documents it as "titles + contribution
only — use sparingly", steering readers to `-v`. Adding a WAITING column
that is null on nearly every card, or a title-cell marker, is a
presentation question that belongs with the open
[board-marks-pullable-and-impeded-cards-with-the-same-hourglass-glyph](../board-marks-pullable-and-impeded-cards-with-the-same-hourglass-glyph/)
— which is deciding exactly how the two "not ready" axes should be
distinguished glyphically. `reproduce.py` therefore scopes its pass/fail
to the detail-line levels and prints the terse rows for context only.

### Adjacent nit, not filed

The `verbose >= 2` relationship dump one line below
(`engine.py:3111`) renders through `f"{list(v)}"`, so a valid card prints
`advanced_by: ['gamma-card']` — a Python list repr in operator-facing
output, where every neighbouring multi-value line uses `", ".join`. That
same line is already catalogued as an unguarded consumer in
[bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes](../bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes/)
(whose DoD names "the `render_table` verbose `-vv` raw-dump loop"), so
the formatting is left to that card rather than filed separately.

## Artifacts

- `reproduce.py`
