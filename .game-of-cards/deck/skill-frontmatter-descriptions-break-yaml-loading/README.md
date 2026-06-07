---
title: skill-frontmatter-descriptions-break-yaml-loading
summary: "Several shipped GoC skill templates contain unquoted frontmatter scalars with nested `: ` text, which strict YAML parsers reject before the skill body can load. Codex plugin-cache and agent-local copies can therefore skip `kickoff`, `advance-card`, `pull-card`, and `next-card` even though GoC's permissive YAML-lite parser accepts the same files."
status: done
stage: null
contribution: medium
created: "2026-06-04T05:10:39Z"
closed_at: "2026-06-04T05:19:00Z"
human_gate: none
advances:
  - release-fixed-skill-frontmatter-to-codex-plugin-cache
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero, proving all shipped skill frontmatter avoids unquoted nested mapping-colon scalars.
  - [x] TDD: regression coverage in `tests/` scans source templates and generated skill payloads for the same strict-loader-invalid shape.
  - [x] MECHANICAL: fix the source-of-truth templates or generator so `kickoff`, `advance-card`, `pull-card`, and `next-card` frontmatter is strict YAML.
  - [x] MECHANICAL: run the plugin/dogfood sync so `claude-plugin/`, `codex-plugin/`, `.claude/skills/`, `.codex/skills/`, and OpenClaw skill ports reflect the fix.
  - [x] EMPIRICAL: `uv run python -m unittest discover -s tests` and `uv run goc validate` pass.
worker: {who: Rodja Trappe, where: main}
---

# Skill frontmatter descriptions break YAML loading

## Location

- `goc/templates/skills/kickoff/SKILL.md:3`
- `goc/templates/skills/advance-card/SKILL.md:4`
- `goc/templates/skills/pull-card/SKILL.md:3`
- `goc/templates/skills/next-card/SKILL.md:3`
- Generated mirrors under `claude-plugin/skills/`, `.claude/skills/`,
  `openclaw-plugin/skills/`, and any installed plugin cache that consumes the
  native skill payload.

## What's broken

Several skill `description:` / `argument-hint:` frontmatter values are plain
YAML scalars but contain a nested colon followed by whitespace. Strict YAML
loaders interpret that as an attempted mapping value and reject the entire
`SKILL.md` before the skill can load.

Observed examples:

```yaml
description: ... Host-agnostic: per-host complements ...
description: Pull the highest-leverage `human_gate: none` open card ...
argument-hint: <title> <new-status: active|open|disproved|superseded> ...
```

GoC's vendored `yaml_lite` parser accepts these lines, so the repo's normal
card/config validation does not catch the host-loader failure. Ruby/Psych,
PyYAML-style loaders, and Codex's skill loader reject the same shape with
`mapping values are not allowed in this context`.

## Empirical evidence

User-visible warning:

```text
Skipped loading 8 skill(s) due to invalid SKILL.md files.
.../skills/kickoff/SKILL.md: invalid YAML: mapping values are not allowed in this context at line 2 column 352
.../skills/advance-card/SKILL.md: invalid YAML: mapping values are not allowed in this context at line 3 column 35
.../skills/pull-card/SKILL.md: invalid YAML: mapping values are not allowed in this context at line 2 column 51
.../skills/next-card/SKILL.md: invalid YAML: mapping values are not allowed in this context at line 2 column 298
```

Local reproduction before the fix:

```text
FAIL — strict skill-loader frontmatter hazards found:
  goc/templates/skills/advance-card/SKILL.md:4: argument-hint contains unquoted ': '
  goc/templates/skills/kickoff/SKILL.md:3: description contains unquoted ': '
  goc/templates/skills/next-card/SKILL.md:3: description contains unquoted ': '
  goc/templates/skills/pull-card/SKILL.md:3: description contains unquoted ': '
```

Final reproduction after the fix:

```text
OK — shipped skill frontmatter avoids unquoted nested mapping-colon scalars.
```

## Why it matters

The reachability path is any host that reads GoC skills from the native skill
payload: Claude plugin installs, OpenClaw ports, and Codex plugin-cache paths
that consume the Claude-shaped plugin instead of the Codex-normalized payload.
When the frontmatter fails, the host skips the skill entirely. The skipped set
includes onboarding (`kickoff`), queue selection (`next-card`), autonomous work
(`pull-card`), and status/edge mutation (`advance-card`), so the methodology is
present on disk but not callable by the agent.

The bug is especially easy to reintroduce because prose descriptions naturally
contain `label: detail` clauses. The source templates need to be strict-YAML
safe, not merely acceptable to GoC's internal YAML subset.

## Fix

The affected single-line frontmatter values are now quoted in the source
templates, and `goc.install._frontmatter_value` decodes double-quoted scalar
escapes so Codex frontmatter normalization preserves human-readable
descriptions instead of double-escaping embedded quotes.

The regression guard in `tests/test_skill_frontmatter_strict_yaml.py` scans
every shipped `SKILL.md` frontmatter surface for unquoted plain scalars
containing `: `. The generated mirrors were refreshed with:

```bash
python3 scripts/sync_plugin_assets.py
python3 scripts/port_skills_to_openclaw.py
```

The first command regenerates Claude/Codex plugin payloads and dogfood copies.
The second updates the reviewed OpenClaw skill ports, which are intentionally
not auto-staged by the sync script.
