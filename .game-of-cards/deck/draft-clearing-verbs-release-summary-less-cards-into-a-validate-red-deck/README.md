---
title: draft-clearing-verbs-release-summary-less-cards-into-a-validate-red-deck
summary: "goc publish, goc status active, and goc done clear the draft flag without checking the summary field, but validate now errors on any non-draft card missing a summary. A first-party verb sequence (goc new without --summary, author DoD/body, publish or claim) exits 0 while leaving the deck failing its own validator, which blocks the next commit in repos using the shipped pre-commit hook."
status: done
stage: null
contribution: medium
created: "2026-07-23T13:24:57Z"
closed_at: "2026-10-06T05:26:02Z"
human_gate: none
advances:
  - goc-verbs-emit-frontmatter-their-own-validator-rejects
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py demonstrates the chosen contract — either draft-clearing verbs refuse/warn on a missing summary, or the release path guarantees a summary exists before the deck can go validate-red
  - [x] TDD: regression test covers all three draft-clear paths (publish, status active, done) against the summary requirement
  - [x] MECHANICAL: the decision below is recorded and the losing options noted in log.md
  - [x] PROCESS: goc validate green on this repo's deck after the fix
worker: {who: claude-code, where: zoe-host}
---

# draft-clearing-verbs-release-summary-less-cards-into-a-validate-red-deck

## What was broken

`goc/engine.py` validate (added 2026-07-23 by
`goc-new-scaffolds-no-summary-field-so-fresh-cards-pass-validate-without-one`,
commit `738db00a`) errors with `summary: missing — required on published
cards` on any non-draft card. But the verbs that *make* a card non-draft
never check the field:

- `_cmd_publish` gated only on `is_placeholder_scaffold(t)` — real DoD +
  body, no summary check.
- `goc status <t> active`, `goc done` and `goc done --bundle` cleared the
  draft flag the same way (`remove_frontmatter_field(text, "draft")`), all
  equally ungated.

So the first-party sequence `goc new t` (no `--summary`) → author DoD/body →
`goc publish t` exits 0 and prints success, and the deck is now validate-red.
In consuming repos the shipped pre-commit hook (`goc/install.py`,
`PRE_COMMIT_HOOK`) runs `goc validate`, so the very next human commit is
blocked by a state a goc verb just produced without complaint.

## Empirical evidence

`reproduce.py` builds a scratch deck per verb, authors a card without
`summary`, and runs the verb; then the same verb on a card with a summary.
On `main` (f510cbe1) every verb released the summary-less draft:

```
FAIL publish        without summary: RELEASED | with summary: released, validate green
FAIL status active  without summary: RELEASED | with summary: released, validate green
FAIL done           without summary: RELEASED | with summary: released, validate green
defect present: a draft-clearing verb ignores the summary
```

With the fix:

```
OK   publish        without summary: refused | with summary: released, validate green
OK   status active  without summary: refused | with summary: released, validate green
OK   done           without summary: refused | with summary: released, validate green
contract holds
```

In a consuming repo (zauberzeug's Zoe workspace) this was the single most
frequent nightly red: `goc validate` failed on 14 of 16 nights between
2026-09-21 and 2026-10-06, 12 summary-less cards on 2026-10-06 alone, almost
all released through `new` → `status active` → `done`.

## Why it matters

Verbs producing states the validator rejects is the inverse of the
already-filed "validate demands states no verb can produce" family. The
observable symptom is an autonomous or human filer following only
first-party verbs and ending with a red deck plus blocked commits.

## Fix

One rule, two doors: `summary_problem(frontmatter)` (next to `card_is_draft`)
is the single definition behind `validate`'s summary errors — same messages
as before — and behind `summary_release_error(card)`, which the four
draft-clearing call sites consult before they mutate anything: `_cmd_publish`
(after the placeholder gate), `_cmd_status` for `active`, `_cmd_done`, and
`_cmd_done_bundle` in its planning loop (so a bundle with one bad card closes
none). The refusal exits 2 and names the problem.

Scope: only the draft → published transition is gated. A card that was never
a draft (written by hand) is not made unclaimable; `validate` stays its net.
Regression test: `tests/test_draft_clearing_verbs_require_summary.py`
(refusal per verb with the card byte-identical, release with a summary plus
green validate, the four invalid forms, the bundle, and the scope boundary).

## Decision

*Resolved 2026-10-06T05:22:31Z:* Option 1: publish, status active and done (incl. --bundle) refuse to release a draft whose summary fails the published-card rule; validate and the verbs share one summary_problem() rule

*Reasoning:* Rodja 2026-10-06 (zauberzeug Zoe workspace card goc-publish-laesst-eine-karte-ohne-summary-in-den-stapel); matches the placeholder-scaffold gate already in publish, and option 3 would silently author frontmatter nobody wrote

