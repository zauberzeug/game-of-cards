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
summary: "On an OpenClaw deployment, GoC skill bodies and the AGENTS.md marker block are the top drivers of orientation reads: agents re-read the same SKILL.md files 150-200 times/day across three path variants, and the ~4k-char AGENTS_GOC.md block crowds out the consumer's bootstrap char budget. Make skill bodies one-read self-sufficient, slim the marker-block template to pointers, and fix skill-catalog locations that sandboxed agents cannot open."
definition_of_done: |
  - [ ] PROCESS: maintainer decision on scope (template slimming vs. skill-body rework vs. catalog-location fix — combinable)
  - [ ] MECHANICAL: `goc/templates/AGENTS_GOC.md` reduced to a lean block (target: pointers + the few rules that must be always-loaded; skills carry the methodology)
  - [ ] MECHANICAL: each shipped skill body audited for one-read self-sufficiency (no SKILL.md -> reference -> --help chains for the common path)
  - [ ] MECHANICAL: openclaw-plugin skill `location` values resolvable from inside a sandboxed session (or bodies served via the skill mechanism), so agents stop shell-guessing host paths
  - [ ] EMPIRICAL: on a consuming deployment, orientation reads targeting GoC skill files drop measurably (before/after trajectory counts)
worker: {who: Rodja Trappe, where: main}
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

Three levers, combinable:

1. **Slim `goc/templates/AGENTS_GOC.md`.** The marker block injected into consumers' AGENTS.md
   is ~4.1k chars of methodology prose. Consumers' bootstrap files have hard char budgets
   (OpenClaw trims AGENTS.md at `bootstrapMaxChars`, default 20k, keeping only the first 45%
   verbatim) — a 4k goc-owned block crowds out the consumer's own always-loaded rules. The block
   already states "skills carry the methodology"; it should practice that: discovery signal,
   skill list, and one-line pointers instead of full paragraphs for README-dashboard /
   closure / three-axis / scheduler-record semantics. Note: consumers cannot fix this locally —
   the block is goc-owned and regenerated wholesale on `goc upgrade`.
2. **One-read skill bodies.** Every shipped SKILL.md should carry the complete common path in a
   single read: exact CLI invocations inline, no chains into secondary references or `--help`
   round-trips. Where a body serves both a rich-tool host (Claude Code) and an exec-only host
   (OpenClaw sandbox), the common path must not depend on host-only affordances.
3. **Sandbox-resolvable catalog locations (openclaw-plugin).** The OpenClaw skill catalog lists
   `location` paths under the host home (`~/.openclaw/plugin-skills/...`). Inside a sandboxed
   session those paths do not exist; agents `cat`/`sed` them, fail, then guess variants. Either
   the plugin registers locations that resolve inside the session mount, or skill bodies are
   delivered through the skill/read mechanism so no shell path is needed.

## Measurement

Reproduced with a trajectory-JSONL analysis (tool-call category split; orientation reads =
`ls`/`cat`/`sed`/`grep`/`head` on skill and workspace files). Before/after comparison for the
EMPIRICAL item can reuse the same counting on any consuming deployment.

## Decision

*Resolved 2026-07-18T12:58:15Z:* Implement all three levers combined: slim AGENTS_GOC.md to a lean pointer block, audit skill cores for one-read self-sufficiency, and serve OpenClaw skill bodies via a tool-side skill verb

*Reasoning:* Maintainer selected all three scope options; OpenClaw SDK verifiably offers no sandbox location rewriting, so tool-served bodies are the only plugin-side fix

