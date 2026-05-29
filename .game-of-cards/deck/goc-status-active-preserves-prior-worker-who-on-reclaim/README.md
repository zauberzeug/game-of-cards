---
title: goc-status-active-preserves-prior-worker-who-on-reclaim
summary: "When `goc status <t> active` re-claims a card a previous worker released (active → open → active), `_auto_populate_worker` preserves the prior `worker.who` from the existing frontmatter while still refreshing `worker.where` from the live branch. The result is a Frankenstein `{who: alice, where: feature/bob}` — Bob's branch credited to Alice."
status: open
stage: null
contribution: medium
created: "2026-05-29T18:26:12Z"
closed_at: null
human_gate: decision
advances:
  - goc-status-active-discards-worker-overrides-when-target-already-active
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] PROCESS: decision recorded in `## Decision required` (refresh both sub-fields on re-claim, OR preserve both as a unit, OR keep current asymmetric behavior and document it as intentional).
  - [ ] TDD: reproduce.py exits zero (the chosen behavior matches expectation).
  - [ ] TDD: a unit test in `tests/` covers the re-claim path under a different `git config user.name`.
  - [ ] MECHANICAL: `_auto_populate_worker` docstring at `goc/engine.py:3905` updated to match the chosen behavior.
  - [ ] PROCESS: `uv run goc validate` passes.
---

# `goc status active` preserves prior worker `who` when a different person re-claims

## Location

`goc/engine.py:3918-3930` — `_auto_populate_worker`.

## What's broken

`_auto_populate_worker` populates the `worker` field asymmetrically when a
card is being re-claimed via `goc status <title> active`. The `who` sub-field
is preserved from the existing frontmatter if present; the `where` sub-field
is always refreshed from the live branch.

```python
3918:    if worker_who is not None:
3919:        who = worker_who
3920:    elif "who" in existing_dict:
3921:        who = existing_dict["who"]      # ← preserve old who
3922:    else:
3923:        r = subprocess.run(["git", "config", "user.name"], ...)
3924:        who = r.stdout.strip() ...
3925:
3926:    if worker_where is not None:
3927:        where: str | None = worker_where
3928:    else:
3929:        r = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], ...)
3930:        where = r.stdout.strip() ...     # ← always refresh from live branch
```

The docstring at `goc/engine.py:3905-3906` codifies the intent:

> If the card already has a worker.who (designation), preserve it and only
> add/update `where`.

That intent is correct when the *same* worker re-claims after a session break,
but it is wrong when a *different* worker re-claims after the previous holder
released the card (active → open → active). The two sub-fields drift apart
whenever the next claimant has a different `git config user.name` than the
previous one.

## Reachability path

Triggered from `_cmd_status` at `goc/engine.py:4002`, which calls
`_auto_populate_worker` on every `open/blocked → active` transition. Any of
the following flows surfaces it:

- A second agent or person picks up a previously-released card on a
  different branch.
- An autonomous `pull-card` loop on a different machine (different
  `git config user.name`) pulls a card released by a human.
- A `/schedule pull-card` cron resumes a card a human had claimed.

The `worker` field is the audit record of *who is responsible right now* —
`--worker <X>` filters and the board's worker label both lean on it. Quietly
inheriting `who` from the prior holder corrupts that record.

## Empirical evidence

`uv run python .game-of-cards/deck/goc-status-active-preserves-prior-worker-who-on-reclaim/reproduce.py`:

```
after Alice claims:
  worker: {who: alice, where: feature/alice}
after Alice releases (status open):
  worker: {who: alice, where: feature/alice}
after Bob re-claims (no --worker-who):
  worker: {who: alice, where: feature/bob}

expected worker.who: bob
actual   worker.who: alice
FAIL — defect reproduced: Bob's re-claim is attributed to Alice.
```

## Why it matters

In a heavy multi-agent or multi-human deck, the worker field continuously
lies about claims. Two concrete consequences:

- `goc --worker alice` continues to surface cards that Bob is actively
  working on, because the frontmatter still records Alice.
- The board's "active by" column and any future cross-agent reporting
  inherit the stale `who`.

The current workaround is to pass `--worker-who <name>` explicitly on every
re-claim, but the default is silently wrong — and `pull-card` does not pass
that flag.

## Decision required

The asymmetry needs a decision. Three credible paths:

1. **Refresh both sub-fields on re-claim.** Treat the persisted `worker`
   as a historical fact about the previous claim; the new claim overwrites
   it. Matches the live-git refresh of `where`. Loses the AGENTS.md guarantee
   that the field "persists after close as a historical record" *between
   claims*, but log.md still captures the journal.

2. **Preserve both sub-fields as a unit when neither flag is passed.**
   If the card already has a worker, leave it untouched (same person, same
   branch) — re-claimants must pass `--worker-who` / `--worker-where`
   explicitly. Loses the auto-refresh-where convenience, but the rule is
   simple and symmetric.

3. **Keep the current asymmetric behavior and document it as intentional.**
   Rename the docstring to say "the same person is assumed to re-claim;
   pass `--worker-who` for a different claimant." Cheapest fix, but enshrines
   the wrong default for the autonomous-loop use case.

Option 1 best matches the "live git is the source of truth at claim time"
mental model already implied by the `where` refresh and by the cron / loop
patterns that depend on `pull-card` getting attribution right without
per-call flags. Option 2 is the safe-conservative fallback.

## Fix sketch (after the decision)

If option 1: drop lines 3920-3921; always fall through to the
`git config user.name` branch when `worker_who is None`.

If option 2: change the `where` branch to mirror the `who` branch — if
`worker_where is None` and `"where" in existing_dict`, preserve it.

## Sibling cards

- [worker-mapping-with-only-a-branch-emits-invalid-empty-who](../worker-mapping-with-only-a-branch-emits-invalid-empty-who/) —
  related but distinct: that card is about `--worker-where X` without
  `--worker-who` writing `{who: "", where: X}`. This card is about the
  preserve-who-on-reclaim path.
