
## 2026-07-18 — Filed

Filed from a consuming deployment's latency analysis (trajectory-JSONL category split,
2026-07-16/17): GoC skill bodies were among the top orientation-read targets, re-read
150-200x/day across three path variants; the goc-owned AGENTS.md marker block (~4.1k chars)
additionally crowds the consumer's bootstrap char budget (OpenClaw trims at 20k). Scoped as
upstream work because both the marker block (regenerated wholesale on `goc upgrade`) and the
shipped skill bodies are goc-owned — consumers cannot durably fix them locally.

## 2026-07-18T12:58:15Z: decision recorded

Implement all three levers combined: slim AGENTS_GOC.md to a lean pointer block, audit skill cores for one-read self-sufficiency, and serve OpenClaw skill bodies via a tool-side skill verb — Maintainer selected all three scope options; OpenClaw SDK verifiably offers no sandbox location rewriting, so tool-served bodies are the only plugin-side fix. Gate decision → none.

## 2026-07-18 — All three levers implemented

Maintainer approved all three scope options (decision recorded above); implemented in one
pass:

- `goc/templates/AGENTS_GOC.md` 4,145 B → 2,001 B; essays → one-line pointer rules;
  dogfood `AGENTS.md` block regenerated; `BriefingBlockSizeTest` caps it at 2,500 B.
  (First replacement attempt matched a prose mention of `<!-- END GOC -->` at
  AGENTS.md:400 and duplicated 105 lines — caught by `test_version_surfaces`; redone with
  line-anchored markers.)
- Skill-core audit: all 18 cores one-read clean; no fixes needed (details in README §2).
- OpenClaw tool-served skill bodies: `skill` verb in `openclaw-plugin/index.ts`
  (`TOOL_ONLY_VERBS`, kept out of the engine-mirroring `GOC_VERBS`), porter now appends a
  catalog-description fetch hint + sibling-files trailer
  (`scripts/port_skills_to_openclaw.py`), dist rebuilt, README updated (also fixed stale
  "14 skills" count → 16 and added the missing openclaw-kickoff/upgrade rows).
  `tests/test_openclaw_skill_serving.py` pins the serve contract (7 node asserts,
  verified locally via esbuild type-strip on node 20).

Docs verified for lever 3: OpenClaw manifest/SDK/skills-config pages offer no programmatic
skill registration and no sandbox location rewriting — tool-served bodies are the only
plugin-side fix.

Card stays active: EMPIRICAL before/after trajectory count requires the next release to
reach the consuming deployment (waiting_on: external).
