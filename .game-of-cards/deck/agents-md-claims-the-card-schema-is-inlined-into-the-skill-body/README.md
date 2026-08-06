---
title: agents-md-claims-the-card-schema-is-inlined-into-the-skill-body
summary: "AGENTS.md's `## Code architecture` bullet says `goc/schema.yaml` is \"inlined into the `card-schema` skill body at install time\", but `goc install` copies skill assets verbatim (`_iter_skill_assets`) and the schema reaches consumers as a separate sibling file — the skill body itself says it \"ships as the sibling `schema.yaml`\", and AGENTS.md contradicts itself 216 lines later by calling the same file a \"verbatim copy\". The wording hides a real obligation: `goc/templates/skills/card-schema/schema.yaml` is a second checked-in copy that no script auto-syncs, so the natural single-file schema edit turns CI red via `tests/test_skill_schema_yaml_parity.py` with no pointer from the briefing. The stale framing has already been copied into an open card's body."
status: open
stage: null
contribution: high
created: "2026-08-06T05:30:53Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [documentation, infra]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — no guidance surface claims the schema is inlined into the skill body.
  - [ ] TDD: a regression assertion in `tests/test_guidance_accuracy.py` pins the `goc/schema.yaml` bullet of AGENTS.md's `## Code architecture` section: it must not claim inlining, and it must name `goc/templates/skills/card-schema/schema.yaml` as the second copy.
  - [ ] MECHANICAL: `AGENTS.md:161` rewritten to describe the real mechanism — the schema ships as a verbatim sibling asset — and to name the hand-maintained `goc/schema.yaml` → template duplication plus the test that guards it.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass.
---

# The agent briefing says the card schema is inlined; it is copied as a sibling file

## Location

`AGENTS.md:159-162`, the `## Code architecture` bullet list:

```markdown
- **`goc/schema.yaml`** — single source of truth for card frontmatter
  (loaded by `engine.load_schema()`; inlined into the `card-schema`
  skill body at install time).
```

The first half is accurate — `engine.load_schema()` does read
`goc/schema.yaml`. The parenthetical's second half is not.

## What's broken

Nothing inlines the schema anywhere. `goc install` copies skill
directories asset-by-asset with a plain tree walk, with no templating
or substitution step (`goc/install.py:1188-1199`):

```python
def _iter_skill_assets(skills_src: Path, agent: str) -> list[Path]:
    """Return bundled skill assets relative to the skill tree root, filtered for `agent`."""
    paths: list[Path] = []
    for skill_dir in sorted(p for p in skills_src.iterdir() if p.is_dir()):
        if not skill_for_agent(skill_dir.name, agent):
            continue
        for asset in skill_dir.rglob("*"):
            if asset.is_dir() or "__pycache__" in asset.parts:
                continue
            paths.append(asset.relative_to(skills_src))
    return paths
```

The schema reaches a consuming repo as its own file,
`.claude/skills/card-schema/schema.yaml`, copied byte-for-byte from
`goc/templates/skills/card-schema/schema.yaml`.

Three other surfaces state the real mechanism, so the briefing is the
outlier:

- The skill body itself
  (`goc/templates/skills/card-schema/SKILL.md:15`):
  "The machine-readable schema ships as the sibling `schema.yaml`."
- The parity test's docstring
  (`tests/test_skill_schema_yaml_parity.py:4-6`): "The card-schema skill
  ships a **sibling copy** at `goc/templates/skills/card-schema/schema.yaml`".
- **AGENTS.md contradicts itself** 216 lines below the stale claim, at
  `AGENTS.md:376-378`: "The same script handles sibling asset files (e.g.
  `card-schema/schema.yaml`) by **verbatim copy**, matching the full-tree
  walk the other four plugin consumers (`goc install`, the claude/codex
  sync, the in-repo `.claude/skills/` and `.codex/skills/` mirrors)
  already do."

## Empirical evidence

`uv run python .game-of-cards/deck/agents-md-claims-the-card-schema-is-inlined-into-the-skill-body/reproduce.py`:

```
[1] AGENTS.md lines asserting 'inlined into the `card-schema`': [161]
[2] `_iter_skill_assets` plans a verbatim copy of 'card-schema/schema.yaml': True
[3] schema keys found inside card-schema/SKILL.md: none
[4] SKILL.md says 'ships as the sibling `schema.yaml`': True
[5] AGENTS.md lines calling the same file a sibling verbatim copy: [377]
[6] scripts/sync_plugin_assets.py mentions schema.yaml: False
[6] goc/schema.yaml and the template copy are byte-identical today: True

FAIL: AGENTS.md still claims the schema is inlined into the skill body
```

Line `[3]` is the direct disproof: not one of the schema's six top-level
keys (`schema_version`, `required_fields`, `optional_fields`,
`title_pattern`, `status_values`, `canonical_tags`) appears anywhere in
`SKILL.md`. A `goc install --local-skills` into a fresh repo confirms the
same thing at the far end — the installed
`.claude/skills/card-schema/schema.yaml` is byte-identical to
`goc/schema.yaml`, and the installed `SKILL.md` contains zero schema keys.

## Why it matters

`AGENTS.md` is this repo's always-loaded agent briefing — `CLAUDE.md`
contains nothing but `@AGENTS.md` — so this sentence is what an agent
reads before touching the schema, and the section it sits in exists
precisely to tell that agent which files matter.

"Single source of truth ... inlined at install time" reads as *one file,
generated everywhere else*. The truth is *two hand-maintained checked-in
files*: `goc/schema.yaml` and `goc/templates/skills/card-schema/schema.yaml`.
Line `[6]` shows `scripts/sync_plugin_assets.py` never mentions
`schema.yaml` — the pre-commit sync mirrors the *template* onward to the
four plugin/vendored copies, but nothing propagates the engine schema into
the template. So the edit the briefing invites — change `goc/schema.yaml`,
trust the rest to regenerate — leaves the template stale and turns CI red
via `tests/test_skill_schema_yaml_parity.py`, with no pointer in the
briefing to the file that has to move too.

That is not hypothetical: the closed card
[card-schema-skill-bundled-schema-omits-supersedes-superseded-by-and-worker](../card-schema-skill-bundled-schema-omits-supersedes-superseded-by-and-worker/)
is exactly this failure — three optional fields added to `goc/schema.yaml`
never reached the skill copy, and the drift shipped through all four
mirrors before anyone noticed. The parity test was written in response;
the briefing was never corrected to match.

The stale framing has also already propagated into deck content: the open
card
[trailing-newline-title-passes-guards-and-scaffolds-unaddressable-card-dir](../trailing-newline-title-passes-guards-and-scaffolds-unaddressable-card-dir/)
justifies its `## Decision required` with "`title_pattern` is a published
contract surface (inlined into the `card-schema` skill and read by
consumers)" — a phrase inherited from this bullet. Its conclusion survives
the correction (the pattern *is* a published contract surface either way),
but a false mechanism spreading into decision rationale is the cost this
card is about.

## Fix

Rewrite the bullet at `AGENTS.md:161` so it describes the copy mechanism
and names the second file, e.g.:

```markdown
- **`goc/schema.yaml`** — single source of truth for card frontmatter
  (loaded by `engine.load_schema()`). The `card-schema` skill ships a
  byte-identical copy at `goc/templates/skills/card-schema/schema.yaml`,
  which `goc install` and the plugin mirrors copy verbatim as a sibling
  file. Nothing auto-syncs the two: edit both, or
  `tests/test_skill_schema_yaml_parity.py` turns the build red.
```

Then pin it. `tests/test_guidance_accuracy.py` already owns this exact
job for the two neighbouring bullets — `test_cli_bullet_does_not_mention_click`
guards the `goc/cli.py` bullet and `test_all_engine_verbs_listed_in_architecture_section`
guards the `goc/engine.py` bullet, both via the `_agents_architecture_section()`
helper. Add the schema bullet to that class rather than filing a new
guard-shaped card: the generalization
([generated-agents-guidance-overstates-done-commit](../generated-agents-guidance-overstates-done-commit/))
already landed, and this is an instance it should have covered.

Deliberately **out of scope**: whether the `goc/schema.yaml` → template
duplication should be auto-synced by `scripts/sync_plugin_assets.py`
instead of guarded after the fact by a test. That is a mechanism change
with two credible answers (auto-sync silently, or keep the test so a
schema edit is a conscious two-file act), and it needs a human pick. This
card only makes the briefing tell the truth about the mechanism that
exists today.
