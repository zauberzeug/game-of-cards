---
title: openclaw-plugin-skills-erzwingen-mehrfach-reads-pro-session
status: active
stage: null
contribution: high
created: "2026-07-18T05:28:51Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [story, infra]
summary: "IMPLEMENTED (pending downstream measurement): all three levers landed — AGENTS_GOC.md slimmed 4,145 B → 2,001 B with a size-cap guard, skill cores audited one-read clean, and the OpenClaw goc tool now serves bundled skill bodies via a tool-only `skill` verb (catalog descriptions + a sibling-files trailer route agents to it), so sandboxed agents stop shell-guessing host paths. The EMPIRICAL before/after trajectory count awaits the next consuming-deployment release."
definition_of_done: |
  - [x] PROCESS: maintainer decision on scope (template slimming vs. skill-body rework vs. catalog-location fix — combinable)
  - [x] MECHANICAL: `goc/templates/AGENTS_GOC.md` reduced to a lean block (target: pointers + the few rules that must be always-loaded; skills carry the methodology)
  - [x] MECHANICAL: each shipped skill body audited for one-read self-sufficiency (no SKILL.md -> reference -> --help chains for the common path)
  - [x] MECHANICAL: openclaw-plugin skill `location` values resolvable from inside a sandboxed session (or bodies served via the skill mechanism), so agents stop shell-guessing host paths
  - [ ] EMPIRICAL: on a consuming deployment, orientation reads targeting GoC skill files drop measurably (before/after trajectory counts)
worker: {who: Rodja Trappe, where: main}
waiting_on: external
---

# openclaw-plugin-skills-erzwingen-mehrfach-reads-pro-session

Agents wake up fresh each session, so every per-session read of a GoC skill body is a recurring
cost. Trajectory analysis on a production OpenClaw deployment (2026-07-17, 156 turns) showed the
shipped GoC skills among the top orientation-read targets: `card-schema` 44 reads/day,
`create-card`/`advance-card`/`scan-deck`/`finish-card`/`deck` ~20 each — repeated across **three
path variants** (`.openclaw/sandbox-skills/skills/...`, the plugin payload path, and a source
clone), because the catalog's `location` points at host-side paths a sandboxed session cannot
open, so agents fall back to guessing. Each read is a full model round-trip (~10 s); GoC skill
reads alone cost that deployment roughly 30-40 minutes of model time per day.

Three levers, all implemented 2026-07-18:

1. **Slim `goc/templates/AGENTS_GOC.md`** — DONE. 4,145 B → 2,001 B (−52%). The four
   methodology essays (README-dashboard, closure, three-axis, scheduler/record) are now
   one-line rules pointing at the skills that carry the full contract. The dedup-test needle
   "Closure is not frozenness" is preserved verbatim (`tests/test_briefing_body_dedup.py`
   pins it to exactly one occurrence). `BriefingBlockSizeTest` in
   `tests/test_skill_body_size.py` caps the template at 2,500 B against re-fattening. The
   dogfood `AGENTS.md` marker block was regenerated to match; consumers pick the slim block
   up on their next `goc upgrade`.
2. **One-read skill bodies** — AUDITED CLEAN. All 18 cores carry their common-path CLI
   inline (standup/retrospective via `!`-preamble blocks); every `reference.md` routing
   table is edge-case-only; the two `--help` surfaces are legitimate (codex-kickoff setup
   health checks, deck's full-verb-list completeness pointer after an inline verb table).
   The heavy lifting predates this card: `plugin-skills-consume-a-third-of-downstream-
   session-usage` and `occasional-goc-skills-still-load-full-manuals` did the
   progressive-disclosure split and size caps. Skill→skill composition (pull-card →
   advance-card/finish-card) is intentional architecture, not a reading chain.
3. **Sandbox-resolvable skill reads (openclaw-plugin)** — DONE, via the "bodies served
   through the tool" option: OpenClaw's SDK verifiably offers no programmatic skill
   registration or sandbox location rewriting (manifest/SDK/skills-config docs checked
   2026-07-18), so `location` cannot be fixed plugin-side. Instead the goc tool grew a
   tool-only `skill` verb (`openclaw-plugin/index.ts`, `serveGocSkill`; deliberately NOT in
   `GOC_VERBS`, which mirrors the engine's subparsers): args `["<name>"]` → SKILL.md, args
   `["<name>", "<file>"]` → sibling (reference.md, schema.yaml), no args → list. Discovery
   is routed at the two points an agent looks before shell-guessing: the porter appends a
   fetch hint to every ported skill's catalog `description` and a "Sibling files on this
   host" trailer to bodies that ship siblings. Contract pinned by
   `tests/test_openclaw_skill_serving.py` (extract-and-run under node, same pattern as the
   session-start hook test; skips on node < 22.6).

## Measurement

Reproduced with a trajectory-JSONL analysis (tool-call category split; orientation reads =
`ls`/`cat`/`sed`/`grep`/`head` on skill and workspace files). Before/after comparison for the
EMPIRICAL item can reuse the same counting on any consuming deployment.

Still pending: the EMPIRICAL before/after count needs a goc release consumed by the
deployment that produced the baseline (2026-07-17). Success signature: near-zero failed
skill-path reads (agents call the goc tool's `skill` verb instead) and a smaller
always-loaded AGENTS.md block share.

## Decision

*Resolved 2026-07-18T12:58:15Z:* Implement all three levers combined: slim AGENTS_GOC.md to a lean pointer block, audit skill cores for one-read self-sufficiency, and serve OpenClaw skill bodies via a tool-side skill verb

*Reasoning:* Maintainer selected all three scope options; OpenClaw SDK verifiably offers no sandbox location rewriting, so tool-served bodies are the only plugin-side fix

