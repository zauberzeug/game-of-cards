---
title: skill-prose-still-calls-queue-impact-sorted-after-impact-contribution-rename
summary: "Sibling drift after `next-card-impact-ladder-references-nonexistent-frontmatter-field` closed: that fix renamed the `impact: <level>` frontmatter examples to `contribution: <level>` but left the prose calling the engine's sort 'impact-sorted', 'Impact ladder', and 'sorted by impact desc' across three skill bodies. The engine has no `impact` concept — it sorts by GRPW value built from `CONTRIBUTION_RANK` over the `contribution` field."
status: open
stage: null
contribution: medium
created: "2026-05-29T12:05:24Z"
closed_at: null
human_gate: none
advances:
  - next-card-impact-ladder-references-nonexistent-frontmatter-field
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [ ] TDD: `uv run python deck/skill-prose-still-calls-queue-impact-sorted-after-impact-contribution-rename/reproduce.py` exits zero (all five drift hits gone; engine 'impact' token count stays at zero)
  - [ ] MECHANICAL: `goc/templates/skills/next-card/SKILL.md` lines 21, 45, 137 rewritten — "impact-sorted queue" → "value-sorted queue"; "sorted by impact desc" → "sorted by value desc"; "impact, why it's the highest-leverage" → "contribution, why it's the highest-leverage"
  - [ ] MECHANICAL: `goc/templates/skills/deck/SKILL.md:130` "(impact-sorted)" → "(value-sorted)"
  - [ ] MECHANICAL: `goc/templates/skills/audit-deck/SKILL.md:67` "Impact ladder" → "Contribution ladder" (matches the sibling rename in next-card)
  - [ ] MECHANICAL: `scripts/sync_plugin_assets.py` regenerates `.claude/skills/`, `.codex/skills/`, `claude-plugin/skills/`, `codex-plugin/skills/`; `uv run python scripts/sync_plugin_assets.py --check` exits zero
  - [ ] MECHANICAL: `python3 scripts/port_skills_to_openclaw.py` re-ported and `--check` exits zero
  - [ ] PROCESS: `uv run goc validate` clean
---

# Skill prose still describes the queue sort as "impact" after the impact→contribution rename

## Location

- `goc/templates/skills/next-card/SKILL.md:21` — "top of the impact-sorted queue"
- `goc/templates/skills/next-card/SKILL.md:45` — "`goc` lists open cards sorted by impact desc"
- `goc/templates/skills/next-card/SKILL.md:137` — "**2-line rationale** — impact, why it's the highest-leverage"
- `goc/templates/skills/deck/SKILL.md:130` — "`goc` | Show the open queue (impact-sorted). |"
- `goc/templates/skills/audit-deck/SKILL.md:67` — "**Hunt the big thing first.** Impact ladder: `high` outranks `medium` outranks `low`."
- Engine source of truth: `goc/engine.py:1806` `CONTRIBUTION_RANK: dict[str, float] = {"high": 9.0, "medium": 3.0, "low": 1.0}`; `goc/engine.py:1813` `def compute_values(cards)` builds GRPW `value` from `CONTRIBUTION_RANK` over the `contribution` field via Bellman discount.
- Schema source of truth: `goc/schema.yaml` declares `contribution_values: [high, medium, low]`. No `impact` token appears in `engine.py`, `schema.yaml`, or `cli.py` (verified by `reproduce.py`).

## What's broken

Sibling card `next-card-impact-ladder-references-nonexistent-frontmatter-field` (closed 2026-05-29) renamed every `impact: <level>` frontmatter example in `next-card` and `pull-card` to `contribution: <level>`. The reproduce.py from that card scoped the search to the field-name regex `\`impact:\s*(high|medium|low)\``; it explicitly did not check for the same vocabulary used as prose.

Five surviving phrases call the engine's sort dimension by the renamed name:

From `goc/templates/skills/next-card/SKILL.md`:

```
21: — pulls one card at a time, top of the impact-sorted queue, gated by
45: `goc` lists open cards sorted by impact desc
137: - **2-line rationale** — impact, why it's the highest-leverage open
```

From `goc/templates/skills/deck/SKILL.md`:

```
130: | `goc` | Show the open queue (impact-sorted). |
```

From `goc/templates/skills/audit-deck/SKILL.md`:

```
67: - **Hunt the big thing first.** Impact ladder: `high` outranks
```

The `audit-deck:67` "Impact ladder" header is the exact section that was just renamed to "Contribution ladder" in `next-card`. Two skills documenting the same concept under two different names within one repo is a textbook structural inconsistency.

The engine sorts cards by GRPW `value`:

```
goc/engine.py:1806: CONTRIBUTION_RANK: dict[str, float] = {"high": 9.0, "medium": 3.0, "low": 1.0}
goc/engine.py:1813: def compute_values(cards) -> dict[str, tuple[float, list[str]]]:
goc/engine.py:1816:     `value(c) = rank(c) + γ · max(value(d) for d in advances(c))`
```

There is no `impact` token anywhere in `engine.py`, `schema.yaml`, or `cli.py`. The skill prose names a dimension the engine does not have.

## Empirical evidence

`reproduce.py` output (run via `uv run python deck/<title>/reproduce.py`):

```
Engine source-of-truth — bare 'impact' token search:
  goc/engine.py: 0 occurrences
  goc/schema.yaml: 0 occurrences
  goc/cli.py: 0 occurrences
  TOTAL: 0 (any non-zero contradicts the skill prose)

Skill bodies — drift-phrase hits:
  goc/templates/skills/next-card/SKILL.md:21: — pulls one card at a time, top of the impact-sorted queue, gated by
  goc/templates/skills/next-card/SKILL.md:45: `goc` lists open cards sorted by impact desc
  goc/templates/skills/next-card/SKILL.md:137: - **2-line rationale** — impact, why it's the highest-leverage open
  goc/templates/skills/deck/SKILL.md:130: | `goc` | Show the open queue (impact-sorted). |
  goc/templates/skills/audit-deck/SKILL.md:67: - **Hunt the big thing first.** Impact ladder: `high` outranks
  TOTAL drift hits: 5

FAIL: skill prose still names a sort dimension the engine does not have.
```

## Why it matters

Reachability path: `next-card`, `deck`, and `audit-deck` are auto-invoked when an agent says "what's next", "show me the deck", "find me a bug", or enters an autonomous `/loop pull-card`. The skill body is read into the agent's context every time. A new contributor or agent reading "the impact-sorted queue" or "sorted by impact desc" will look for an `impact` concept in `goc --help`, `schema.yaml`, or `engine.py` — and find nothing. Worse, the just-closed sibling already proved that `impact` vocabulary contaminates downstream usage: a filer following the example wrote junk-key cards.

This drift is also a continuation indicator — the closed card's `reproduce.py` regex was narrowly scoped to the field-name form `\`impact:\s*<level>\``, which is why this prose survived the fix. The right resolution is to finish the rename: replace "impact" used as the *name of the sort dimension* with the engine's actual terminology (`contribution` for the per-card field, `value` for the GRPW-composed sort key).

Adjective uses elsewhere ("research-impacting decision", "high-impact seams", "research-impacting framework derivations") are NOT in scope and stay. Those are English-language qualifiers, not claims about a frontmatter field or sort dimension.

## Fix

Mechanical sed-style rewrites (the rationale was settled by the sibling card's decision to rename the field — this card extends the rename to prose at the same conceptual surface):

| File:line | Before | After |
|---|---|---|
| `next-card:21` | "top of the impact-sorted queue" | "top of the value-sorted queue" |
| `next-card:45` | "`goc` lists open cards sorted by impact desc" | "`goc` lists open cards sorted by value desc" |
| `next-card:137` | "**2-line rationale** — impact, why it's the highest-leverage" | "**2-line rationale** — contribution, why it's the highest-leverage" |
| `deck:130` | "Show the open queue (impact-sorted)." | "Show the open queue (value-sorted)." |
| `audit-deck:67` | "Impact ladder:" | "Contribution ladder:" |

Then run the mirror sync (`scripts/sync_plugin_assets.py` for Claude/Codex mirrors; `scripts/port_skills_to_openclaw.py` for the OpenClaw port), and append the forward pointer to the closed parent's `log.md` per AGENTS.md "Closure is not frozenness".

The closed sibling chose `Contribution ladder` for the next-card header; matching that exactly in audit-deck keeps the family-shape consistent across skills.
