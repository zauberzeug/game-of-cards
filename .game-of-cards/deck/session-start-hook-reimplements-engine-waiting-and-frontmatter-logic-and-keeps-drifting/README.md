---
title: session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting
summary: "META-FIX. The Python SessionStart hook (goc/templates/hooks/deck_session_start.py) hand-reimplements several engine predicates — frontmatter scalar/null/comment parsing, waiting_impedes, and the waiting_until instant parse — because it must run dependency-free from any working tree. They drift from the engine one bug at a time: 7+ instances fixed as separate cards, each caught only by a hand-written matrix test, never by a guard derived from the engine. Decide a systematic parity guard."
status: open
stage: null
contribution: medium
created: "2026-06-20T05:10:32Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - session-start-hook-frames-waiting-on-active-cards-as-resumable
  - session-start-hook-impeded-check-ignores-elapsed-waiting-until
  - session-start-hook-treats-malformed-bare-waiting-until-as-not-impeded
  - session-start-hook-treats-non-canonical-waiting-on-as-not-impeded
  - session-start-hook-misreads-same-day-datetime-waiting-until-as-not-impeded
  - deck-session-start-hook-misreads-frontmatter-fields-with-inline-yaml-comments
  - deck-session-start-hook-strips-quotes-asymmetrically-across-frontmatter-readers
  - session-start-hook-treats-explicit-yaml-null-waiting-fields-as-impediment
  - session-start-hook-treats-coerced-bool-or-int-waiting-on-as-impediment
  - session-start-hook-over-coerces-quoted-waiting-scalars-to-absent
  - session-start-hook-comment-stripper-truncates-quoted-scalar-with-internal-hash
tags: [meta-fix, infra, api-contract]
definition_of_done: |
  - [ ] (replace after the decision is recorded)
---

# The Python SessionStart hook reimplements engine logic and keeps drifting

## The recurring shape

`goc/templates/hooks/deck_session_start.py` runs at session start to decide
which active cards are resumable vs. parked vs. impeded. It is **deliberately
dependency-free** — it reads each `README.md` with its own mini-frontmatter
parser rather than importing `goc.engine`, so it works from any working-tree
shape (plugin payload, fresh clone, no installed package). The cost of that
independence: it **hand-reimplements engine semantics**, and those copies drift
from the engine one bug at a time.

The predicates currently re-derived by hand:

- `_is_impeded` ⟷ `goc.engine.waiting_impedes`
- `_parse_waiting_until` ⟷ `goc.engine._waiting_until_instant` (+ ISO regexes)
- `_frontmatter_tail` / `_scalar_or_none` ⟷ `goc._vendor.yaml_lite` scalar,
  inline-comment, quote, and `_NULL_SET` resolution

Each cell has drifted and been fixed as its own one-off card, never caught by a
guard derived from the engine:

1. `session-start-hook-frames-waiting-on-active-cards-as-resumable` (done) —
   the overlay was ignored entirely.
2. `session-start-hook-impeded-check-ignores-elapsed-waiting-until` (done).
3. `session-start-hook-treats-malformed-bare-waiting-until-as-not-impeded`
   (done, meta-fix) — `until_unparseable` backstop.
4. `session-start-hook-treats-non-canonical-waiting-on-as-not-impeded`
   (done, meta-fix) — `reason is not None` gate.
5. `session-start-hook-misreads-same-day-datetime-waiting-until-as-not-impeded`
   (done) — full UTC-instant precision vs. date truncation.
6. `deck-session-start-hook-misreads-frontmatter-fields-with-inline-yaml-comments`
   (done).
7. `deck-session-start-hook-strips-quotes-asymmetrically-across-frontmatter-readers`
   (done).
8. `session-start-hook-treats-explicit-yaml-null-waiting-fields-as-impediment`
   (done) — `_NULL_SET` literals (`null`/`~`/`Null`/`NULL`) were read as a live
   reason. **This card was filed from the pattern-generalization check on
   instance #8.**

The only guard is the hand-written cell list in
`tests/test_session_start_hook.py`: it asserts a fixed set of cases someone
remembered to add. It is not derived from the engine, so a new engine behavior
(or a newly-touched predicate) is invisible until a human extends it.

## Sibling families (same shape, other surfaces)

This is the same "reimplements the same logic and keeps drifting" shape the deck
already tracks elsewhere — and the SessionStart hook is the *upstream reference*
for the OpenClaw TS port, so its drift propagates downstream:

- [openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting](../openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting/)
  — the TS port in `index.ts` mirrors *this* hook plus the engine; downstream of this card.
- [goc-waiting-filter-drifts-from-engine-on-elapsed-and-bare-waits](../goc-waiting-filter-drifts-from-engine-on-elapsed-and-bare-waits/)
  and [standup-impeded-filter-drifts-from-engine-on-elapsed-and-bare-waits](../standup-impeded-filter-drifts-from-engine-on-elapsed-and-bare-waits/)
  — other consumers re-deriving `waiting_impedes`.
- [yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting](../yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting/),
  [dod-fence-mask-reimplements-commonmark-fences-and-keeps-drifting](../dod-fence-mask-reimplements-commonmark-fences-and-keeps-drifting/),
  [frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting](../frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting/)
  — the broader "reenumerate the parser and drift" family.

## Why it matters

These predicates gate the first thing an agent sees on resume: whether it owns
a card or must stand down. Every silent drift either hides a card the agent
should resume or frames a resumable card as impeded — exactly the failure modes
the 8 instances above each fixed after the fact. The independence constraint is
real (the hook cannot import `goc.engine`), so "just call the engine" is not
available; the fix needs a deliberate parity mechanism.

## Decision required

What systematic guard replaces "fix each drift as its own card"? Credible
options, all constrained by the hook's dependency-free runtime requirement:

1. **Engine-derived parity test.** A regression test that, for a generated
   matrix of frontmatter inputs, asserts `_is_impeded(readme) ==
   engine.waiting_impedes(load_card(...))` and `_card_*` readers agree with the
   engine's parsed `Card` fields. The test imports the engine (tests may); the
   shipped hook stays dependency-free. Catches future drift without changing the
   runtime shape. Lowest-risk; does not de-duplicate the code.
2. **Vendor a shared minimal module.** Extract the scalar/null/comment/quote +
   `waiting_impedes` core into a tiny no-dependency module vendored into the hook
   payload (like `goc/_vendor/yaml_lite.py`), imported by both the engine and
   the hook. Removes the duplication but adds a vendoring/sync surface.
3. **Codegen the hook from the engine.** Generate the predicates at
   build/sync time from a single source. Strongest guarantee, heaviest
   machinery.

Pick the mechanism (and its scope: this hook only, or unify with the OpenClaw
TS port and the CLI/standup filter consumers under one parity harness), then
replace this DoD with the implementation criteria.
