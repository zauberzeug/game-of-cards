---
title: openclaw-porter-fetch-hint-lands-outside-quoted-description-breaking-frontmatter-yaml
summary: "The OpenClaw skill porter appends its tool-served fetch hint after the description line's closing double quote, so the shipped pull-card and next-card SKILL.md frontmatter is invalid YAML that any strict loader rejects. The strict-YAML regression test skips quoted scalars entirely, so CI stays green on the broken payload."
status: done
stage: null
contribution: high
created: "2026-07-23T13:17:29Z"
closed_at: "2026-07-23T13:23:48Z"
human_gate: none
advances:
  - yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — every shipped openclaw-plugin/skills/*/SKILL.md description is one complete strict-YAML scalar
  - [x] TDD: tests/test_skill_frontmatter_strict_yaml.py flags content after a quoted scalar's closing quote (fails on the pre-fix payload, passes post-fix)
  - [x] MECHANICAL: porter inserts the fetch hint inside quoted description scalars with YAML quote escaping; re-ported payload committed and port_skills_to_openclaw.py --check green
  - [x] TDD: full regression suite green (uv run python -m unittest discover -s tests)
worker: {who: "claude[bot]", where: main}
---

# openclaw-porter-fetch-hint-lands-outside-quoted-description-breaking-frontmatter-yaml

## Location

- `scripts/port_skills_to_openclaw.py:190` (pre-fix) — the blind hint append.
- Shipped casualties: `openclaw-plugin/skills/pull-card/SKILL.md:3`,
  `openclaw-plugin/skills/next-card/SKILL.md:3`.
- Blind guard: `tests/test_skill_frontmatter_strict_yaml.py:34-35`
  (`_is_quoted_or_structured` — pre-fix).

## What's broken

The porter's tool-served-read feature appends a fetch hint to each ported
skill's catalog description line:

```python
DESCRIPTION_LINE_RE = re.compile(r"^(description:[^\n]*?)[ \t]*$", re.MULTILINE)
...
text = DESCRIPTION_LINE_RE.sub(lambda m: m.group(1) + hint, text, count=1)
```

The comment above it assumed plain scalars: "The hint stays free of `: `
sequences — frontmatter descriptions are plain YAML scalars". But two source
templates carry **double-quoted** descriptions — quoted precisely because
they contain `human_gate: none` and escaped inner quotes (the fix shipped by
the closed card `skill-frontmatter-descriptions-break-yaml-loading`):
`goc/templates/skills/pull-card/SKILL.md:3` and
`goc/templates/skills/next-card/SKILL.md:3`. Appending to the *line* puts the
hint after the closing quote:

```yaml
description: "Pull the highest-leverage `human_gate: none` open card ... /schedule." If the catalog location path is unreadable, fetch the body via the goc tool verb "skill", args ["pull-card"].
```

Trailing content after a quoted scalar's closing quote is invalid YAML — every
strict loader raises a ParserError, and the OpenClaw host (which reads these
files via its manifest `skills` array) skips loading the skill, the exact
"Skipped loading N skill(s)" failure the earlier card documented.

The regression guard that owns this contract cannot see it: for any value
starting with `"` it hit `_is_quoted_or_structured` → `continue`, never
checking that the quoted scalar is *complete*.

## Empirical evidence

`uv run python .game-of-cards/deck/<this-card>/reproduce.py` pre-fix:

```
[FAIL] openclaw-plugin/skills/next-card/SKILL.md:3: content after closing quote: 'If the catalog location path is unreadable, fetch the body v'
[FAIL] openclaw-plugin/skills/pull-card/SKILL.md:3: content after closing quote: 'If the catalog location path is unreadable, fetch the body v'
2 shipped skill(s) have unparseable frontmatter
```

Cross-checked with PyYAML (system python3): `yaml.safe_load` raises
`ParserError` on exactly those two files; the other 14 parse clean.

## Why it matters

Reachability: `goc/templates/skills/{pull-card,next-card}/SKILL.md` carry
quoted descriptions → `scripts/port_skills_to_openclaw.py` (run by hand,
enforced byte-for-byte by `--check` and `tests/test_plugin_mirror_parity.py`)
→ committed `openclaw-plugin/skills/` → published npm/ClawHub payload → the
OpenClaw host's strict YAML skill loader. The two broken skills include
`pull-card`, the autonomous-loop workhorse, so consuming OpenClaw
deployments lose the queue-drain entry point entirely. The drift guard makes
the breakage *stable*: a fresh re-port reproduces it byte-for-byte, so CI
stays green forever.

## Fix (applied)

1. `scripts/port_skills_to_openclaw.py` — `_hint_into_description()`: when
   the description value is a complete double- or single-quoted scalar,
   insert the hint before the closing quote, escaping the hint per YAML
   rules (`"` → `\"` / `'` → `''`); plain scalars keep the old append.
2. Re-ported `openclaw-plugin/skills/` (only pull-card and next-card
   changed).
3. `tests/test_skill_frontmatter_strict_yaml.py` — `_quoted_scalar_hazard()`
   now flags trailing content after the closing quote (and unterminated
   quoted scalars) across all six shipped skill roots; unit-tested against
   the exact pre-fix shape and confirmed to flag the HEAD payload.
