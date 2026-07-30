---
title: a-shared-tag-groups-a-cluster-that-no-edge-walk-can-reach
status: open
stage: null
contribution: high
created: "2026-07-30T04:55:33Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [api-contract, meta-fix, documentation]
draft: false
summary: |-
  The schema tells a governing card - one that closes when *decided*, independent of the work it
  standardizes - to group its cluster with a shared tag and no `advances` edge. That prescription is
  correct: no edge direction models the relationship without deadlocking or contradicting the
  decision's independence. It also has a consequence nothing warns about. A tag is invisible to every
  edge walk in the tool, so the moment the grouping becomes a tag, the cluster stops being reachable
  from any card in it. Observed in a consuming repository on 2026-07-30: a governing card retracted
  its seven grouping edges so `goc done` would accept it, regrouped by tag as prescribed, and became
  unfindable - 22 cards carried the tag and a later umbrella card on the same subject cited none of
  them, re-deriving results that were already measured and closed. `goc validate` was clean
  throughout, because referential integrity proves the edges that exist resolve and cannot see a
  grouping that has no edges at all. This card states the problem and sketches options; it decides
  nothing.
definition_of_done: |
  - [ ] PROCESS: decide whether this is GoC's problem to solve or a documentation duty. Either a
        mechanism ships, or the schema's edge-versus-tag fork gains an explicit warning that a tag
        grouping is unreachable by traversal and what the author should do instead. Both are
        defensible; the card exists to force the choice rather than to make it.
  - [ ] MECHANICAL: whichever way the decision goes, the edge-versus-tag fork in `card-schema`
        states the traversal consequence at the point of choosing. Today it names the correctness
        reason for a tag and is silent on the discoverability cost, so an author following it
        correctly cannot know what they gave up.
  - [ ] TDD: if a mechanism ships, it needs a red witness on a real shape - a set of cards sharing a
        tag with no edge among them, against a control set that shares a tag AND an edge, so a green
        run is a claim about reachability rather than about tags existing.
  - [ ] PROCESS: record the false-positive rate before any mechanism becomes a gate. A tag with no
        edges is often correct - `bug` is not a cluster. Whatever is proposed must say which tags it
        would fire on and why that is a question worth asking rather than noise.
  - [ ] PROCESS: state explicitly whether `goc done`'s `advanced-by-closed` behaviour is in scope.
        A consuming repository proposed loosening it so a governing card could keep its edges. That
        is a different fix with different risks and it is named in "Options" below so the decision
        can reject or adopt it deliberately rather than by omission.
worker: Claude
---

# A shared tag groups a cluster that no edge walk can reach

## The problem

`card-schema` gives three shapes for a card that coordinates other work. For a **governing
cluster** — a decision or standard-setting card that closes when *decided*, independent of
whether the cluster's work is finished — the prescription is a **shared tag and no `advances`
edge in either direction**.

That prescription is right, and the reasoning holds. `epic.advances: [children]` inverts the
value law. `child.advances: [governing card]` says the governing card's value chain includes
the cluster's work, which for a decision card is false — it closes on its own deliverable. So
no edge direction models the relationship.

**What nothing says is that the tag is unreachable.** Every relationship walk in the tool
follows `advances` / `advanced_by`. Value composition, dependency readiness, the board's
blocked display, the overlap detector's distance metric — all of them traverse edges. A tag is
a filter, not an edge. So at the moment an author follows the guidance correctly, the cluster
stops being reachable from any card inside it.

`goc validate` cannot see this. Referential integrity proves that every edge which *exists*
resolves; it has no way to notice a grouping that deliberately has no edges.

## The observed instance

In a consuming repository, 2026-07-30:

- A governing card had seven grouping `advanced_by` edges. `goc done` refused it, correctly, on
  `advanced-by-closed`.
- The author took the documented resolution: retract the false edges with `goc unadvance`,
  regroup by shared tag. Its own closure note records this.
- The tag accumulated **22 cards** on that subject.
- Two months later a new umbrella card was filed on the same subject and cited **none** of
  them — not by edge, not in prose. Nine of them bore directly on its open questions. One had
  already answered a desk test the umbrella listed as unrun. Seven had no typed edge to any
  card in the deck.
- Cost: a subagent sweep and roughly 900k tokens to rediscover what was on disk, and two
  reviewers reported "nobody has built this" with confidence about work that was built and
  closed.

The failure is not that anyone broke a rule. Everyone followed the rule.

## Why the existing overlap detector does not catch it

Worth stating so a reader does not assume the tool already covers this. Two independent
reasons, both measured on the consuming repository's deck:

1. **It excludes terminal cards by default** — 799 non-terminal of 1844. Seven of the nine
   missed cards were `done`, so they were never candidates. An `--include-terminal` flag exists
   and is off by default.
2. **Its similarity metric is shared rare tokens** — identifiers, config keys, revision hashes.
   Two lanes that use different words for the same concept share no rare tokens by
   construction, which is precisely the case the detector exists to catch. A seeded probe on
   the umbrella card returned `0 disconnected pair(s) reported out of 1 above the similarity
   floor`.

So a clean overlap run is not evidence of no overlap, and that is worth knowing independently
of whatever this card decides.

## Options, not a recommendation

These are sketches to be argued over. No option is endorsed here, and the first
Definition-of-Done item owns the choice.

**1. A tag-cohort report.** For each tag, report cards that share it with no `advances` path
between them. Report-only, in the stance `validate` already uses for advisory hints — a hit is
a question, not a defect. Attractive because it needs no vocabulary overlap and no new schema.
Open questions: which tags are cluster-shaped versus categorical (`bug` is not a cluster), and
whether the output volume is readable. Note that in the consuming repository `goc validate`
already emits **150** `WARN` lines, so an advisory that lands in that stream may not be read —
whatever ships needs a channel, not just a check.

**2. A third relation field for grouping.** A `groups` / `grouped_by` pair that traversal can
follow but neither value composition nor `advanced-by-closed` gates on. Models the relationship
honestly instead of overloading tags. Cost: a schema addition, a migration story for existing
tag groupings, and a fourth edge field for `validate` to keep consistent — the deck already has
a card noting that cycle detectors walk different edge fields, which is the maintenance shape
this would add to.

**3. Make tags first-class in traversal.** Treat tag co-membership as a zero-weight edge inside
the walks that answer "what else is about this?", while leaving value composition on `advances`
alone. No schema change. Cost: every categorical tag becomes a clique, so the distance metric
degrades unless cluster tags are distinguished from categorical ones — which is option 1's open
question, promoted to a requirement.

**4. Documentation only.** State the traversal consequence at the edge-versus-tag fork and give
the author a workaround to apply by hand — for example, an explicit prose index on the governing
card listing its cluster. Cheapest, and it fails the same way the original guidance did: it
depends on the author knowing to look, at the moment they are being told the tag is correct.

**5. Loosen `advanced-by-closed` so a governing card can keep its edges.** Proposed by the
consuming repository. Recorded here for completeness and because a decision should reject it
deliberately rather than by omission. Two arguments against, both worth weighing rather than
treating as settled: the edges would still be semantically wrong under the value-chain identity,
and a genuine aggregation epic could then close with its work outstanding. The argument for is
that losing track of completed work has now cost more than a false closure would have.

## Non-goals

- Not a claim that the edge-versus-tag fork is wrong. Its correctness argument stands and is
  not re-litigated here.
- Not a change to `goc validate`'s referential-integrity contract. That property works; this is
  about a relationship that is deliberately edgeless.
- Not a fix for the overlap detector's similarity metric or its terminal-card default. Those are
  named because they explain why the gap survived, and they are separable work.

## Cross-references

- [[no-guardrail-for-canonical-epic-edge-direction]] — where the governing-cluster shape and the
  shared-tag prescription were decided (closed 2026-05-26). This card is later evidence about a
  consequence of that decision, not a dispute with it.
- [[relationship-modeling-has-no-discoverable-home]] — made `advance-card` the home for
  relationship modelling. If option 4 or the second Definition-of-Done item is taken, that is
  where the warning belongs.
