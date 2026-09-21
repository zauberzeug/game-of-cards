---
title: shipped-epic-recipe-builds-the-backwards-edge-its-own-next-bullet-forbids
summary: "The aggregation-epic recipe in `advance-card/reference.md` states the canonical encoding as `child.advances: [epic]` and then gives the verb as `goc advance <child> --by <epic>` — but `goc advance <title> --by <advancer>` writes `advancer.advances += title`, so running the recipe verbatim produces `epic.advances: [children]`, the exact shape the next bullet nine lines down calls Never and that `goc validate` flags as BACKWARDS_EPIC_EDGE. The correct verb is `goc advance <epic> --by <child>`. The line ships identically in all six skill trees (templates, the two dogfood mirrors, and the three plugin payloads), so every consumer repo that follows the documented recipe builds the inverted edge on its first epic and inherits the broken value chain and the spurious attest failures the same bullet warns about."
status: active
stage: null
contribution: high
created: "2026-09-21T01:21:37Z"
closed_at: null
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation, api-contract]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — the verb form extracted from the shipped text produces the canonical encoding the same file states, and `goc validate` stays silent; it exits 1 today.
  - [ ] MECHANICAL: `goc/templates/skills/advance-card/reference.md:108` reads ``goc advance <epic> --by <child>``, and the five mirrors are regenerated (pre-commit `sync-plugin-assets` covers four; `python3 scripts/port_skills_to_openclaw.py` re-ports the OpenClaw copy).
  - [ ] TDD: a guard asserts that every `goc advance` example in a shipped skill body, run against a scratch deck, produces the edge direction the surrounding prose claims — so the next swap is caught at test time rather than in a consumer's deck.
  - [ ] MECHANICAL: the body of [auto-commit-publishes-dangling-edges-when-counterpart-endpoint-is-a-draft](../auto-commit-publishes-dangling-edges-when-counterpart-endpoint-is-a-draft/) is corrected where it repeats the swapped form as "the documented aggregation-epic wiring order" (lines 94 and 131).
  - [ ] PROCESS: cross-referenced from [validate-backwards-epic-edge-fix-suggestion-has-swapped-command-arguments](../validate-backwards-epic-edge-fix-suggestion-has-swapped-command-arguments/) as the second site where shipped text gets this verb's argument order backwards, and wired as an instance row on [doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/).
  - [ ] PROCESS: `uv run goc validate` passes, `python scripts/sync_plugin_assets.py --check` and `python3 scripts/port_skills_to_openclaw.py --check` are green, and `uv run python -m unittest discover -s tests` is green.
worker: {who: "claude[bot]", where: main}
---

# The shipped epic recipe builds the backwards edge its own next bullet forbids

## Location

`goc/templates/skills/advance-card/reference.md:106-108`, and the identical
line 108 in all five mirrors (`.claude/skills/`, `.codex/skills/`,
`claude-plugin/skills/`, `codex-plugin/skills/`, `openclaw-plugin/skills/`).

## What's broken

The three-way coordinating-card fork states the canonical encoding and then
gives the verb that is supposed to produce it:

```markdown
- **Aggregation epic** — its value chain *is* its children; closes
  when they close. Encoding: `child.advances: [epic]`. Verb on the
  child: `goc advance <child> --by <epic>`.
```

Nine lines below, the same list defines the shape to avoid:

```markdown
- **Backwards aggregation** — `epic.advances: [children]`. **Never.**
  Defeats the value law (children stop inheriting the epic's value,
  so the priority sort cannot see the chain) and trips a spurious
  `advanced-by-closed` FAIL on every child at attest time.
  `goc validate` flags this signature as `BACKWARDS_EPIC_EDGE`.
```

The verb's argument order is fixed by `goc/engine.py:6580`:

```python
    _mutate_pair(title, advancer, "advanced_by", "advances", add=True)
    print(f"advance: {title}.advanced_by += {advancer}; {advancer}.advances += {title}")
```

`goc advance <title> --by <advancer>` writes `advancer.advances += title`.
Substituting the recipe's arguments — `title = <child>`,
`advancer = <epic>` — gives `epic.advances += child`: the Never shape,
built by following the bullet that promises the opposite one. The
command that produces the stated `child.advances: [epic]` encoding is
`goc advance <epic> --by <child>`.

The prose and the verb in the same bullet disagree, so a reader who
trusts the encoding is right and a reader who runs the command is
wrong — and running the command is what the bullet asks for.

## Empirical evidence

`reproduce.py` extracts the verb form from the shipped text itself (so it
cannot drift from the doc), scaffolds a throwaway deck, and runs it:

```
$ uv run python .game-of-cards/deck/shipped-epic-recipe-builds-the-backwards-edge-its-own-next-bullet-forbids/reproduce.py
goc/templates/skills/advance-card/reference.md:107 states the canonical encoding: Encoding: `child.advances: [epic]`
goc/templates/skills/advance-card/reference.md:108 gives the verb:               goc advance <child> --by <epic>
goc/templates/skills/advance-card/reference.md:117 forbids:                      **Backwards aggregation** — `epic.advances: [children]`. **Never.**

goc/engine.py:6580 — `goc advance <title> --by <advancer>` writes advancer.advances += title

--- running the shipped verb form verbatim ---
    advance: child-one.advanced_by += ship-the-epic; ship-the-epic.advances += child-one
    advance: child-two.advanced_by += ship-the-epic; ship-the-epic.advances += child-two

    ship-the-epic.advances    = ['child-one', 'child-two']
    ship-the-epic.advanced_by = []
    child-one.advances        = []
    child-one.advanced_by     = ['ship-the-epic']

    goc validate: WARN BACKWARDS_EPIC_EDGE ship-the-epic: contribution=high but advances targets are predominantly lower: [child-one(low), child-two(low)] — likely backwards aggregation epic. Fix: card looks like a governing cluster (human_gate: decision) — drop the edge and group via a shared tag. See Skill(card-schema) 'Coordinating cards'.

--- the un-swapped form, for contrast: goc advance <epic> --by <child> ---
    ship-the-epic.advances = []
    child-one.advances     = ['ship-the-epic']
    goc validate: no BACKWARDS_EPIC_EDGE warning

FAIL: the verb form at goc/templates/skills/advance-card/reference.md:108 produced epic.advances = ['child-one', 'child-two'] — the shape the same file calls "Backwards aggregation … Never." and goc validate flags as BACKWARDS_EPIC_EDGE. The canonical child.advances: [epic] encoding needs `goc advance <epic> --by <child>`.
```

## Why it matters

Reachability is the shipped authoring path, not a corner: a consumer
installs GoC, files an epic and its children, and `Skill(advance-card)`
routes the "one card coordinates many others" question to exactly this
fork in `reference.md`. The first command they run builds the inverted
edge. The consequences are the ones the forbidden bullet already
enumerates — children stop inheriting the epic's value so the priority
sort cannot see the chain, and every child trips a spurious
`advanced-by-closed` FAIL at attest time — with the added cost that
`goc validate` then emits a `BACKWARDS_EPIC_EDGE` warning whose own fix
suggestion has the same arguments swapped
([validate-backwards-epic-edge-fix-suggestion-has-swapped-command-arguments](../validate-backwards-epic-edge-fix-suggestion-has-swapped-command-arguments/),
open). A consumer who hits this has two shipped texts in a row telling
them to do the wrong thing, and no third one telling them otherwise.

The recipe is read and reused, not skimmed past:
[auto-commit-publishes-dangling-edges-when-counterpart-endpoint-is-a-draft](../auto-commit-publishes-dangling-edges-when-counterpart-endpoint-is-a-draft/)
cites `goc advance <child> --by <epic>` twice as "the documented
aggregation-epic wiring order" while reasoning about a different defect
— the swapped form has already propagated out of the skill and into the
deck's own record.

It is also an instance of the executed-rather-than-read doc rot that
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/)
named as its fourteenth shape: a skill body specifying a procedure an
agent follows literally. A derive-from-tree guard cannot catch it, but a
*run-it-against-a-fixture* guard can, and the fixture is three cards —
which is why this instance is worth pinning rather than just patching.

## Fix

One line in the template, then the mirrors:

```diff
-  child: `goc advance <child> --by <epic>`.
+  epic: `goc advance <epic> --by <child>`.
```

(the label moves with the argument: the verb is now run naming the epic,
so "Verb on the child" becomes "Verb on the epic"). Re-run the
pre-commit sync for the four auto-synced trees and
`python3 scripts/port_skills_to_openclaw.py` for the OpenClaw copy.

Then add the guard: walk every `goc advance` example in a shipped skill
body, run it against a scratch deck, and assert the resulting edge
direction matches the encoding the surrounding prose states. That is the
only technique that would have caught this one, and it is the technique
the root card is still missing.
