---
title: goc-new-scaffolds-no-summary-field-so-fresh-cards-pass-validate-without-one
summary: "`goc new` scaffolds every schema field except `summary` and has no `--summary` flag, and `goc validate` enforces summary quality only when the key is present — so a card authored and published without one reaches the queues validate-clean, with a blank line in every triage view. Only `goc quality-pass` (run during refine passes) detects the gap; five cards filed 2026-07-17..23 landed summary-less and were backfilled by the 2026-07-23 refine pass. Fix: extend the blank-summary validate rule to fire on an absent key for non-draft cards, keeping draft scaffolds exempt."
status: done
stage: null
contribution: medium
created: "2026-07-23T02:45:40Z"
closed_at: "2026-07-23T13:00:43Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — a summary-less card that is published no longer survives `goc validate` clean (or the scaffold itself carries the field)
  - [x] TDD: unittest asserts `goc validate` flags an absent `summary` on a non-draft card with a message of shape `<title>: summary: missing — required on published cards`, and stays silent on a fresh `draft: true` scaffold
  - [x] TDD: unittest confirms the existing present-but-blank rejection (`summary: ""` / whitespace-only) still fires — the absent-key rule extends it, not replaces it
  - [x] MECHANICAL: whichever convenience path lands (`goc new --summary` flag, or none) is reflected in the create-card skill's Step 4 command block, and the choice is recorded in log.md
  - [x] PROCESS: `uv run goc validate` green on the real deck and `uv run python -m unittest discover -s tests` green
worker: {who: "claude[bot]", where: main}
---

# goc new scaffolds no summary field so fresh cards pass validate without one

## Location

- `goc/engine.py` `validate_card` summary rule — now fires on an absent
  `summary` key when the card is not `draft: true`, extending the
  present-but-blank rejection shipped by
  [validate-accepts-whitespace-only-summary-as-non-empty](../validate-accepts-whitespace-only-summary-as-non-empty/).
- `goc/engine.py` `_cmd_new` — gained a `--summary` flag; when passed, the
  scaffold emits the key right after `title`, matching hand-authored
  cards. A blank/whitespace `--summary` is rejected at parse time.
- quality-pass (`(c.summary or "").strip()`) already treated absent and
  blank identically; validate now agrees with it.

## What's broken

The create-card skill's Step 5 makes the summary part of authoring:

> **Summary** — frontmatter `summary:` (≤ 3 sentences, what + why)
> so triage views can scan without opening.

But nothing downstream of the skill enforces it. `goc publish` checks for
a real DoD and body ("releases authored work, it does not author it")
yet says nothing about the summary; `goc validate` only judges summaries
that exist. So an agent that authors DoD and body but skips the summary
line ships a card that is validate-clean, publishable, claimable, and
blank in every `goc -v` / triage row until a refine pass runs
`goc quality-pass` — the only surface that notices.

The two guards also disagree about the same state: validate treats
`summary: ""` as an error but the absent key as fine, while quality-pass
treats both as the same defect.

## Empirical evidence

`uv run python .game-of-cards/deck/goc-new-scaffolds-no-summary-field-so-fresh-cards-pass-validate-without-one/reproduce.py`
(post-fix):

```
scaffold has summary key: False
goc publish exit: 0
draft flag after publish: (removed)
goc validate exit: 1
[OK] defect no longer fires: the scaffold carries a summary field or
validate flags its absence on a published card.
```

On the real deck the leak is not hypothetical: the 2026-07-23 refine pass
backfilled five summary-less cards, all created 2026-07-17..23 — long
after the "pre-2026-05-01 legacy cards" era the refine skill attributes
missing summaries to — including two filed and closed by the autonomous
loop itself.

## Why it matters

The summary is the field triage runs on: `goc -v`, the board hover
surfaces, and every refine/audit sweep read it instead of opening 150
bodies. Each summary-less card silently degrades those views, and the
deck currently pays an unbounded backfill tax: every refine pass
re-litigates summaries that filing should have required. The whitespace
card already established the contract that a published card's summary
must be non-empty; the absent-key case is the same defect one door over.

## Fix (applied)

`validate_card` gained an else-branch on the summary rule: absent key +
non-draft card → `<title>: summary: missing — required on published
cards`. Draft scaffolds stay exempt (unauthored by definition — flagging
them would make every fresh `goc new` red). The real deck was already
conformant after the 2026-07-23 backfill, so the rule landed green.

The convenience path also landed: `goc new --summary "<what + why>"`
writes the key at scaffold time (emitted right after `title`), and the
create-card skill's Step 4 command block now shows the flag. Regression
coverage in `tests/test_validate_summary_missing.py` (absent-key
rejection, draft exemption, blank-summary rule unchanged, `--summary`
placement); `tests/test_validate_summary_whitespace.py` untouched and
green.

## Cross-links

- [validate-accepts-whitespace-only-summary-as-non-empty](../validate-accepts-whitespace-only-summary-as-non-empty/)
  (done) — established the non-empty contract this card extends to the
  absent-key case.
- Surfaced by the 2026-07-23 `Skill(refine-deck)` pass ("Missing
  summaries" category, five backfills in the same commit).
