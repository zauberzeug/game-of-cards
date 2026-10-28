## 2026-06-25 — gate raised to `decision` (pull-card)

An autonomous pull-card pass pulled this epic (the only ready card) and
found it is not drainable autonomously: DoD item 1 is a shared-shape
API-contract taste call, and all eight `advanced_by` children carry
their own `human_gate: decision`. No project-local consultation hook is
defined (`.game-of-cards/hooks/pull-card.md` is empty), so per the
pull-card Andon contract the gate was raised to `decision` rather than
guessing the contract.

Added a `## Decision required` section recording the three candidate
shapes (strict-refuse exit 2 / exit-0 stderr WARNING / honest no-op
success line) plus the factoring sub-decision, and surfaced the strong
codebase-internal default: `_cmd_advance` already strict-refuses the
self-target and cycle cases (`engine.py:5233`, `:5237`) and the engine
uniformly uses `goc: error: …` + `sys.exit(2)` for invalid input
(`:2496`, `:2510`, `:3437`, …). Recommended strict-refuse so the
shared-shape decision is a quick confirmation, not an open design space.

No code changed. The eight children remain open; this epic is parked
awaiting the shared-shape decision.

## 2026-08-26T04:43:42Z: ninth child wired — goc-wait-with-a-past-until-date-leaves-the-card-in-the-queue

An audit pass (queue empty of `human_gate: none` work) found a new instance
of this family and wired it in rather than filing it beside the epic:
`goc wait <t> --until <date already elapsed>` writes the overlay, prints the
same success line a live wait gets, and auto-commits — while
`waiting_impedes` reads the elapsed `waiting_until` as non-impeding, so the
card stays in `--ready` and out of `--waiting`. The everyday form is a bare
`--until <today>`: `_waiting_until_instant` resolves `YYYY-MM-DD` to midnight
UTC, so it is elapsed at every moment of the day it names.

Dashboard updated in place: the roster gained a bullet, and the eight-child
counts in the summary, DoD item 2, `## Decision required` and `## Why it
matters` now read nine. The "found these eight" sentence under
`## How this card was surfaced` is left at eight — it describes what the
2026-06-25 refine-deck pass saw, not the current roster.

Also corrected a stale claim in `## Scope notes`: it still said "This epic is
filed at `human_gate: none`" while the frontmatter has read `decision` since
the 2026-06-25 pull-card pass raised it (as `## Decision required` already
recorded). Rewritten in place to state the gate history rather than contradict
the frontmatter.

No code changed. The shared-shape decision remains the blocker for all nine.

## 2026-06-25T01:36:42Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

This epic cannot be drained by an autonomous puller: its DoD requires a
shared validation-failure-shape decision (DoD item 1) **and** closing
all nine children — each of which carries its own `human_gate:
decision` per-verb option menu. The gate was raised here (by a
2026-06-25 pull-card pass) precisely to record the shared-shape bundle
before authorising a single implementation series, exactly as the
original scope note anticipated. A human (or a session with authority
to make API-contract taste calls) needs to pick **one** shared shape so
the nine children stop re-deriving it nine ways.

### The three candidate shapes (DoD item 1)

1. **Strict-refuse** — print `goc: error: <reason>` (or `ERROR: …`) to
   stderr, mutate nothing, `sys.exit(2)`.
2. **Exit-0-with-stderr-WARNING** — perform/skip as today but emit a
   `WARNING:` line to stderr; exit stays 0.
3. **Distinct no-op success message** — exit 0, but the stdout line
   honestly states no mutation occurred (e.g. `advance: edge already
   exists; no change`).

### Recommended default: strict-refuse (exit 2)

The codebase already establishes strict-refuse as *the* precondition-
failure shape, so this is a small confirmation rather than an open
design space:

- `_cmd_advance` already rejects a self-target with
  `print("ERROR: cannot advance a card with itself", file=sys.stderr);
  sys.exit(2)` and rejects a would-be cycle the same way
  (`goc/engine.py:6572`, `:5237`). The
  `goc-unadvance-with-self-target` child is literally asking for the
  symmetric guard `advance` already has.
- Argument/precondition errors throughout `engine.py` use the
  `print("goc: error: …", file=sys.stderr); sys.exit(2)` pattern
  (`:2496`, `:2510`, `:2541`, `:3437`, `:3463`, …); exit 1 is reserved
  for validation-graph failures and exit 3 for FATAL schema/IO.
- Strict-refuse is the only shape that protects the `--commit`-driven
  scripts and agents the "Why it matters" section names: a non-zero
  exit is the contract those callers already check.

The two no-op-success siblings (`advance`/`unadvance` redundant edge)
want one shape applied symmetrically to BOTH directions; strict-refuse
satisfies that (redundant add → exit 2; redundant remove → exit 2).

### Factoring sub-decision (also DoD item 1)

A reusable helper (e.g. `_refuse(reason: str)` that prints
`goc: error: {reason}` and `sys.exit(2)`) vs. per-verb inline checks.
Recommendation: a one-line helper for the message+exit, with the
*precondition predicate* inline per verb (each verb's invalid-input
test is verb-specific — redundant edge, empty string, mode conflict,
non-active transition — so only the failure emission is shared).

**To proceed:** `Skill(decide-card)
mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success
--decision "<shape + factoring>" --because "<why>"`, then a follow-on
series can close the nine children under the recorded shape.


## 2026-10-22T05:20:21Z: decision recorded

1. Strict-refuse: invalid input exits 2 with a goc error on stderr and mutates nothing; factoring per the card's recommendation, a one-line shared helper for the message and exit with the precondition predicates inline per verb — The maintainer accepted the card's recommendation in a human session on 2026-10-22; strict-refuse is the precondition-failure shape the engine already uses (exit 2) and the only one that protects --commit-driven scripts and agents. Gate decision → none.


## 2026-10-28: first child closed — shared helper landed

`goc-unadvance-claims-success-when-removing-a-non-existent-edge` closed under
the decided shape. It introduced the emission helper this card's decision
prescribed, `engine._refuse_invalid_input(reason)` (`ERROR: <reason>` on
stderr, exit 2 — `ERROR:` rather than `goc: error:`, because every mutation
verb's precondition refusal already printed it and `goc: error:` is the
query-flag parser's), and routed `_cmd_advance`'s existing self-edge and
cycle refusals through it with byte-identical output. The family's tests
start in `tests/test_mutation_verbs_refuse_invalid_input.py`.

Checked on the way, as the unadvance card's archived deliberation asked:
`goc wait --clear` on a card with no overlay already prints `<title>: no
waiting overlay to clear; nothing to do`, exits 0 and writes nothing — an
honest no-op, not the misleading success this family refuses — so it was
left as is.

Dashboard updated in place: the unadvance roster bullet carries its closure,
the roster heading no longer says "open", the summary no longer counts nine
*open* children, and `### How the decision reached the children` names the
helper and the test module.
