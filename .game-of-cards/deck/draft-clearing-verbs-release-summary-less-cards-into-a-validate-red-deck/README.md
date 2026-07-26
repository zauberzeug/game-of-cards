---
title: draft-clearing-verbs-release-summary-less-cards-into-a-validate-red-deck
summary: "goc publish, goc status active, and goc done clear the draft flag without checking the summary field, but validate now errors on any non-draft card missing a summary. A first-party verb sequence (goc new without --summary, author DoD/body, publish or claim) exits 0 while leaving the deck failing its own validator, which blocks the next commit in repos using the shipped pre-commit hook."
status: open
stage: null
contribution: medium
created: "2026-07-23T13:24:57Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, unverified]
definition_of_done: |
  - [ ] TDD: reproduce.py demonstrates the chosen contract — either draft-clearing verbs refuse/warn on a missing summary, or the release path guarantees a summary exists before the deck can go validate-red
  - [ ] TDD: regression test covers all three draft-clear paths (publish, status active, done) against the summary requirement
  - [ ] MECHANICAL: the decision below is recorded and the losing options noted in log.md
  - [ ] PROCESS: goc validate green on this repo's deck after the fix
---

# draft-clearing-verbs-release-summary-less-cards-into-a-validate-red-deck

## Hypothesis (unverified — parked by an audit round without reproduce.py budget)

`goc/engine.py` validate (added 2026-07-23 by
`goc-new-scaffolds-no-summary-field-so-fresh-cards-pass-validate-without-one`,
commit `738db00a`) errors with `summary: missing — required on published
cards` on any non-draft card. But the verbs that *make* a card non-draft
never check the field:

- `_cmd_publish` (`goc/engine.py`, `_cmd_publish` around line 5347) gates
  only on `is_placeholder_scaffold(t)` — real DoD + body, no summary check.
- Its own docstring notes `goc status active` and `goc done` perform the
  same implicit draft-clear; both are equally ungated.

So the first-party sequence `goc new t` (no `--summary`) → author DoD/body →
`goc publish t` exits 0 and prints success, and the deck is now validate-red.
In consuming repos the shipped pre-commit hook (`goc/install.py`,
`PRE_COMMIT_HOOK`) runs `goc validate`, so the very next human commit is
blocked by a state a goc verb just produced without complaint.

## Falsification recipe

In a fresh scratch repo with a scaffolded deck: `goc new t`; replace the
placeholder DoD and body; `goc publish t` (expect exit 0); `goc validate`
(defect confirmed if exit 1 with the summary error). Repeat with
`goc status t2 active` as the draft-clearing verb. The hunter that surfaced
this reported both paths reproduce; this card is tagged unverified until a
committed reproduce.py shows it.

## Why it matters

Verbs producing states the validator rejects is the inverse of the
already-filed "validate demands states no verb can produce" family. The
observable symptom is an autonomous or human filer following only
first-party verbs and ending with a red deck plus blocked commits.

## Decision required

Which contract should hold?

1. **Gate the draft-clear**: `publish` / `status active` / `done` refuse
   (or interactively prompt) when `summary` is empty, mirroring the
   placeholder-scaffold gate. Strictest; may annoy quick claim flows.
2. **Warn, don't block**: draft-clearing verbs print a warning and proceed;
   validate stays the enforcement point. Cheapest, but keeps the
   verb-then-red-deck window open.
3. **Auto-stub**: draft-clear copies the H1/first body line into `summary`
   when missing. No red state, but silently authors frontmatter the human
   never wrote.

Option 1 matches the existing placeholder-scaffold precedent in
`_cmd_publish`; option 3 contradicts the repo's aversion to silent
mutations. A human should pick.
