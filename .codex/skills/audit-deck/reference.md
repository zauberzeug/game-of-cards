# audit-deck reference — probes, rationale, and edge cases

Companion to `SKILL.md`. Each section below is routed from the core
skill; read the one that matches the situation at hand.

## Rationale

XP's **spike** (Beck, 1999) plus Scrum's **backlog refinement**: the
deck only contains what we've already noticed. Every iteration must
close the gap between what's known and what's documented — otherwise
the read-pattern guarantee silently rots as code drifts away from the
filed cards. Treat nothing as truth — neither code, comments, docs,
nor the deck itself; **inconsistencies and contradictions are the
primary lead**.

"Ugly architecture" (mechanism in the wrong module, modules that
must be detached together, double-counted concerns, five special
cases hiding one rule) signals a missing abstraction and counts as
a defect. "I looked and didn't find anything" is a failure mode,
not an acceptable outcome.

## Typical probe recipes

The consuming repo defines its probe recipe in
`.game-of-cards/hooks/audit-deck.md`. Typical probes:

- **Metrics probe (steady-state):** run the canonical demo / test
  suite for a few seeds in parallel; compare to a baseline metrics
  table; flag divergence ≥ 2σ as a candidate.
- **Boundary-exercise probe:** snapshot state, hit reset / freeze /
  checkpoint surfaces, diff. Silent state-leaks live here.
- **Introspection-trace probe:** run any project-specific trace
  tool, triage `[FAIL]` / `nan` / `inf` / discontinuity hits.

## Consulting the project rubric on decision-shaped candidates

The mindset bullets in the core skill are for _rapid hunt triage_.
When a candidate touches a substantive design decision (mechanism
choice, sign convention, default anchored to a project principle) —
and especially when the right gate for the new card is unclear —
consult the consuming repo's project-specific rubric (wired in via
`.game-of-cards/hooks/audit-deck.md`, loaded in the core skill). The
rubric often reveals that what looks like a fresh decision is already
determined by an existing principle + primary source, in which case
the card can be filed with `--gate none` and a `## Decision
(rubric-derived)` body section (see `Skill(create-card)` Step 3).
Keeps the human out of the loop when project-specific reasoning is
decisive.

## Reachability paths (`## Why it matters`)

For parser / emitter / serializer / storage-layer defects, the card
body must name a path that produces the offending input — "the
emitter at `engine.py:NNN` writes this," "a one-shot-authored card
produced it," or the concrete consumer flow that surfaces the bug.
Without a reachability path, a card describes a theoretical defect;
with one, the next reader can tell whether the input shape actually
flows through shipping code (or is only hypothetically possible).
This convention is already current good practice — making it explicit
keeps audits from drifting back into theoretical-bug territory.

## Park-or-disprove: bounds and escape valve

The park-or-disprove rule applies even when the round produces a
confirmed defect. The "zero confirmed → ≥1 unverified" rule is the
_minimum_; park-or-disprove is the _maximum-amnesia bound_.

The only escape valve: an agent claim that's clearly hallucinated
(file path doesn't exist, symbol doesn't appear via `grep`) AND
has no underlying substance can be silently dropped.

If zero confirmed defects after a round, restart Phase 2 with
different agents and seams. After the restart: if still zero, the
round must produce ≥1 unverified entry before reporting empty.

## Canonical commit subject

Every audit-deck commit uses:

```
new card: <one-line description of the finding(s)>
```

Detail (contribution, tags, agent attribution) goes in the commit body,
not the subject. The subject must NOT contain iteration counters,
round labels, absolute dates, or trigger-mode tags. The git log
itself records timestamps; the subject doesn't need to.
