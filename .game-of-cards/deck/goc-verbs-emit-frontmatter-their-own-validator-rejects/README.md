---
title: goc-verbs-emit-frontmatter-their-own-validator-rejects
summary: "Aggregation epic for a family of first-party `goc` verbs that exit 0 with a success line after writing frontmatter `goc validate` then rejects. Four independently-filed instances span `new`, `status active`, `publish`, `done` and the full-frontmatter re-emit verbs — `goc status active` alone self-corrupted twice and took two separate point fixes. The root cause is structural: each writer re-derives its own notion of a legal value, so nothing ties the writers' accept-set to `validate_card`'s, and every tightening of the validator silently opens a new gap in a writer. Needs a mechanism decision (shared predicates, a validate-the-result assertion, or schema-driven per-field validators) before another point fix."
status: open
stage: null
contribution: high
created: "2026-08-07T05:35:15Z"
closed_at: null
human_gate: none
advances: []
advanced_by:
  - worker-mapping-with-only-a-branch-emits-invalid-empty-who
  - draft-clearing-verbs-release-summary-less-cards-into-a-validate-red-deck
  - blank-worker-overrides-write-cards-that-goc-validate-rejects
  - goc-status-active-stamps-empty-who-worker-when-git-user-name-unset
tags: [epic, meta-fix, api-contract]
definition_of_done: |
  - [ ] PROCESS: A mechanism is decided and recorded in this card's `log.md` — shared predicates, a validate-the-result assertion at the write boundary, or schema-driven per-field validators (see `## Decision required`) — including whether it is enforced at runtime, by a test, or both.
  - [ ] TDD: A single test drives every frontmatter-writing verb with each field's invalid values and asserts the verb refuses; the test enumerates verbs and fields from the schema (or an explicit registry the schema is checked against), so a new field or verb cannot silently escape coverage.
  - [ ] TDD: The same test asserts the complement — no verb can leave a card on disk that `validate_card` rejects — which is the invariant the four instances each violated in a different place.
  - [ ] PROCESS: All open child cards are closed or superseded under the agreed mechanism; this epic's `advanced_by` roster is all terminal.
  - [ ] MECHANICAL: `uv run goc validate` clean and `uv run python -m unittest discover -s tests` green.
---

# `goc` verbs emit frontmatter their own validator rejects

## What this epic coordinates

A family of first-party `goc` verbs **write frontmatter that `goc validate`
then refuses**, exiting 0 with a confident success line. The deck ends up in a
state the tool itself calls invalid, produced by the tool itself, with nothing
in the output suggesting which verb did it. In this repo `goc validate` gates
CI and the shipped pre-commit hook, so the blast radius is the *next* commit by
*any* author — not the person who ran the verb.

Four instances, filed independently over ten weeks, each found and fixed (or
awaiting fix) on its own:

| Instance | Verb(s) | Invalid state written | Status |
|---|---|---|---|
| [goc-status-active-stamps-empty-who-worker-when-git-user-name-unset](../goc-status-active-stamps-empty-who-worker-when-git-user-name-unset/) | `status active` | `worker: {who: "", where: <branch>}` when git `user.name` is unset | done |
| [worker-mapping-with-only-a-branch-emits-invalid-empty-who](../worker-mapping-with-only-a-branch-emits-invalid-empty-who/) | every full-frontmatter re-emit verb (`wait`, `decide`, `advance`, `unadvance`, `quality-pass`, `migrate-list-style`) | `{who: "", where: x}` invented from a `where`-only card | open |
| [draft-clearing-verbs-release-summary-less-cards-into-a-validate-red-deck](../draft-clearing-verbs-release-summary-less-cards-into-a-validate-red-deck/) | `publish`, `status active`, `done` | non-draft card with no `summary` | open |
| [blank-worker-overrides-write-cards-that-goc-validate-rejects](../blank-worker-overrides-write-cards-that-goc-validate-rejects/) | `new`, `status active` | whitespace-only `worker` / `worker.who` / `worker.where` | done |

## Why a point fix keeps missing

The tell is in the table: **`goc status active` appears three times.** It was
fixed once for the empty-`who` case (2026-06), then self-corrupted again through
a different door — the `--worker-who` / `--worker-where` overrides — and needed a
second, separate point fix. The same function, the same field, the same
validator rule, two independent filings.

That happens because the two sides are written independently. `validate_card`
(`goc/engine.py:1838-2011`) is the single place that knows what a legal field
value is. Every writer re-derives it:

- `_auto_populate_worker` checked `if not who:` — falsiness, which a
  whitespace string passes.
- `_emit_worker` checked nothing, and rendered a missing `who` as `""`.
- The draft-clearing verbs check the draft flag but not `summary`.
- `_cmd_new` grew its guards one predicate at a time: `--summary` got a
  whitespace check, `--worker` got a line-break check, and neither got the
  other's.

Nothing connects these to `validate_card`, so the asymmetry is invisible at
review time and **every tightening of the validator silently opens a new gap in
a writer**. Both of the whitespace-only-worker validator cards
([summary](../validate-accepts-whitespace-only-summary-as-non-empty/),
[worker](../validate-accepts-whitespace-only-worker-as-non-empty/),
[worker.where](../validate-accepts-whitespace-only-worker-where-as-non-empty/))
closed *before* the writers that violate them were even filed — the validator
moved, and the writers were left behind. That is the mechanism by which this
family grows, and it will keep growing as the schema does.

## Relationship to the ordering root

Distinct from — and discovered through —
[mutating-verbs-leave-card-modified-on-conflicting-commit-flags](../mutating-verbs-leave-card-modified-on-conflicting-commit-flags/),
which established *validate every input before any disk write* across five
verbs. That card's invariant is about **when** validation runs relative to the
write; this epic is about **whether the writer's accept-set matches the
validator's at all**. A verb can satisfy the ordering rule perfectly and still
land in this family — `_cmd_status` did: pre-fix it validated and raised before
`write_text`, so nothing was half-written, yet the whitespace case had no check
to run at all and wrote a card `validate` rejects.

That card's log recorded "if a seventh site appears, that is the signal to file
[an umbrella]". The `--worker-who` / `--worker-where` gap in `_cmd_status` is
that site, and filing this epic is the recorded response. Note what the seventh
site actually demonstrates: the sixth-site fix was itself scoped to *the failing
check* (line breaks) rather than *the invariant* — it touched `--worker` and did
not add the whitespace predicate sitting eleven lines above it. The lesson that
card recorded recurred on the very next commit.

## Decision

*Resolved 2026-10-22T05:29:04Z:* 2. Validate the result at the write boundary: every frontmatter write goes through one function that runs validate_card on the rendered card and refuses to write on error, with an explicit escape hatch for drafts and migrate; enforced by both a runtime guard and a verbs x fields test proven to catch a planted offender

*Reasoning:* The maintainer chose the only option that closes the family structurally in a human session on 2026-10-22; writers may keep their precise per-flag checks for better messages, and the test must prove it can fail before its green run is trusted

## Scope note

This epic does **not** re-open the two closed children; their point fixes are
correct and their regression tests stand. It exists to stop the fifth instance
from being found the same way as the first four — one door at a time, by
audit, after the fact.
