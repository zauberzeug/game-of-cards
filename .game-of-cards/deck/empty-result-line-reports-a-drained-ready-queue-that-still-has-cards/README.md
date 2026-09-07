---
title: empty-result-line-reports-a-drained-ready-queue-that-still-has-cards
summary: "`render_empty_query_line` treats `--ready` as replacing the status conjunct instead of adding to it, so `goc --ready --status done` prints \"No cards match (ready: status open, gate none, no active impediment).\" — asserting the ready predicate matched nothing while plain `goc --ready` on the same deck lists a card. The `--status` / `--done` filter that actually emptied the result is never named, contradicting the function's own docstring promise to name the filters in effect."
status: done
stage: null
contribution: medium
created: "2026-08-04T05:52:37Z"
closed_at: "2026-08-04T06:01:10Z"
human_gate: none
advances:
  - query-flag-validation-is-opt-in-per-flag-and-new-flags-keep-missing-it
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — all three `--ready` + explicit-status
        variants name the status filter in effect
  - [x] TDD: a regression test pins `--ready --status done` naming both
        conjuncts, and pins that plain `--ready` does NOT gain a redundant
        second `status:` clause from the auto-resolved default
  - [x] TDD: existing pins in `tests/test_empty_query_result_line.py` stay
        green (`--json` still `[]`, `--board` still header-only, non-empty
        tables unchanged)
  - [x] MECHANICAL: plugin mirrors re-synced so the four `engine.py` copies
        stay byte-identical
  - [x] PROCESS: guard sensitivity confirmed — reverting the fix turns the new
        test red, recorded in `log.md`
worker: {who: "claude[bot]", where: main}
---

# empty-result-line-reports-a-drained-ready-queue-that-still-has-cards

The zero-match queue message names `--ready` *instead of* the `--status`
filter that actually emptied the result, so it asserts the ready queue is
drained on a deck where the ready queue still has cards.

## Location

`goc/engine.py` — `render_empty_query_line`, the `--ready` branch of the
predicate enumeration (introduced by commit `8e565381`, which closed
[empty-queue-view-prints-nothing-instead-of-saying-no-cards-match](../empty-queue-view-prints-nothing-instead-of-saying-no-cards-match/)).
Mirrored byte-for-byte in `claude-plugin/goc/engine.py`,
`codex-plugin/goc/engine.py`, `openclaw-plugin/goc/engine.py`.

## What's broken

`_cmd_default` resolves the status filter and records whether the user asked
for it explicitly:

```python
status_filter_explicit = bool(args.done_flag or args.status_flag is not None)
```

It then passes `--ready` and `status` to `filter_cards` as **two independent
conjuncts** — both are applied:

```python
if status is not None and status != "all":
    out = [t for t in out if t.status == status]
...
if ready:
    out = [t for t in out if card_is_ready(t, lookup)]
```

But the message builder treats them as mutually exclusive, taking `--ready`
as a *replacement* for the status clause:

```python
if getattr(args, "ready", False):
    parts.append("ready: status open, gate none, no active impediment")
else:
    parts.append(f"status: {status}")
```

So whenever `--ready` is combined with an explicit `--status` / `--done`, the
one filter that emptied the result is the one filter the message omits. The
function's own docstring states the contract it breaks:

> State that a queue query matched nothing, naming the filters in effect.

and the commit that added it described the enumeration the same way — "builds
a sentence naming every filter in effect".

The result is not merely incomplete, it is **false**. `card_is_ready` requires
`status == "open"`, so `--ready --status done` is an unsatisfiable conjunction;
the printed sentence nonetheless asserts that the ready predicate — "status
open, gate none, no active impediment" — matched nothing, while plain
`goc --ready` on the identical deck lists a card.

## Empirical evidence

`uv run python .game-of-cards/deck/empty-result-line-reports-a-drained-ready-queue-that-still-has-cards/reproduce.py`
— exit 1 before the fix, exit 0 after:

```
the ready predicate on this deck

  `goc --ready`  -> 1 row(s) matched
                    pullable-card

what each zero-match variant says          BEFORE                     AFTER
  `goc --ready --status done`              (ready: …)                 (ready: …; status: done)
  `goc --ready --done`                     (ready: …)                 (ready: …; status: done)
  `goc --ready --status active`            (ready: …)                 (ready: …; status: active)

BEFORE: DEFECT — 3 of 3 variants claim the ready predicate matched
        nothing while it matches 1 card(s), and none of them names
        the --status filter that emptied it.
AFTER:  OK — all 3 variants name the status filter in effect.
```

Live on this repo's deck, where the ready queue *is* genuinely drained:

```
$ uv run goc --ready
No cards match (ready: status open, gate none, no active impediment).

$ uv run goc --ready --status done
No cards match (ready: status open, gate none, no active impediment; status: done).
```

The correct combinations are unaffected: `--ready --status open` and
`--ready --status all` both still list `pullable-card`, because neither
contradicts `card_is_ready`.

## Why it matters

`goc --ready` is the queue evidence `Skill(pull-card)` and `Skill(next-card)`
inject as their only view of what is pullable, and "the ready queue is
drained" is the specific signal that routes a session away from working a card
and into `Skill(audit-deck)`. A message that reports a drained ready queue
when cards are pullable inverts that routing decision.

Reachability: no shipped skill or workflow combines the flags. `--ready`
appears on 13 lines under `goc/templates/`, but only three are invocations
(the executed `!` preamble blocks in `pull-card/SKILL.md` and
`next-card/SKILL.md`, plus the documented recipe in `scan-deck/SKILL.md`);
each passes `--ready` alone or with `-v` / `--worker`, never with `--status`
or `--done`. The reachable path is a hand-typed or hand-scripted query, which
is exactly the audience the enumeration was added for: a reader who cannot
tell "matched nothing" from "did not run" reaches for extra flags to narrow
the query, and the narrowing flag is the one silently dropped from the
explanation.

Existing coverage misses it because
`tests/test_empty_query_result_line.py::test_every_filter_is_named` exercises
the multi-filter enumeration with `ready=False`, and
`test_drained_ready_queue_says_so` exercises `ready=True` with no explicit
status — so the two arms are each pinned alone and never in combination.

## Fix (applied)

`render_empty_query_line` now treats `--ready` as an additional conjunct
rather than a replacement: it keeps the ready sentence and *also* names the
status filter when the user passed one explicitly. Explicitness is recomputed
locally from `args` — mirroring `_cmd_default`'s own `status_filter_explicit`
— so the signature stays `(args, status)` like every other filter the function
reads straight off `args`:

```python
status_explicit = bool(
    getattr(args, "done_flag", False)
    or getattr(args, "status_flag", None) is not None
)
if getattr(args, "ready", False):
    parts.append("ready: status open, gate none, no active impediment")
    if status_explicit:
        parts.append(f"status: {status}")
else:
    parts.append(f"status: {status}")
```

Gating on `status_explicit` rather than always appending is what keeps plain
`goc --ready` unchanged: there, `status` is the auto-resolved `"open"` default
that the ready sentence already covers, and naming it twice would be noise
rather than information. Both directions are pinned — see the sensitivity
sweep in `log.md`.

`python scripts/sync_plugin_assets.py` re-synced the three mirror copies
(`claude-plugin/`, `codex-plugin/`, `openclaw-plugin/`).

### Deliberately not done

Rejecting the contradictory pair at parse time (the way `--done` + `--status`
is rejected) was considered and dropped: `--ready --status open` and
`--ready --status all` are legal, satisfiable queries, so a blanket conflict
guard would break working invocations. The defect was never that the query is
accepted — it is that the explanation omitted an applied filter, which is
exactly what the docstring already promised not to do.

## Related

- [empty-queue-view-prints-nothing-instead-of-saying-no-cards-match](../empty-queue-view-prints-nothing-instead-of-saying-no-cards-match/)
  — added the message; this is a defect in that addition, not a rollback of it.
- [query-flag-validation-is-opt-in-per-flag-and-new-flags-keep-missing-it](../query-flag-validation-is-opt-in-per-flag-and-new-flags-keep-missing-it/)
  — wired as `advances`. That root's open decision asks which mechanism
  replaces per-flag opt-in validation, and the closure above supplied the
  constraint that the output-side statement is the only signal available for
  `--worker`. Making that statement *correct* is a precondition for it
  carrying any of the contract's weight.
- [extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate](../extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate/)
  — a **separate** defect in the same sentence, filed as evidence there
  rather than duplicated here: the ready clause restates `card_is_ready`'s
  conjuncts in prose and has already drifted from it (it omits the
  `card_is_draft` exclusion), making it a fifth uncoupled copy of the
  readiness predicate that card already catalogues — and the first prose
  one, which constrains that card's open decision toward an extraction
  that exposes named rejection axes.
