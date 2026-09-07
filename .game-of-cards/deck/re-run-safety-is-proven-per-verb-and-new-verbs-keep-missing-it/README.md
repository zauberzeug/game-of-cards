---
title: re-run-safety-is-proven-per-verb-and-new-verbs-keep-missing-it
summary: "Seven cards fixed an operation that was correct on its first run and wrong on its second — install, done, kickoff, upgrade, the settings merge twice, and refine-deck's citation-repair recipe — each found in production, each shipping a test for that one surface, so re-run safety was coverage a verb earned only after a defect bit it. `tests/test_verb_rerun_safety.py` now enforces it as a class over all nineteen surfaces goc registers, deriving the list from the engine parser plus `cli.INSTALL_VERBS` so a verb added tomorrow fails the recipe check instead of inheriting nothing. Each surface declares its second-run shape; refusal turns out not to be the safety property, preserving recorded state is."
status: done
stage: null
contribution: medium
created: "2026-08-17T03:14:22Z"
closed_at: "2026-08-17T05:31:23Z"
human_gate: none
advances: []
advanced_by:
  - second-citation-repair-pass-moves-correct-cites-onto-unrelated-code
tags: [bug, test, meta-fix]
definition_of_done: |
  - [x] TDD: a class-level re-run test lands in `tests/` — it derives the verb list rather than enumerating it by hand, runs each mutating verb twice against a scratch deck, and asserts the second run either leaves the deck byte-identical or refuses. `reproduce.py` exits zero once it exists.
  - [x] TDD: the new test proves it can catch an offender — a deliberately non-idempotent verb (or a stubbed one) makes it fail, per `static-source-guards-never-prove-they-can-catch-an-offender`. A guard that only ever sees a clean tree is indistinguishable from one that stopped running.
  - [x] MECHANICAL: the verb list is derived from the engine's own parser registration, so a verb added tomorrow is covered without anyone remembering to add it. Hard-coding the list reproduces the defect this card describes.
  - [x] PROCESS: decide and record in `log.md` whether "refuses on the second run" counts as safe for every verb or only for the ones where refusing is the documented contract — today `decide` and `move` exit 2 on re-run and that is correct, while `publish` exiting 2 on an unauthored scaffold is a different thing entirely.
  - [x] PROCESS: the non-verb surfaces in the instance list (the `goc install` / `goc upgrade` entry points and `_merge_claude_settings`) are either brought under the same check or explicitly scoped out with a reason.
  - [x] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass.
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

## What was broken

Re-run safety was a property every one of these surfaces was expected to
have and none of them was asked to prove. Each fix shipped a test for its
own surface, which is right, and no fix could have covered the next
surface, which was the problem. The property was enforced one verb at a
time, in arrears, so a verb added tomorrow inherited nothing.

The census made the gap concrete. Of the fourteen mutating verbs the
engine registers, exactly one — `repair-edges` — carried a test whose name
said it re-ran the verb; the other thirteen were unpinned. That was not the
same as broken. Probing each verb by running it twice against a scratch
deck, every one was stable. **No live re-run defect was ever claimed here.**
The finding was that the deck's being in good shape on this axis was not
load-bearing on anything: no test asserted it, so the next refactor that
broke it would be discovered the way the previous seven were.

## What now holds

`tests/test_verb_rerun_safety.py` runs every surface goc registers twice
against a scratch repo and asserts the second run preserves recorded state.
The list is derived from two places, not written down: the engine parser's
subparser registry, plus `cli.INSTALL_VERBS` for the two verbs `goc/cli.py`
intercepts on `argv[0]` before the parser exists. Nineteen surfaces are
covered. A verb added tomorrow has no row in the recipe table and fails
`test_every_registered_surface_has_a_rerun_recipe`, which is the point.

Each surface declares its second-run shape in one word — `READ_ONLY`,
`NO_OP`, `REFUSES`, `RE_EMITS` or `APPENDS`. `log.md` carries the reasoning
and the per-verb assignment; the short version is that **refusal is not the
safety property**. Preserving recorded state is, and refusal is one way to
get there. Exit codes are pinned coarsely (zero versus nonzero) so a verb
flipping between refusing and no-op reddens the build, while the exact code
stays the per-verb test's business.

Two clauses earn their keep and are worth knowing about before editing the
table. A same-bytes rewrite counts as a change, because the two runs land
in the same wall-clock second and a re-stamped `closed_at` — instance 2
above — otherwise compares byte-equal. And `attest` is append-only rather
than idempotent: `log.md` is a journal, so its check is that the second run
extends the record instead of rewriting it.

## Empirical evidence

`reproduce.py` prints the instance roster, the static census and the
dynamic probe, and exits 1 unless `tests/` carries a module that covers the
whole registered verb set and passes.

Two false-positive stories from building this are worth keeping, because
both are instances of a *different* family this deck tracks. The census's
first draft matched the re-run signal anywhere in a test's body and
reported **4/14** coverage — three false positives, including a `yaml_lite`
parser test that scored as coverage for `goc status` because it quotes
`"status"` as a frontmatter key. Requiring the signal in the test's name
and requiring the body to drive the CLI brought it to a true 1/14. Then the
rewritten "does the class-level check exist yet" detector, still
grep-shaped, nominated `tests/test_guidance_accuracy.py`; it now requires a
module carrying a table keyed by exactly the registered verb set, and runs
that module for the verdict. A grep-shaped guard that over-reports coverage
is the failure
[static-source-guards-never-prove-they-can-catch-an-offender](../static-source-guards-never-prove-they-can-catch-an-offender/)
describes, which is why this card's DoD asked the new test to demonstrate
it can go red — and why the guard is now shown to redden three separate
ways: five stub surfaces (one per clause), a synthetic `frobnicate`
subparser, and the reintroduced `done` re-stamp.

The census still reads 1/14 and should. It counts per-verb re-run tests,
which is a different measurement from the one class-level check that now
covers all of them.

## Why it mattered

The cost was not the seven fixes — those were cheap individually. It was
that the seventh was found the same way as the first, with no accumulated
defence in between.

The most recent instance shows what that costs. The citation-repair recipe
was correct on the pass that introduced it and corrupting on the pass
after; had it not been caught by hand during the 2026-08-17 hygiene pass,
it would have rewritten 165 correct citations onto unrelated code and each
subsequent pass would have tracked the corruption faithfully forward. The
class-level check does not catch that one — the recipe lives in a skill
body, not a verb — and skill bodies are scoped out deliberately, with the
reason recorded in `log.md`: there is no process to run twice and no exit
code to read, so prose an agent executes needs a different mechanism.

## Relationship to the instances

The seven instances stay closed; they are cited here as the evidence for
the family, not as work to redo. The last of them,
[second-citation-repair-pass-moves-correct-cites-onto-unrelated-code](../second-citation-repair-pass-moves-correct-cites-onto-unrelated-code/),
carries an `advances` edge to this card: a class-level re-run guard could
not ship green while a known re-run defect was still open, and it closed
first.

Filed at `human_gate: none` per this repo's autonomous-filing convention.
The DoD's two genuine judgment calls — whether "refuses on re-run" counts
as safe, and which non-verb surfaces come under the check — were recorded
as PROCESS items rather than a gate, and both are settled in `log.md`.
