---
title: goc-wait-with-a-past-until-date-leaves-the-card-in-the-queue
summary: "`goc wait <t> --until <date already past>` wrote the overlay, printed a success line and auto-committed, but the engine's own `waiting_impedes` reads an elapsed `waiting_until` as non-impeding — so the card stayed in `--ready`, was absent from `--waiting`, and the next autonomous pull claimed it. The common form was a bare `--until <today>`: a `YYYY-MM-DD` value resolves to midnight UTC, so it is elapsed at every moment of the day it names. It now refuses an `--until` the read guard says would not impede, asked of `waiting_impedes` on the card as it would be written — exit 2, `ERROR: <title>: --until '<value>' has already elapsed …`, nothing written — through the parent epic's shared `_refuse_invalid_input` helper."
status: done
stage: null
contribution: medium
created: "2026-08-26T04:40:53Z"
closed_at: "2026-10-29T04:54:12Z"
human_gate: none
advances:
  - mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [x] PROCESS: the shared validation-failure shape decided on [mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success](../mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success/) is applied here rather than re-derived — strict-refuse (exit 2, no mutation), exit-0-with-stderr-WARNING, or an honest no-op line. Record which, and why, in this card's `log.md`. — strict-refuse through the shared `_refuse_invalid_input`, as the parent decided on 2026-10-22 for all nine children; the why is in log.md's closure entry.
  - [x] TDD: `reproduce.py` exits zero — neither `--until <today>` nor `--until <long-past date>` produces exit 0 with a bare success line while the card stays in `--ready` and out of `--waiting`. — both get exit 2, `ERROR:` naming `--until` and the README untouched, beside a future-date control that still hides its card; the same script exits 1 against the pre-fix engine. Rewritten to the 0/1/2 contract: as filed, a broken harness exited 1 (read as the defect) and any non-zero exit read as fixed.
  - [x] MECHANICAL: `_cmd_wait` (`goc/engine.py:6439`) decides the elapsed case from the engine's own read guard rather than a second copy of the comparison — reuse `_waiting_until_instant` + `_now_instant` (or `waiting_impedes` on the post-write card), so this check cannot drift from `waiting_impedes` the way the hook readers repeatedly did. — `waiting_impedes` on a `Card` built from the frontmatter about to be written; no copy of `until_dt > now`.
  - [x] MECHANICAL: scoped to the `--until` value supplied in THIS invocation. Whether a bare `--reason` should refresh or clear a **pre-existing** stale `waiting_until` is a different question, owned by [goc-wait-does-not-clear-stale-elapsed-waiting-until](../goc-wait-does-not-clear-stale-elapsed-waiting-until/) — do not resolve it here. — the check runs only when this call passes `--until`; `test_judges_only_the_until_this_call_passes` pins that a bare `--reason` over a stale elapsed date is not refused by it.
  - [x] TDD: regression test in `tests/` covers `--until <today>` (bare date, elapsed at midnight UTC), `--until <long-past date>`, `--until <future date>` (unchanged — still impedes, no new output), and the datetime shape `YYYY-MM-DDTHH:MM:SSZ` on both sides of `now`. — `WaitCliTest` in `tests/test_mutation_verbs_refuse_invalid_input.py`: today, 2020-01-01, a datetime an hour past and an elapsed `--until` over a live wait are refused (all four fail against the pre-fix engine); a date 30 days out and a datetime an hour out keep the exact pre-fix success line and hide the card.
  - [x] MECHANICAL: `Skill(advance-card)` Step 6 (`goc/templates/skills/advance-card/SKILL.md:139-142`) states what an already-elapsed `--until` does — it currently documents only that `goc validate` reports an elapsed date as `WAITING_OVERDUE`, which is the state a card drifts into, not the state this verb can create outright. Plugin mirrors synced; `uv run goc validate` clean. — Step 6 now says an elapsed `--until` is refused (exit 2, nothing written) and that a bare date is midnight UTC, so deferring through today takes tomorrow's date; its examples use `<YYYY-MM-DD>`. Mirrors synced, OpenClaw port re-run; `goc validate` exits 0.
worker: {who: "claude[bot]", where: main}
---

# `goc wait --until <past date>` leaves the card in the queue

## Location

- `goc/engine.py:6439` — `_cmd_wait`, the overlay setter.
- `goc/engine.py:6530-6539` — the whole of `--until` validation, and the
  write that follows it:

  ```python
  if new_until is not None and not _is_iso_date(new_until):
      print(
          f"ERROR: --until: {new_until!r} not a valid ISO YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ date",
          file=sys.stderr,
      )
      sys.exit(2)
  if new_reason is not None:
      fm["waiting_on"] = new_reason
  if new_until is not None:
      fm["waiting_until"] = new_until
  ```

- `goc/engine.py:6441-6447` — the success line, which already carries the
  idiom for "what you typed is not what the state means", but only for the
  implied-reason case:

  ```python
  print(
      f"{title}: waiting_on={fm.get('waiting_on')!r} "
      f"waiting_until={fm.get('waiting_until')!r}"
      + (f" (no reason set; implied {effective_reason!r})"
         if fm.get("waiting_on") is None and effective_reason else "")
  )
  ```

- `goc/engine.py:2731-2777` — `waiting_impedes`, the read guard the write
  never consults: `return until_dt > now`.
- `goc/engine.py:1218` — `_waiting_until_instant`: a bare `YYYY-MM-DD`
  becomes **midnight UTC** of that day.

## What was broken

`_cmd_wait` validated two things about `--until`: that it parses as ISO, and
nothing else. It never asked whether the overlay it was about to write actually
impedes. The engine's read guard says it does not:

```python
# Future instant hides; elapsed instant resurfaces the card.
return until_dt > now
```

That elapsed-resurfaces rule is deliberate and documented — a wait that has
*matured* should return its card to the queue. But `goc wait` would just as
happily write a wait that is **born elapsed**, and then report it exactly like
a wait that took effect: a success line naming both fields, exit 0, and an
auto-commit. Nothing in the output distinguished "parked" from "no-op".

The `--until <today>` case is the one an operator hits without doing anything
unusual. `_waiting_until_instant` resolves a bare `YYYY-MM-DD` to midnight UTC,
so `--until 2026-08-26` is already in the past at 00:00:01 on 2026-08-26. The
natural reading of "wait until today" — *don't offer this again during today* —
is the exact opposite of what the value does.

The skill body said only what happens to a date that goes stale on its own
(`goc/templates/skills/advance-card/SKILL.md:139-142`):

> A future `waiting_until` (or a reason with no date) hides the card from
> `--ready` / next-card / pull-card and re-enters it automatically when the
> date passes; an elapsed date is surfaced by `goc validate` as
> `WAITING_OVERDUE`.

It did not say that `goc wait` would *create* one on request and call it a
success — because nobody expected the verb to accept an input it can prove
inert at the moment it writes it.

## Empirical evidence

`uv run python .game-of-cards/deck/goc-wait-with-a-past-until-date-leaves-the-card-in-the-queue/reproduce.py`
against the pre-fix engine (exit 1), abridged — as filed; the script has since
gained a future-date control and the 0/1/2 exit contract, and exits 0 against
the fixed engine:

```
=== goc wait demo-today --reason deferred --until 2026-08-26  (today) ===
exit code: 0
stdout: demo-today: waiting_on='deferred' waiting_until='2026-08-26'
stderr:

--- goc --ready (card should be hidden if the overlay impedes) ---
TITLE       STATUS  CONTR.  VALUE  GATE  TAGS          DOD
----------  ------  ------  -----  ----  ------------  ---
demo-today  open    low       1.0  none  api-contract  0/1

--- goc --waiting (card should be listed if the overlay impedes) ---
No cards match (status: all; waiting: active impediment overlay).

BUG (today): exit 0 and a success line, yet demo-today is still listed by
--ready and absent from --waiting — the overlay impedes nothing.
...
=== diagnosis ===
BUG: 2 of 2 elapsed --until values were accepted silently.
```

`goc validate` then reports the card the operator believes they parked:

```
WARN WAITING_OVERDUE demo-today: waiting_on=deferred waiting_until=2026-08-26 elapsed 4h ago — re-triage or clear
```

So the deck's *own* validator can tell the value is inert seconds after the
verb wrote it — the information is available at write time, it is simply not
consulted there.

## Why it matters

The overlay is the only mechanism that hides a card from an unattended puller.
`card_is_ready` gates on status, draft, gate, and `waiting_impedes`; an
operator who wants a card out of the autonomous queue for exogenous reasons has
`goc wait` and nothing else. When that verb no-ops silently, the failure is
invisible in exactly the direction that costs: the operator moves on believing
the card is parked, and the next `pull-card` pass claims it, works it, and
commits — against the wait they just set.

Every other surface agrees the card is fine. `--ready` lists it, `--waiting`
does not, the board paints no `⏳`, `goc triage` says nothing (the gate is
still `none`). The only signal is a `goc validate` WARN, which nothing on the
pull path reads.

## Fix

Landed 2026-10-29 under the shape the parent
[mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success](../mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success/)
decided for all nine children: **strict-refuse**. When this call passes
`--until`, `_cmd_wait` builds the card as it would be written and asks
`waiting_impedes` whether it impedes. If not, it refuses through the shared
`_refuse_invalid_input` before the write — exit 2, nothing written, no commit:

```
ERROR: demo: --until '2026-10-29' has already elapsed (a bare date is midnight UTC
at the start of that day), so the wait would not hide demo from the queue — pass
a later --until, or --reason alone for an open-ended wait
```

The parenthetical appears only for a bare date, where the midnight-UTC reading
is the trap. A future `--until` is untouched: same success line, same overlay.

The predicate is the read guard itself, not a fourth hand-written copy of
`until_dt > now`. `waiting_impedes`, `validate_waiting_overlay`, the
SessionStart hook and the OpenClaw port have each drifted from that comparison
at least once (see
[session-start-hook-impeded-check-ignores-elapsed-waiting-until](../session-start-hook-impeded-check-ignores-elapsed-waiting-until/)
and
[waiting-impedes-callers-reimplement-the-terminal-status-liveness-gate-and-drift](../waiting-impedes-callers-reimplement-the-terminal-status-liveness-gate-and-drift/)),
so asking `waiting_impedes` keeps the write path from drifting the same way.

`--until`'s help text and `Skill(advance-card)` Step 6 now say an already
elapsed date is refused and that a bare date is midnight UTC; Step 6's
examples use a `<YYYY-MM-DD>` placeholder in place of a literal date, which
had itself gone stale. The regression tests are `WaitCliTest` in
`tests/test_mutation_verbs_refuse_invalid_input.py`.

## Scope boundary

- **Sibling, not this card:**
  [goc-wait-does-not-clear-stale-elapsed-waiting-until](../goc-wait-does-not-clear-stale-elapsed-waiting-until/)
  asks whether a bare `--reason` should refresh or clear a `waiting_until` that
  was *already* on the card. That is a state-reconciliation question with no
  obvious answer. This card is only about the value handed to the verb **in
  this invocation**, which the verb can evaluate before writing it. Fixing one
  does not fix the other, and a fix here must not silently decide that one.
- **Not the read guard.** `waiting_impedes` is correct; the elapsed-resurfaces
  contract stays. Nothing in this card changes when a card leaves the queue —
  only what the write path does when asked to create a wait that is already
  over.
- **Not the terminal-status family.**
  [goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard](../goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard/)
  and its epic
  [terminal-status-guard-missing-across-mutation-verbs](../terminal-status-guard-missing-across-mutation-verbs/)
  guard on the *card's status*; this one guards on the *argument*.

## Decision

*Resolved 2026-10-22T05:20:23Z:* Decided via parent mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success: strict-refuse — goc wait with an --until instant that has already elapsed exits 2 and writes nothing, judged by the engine's own waiting read guard

*Reasoning:* The maintainer decided the parent's shared validation-failure shape (1. Strict-refuse) in a human session on 2026-10-22, which answers exactly this card's question; this card's DoD defers the shape to the parent

