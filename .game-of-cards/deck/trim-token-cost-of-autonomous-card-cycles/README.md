---
title: trim-token-cost-of-autonomous-card-cycles
summary: "The methodology was designed for a deliberate, human-paced regime where the briefing in each skill is the point. In the autonomous-agent regime (50+ cards/day), that same briefing is re-loaded on every invocation and dominates token spend. This umbrella collapses five small, mechanical, gate:none fixes that trim that overhead — lighter `goc --json` endpoints, `goc done --bundle`, plugin-mirror diff compression in review, a leverage-comparison line in pull-card, and a codified reachability convention for parser/emitter cards. Two larger, methodology-shape items (audit-deck umbrella extension; lean/full skill stratification) are filed separately as session-gated cards."
status: done
stage: null
contribution: medium
created: "2026-05-28T04:00:04Z"
closed_at: 2026-05-29T04:37:04Z
human_gate: none
advances: []
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [x] MECHANICAL: `goc --json` gains `--closed-since <window>`, `--slim`, and `--waiting` filters. `--closed-since 24h` returns only cards whose `closed_at` falls in the window. `--slim` strips body/large fields, keeping title/status/gate/contribution/value/tags/closed_at/waiting_on. `--waiting` returns only cards carrying a `waiting_on` overlay. Each is independently testable; combining `--closed-since` + `--slim` works.
  - [x] MECHANICAL: standup SKILL.md migrates its Section 3 to use `goc --json --closed-since 24h --slim` (replacing the inline 339KB full-deck JSON dump it currently pulls). Re-run the standup reproducer; passes.
  - [x] MECHANICAL: `goc done --bundle <title-A> <title-B> [...]` closes multiple cards in one invocation, writing one shared attestation block (referencing all titles), one `closed_at` per card, and one log.md closure entry per card with `Bundled with:` cross-references populated automatically. Refuses if any card has unchecked DoD boxes; the existing per-card DoD enforcement is preserved. finish-card SKILL.md is updated to document the affordance.
  - [x] MECHANICAL: plugin-mirror diffs are collapsed in the review surface. A `.gitattributes` entry marks `claude-plugin/goc/**`, `codex-plugin/goc/**`, `openclaw-plugin/goc/**`, `.claude/skills/**`, `.codex/skills/**`, `claude-plugin/skills/**`, `codex-plugin/skills/**` as `linguist-generated` so GitHub PR review collapses them by default. AGENTS.md's "Plugin assets are auto-synced" section documents a `[sync auto]` commit-subject convention for bulk-mirror commits.
  - [x] MECHANICAL: `pull-card` prints a one-line leverage comparison after picking. Format: `Pulling <title> (value <N>). Highest gated card: <title> (value <M>, gate <kind>).` Emitted by the engine verb pull-card invokes (so the data is computed once); the skill body is updated to interpret the new line. When no gated cards exist, the line is omitted.
  - [x] MECHANICAL: audit-deck SKILL.md and create-card SKILL.md codify a soft reachability-naming convention for parser/emitter/serializer/storage-layer cards — the `## Why it matters` section must name a path that produces the offending input (e.g. "the emitter produces this string," "a one-shot-authored card produces it," or a concrete consumer flow). This is descriptive of current good practice; the convention makes it explicit so future audit passes don't drift.
  - [x] EMPIRICAL: a representative autonomous-card cycle re-run after these changes shows a measurable Context-shipment reduction. Capture: `goc --json --closed-since 24h --slim` bytes vs the current 339 KB `goc --json --status all` payload. Both numbers recorded in `log.md`.
  - [x] PROCESS: only `goc/`, `goc/templates/`, `.gitattributes`, and `AGENTS.md` are hand-edited; `python scripts/sync_plugin_assets.py --check` passes (mirrors regenerated, no drift).
  - [x] PROCESS: `uv run goc validate` passes.
worker: {who: "claude[bot]", where: main}
---

# trim-token-cost-of-autonomous-card-cycles

## Why this is an umbrella

Each of the five mechanical items below is small enough on its own that filing it as a separate card would pay the per-card ceremony multiplier (per the stored umbrella-card preference: one growing card per multi-failure-mode problem). The unifying theme is **token cost in the autonomous-agent regime**, which is genuinely one problem with multiple cheap surfaces. Two related items — auto-grouping in audit-deck, and stratifying the heaviest skills into lean/full surfaces — are filed separately because they are session-gated methodology decisions, not gate:none mechanics.

## The two regimes the methodology serves

The deck has two operating regimes:

- **Deliberate, human-paced.** One card every few hours; the methodology framing in each skill body is the point because a new agent or cold reader needs the briefing.
- **Autonomous-agent.** Tens of cards per day; the framing is internalized and the ceremony dominates token spend. The recent 62-card batch loaded `create-card` (328 lines) + `finish-card` (352 lines) = ~680 lines of skill body **per card cycle**, plus the 339 KB `goc --json --status all` payload shipped through every Context block that uses it.

This umbrella does not change that architecturally — the lean/full skill split is the separate session-gated card. What it does is take the cheapest wins available without methodology decisions: smaller payloads, bundled closures, collapsed mirror diffs, a useful nudge in pull-card, and a codified convention that is already de-facto practice.

## Item-by-item rationale

### 1. Lighter `goc --json` endpoints

Standup, scan-deck, and audit-deck-class Context blocks pull the full 339 KB / 268-card JSON to use a sliver of it. `--closed-since <window>` covers the standup case; `--slim` covers queue views that don't need bodies; `--waiting` covers the impediment surface. The fix that landed for the standup closure scan had to inline a Python date-parser because no `--closed-since` existed; with this, it becomes a one-liner.

### 4. `goc done --bundle`

`finish-card` already documents bundled closures conceptually, but the affordance is missing — closers still pay `attest` + `done` + commit per card. A bundled CLI command writing one shared attestation block and one log.md `Bundled with:` cross-reference per card compresses 3× ceremony to ~1.2×.

### 5. Plugin-mirror diff compression

Every fix's diffstat shows `engine.py` × 4 (the recent supersession-cycle fix: 90 lines × 4 = 360 lines of effectively identical diff). The sync script enforces parity automatically, so the duplicated lines are *generated*, not authored. Marking the mirror trees `linguist-generated` collapses them in GitHub PR review and in local `git show`. A commit-subject convention (`[sync auto]` when bulk-mirror) lets reviewers skip with confidence.

### 6. Leverage line in `pull-card`

A 3-line addition to pull-card's output costs nothing and helps when the autonomous vein thins: `Pulling X (value 3.0). Highest gated card: Y (value 19.7, session).` Cheap to ignore when the gated max is comparable; useful when it isn't.

### 7. Audit-deck reachability convention

The recent parser-class cards all *did* show a reachability path in their `## Why it matters` (typically "the emitter produces this input"). The convention is current good practice — codifying it in `audit-deck` and `create-card` SKILL.md makes the standard explicit so it doesn't drift on a future audit pass.

## Related, filed separately

- `audit-deck-cannot-extend-an-existing-umbrella-card-for-related-findings` (session) — methodology decision on the trigger and append mechanism.
- `heaviest-skills-re-load-full-methodology-briefing-per-card-cycle` (session) — methodology decision on the lean/full boundary.

## Notes

This card itself is the demo: five fixes under one ceremony cost, instead of five separate file→claim→implement→attest→done→commit cycles.
