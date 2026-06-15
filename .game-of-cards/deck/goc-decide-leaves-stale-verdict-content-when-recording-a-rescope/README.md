---
title: goc-decide-leaves-stale-verdict-content-when-recording-a-rescope
summary: "`goc decide` records a re-scope/reversal as an appended `## Decision` block and lowers the gate, but never touches the card's existing verdict-bearing content (summary frontmatter, body `> ⚠` banner, DoD wording) or any reference to the card in its advances/advanced_by neighbors. The card is left asserting both the old verdict at the top and the new one at the bottom; `goc validate` reports nothing. The stale top-framing is exactly what an AI agent reads first, so it drives wrong downstream actions (e.g. a near-miss `goc status … disproved` flip against a freshly re-scoped mechanism)."
status: active
stage: null
contribution: medium
created: "2026-06-15T03:40:20Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: `tests/test_decide_rescope_reconciliation.py` asserts that `goc decide <t> --decision "Re-scope: X is viable …" --because "…"` prints a reconciliation reminder naming the card's summary, body banner, and its advances/advanced_by neighbors as NOT auto-updated, and pointing at `goc status … superseded --by …` for a true re-scope.
  - [ ] TDD: the same test asserts a *plain* decision (no re-scope/reversal marker in `--decision`) prints NO reminder (no false positive), and that the reminder lists actual neighbor titles when the card has `advances`/`advanced_by` edges.
  - [ ] TDD: `tests/test_validate_decision_contradicts_verdict.py` asserts `goc validate` emits an advisory `WARN DECISION_CONTRADICTS_VERDICT <title>` for a non-terminal card carrying a resolved `## Decision` whose text matches re-scope/reversal markers over a summary/banner still carrying a strong negative-verdict token — and does NOT emit it for (a) terminal cards, (b) cards whose decision lacks reversal markers, (c) cards whose summary lacks a negative-verdict token. Advisory only: `validate` still exits 0.
  - [ ] MECHANICAL: `goc/engine.py` gains a shared `RESCOPE_MARKERS_RE`; `_cmd_decide` prints the reminder when `--decision` matches; a new `validate_decision_verdict_coherence` advisory validator is wired into `_cmd_validate`'s advisory block (never gates the exit code).
  - [ ] PROCESS: `goc/templates/skills/decide-card/SKILL.md` documents the reconciliation step (reconcile summary/banner/DoD/neighbors after a re-scope, or prefer supersede+create) — edit the template; the sync hook mirrors it.
  - [ ] PROCESS: cross-link the sibling [goc-decide-leaves-prior-decision-block-when-the-body-already-has-one](../goc-decide-leaves-prior-decision-block-when-the-body-already-has-one/) in log.md (adjacent surface: that card dedups duplicate `## Decision` *headings*; this card reconciles the *other* verdict surfaces).
worker: {who: Rodja Trappe, where: main}
---

# goc-decide-leaves-stale-verdict-content-when-recording-a-rescope

## Location

- `goc/engine.py:5028` — `_cmd_decide`. Appends/replaces the `## Decision`
  block, archives the prior `## Decision required` to log.md, flips
  `human_gate → none`, and auto-commits. It never inspects or reconciles
  the card's summary, body banner, DoD wording, or neighbor references.
- `goc/engine.py:3240` — `_cmd_validate`. The "advisory warnings print
  first" block (lines ~3266-3275) has no check for a recorded decision
  that contradicts a still-standing negative verdict on the same card.
- `goc/templates/skills/decide-card/SKILL.md:180-184` — "When NOT to use
  this skill / Decision changes scope" already says a re-scope should go
  through `supersede + create`, but the CLI neither enforces nor reminds.

## What's broken

`goc decide <title> --decision … --because …` is correct for a *first*
decision. But when the decision **reverses or re-scopes a verdict the
card already states**, `decide` updates only:

- ✅ appends a `## Decision` section (`*Resolved …:* <decision>` + `*Reasoning:*`)
- ✅ lowers `human_gate` → `none`
- ✅ auto-commits

…and leaves stale, with no warning:

- ❌ the `summary:` frontmatter (the first thing a triage view / agent reads)
- ❌ any `> ⚠`-style verdict banner in the body
- ❌ DoD-item wording that encodes the old verdict
- ❌ every reference to this card in its `advances` / `advanced_by` neighbors

`goc validate` reports nothing, so the contradiction (a `REFUTED`
summary sitting over a `viable` decision) survives into the record.

## Why it matters

GoC explicitly targets AI-agent collaborators, and the `summary:` +
body banner are exactly what an agent reads first. In a real incident,
a re-scoped card's stale top-framing led an automated sub-agent to
report the card as "refuted" — nearly triggering an incorrect
`goc status … disproved` flip on the very mechanism the live decision
had just re-scoped *toward*. The stale state is not cosmetic: it drives
wrong downstream actions, and it survives `goc validate`, so nothing
catches it before it misleads the next reader.

This is the `goc decide`-specific manifestation of the general "fix
every occurrence when you demote a claim" discipline — but the tool
neither enforces nor reminds it, and the usual statement of that
discipline doesn't cover the cross-card (neighbor-reference)
propagation. Contrast `goc status … superseded --by …`, which already
records a typed bidirectional link so a reader is routed forward;
`goc decide` has no equivalent reconciliation affordance for an
in-place re-scope. That's the gap.

Reachability: any agent or human running the documented re-decide
workflow on a card whose summary/body asserts a verdict produces this
state. The decide-card skill says re-scopes should be `supersede +
create`, but `goc decide` is a CLI verb anyone can call directly.

## Fix (tiered, all three land together)

**Primary — `goc decide` reconciliation reminder (point-of-action guard).**
Add a module-level `RESCOPE_MARKERS_RE` matching re-scope/reversal
language (`re-scope`, `rescope`, `supersede`, `reverse`, `overturn`,
`no longer`, `instead of`, `was wrong`, `now viable`, …). In
`_cmd_decide`, after recording, when `--decision` matches, print a
`⚠` notice that:

- states that `decide` updated only the `## Decision` block + gate;
- lists the card's own verdict-bearing surfaces to reconcile — the
  `summary:` (echo it; flag if it carries a strong negative-verdict
  token), a body `>` banner if present, and DoD wording;
- lists the card's `advances` / `advanced_by` neighbor titles as
  "NOT auto-updated — reconcile references there too" (only when the
  card has such edges);
- points at `goc status <title> superseded --by <new-card>` as the
  sanctioned path for a *true* re-scope.

**Primary — skill documentation.** Document the reconciliation step in
`decide-card/SKILL.md` so an agent recording a re-scope doesn't stop at
the appended block. Edit the template; the sync hook mirrors it.

**Secondary — `goc validate` advisory lint (safety net for the record).**
A new `validate_decision_verdict_coherence(cards)` returning
`BlockerWarning`s, wired into the advisory block of `_cmd_validate`
(never affects the exit code). Tight, low-false-positive trigger —
flag a card only when ALL hold:

- the card is **non-terminal** (terminal cards legitimately carry a
  negative verdict — a `disproved` card *should* say REFUTED);
- its body has a **resolved `## Decision`** block (not `## Decision
  required`);
- that decision text **matches `RESCOPE_MARKERS_RE`** (the same regex
  the reminder uses — a normal "go with B" decision won't match); and
- the **summary or a body banner still carries a strong negative-verdict
  token** (`REFUTED`, `disproved`, `does not work`, `unviable`,
  `do not pursue`, …).

Requiring the decision to *literally* contain reversal language AND a
still-negative summary makes this precise enough to ship as advisory
without spamming this repo's own `goc validate`.

## Notes

- Reuse the existing `BlockerWarning` advisory pattern and the
  "advisory warnings print first" wiring; do not add an exit-gating error.
- Keep the reminder’s neighbor list edge-aware: print the neighbor
  bullet only when `advances`/`advanced_by` is non-empty.
- No new schema fields; no migration. Reminder is print-only; lint is
  advisory-only.
