---
title: verdict-coherence-check-mistakes-the-disproved-status-name-for-a-negative-verdict
summary: "DECISION_CONTRADICTS_VERDICT fired when a summary merely named the status disproved and the decision used everyday words like 'no longer' — five cards in the 2026-10-22 decision round, whose decisions were reworded only to quiet it. Both token lists now skip a match that only names something (a status in a list or after a status cue, a code span, a card slug); 'instead of' is no longer a re-scope marker and 'no longer' counts only before a verdict word. Genuine verdict reversals still warn."
status: done
stage: null
contribution: medium
created: "2026-10-22T06:03:27Z"
closed_at: "2026-10-31T04:36:03Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — a summary that only names the status (`flips to \`disproved\``, "or the card is disproved") next to a decision containing "no longer" or "instead of" raises no DECISION_CONTRADICTS_VERDICT, while a genuine "REFUTED"/"do not pursue" summary over a reversing decision still does
  - [x] TDD: a unittest pins both directions (planted false positive stays silent, planted true positive still warns)
  - [x] MECHANICAL: drop the `unverified` tag once reproduce.py lands
  - [x] PROCESS: `uv run goc validate` passes and the suite is green
worker: {who: "claude[bot]", where: main}
---

# The verdict-coherence check mistakes the disproved status name for a negative verdict

## Status

Fixed. Both token lists are now read through `negative_verdict` / `rescope_marker` in `goc/engine.py`, which skip a match that only *names* something. `instead of` is no longer a re-scope marker, and `no longer` counts only before a verdict word. `reproduce.py` exits 0; against the pre-fix engine it exits 1, with all three planted false positives warning.

## Location

- `goc/engine.py` — `RESCOPE_MARKERS_RE`, `NEGATIVE_VERDICT_RE`, and the new `_names_rather_than_asserts` / `negative_verdict` / `rescope_marker` next to them.
- `goc/engine.py` — `validate_decision_verdict_coherence` (the advisory), `_rescope_reconciliation_notice` (its "still asserts a negative verdict" flag) and `_cmd_decide` (the decide-time reminder trigger) all read through the helpers.

## What was broken

The two token lists were built for a narrow situation: a "REFUTED" summary left standing over a decision that reverses it. But `disproved` is also a status name that ordinary summaries and DoD lines mention ("…or the run disproves the hypothesis and the card flips to `disproved`"). And "no longer" and "instead of" are everyday words in decisions that reverse nothing. Both lists matched on those ordinary uses, so the advisory fired on cards whose verdict was perfectly coherent. The decide-time reminder shared the marker list, so it printed its ⚠ re-scope notice on the same everyday decisions.

## Empirical evidence

- **The 2026-10-22 round, replayed.** Re-running the pre-fix regexes over each `decide:` commit of that day finds exactly five cards that would warn. They are `terminal-status-guard-missing-across-mutation-verbs` (decided in 38e4cdb0) and its four children (992db59f, 0f399110, 8ac0d16d, 81742f82). Every one pairs a summary listing `` (`done`/`disproved`/`superseded`) `` with a decision saying "_cmd_decide no longer refuses terminal cards". Commit 413a2026 then rewrote that to "has stopped refusing" only to quiet the check. All five are closed now, which is why today's `goc validate` no longer shows them.
- **Deck-wide token audit (823 cards, all statuses).** `NEGATIVE_VERDICT_RE` hit 43 summary/banner spans. 37 only name a status (status lists, code spans, "status disproved", "mark this disproved", "a disproved or superseded card"), and the fix skips all 37. The 6 it keeps are the five real verdicts, all on `disproved` cards ("DISPROVED: …", "Verdict: DISPROVED (2026-07-11)", "Disproved 2026-06-24."), plus one prose "now-refuted claim" on a done card. On the decision side, all 8 `instead of` / `no longer` hits were everyday usage. 12 of 19 `supersed*` / `rescope` hits were field names, slugs or status mentions, and the fix skips them. The genuine "Supersede by …", "Superseded by …" and "was wrong" decisions still count.
- **`reproduce.py`** drives the real CLI on a scratch deck (`goc new` → `goc decide` → `goc validate`) with five cards: three false positives that each isolate one side of the fix, and two true positives. Pre-fix: the 3 false positives warn. Post-fix: they are silent, and both true positives still warn.

## Why it matters

An advisory that cries wolf trains deciders to reword decisions until it goes quiet. That hides the real self-contradictions it exists for, and it makes `goc decide` look unreliable in exactly the bulk decision rounds the deck now needs.

## Fix

Tighten the pattern, not the surfaces:

- **Marker list.** `instead of` is dropped. `no longer` counts only before a verdict word (`holds`, `stands`, `true`, `valid`, `correct`, `refuted`, `disproved`, `disproven`, `unviable`). So "the refutation no longer holds" and "no longer refuted" still reverse, and "no longer refuses terminal cards" does not.
- **Names are not assertions** (`_names_rather_than_asserts`), on two tiers:
  - *Code or identifier, for any token:* the token sits inside an inline code span, is joined by an underscore (`superseded_by`), or is one part of a hyphenated run of three or more parts (a card slug).
  - *Status used as a name, for a token equal to a schema status value:* the token is in a list with another status (`done/disproved/superseded`, "disproved or superseded"), follows a status cue ("status", "goc status <t>", "to", "as", "mark this"), or qualifies a card or a status noun ("the card is disproved", "disproved cards", "the superseded gate", "the DISPROVED column").
- Status values come from `STATUS_VALUES`, which derives from the schema, so no status literal is restated.
- A verdict that happens to use the status word matches none of these and still counts. Examples: "DISPROVED: …", "Verdict: DISPROVED", "The hypothesis was disproved by the benchmark".
- `Skill(decide-card)` reference.md § Re-scope reconciliation lists the narrowed markers. It also says that status names and everyday words never need rewording.

Known residue: some status-name uses have no list, cue or noun next to them ("the gate keeps blocking superseded"), so they still read as markers. None of them fires the advisory unless the same card's summary also states a real negative verdict.

Related: [goc-decide-leaves-stale-verdict-content-when-recording-a-rescope](../goc-decide-leaves-stale-verdict-content-when-recording-a-rescope/) (introduced the check), [decision-verdict-coherence-check-skips-rubric-derived-decision-headings](../decision-verdict-coherence-check-skips-rubric-derived-decision-headings/).
