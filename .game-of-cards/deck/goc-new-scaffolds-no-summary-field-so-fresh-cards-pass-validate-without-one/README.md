---
title: goc-new-scaffolds-no-summary-field-so-fresh-cards-pass-validate-without-one
summary: "`goc new` scaffolds every schema field except `summary` and has no `--summary` flag, and `goc validate` enforces summary quality only when the key is present — so a card authored and published without one reaches the queues validate-clean, with a blank line in every triage view. Only `goc quality-pass` (run during refine passes) detects the gap; five cards filed 2026-07-17..23 landed summary-less and were backfilled by the 2026-07-23 refine pass. Fix: extend the blank-summary validate rule to fire on an absent key for non-draft cards, keeping draft scaffolds exempt."
status: open
stage: null
contribution: medium
created: "2026-07-23T02:45:40Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — a summary-less card that is published no longer survives `goc validate` clean (or the scaffold itself carries the field)
  - [ ] TDD: unittest asserts `goc validate` flags an absent `summary` on a non-draft card with a message of shape `<title>: summary: missing — required on published cards`, and stays silent on a fresh `draft: true` scaffold
  - [ ] TDD: unittest confirms the existing present-but-blank rejection (`summary: ""` / whitespace-only) still fires — the absent-key rule extends it, not replaces it
  - [ ] MECHANICAL: whichever convenience path lands (`goc new --summary` flag, or none) is reflected in the create-card skill's Step 4 command block, and the choice is recorded in log.md
  - [ ] PROCESS: `uv run goc validate` green on the real deck and `uv run python -m unittest discover -s tests` green
---

# goc new scaffolds no summary field so fresh cards pass validate without one

## Location

- `goc/engine.py:5492-5505` — `_cmd_new`'s frontmatter scaffold enumerates
  `title`, `status`, `stage`, `contribution`, `created`, `closed_at`,
  `human_gate`, `advances`, `advanced_by`, `tags`, `draft`,
  `definition_of_done` (plus optional `worker`) — no `summary` key, and
  the argparse surface has no `--summary` flag.
- `goc/engine.py:~1210` (validate) — the summary rule shipped by the closed
  card [validate-accepts-whitespace-only-summary-as-non-empty](../validate-accepts-whitespace-only-summary-as-non-empty/)
  rejects a present-but-blank `summary: ""` / `"   "`, but an absent key
  never reaches it.
- `goc/engine.py:3198` area (quality-pass) — `(c.summary or "").strip()`
  already treats absent and blank identically as "Missing summary".

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

`uv run python .game-of-cards/deck/goc-new-scaffolds-no-summary-field-so-fresh-cards-pass-validate-without-one/reproduce.py`:

```
scaffold has summary key: False
goc publish exit: 0
draft flag after publish: (removed)
goc validate exit: 0
validate line: OK  sample-card-filed-without-a-summary
[FAIL] goc new scaffolded no summary: key and goc validate accepted the
published summary-less card — the card reaches triage views with a blank
summary and only goc quality-pass (run during refine passes) ever flags it.
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

## Fix

Extend the validate summary rule to fire when the key is absent and the
card is not `draft: true` (draft scaffolds are unauthored by definition —
flagging them would make every fresh `goc new` red). Same shape as the
whitespace fix: one clause in `validate_card`, message
`<title>: summary: missing — required on published cards`. The deck is
already conformant (0 missing after the 2026-07-23 backfill), so the rule
lands green. Optionally add `--summary` to `goc new` so skill-driven
filings can set it atomically; that is a convenience, not the guard.

## Cross-links

- [validate-accepts-whitespace-only-summary-as-non-empty](../validate-accepts-whitespace-only-summary-as-non-empty/)
  (done) — established the non-empty contract this card extends to the
  absent-key case.
- Surfaced by the 2026-07-23 `Skill(refine-deck)` pass ("Missing
  summaries" category, five backfills in the same commit).
