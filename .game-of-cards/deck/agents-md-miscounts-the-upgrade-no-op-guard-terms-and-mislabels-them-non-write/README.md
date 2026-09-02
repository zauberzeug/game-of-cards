---
title: agents-md-miscounts-the-upgrade-no-op-guard-terms-and-mislabels-them-non-write
summary: "FIXED: AGENTS.md's plan-derived-verdict paragraph closed with \"The two remaining terms next to the plan cover non-write work only\", but upgrade() ANDs three terms beside plan_has_effect and the third one writes — pending_skills_source is true exactly when _write_skills_source would change .game-of-cards/config.yaml, as the code comment directly above the guard already said. The sentence now names all three terms, states that the skills_source pin does gate a write, and marks it a holdover rather than a shape to copy. UpgradeNoOpGuardParagraphAccuracyTest derives both the count and which terms write (a pending_* term assigned from a probe=True call) out of goc/install.py, so the next term added turns the build red."
status: done
stage: null
contribution: low
created: "2026-09-02T05:09:45Z"
closed_at: "2026-09-02T05:28:33Z"
human_gate: none
advances: []
advanced_by: []
tags: [documentation, infra]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — AGENTS.md's count matches the `pending_*` terms parsed out of `upgrade()`'s short-circuit, and no term it calls non-write actually writes.
  - [x] MECHANICAL: the AGENTS.md sentence names all three terms and stops calling them non-write work only — `pending_skills_source` gates a write to `.game-of-cards/config.yaml`, so the honest framing is "work the plan does not model", not "non-write work".
  - [x] TDD: a guard in `tests/test_guidance_accuracy.py` fails when the sentence's count drifts from the `pending_*` terms `upgrade()` actually ANDs into the short-circuit, so the next term added cannot re-open this.
worker: {who: "claude[bot]", where: main}
---

# agents-md-miscounts-the-upgrade-no-op-guard-terms-and-mislabels-them-non-write

AGENTS.md told the reader that everything the plan does not model is non-write
work, and that there were two such things. There are three, and one of them
writes. The sentence is rewritten and pinned to the source — see
`## Fix (landed)`; the sections below record the defect as it stood.

## Location

- `AGENTS.md`, "Code architecture" § — the paragraph headed **"already at goc X
  — nothing to do" is derived, never enumerated**, final sentence.
- `goc/install.py` — `upgrade()`'s `pending_*` assignments and the
  short-circuit `if` that ANDs them with `plan_has_effect`.
- `tests/test_guidance_accuracy.py` — `UpgradeNoOpGuardParagraphAccuracyTest`,
  the guard added here that holds the sentence to that code.

## What was broken

AGENTS.md closed the paragraph with:

> The two remaining terms next to the plan cover non-write work only — the
> interactive vendored-cleanup prompt and the legacy-briefing strip.

`upgrade()` computes three:

```python
    plan_has_effect = any(write.action not in _NO_OP_ACTIONS for write in upgrade_plan)
    pending_cleanup = needs_vendored_cleanup
    pending_briefing_migration = bool(legacy_briefings_to_strip)
    pending_skills_source = "claude" in agents and _write_skills_source(
        target, claude_skills_mode, probe=True
    )
```

and ANDs all three, negated, into the short-circuit. The third is not non-write
work: `_write_skills_source(..., probe=True)` returns true exactly when the real
call would rewrite the `skills_source:` key in `.game-of-cards/config.yaml`.

The code comment directly above the same guard already got it right:

> Only the two pieces of non-write work the plan does not model (the
> interactive cleanup prompt, the legacy briefing strip) plus the skills_source
> pin still need their own terms, and the pin asks the executor that performs
> it rather than restating it.

So the contradiction was between two descriptions of one eight-line block — the
comment counted the pin separately and AGENTS.md dropped it.

## Empirical evidence

`uv run python .game-of-cards/deck/agents-md-miscounts-the-upgrade-no-op-guard-terms-and-mislabels-them-non-write/reproduce.py`
parses the guard out of `goc/install.py` with `ast` rather than restating it,
so it stays correct if a term is later added or removed. It also derives *which*
terms write instead of listing them: a `pending_*` term assigned from a call
carrying `probe=True` is asking a write-executor whether it would change the
file, which is the convention this very paragraph names.

Before the fix (exit 1):

```
upgrade() pending_* terms beside plan_has_effect: 3
  - pending_cleanup
  - pending_briefing_migration
  - pending_skills_source  (WRITES to disk — probes _write_skills_source)

AGENTS.md says: The two remaining terms next to the plan cover non-write work only — the interactive vendored-cleanup prompt and the legacy-briefing strip.
  claimed count: 2

DEFECT PRESENT (3 of 3 assertions failed):
  BUG: AGENTS.md claims 2 remaining terms; upgrade() has 3 (pending_cleanup, pending_briefing_migration, pending_skills_source)
  BUG: AGENTS.md calls the remaining terms "non-write", but pending_skills_source gates a write to .game-of-cards/config.yaml
  BUG: AGENTS.md's sentence does not name the writing term(s) pending_skills_source — a reader cannot tell which of the terms writes
```

After the fix (exit 0): `DEFECT ABSENT: AGENTS.md's sentence matches the guard
it describes.`

The script scopes itself to the `pending_*` prefix on purpose — that is the
register the paragraph is counting ("Do not reintroduce a `pending_*` allowlist
term"). The guard's other negated operands, `agents_explicit` and
`keep_local_skills`, are caller-flag overrides rather than answers to "is there
work?", so they are outside what the sentence describes.

## Why it matters

The paragraph exists to establish one belief and to make it load-bearing for
future contributors: *every write is covered by the plan, so do not add a
`pending_*` term for one.* The sentence that closes it is the reader's check on
that belief — and it was the sentence that quietly exempted a write. A
contributor who read it and then found `pending_skills_source` had two
incompatible rules and no way to tell which one governs the term they were
about to add. That is exactly the confusion the predecessor card
[goc-upgrade-cannot-repair-a-damaged-install-at-the-same-version](../goc-upgrade-cannot-repair-a-damaged-install-at-the-same-version/)
paid for once, with four repairs unreachable at the same version.

Reachability is total: this is the paragraph an agent reads before touching
`upgrade()`, and the block it describes is loaded on every invocation of the
verb. The seven closed `agents-md-*` cards
([one](../agents-md-mislabels-claude-settings-json-as-user-owned-permission-list/),
[two](../agents-md-cli-bullet-describes-parser-wiring-the-entry-point-never-does/))
are the same family — a guidance sentence that drifted past the code it
describes — and were each fixed in place; three of them left a
`tests/test_guidance_accuracy.py` guard behind.

Found while closing
[upgrade-write-plan-omits-the-skill-tree-prune-from-dry-run-and-no-op-verdict](../upgrade-write-plan-omits-the-skill-tree-prune-from-dry-run-and-no-op-verdict/),
which edited the two sentences immediately above this one. Not fixed there
because the sibling-sweep rule keeps a surfaced finding as its own card.

## Fix (landed)

The closing sentence now reads:

> The three remaining terms next to the plan cover work the plan does not
> model: the interactive vendored-cleanup prompt, the legacy-briefing strip,
> and the `skills_source` pin — the one surviving `pending_*` term that does
> gate a write, kept honest by asking `_write_skills_source` in `probe=True`
> mode rather than restating what it would do, and a holdover rather than a
> shape to copy.

It names all three terms, drops the "non-write work only" claim, and says
outright which one writes — plus the "holdover, not a shape to copy" clause
that reconciles the pin with the "do not reintroduce a `pending_*` allowlist
term" rule two sentences above it, which the old wording left in open
contradiction.

`UpgradeNoOpGuardParagraphAccuracyTest` in `tests/test_guidance_accuracy.py`
pins all three properties against the source: the claimed count equals the
`pending_*` terms `upgrade()` negates beside `plan_has_effect`; the sentence
does not say "non-write" while one of those terms probes a writer; and every
writing term is named in the sentence. Both the term list and the writer set are
parsed out of `goc/install.py` with `ast`, so neither the guard nor
`reproduce.py` carries the hand-maintained register the paragraph forbids.

**Explicitly out of scope.** `pending_skills_source` is a hand-registered signal
for a write, which is the shape the paragraph forbids — so it may belong in the
plan as a `PlannedWrite`, the treatment
[upgrade-write-plan-omits-the-skill-tree-prune-from-dry-run-and-no-op-verdict](../upgrade-write-plan-omits-the-skill-tree-prune-from-dry-run-and-no-op-verdict/)
gave the skill-tree prune. That is an architectural call for its own card, and
it did not gate this one: the sentence has to describe the code as it stands
either way, and the guard above will fail on the day the pin moves into the
plan, which is when the sentence gets rewritten again.
