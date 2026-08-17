---
title: re-run-safety-is-proven-per-verb-and-new-verbs-keep-missing-it
summary: "Seven cards have fixed an operation that was correct on its first run and wrong on its second — install, done, kickoff, upgrade, the settings merge twice, and now refine-deck's citation-repair recipe. Each was found in production and each shipped a test for that one surface, so re-run safety is coverage a verb earns only after a defect bites it: of the fourteen mutating verbs the engine registers, one has a dedicated re-run test. Probing the rest shows they are stable today, which is the point — nothing holds them there."
status: active
stage: null
contribution: medium
created: "2026-08-17T03:14:22Z"
closed_at: null
human_gate: none
advances: []
advanced_by:
  - second-citation-repair-pass-moves-correct-cites-onto-unrelated-code
tags: [bug, test, meta-fix]
definition_of_done: |
  - [ ] TDD: a class-level re-run test lands in `tests/` — it derives the verb list rather than enumerating it by hand, runs each mutating verb twice against a scratch deck, and asserts the second run either leaves the deck byte-identical or refuses. `reproduce.py` exits zero once it exists.
  - [ ] TDD: the new test proves it can catch an offender — a deliberately non-idempotent verb (or a stubbed one) makes it fail, per `static-source-guards-never-prove-they-can-catch-an-offender`. A guard that only ever sees a clean tree is indistinguishable from one that stopped running.
  - [ ] MECHANICAL: the verb list is derived from the engine's own parser registration, so a verb added tomorrow is covered without anyone remembering to add it. Hard-coding the list reproduces the defect this card describes.
  - [ ] PROCESS: decide and record in `log.md` whether "refuses on the second run" counts as safe for every verb or only for the ones where refusing is the documented contract — today `decide` and `move` exit 2 on re-run and that is correct, while `publish` exiting 2 on an unauthored scaffold is a different thing entirely.
  - [ ] PROCESS: the non-verb surfaces in the instance list (the `goc install` / `goc upgrade` entry points and `_merge_claude_settings`) are either brought under the same check or explicitly scoped out with a reason.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass.
worker: {who: "claude[bot]", where: main}
---

# Re-run safety is proven per verb, and new verbs keep missing it

## The family

Seven cards in this deck have fixed the same shape of defect: an operation
that is correct the first time it runs and wrong the second.

| Closed | Surface | Card |
|---|---|---|
| 2026-05-05 | `goc install` | `second-install-exits-nonzero` |
| 2026-05-05 | `goc done` | `done-rerun-rewrites-closure-date` |
| 2026-05-08 | kickoff skill | `make-kickoff-idempotent-on-restart` |
| 2026-05-26 | `goc upgrade` | `goc-upgrade-duplicates-the-goc-guidance-block-on-suffixed-versions` |
| 2026-06-23 | `_merge_claude_settings` | `merge-claude-settings-rewrites-settings-json-on-idempotent-merge` |
| 2026-06-24 | `_merge_claude_settings` | `merge-claude-settings-spams-bak-files-on-idempotent-merge` |
| 2026-08-17 | refine-deck citation repair | [second-citation-repair-pass-moves-correct-cites-onto-unrelated-code](../second-citation-repair-pass-moves-correct-cites-onto-unrelated-code/) |

Six distinct surfaces over three and a half months. They are not variations
on one bug — a nonzero exit, a rewritten timestamp, a duplicated marker
block, a reflowed settings file, a spurious backup, and a citation moved
onto unrelated code have nothing in common at the code level. What they
share is how they were found: by someone running the thing twice, in
production, after it shipped.

## What's broken

Re-run safety is a property every one of these surfaces was expected to
have and none of them was asked to prove. Each fix shipped a test for its
own surface, which is right, and no fix could have covered the next
surface, which is the problem. The property is enforced one verb at a time,
in arrears, so a verb added tomorrow inherits nothing.

The census makes the gap concrete. Of the fourteen mutating verbs the
engine registers, exactly one — `repair-edges` — carries a test whose name
says it re-runs the verb:

```
static census — mutating verbs with a re-run test: 1/14
    yes  goc repair-edges  (test_repair_edges.py::test_repair_edges_apply_repairs_and_is_idempotent)
```

The other thirteen are unpinned. That is not the same as broken — probing
each verb by running it twice against a scratch deck, all eight probed
today are stable:

```
dynamic probe — run each verb twice on a scratch deck:
    goc publish        exit 0/0   stable
    goc wait           exit 0/0   stable
    goc advance        exit 0/0   stable
    goc status         exit 0/0   stable
    goc decide         exit 0/2   stable
    goc move           exit 0/2   stable
    goc quality-pass   exit 0/0   stable
    goc repair-edges   exit 0/0   stable
```

**No live re-run defect is being claimed here.** The deck is in good shape
on this axis right now. The finding is that its being in good shape is not
load-bearing on anything: no test asserts it, so the next refactor that
breaks it will be discovered the same way the previous seven were.

The probe above is roughly forty lines and derives its behaviour from the
verb list rather than from thirteen hand-written cases. That is the whole
argument — the class-level check is cheap, it generalizes, and it does not
exist.

## Empirical evidence

`reproduce.py` prints the instance roster, the static census, and the
dynamic probe, and exits 1 while `tests/` contains no test that walks the
verb list re-running each one.

One detail from building it is worth keeping, because it is an instance of
a *different* family this deck already tracks. The census's first draft
matched the re-run signal anywhere in a test's body and reported **4/14**
coverage — three false positives, including a `yaml_lite` parser test that
scored as coverage for `goc status` because it quotes `"status"` as a
frontmatter key. Requiring the signal in the test's name and requiring the
body to actually drive the CLI brought it to a true 1/14. A grep-shaped
guard that over-reports coverage is exactly the failure
[static-source-guards-never-prove-they-can-catch-an-offender](../static-source-guards-never-prove-they-can-catch-an-offender/)
describes, which is why this card's DoD asks the new test to demonstrate it
can go red.

## Why it matters

The cost is not the seven fixes — those were cheap individually. It is that
the seventh was found the same way as the first, with no accumulated
defence in between, and the eighth will be too.

The most recent instance is the one that shows what that costs. The
citation-repair recipe was correct on the pass that introduced it and
corrupting on the pass after; had it not been caught by hand during the
2026-08-17 hygiene pass, it would have rewritten 165 correct citations onto
unrelated code and each subsequent pass would have tracked the corruption
faithfully forward. A class-level re-run check would not have caught that
one directly — the recipe lives in a skill body, not a verb — which is why
the DoD asks explicitly whether the non-verb surfaces come under the same
check or are scoped out with a reason.

## Relationship to the instances

The six closed instances stay closed; they are cited here as the evidence
for the family, not as work to redo. The one open instance,
[second-citation-repair-pass-moves-correct-cites-onto-unrelated-code](../second-citation-repair-pass-moves-correct-cites-onto-unrelated-code/),
carries an `advances` edge to this card: a class-level re-run guard cannot
ship green while a known re-run defect is still open.

Filed at `human_gate: none` per this repo's autonomous-filing convention.
The DoD's one genuine judgment call — whether "refuses on re-run" counts as
safe — is recorded as a PROCESS item rather than a gate, so a reader can
settle it in place.
