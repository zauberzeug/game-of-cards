---
title: goc-decide-loses-deliberation-history-by-not-archiving-replaced-section
summary: "`goc decide` replaces the README's `## Decision required` section with the resolved `## Decision` block (correct dashboard behaviour) but writes only a one-line entry to log.md, losing the deliberation context (original options, agent recommendation, trade-offs). README is the dashboard, log.md is the journal — the engine should archive the replaced content to log.md before/during the replacement. Scope decision needed: decide-only fix, generalised engine convention, or skill-workflow-only fix."
status: done
stage: null
contribution: medium
created: "2026-05-23T05:06:53Z"
closed_at: "2026-05-26T20:02:24Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] `goc decide` archives the prior `## Decision required` section content to log.md as a dated entry that precedes the new "decision recorded" entry chronologically.
  - [x] log.md after `goc decide` reads as a timeline: (filing date) options enumerated → (decision date) decision recorded.
  - [x] No README content is lost — dashboard reflects current state, journal preserves the path that led there.
  - [x] Test coverage: file a card with a `## Decision required` section, run `goc decide`, assert log.md contains both the archival entry AND the resolution entry; assert README contains only the resolved `## Decision`.
  - [x] `goc/templates/skills/decide-card/SKILL.md` "What this skill does to the card" subsection updates to describe the new dual-write behaviour (README replaced; log.md archives prior section AND records resolution).
  - [x] MOOT — scope decision picked Option A (decide-only fix), not Option B; no `goc archive-section` helper is built. Deferred until a second section-replacing caller appears.
worker: {who: "claude[bot]", where: main}
---

# goc-decide-loses-deliberation-history-by-not-archiving-replaced-section

## Location

- `goc/engine.py` — the `goc decide` command implementation (the `## Decision required` → `## Decision` rewrite + one-line log.md append).
- `goc/templates/skills/decide-card/SKILL.md` "What this skill does to the card" subsection — Step 1 (README replacement), Step 2 (log.md append).

## What's broken

`goc decide` enforces the README-as-dashboard convention correctly: it replaces `## Decision required` with the resolved `## Decision` block so the README always reflects the current decision state. The dashboard half works.

The journal half is missing. The current skill description says:

```
2. **log.md.** Appends one entry:

   ## YYYY-MM-DD: decision recorded

   <decision> — <reason>. Gate <prior> → none.
```

That entry records the outcome, not the deliberation. The original options considered, the agent's recommendation (which may have been overridden), the trade-offs surfaced when the card was filed — all of that lives only in the just-replaced README section, which is now gone. When a future reader opens the card cold, they see the chosen option but no record of what was considered or rejected.

This violates the documented "What goes where" convention in `Skill(card-schema)`: README is the live dashboard (rewritten in place each round), log.md is the chronological journal (append-only, preserves history). The convention is documented but not engine-enforced for `goc decide`.

## Empirical evidence

The just-completed flow on the predecessor card `refine-deck-drops-structural-findings-by-defaulting-to-propose-not-file` exhibited the defect. The card was filed with a `## Decision required` section enumerating four options (A: full audit-deck mirror, B: Step 4.5 audit only, C: per-category rules — recommended, D: defer) plus an agent recommendation. After `goc decide`, the README showed only the resolved Option A; log.md contained only:

```
## 2026-05-23T04:49:36Z: decision recorded

Apply Option A — ... Gate decision → none.
```

The four options and the recommendation were unrecoverable from the card itself — they had to be reconstructed and manually prepended to log.md as a separate commit (`chore(deck): archive Decision-required deliberation in log.md`, commit `674cc5e`). That commit is the manual workaround this card replaces.

## Why it matters

- **Audit-deck pattern detection cost.** The pattern "agent recommends X, user picks Y" is a high-signal observation for the audit-deck skill (it shows where agent rubrics misalign with human judgement). If only the resolution is recorded in log.md, that pattern is invisible across the deck.
- **Cold-read cost.** Cards are designed to be picked up cold by future readers (per `Skill(create-card)`'s opening: "a self-contained briefing for the next reader"). A decided card with no deliberation history is half a briefing — the *what* without the *why-not*.
- **Half-enforced convention.** The README-as-dashboard / log.md-as-journal split is documented in `Skill(card-schema)` and enforced in some places (e.g., status-flip verbs add log.md entries for state transitions) but not for the decision-section replacement that `goc decide` performs. This is the same shape as `audit-deck`'s mature Phase 3 "Park-or-disprove" discipline vs `refine-deck`'s missing equivalent (the topic of the predecessor card) — a convention that's a contract in name only until the engine makes it one.

## Decision

*Resolved 2026-05-26T12:10:35Z:* Option A — goc decide-specific archival. Modify goc decide in engine.py to append the prior Decision-required section content to log.md as a dated archive entry before replacing it in the README, and update the decide-card SKILL.md to document the dual-write behaviour (README replaced; log.md archives prior section AND records resolution).

*Reasoning:* Minimum-viable fix that lands the discipline at the engine level for the one confirmed caller; narrow blast radius and easy to test. The generalised archive-section helper (Option B) is deferred until a second section-replacing caller appears.
## Notes on fix scope

The skill body section in `goc/templates/skills/decide-card/SKILL.md` describing "What this skill does to the card" already documents Step 1 (README replace) and Step 2 (log.md append). Option A's fix updates Step 2's description to "Archives the prior section content AND records the resolution" — both entries dated, the archive entry timestamped from the card's `created` field (so the chronology of log.md reads filed → decided), the resolution entry timestamped from the decide call.

The fix is **additive** for existing projects: decisions taken before the fix continue to work (log.md just won't have the archival entry for those), decisions taken after the fix get full history.

## Cross-references

- Sibling card: [decide-card-rephrases-and-reorders-the-cards-own-options](../decide-card-rephrases-and-reorders-the-cards-own-options/) — a parallel defect in the decide-card flow (the AskUserQuestion bridge doesn't mirror source-option labels and order). Same root: decide-card workflow has UX gaps that surfaced together.
- Manual workaround commit: `674cc5e chore(deck): archive Decision-required deliberation in log.md` — applied to `refine-deck-drops-structural-findings-by-defaulting-to-propose-not-file` to recover the deliberation history that this defect lost. The workaround is the contract the engine fix must satisfy automatically.
- Convention reference: `Skill(card-schema)` "What goes where" subsection — README as dashboard, log.md as journal. The convention this card enforces at the engine level.
