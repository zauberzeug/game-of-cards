---
title: half-edge-errors-recur-because-goc-new-cannot-wire-edges
summary: "`goc new` has no `--advances` / `--advanced-by` flags, so agents filing an already-wired card hand-author the frontmatter and forget the reverse edge. Add the flags and route through `_mutate_pair` so both sides land symmetric in one shell call."
status: active
stage: null
contribution: high
created: "2026-05-17T09:33:25Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] `goc new <title> --advances X --advances Y` creates the card with `advances: [X, Y]` AND adds `<title>` to `X.advanced_by` and `Y.advanced_by`
  - [ ] `goc new <title> --advanced-by P --advanced-by Q` creates the card with `advanced_by: [P, Q]` AND adds `<title>` to `P.advances` and `Q.advances`
  - [ ] Flags are repeatable and combinable in a single invocation
  - [ ] If any referenced target does not exist, `goc new` fails with a clear error and creates nothing (no card dir, no mutated targets)
  - [ ] If any proposed edge would create an `advances` cycle, `goc new` fails with the same atomic-or-nothing guarantee (reuses `_would_create_advance_cycle`)
  - [ ] `uv run goc validate` reports zero half-edges after every accepted invocation in `tests/test_new_wires_edges.py`
  - [ ] `goc/templates/skills/create-card/SKILL.md` Step 4 names the new flags as the preferred one-shot path for wiring at creation; the two-step `goc new` + `goc advance` is demoted to fallback
  - [ ] `goc new --help` lists both flags with examples
worker: {who: Rodja Trappe, where: main}
---

# half-edge-errors-recur-because-goc-new-cannot-wire-edges

## What's broken

The bidirectional `advances ↔ advanced_by` invariant is enforced only
by `validate_bidirectional_edges()` at `goc/engine.py:913`, not by the
data layer that writes the frontmatter. Three engine paths write
edges:

| Writer | Symmetric? |
|---|---|
| `goc advance` / `goc unadvance` (`_mutate_pair`, `goc/engine.py:2768`) | yes — writes both files |
| `goc move` (whole-tree text rewrite, `goc/engine.py:2889`) | yes — rewrites every reference |
| **Direct frontmatter authoring** (hand-typed `advances:` block) | **no — writer must remember to update both cards** |

`goc new` (`goc/engine.py:2688`) accepts no edge flags. It initializes:

```python
fm = {
    ...
    "advances": [],
    "advanced_by": [],
    ...
}
```

So the only one-shot way for an agent to file an already-wired card
is to scaffold and then hand-edit `advances:` directly. The
two-step alternative — `goc new <title>` then
`goc advance <target> --by <title>` — requires the agent to
remember and execute a follow-up, which drops under load.

## Empirical evidence

Two historical repair commits explicitly name this failure mode:

```
e8e6cb7 deck: backfill three missing reverse advanced_by edges
b4b004f deck: three kickoff-flow cards ...; repair v0.0.7 half-edges
```

Smoking gun: `cut-v0-0-7-release-before-openclaw-publish` was *born*
in commit `fa53e21` with `advances: [publish-openclaw-plugin,
provide-openclaw-plugin-for-skills-and-hooks]` already populated and
no reverse edges on either target — the agent never called
`goc advance`.

The pre-commit `goc validate` hook catches the local-author path,
but cloud agents pushing via the GitHub API bypass it. CI catches
the rest, but only after the bad commit has landed — repair then
requires manual two-file edits, which is what every "backfill"
commit in the log shows.

## Why it matters

Each occurrence costs a human a manual `git commit` to backfill the
reverse edge on every offending pair. The deck's value-flow graph
also drifts silently in the gap between the bad commit and the
repair — sort orders, board renders, and pull-queue ordering all use
the broken graph in the meantime.

## Fix

Add two repeatable flags to `goc new`:

- `--advances TITLE` — adds `TITLE` to the new card's `advances`
  list AND adds the new card's title to `TITLE.advanced_by`.
- `--advanced-by TITLE` — adds `TITLE` to the new card's
  `advanced_by` list AND adds the new card's title to
  `TITLE.advances`.

Implementation: after `_cmd_new` writes the new card with empty
edge lists, iterate the flag values and call `_mutate_pair` for
each. The existing cycle check (`_would_create_advance_cycle`) runs
per edge. **Atomic-or-nothing**: validate every target exists and
every proposed edge is cycle-free *before* creating the new card
directory; on any failure, exit without touching disk.

The skill text in `create-card/SKILL.md` Step 4 names the new flags
as the preferred path; the two-step recipe survives as a fallback
for adding edges to an existing card.

See sibling card
[goc-repair-edges-fixes-half-edge-validator-errors](../goc-repair-edges-fixes-half-edge-validator-errors/)
for the cleanup tool that handles the residual cloud-agent leak.

## Cross-references

- Sibling card: `goc-repair-edges-fixes-half-edge-validator-errors`
- Validator: `goc/engine.py:913` (`validate_bidirectional_edges`)
- Symmetric writer this work reuses: `goc/engine.py:2768`
  (`_mutate_pair`)
- Cycle guard already exists: `goc/engine.py:960`
  (`_would_create_advance_cycle`)
