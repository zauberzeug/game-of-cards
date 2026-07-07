## 2026-05-28T04:02:24Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

### 1. The lean/full boundary

Three credible cuts, each with different trade-offs:

- **Verb-mechanics only.** Lean = just the CLI shape (`goc new <title> --contribution X --gate Y --tag ...`), the DoD method-tag enum, the parallel-agent commit guard. ~40-60 lines. Cuts the deepest; relies entirely on the autonomous loop already knowing the methodology.
- **Verb-mechanics + soft conventions.** Adds the title-antipattern guard summary, the "edit the README dashboard not append a Latest finding block" rule, the relationship-edge direction rule. ~80-120 lines. Modest savings; preserves the most-violated soft rules.
- **Verb-mechanics + everything except XP/Kanban citations.** Removes only the philosophy framing (the "Scrum's Daily Scrum" / "Kanban explicit policies" prose), keeping all operational guidance. ~200-250 lines. Smallest savings; lowest risk.

### 2. Routing — how does the right variant get invoked?

Options:

- **Skill-name suffix convention.** `create-card-lean` is a separate skill with its own auto-invoke triggers and frontmatter. The host (Claude / Codex / OpenClaw) picks at trigger-match time. Two skill files per verb, sync-script aware.
- **Single skill with two sections.** `create-card` SKILL.md contains both a `## Lean` and `## Full` section; an environment variable or `!` block at the top selects which is rendered. One file, more complex routing.
- **Caller hint.** `Skill(create-card, mode=lean)` — a calling convention the autonomous loop uses. Requires harness support and a documented contract; cleanest if the harness can opt in.

### 3. `card-schema`'s 826 lines

`card-schema` is loaded by *other* skills as a cross-reference, not auto-invoked on its own. Its size is the single biggest per-load cost.

Options:

- **Split into `card-schema-reference` (always-loaded, ~150 lines: enum values, required fields, tag names, slug pattern) + `card-schema-rationale` (loaded on schema-question prompts, the remaining ~676 lines).** Mirrors the verb split.
- **Inline the lookup tables into each consuming skill** and retire `card-schema` as a cross-reference target; keep it as documentation only.
- **Leave alone.** Smaller wins on the verbs may suffice; `card-schema` only loads when prompts mention schema-shape questions, so the per-loop cost is amortized.


## 2026-07-07T04:04:48Z: decision recorded

Adopt progressive disclosure inside each skill (happy-path SKILL.md core + on-demand reference.md sibling) instead of lean/full skill variants; supersede this card by plugin-skills-consume-a-third-of-downstream-session-usage — A downstream plugin-usage report (31% of session usage, finish-card alone 15%) shows deliberate human-paced use pays the same per-invocation cost as autonomous loops, so there is no audience for a fat default variant and the lean/full routing question dissolves. Gate session → none.

## 2026-07-07T04:35:00Z: superseded

Superseded by [`plugin-skills-consume-a-third-of-downstream-session-usage`](../plugin-skills-consume-a-third-of-downstream-session-usage/)
— same body-size problem, different mechanism: progressive disclosure inside
each skill (core SKILL.md + on-demand reference.md sibling) instead of
parallel `<verb>-lean` skill variants. The downstream usage report showed
deliberate use pays the same per-invocation cost as autonomous loops, which
dissolved this card's open routing question (decision entry above).
