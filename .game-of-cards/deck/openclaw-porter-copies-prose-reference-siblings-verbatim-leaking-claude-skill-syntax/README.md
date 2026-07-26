---
title: openclaw-porter-copies-prose-reference-siblings-verbatim-leaking-claude-skill-syntax
summary: "The OpenClaw porter copies non-SKILL.md siblings verbatim by design, but the skill-split refactor moved methodology prose into reference.md siblings, so the shipped payload now carries 37 raw Skill(...) invocations across 8 reference files plus Claude Code install instructions — syntax and host that do not exist on OpenClaw. The ported SKILL.md bodies actively route agents to these unported files via the sibling trailer."
status: open
stage: null
contribution: medium
created: "2026-07-23T13:24:57Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, documentation, infra]
definition_of_done: |
  - [ ] MECHANICAL: decision below recorded; porter siblings routed per the chosen contract
  - [ ] TDD: a guard (porter --check extension or regression test) fails when a shipped openclaw sibling contains Skill( invocation syntax that the chosen contract says must be neutralized
  - [ ] MECHANICAL: re-ported openclaw-plugin/skills/ committed; port_skills_to_openclaw.py --check green
  - [ ] PROCESS: AGENTS.md sibling-asset row updated if the verbatim-copy contract changes
---

# openclaw-porter-copies-prose-reference-siblings-verbatim-leaking-claude-skill-syntax

## Location

- `scripts/port_skills_to_openclaw.py` — `port_sibling()`: "Copy a
  non-SKILL.md sibling asset verbatim — no host-neutral rewrite."
- `AGENTS.md` sibling-asset table row: "copied verbatim, no host-neutral
  rewrite".
- Leaked output (verified by grep on this tree): 8 of the shipped
  `openclaw-plugin/skills/*/reference.md` files contain raw `Skill(...)`
  syntax — `deck/reference.md` alone has 14 (its ported `SKILL.md` has 0);
  `kickoff/reference.md:21,30` instructs installing "Claude Code skills,
  hooks" via the Claude plugin.

## What's broken

The verbatim-copy contract was designed when siblings were data assets
(`card-schema/schema.yaml`). The later skill-split refactor moved
methodology prose out of SKILL.md bodies into `reference.md` siblings —
which therefore bypass every host-neutralization the porter exists to
perform (the SUBSTITUTIONS table rewrites `Skill(name)` → "the `name`
skill", Claude-host phrasing, etc., for SKILL.md only). The porter then
*routes agents to the unported prose*: `_sibling_trailer()` appends a
"Sibling files on this host" section telling OpenClaw agents to fetch
`reference.md` through the goc tool.

Net effect: OpenClaw agents following a skill's deep-dive documentation are
instructed in an invocation syntax (`Skill(...)`) and a host (Claude Code)
that do not exist on their platform. The port is deterministic, so
`--check` and `tests/test_plugin_mirror_parity.py` stay green forever —
the leak is in-contract for the drift guard.

## Decision required

What is the porting contract for prose siblings?

1. **Port prose siblings like SKILL.md**: run `reference.md` (and any
   future `.md` sibling) through the same substitution pipeline; keep
   verbatim copy only for non-markdown data assets. Cleanest semantics;
   needs care that substitutions are safe on files the porter never
   previously touched.
2. **Neutralize selectively**: apply only the invocation-syntax
   substitutions (`Skill(...)`, Claude host names) to `.md` siblings,
   skipping the structural rewrites (preflight/context blocks don't occur
   there anyway).
3. **Keep verbatim, fix at the source**: rewrite the source
   `reference.md` files in host-neutral language so all consumers share
   one text. Touches Claude/Codex payloads too; larger blast radius.

Options 1 and 2 change the porter and the AGENTS.md contract row; option 3
changes authored template prose repo-wide. A human should pick the
contract before any re-port lands.

## Why it matters

The OpenClaw payload's own SKILL.md bodies advertise these files as the
deep-dive path, so the leak is on the main read path, not a dusty corner.
Related precedent: the porter's SKILL.md substitutions exist precisely
because this class of leak was judged worth preventing when the payload
first shipped.
