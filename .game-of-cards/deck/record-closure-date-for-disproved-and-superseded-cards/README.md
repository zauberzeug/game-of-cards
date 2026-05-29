---
title: record-closure-date-for-disproved-and-superseded-cards
summary: "Today `goc/engine.py` only writes `closed_at` when a card flips to `done`; the validator (engine.py:782-791) actively forbids `closed_at` on any other status. Disproved and superseded cards therefore lose their card-local closure date — recovery requires `git log` on the auto-commit, which is a separate artefact that can be lost on repo migration, history rewrite, or hand-editing without the CLI. Change the semantics so `closed_at` records *any* terminal transition (done / disproved / superseded); `status` already names the outcome, so a single timestamp on every terminal exit gives queryable per-outcome dates without schema bloat."
status: done
stage: null
contribution: medium
created: "2026-05-14T04:23:39Z"
closed_at: "2026-05-14T09:06:49Z"
human_gate: none
advances: []
advanced_by: []
tags: [api-contract, meta-fix]
definition_of_done: |
  - [x] `_cmd_status` (engine.py:2468-2514) sets `closed_at` to the current UTC timestamp when transitioning to `disproved` or `superseded`
  - [x] Validator rule at engine.py:782-791 inverted: `closed_at` is required for every terminal status (`done`, `disproved`, `superseded`) and must be null otherwise — single symmetric rule, not a `done`-special-case
  - [x] `--since` filter (engine.py:1001) and any other `closed_at` consumers still behave correctly with the broader population; document any filters that should remain done-only via an additional `--status done` predicate
  - [x] Existing disproved/superseded cards in `.game-of-cards/deck/` backfilled with their closure date derived from `git log -- deck/<title>/README.md` (the auto-commit that flipped the status). Cards with no derivable git timestamp get the date of the first commit touching the README post-creation; document the migration script under `scripts/`
  - [x] `goc validate` green across the deck after migration
  - [x] Skill bodies updated where they describe `closed_at` semantics — at minimum `card-schema/SKILL.md`, `advance-card/SKILL.md`, `finish-card/SKILL.md` — to reflect that `closed_at` marks any terminal exit, with `status` disambiguating the outcome
  - [x] CLAUDE.md / consumer-facing docs reviewed for any "closed_at = shipped" framing that becomes stale
worker: {who: "claude[bot]", where: main}
---

# record-closure-date-for-disproved-and-superseded-cards

## Current behavior

`closed_at` fires only on `goc done` (engine.py:1951-1954). `_cmd_status`
never touches it. The validator at engine.py:782-791 enforces a
one-directional rule:

- `status == 'done'` ⇒ `closed_at` MUST be set
- `status != 'done'` ⇒ `closed_at` MUST be null (added in commit
  4c916e9, 2026-05-05, to prevent stale timestamps surviving a
  terminal flip)

Effect: a card that exits via `disproved` or `superseded` carries no
card-local record of *when* it exited. To answer "when was this card
set aside?" a reader must run `git log -- deck/<title>/README.md` and
locate the auto-commit produced by `_git_auto_commit`
(engine.py:2510).

## Why this is worth changing

1. **Card frontmatter should be self-contained.** Today a card is
   moved between repos, archived, or audited offline. `git log` is a
   *separate artefact*: it disappears if the deck is exported, if
   history is rewritten (rebase/squash), or if a human edits the
   README by hand without the CLI auto-commit path.

2. **The status field already names the outcome.** `closed_at: null`
   adds zero information on a disproved card — `status: disproved`
   already says "not shipped." The timestamp's unique contribution is
   the *date*. Withholding the date on the non-shipped outcomes
   throws away the only thing the field is good for.

3. **Other date-bearing queries exist beyond "shipped."** Discard
   rate over time, churn from supersession, recent-terminal-activity
   audits — all want a card-local date keyed by status. Today they
   require git archaeology; under the proposed semantics they are
   one frontmatter scan.

4. **Other trackers converge on the broader semantics.** Linear has
   separate `completedAt` + `canceledAt`. Jira has one
   `resolutiondate` paired with a `resolution` field (the GoC analog
   is `status`). GitHub Issues uses one `closed_at` across all
   closures. The current GoC design — date on one outcome only — is
   unusual.

## Proposed behavior

- `_cmd_status` writes `closed_at = _utc_now_iso()` when the target
  status is in the terminal set `{disproved, superseded}`. (`_cmd_done`
  already does this for `done`.)
- `_cmd_status` does NOT touch `closed_at` for non-terminal targets
  (`open`, `active`, `blocked`) — those keep null.
- Validator rule becomes symmetric: `closed_at` is required iff
  `status` is terminal. The current done-special-case branch
  collapses into a single check over the terminal set.

## Implementation surface

- `goc/engine.py` — `_cmd_status` (write), validator rule (read), and
  the docstring on the `closed_at` Card property at line 392.
- `goc/schema.yaml` — schema_version bump may be warranted depending
  on how strict consumer-side schema-version checks are. Field list
  is unchanged.
- `goc/templates/skills/card-schema/SKILL.md` — explicit semantic
  description of `closed_at`.
- `goc/templates/skills/advance-card/SKILL.md` — the Disproved /
  Superseded sections should note that the CLI now stamps the date.
- Existing disproved/superseded cards in this repo's deck need a
  one-time backfill. Migration script under `scripts/` reads
  `git log --diff-filter=M --format=%aI -1 -- deck/<title>/README.md`
  for each terminal card and writes the matching frontmatter field.
- `tests/` (none yet) — when a test suite lands, the new symmetric
  validator rule should be exercised in both directions.

## Risks / open questions

- **Backfill correctness**: not every disproved/superseded card was
  flipped via the CLI's auto-commit path. Some may have been edited
  by hand or have multiple status-flip commits in their history. The
  migration script should pick the *latest* commit that touched the
  README (the one that established the current status), not the first.
  For cards where no useful timestamp can be derived, the migration
  script should print a warning and skip, leaving the field null —
  validation will then fail on those specific cards and a human must
  decide a fallback date (e.g., the `created` field).

- **`--since` consumer drift**: today `--since` filters by `closed_at`
  and implicitly returns only `done` cards. After the change it would
  return all terminal cards in the window. Callers expecting "what
  shipped recently" need to combine `--since` with `--status done`
  (or `--done`, which already does that). Worth a release-note line.

- **Predecessor cards**: the now-closed `done-command-overwrites-terminal-cards`
  and `status-command-reopens-terminal-cards` cards established the
  terminal-guard invariant; this card builds on it (the guard
  ensures `closed_at` once written is never rewritten by a backward
  flip). No conflict, but the new validator rule subsumes the
  current "must be null when status is not done" assertion — the
  predecessor's verdict text should be re-read to confirm no
  surprise.

## Surfaced by

Code-review discussion 2026-05-14 questioning whether the "closed_at
= shipped" semantics is a good design. The deeper objection: `status`
already encodes shipped-vs-not, so a sparse `closed_at` discards the
only unique value the field offers (the date) for half the terminal
population.
