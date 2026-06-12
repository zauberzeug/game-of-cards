---
title: agents-md-claims-bundled-engine-omits-hook-templates-it-now-ships
summary: "AGENTS.md says the nested claude-plugin/goc/templates/ mirror 'deliberately omits templates/skills/ and the deck_prompt_router / deck_session_start hook templates'. Since commit 8277962 (derive hook manifest from templates/hooks/*.py) only templates/skills is excluded — the hook templates DO ship in the deep mirrors, and the sync script's own docstring states the opposite of AGENTS.md ('hook scripts are NOT excluded so the bundled engine can derive its hook list'). One-sentence doc fix."
status: open
stage: null
contribution: low
created: "2026-06-12T04:45:32Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [documentation]
definition_of_done: |
  - [ ] MECHANICAL: AGENTS.md's "deliberately omits" sentence names only `templates/skills/` (and, if it mentions hooks at all, says they are deliberately INCLUDED so the bundled engine can derive its hook list — matching the sync script's docstring).
  - [ ] MECHANICAL: `grep -n "deck_prompt_router.*hook templates" AGENTS.md` no longer claims the hook templates are omitted; `python scripts/sync_plugin_assets.py --check` stays green (AGENTS.md is not a synced mirror, this is just the no-collateral check).
---

# AGENTS.md claims the bundled engine omits hook templates it now ships

## Location

`AGENTS.md:259-265` (the "Plugin assets are auto-synced" section):

> The nested `claude-plugin/goc/templates/...` mirrors the rest
> of the package (engine, schema, agents, game_of_cards templates, etc.)
> but **deliberately omits** `templates/skills/` and the
> `deck_prompt_router` / `deck_session_start` hook templates: …

## What's broken

Only `templates/skills` is excluded from the deep mirror —
`scripts/sync_plugin_assets.py:118-125` builds the `goc →
claude-plugin/goc` pair with `frozenset({"templates/skills"})` as the
exclude set, and the script's own docstring
(`scripts/sync_plugin_assets.py:69-71`) states the opposite of AGENTS.md
verbatim:

> That path is excluded from the `goc → claude-plugin/goc` deep mirror;
> hook scripts are NOT excluded so the bundled engine can derive its hook
> list from `templates/hooks/`.

On disk: `claude-plugin/goc/templates/hooks/` and
`codex-plugin/goc/templates/hooks/` both contain `deck_prompt_router.py`,
`deck_session_start.py`, and `pattern_generalization_check.py`.

The hook templates entered the deep mirror at commit `8277962`
("Derive Claude hook manifest from templates/hooks/*.py", 2026-05-09),
which made `deck_hook_scripts()` glob `templates/hooks/*.py` at runtime —
the bundled engine now *needs* those files. The AGENTS.md sentence
predates that change and was never updated.

## Why it matters

AGENTS.md is the briefing every agent loads each session. An agent asked
to touch the hook-template exclusion logic (or to debug why the plugin
payload contains hook files) starts from a premise that contradicts both
the code and the script docstring, and has to burn a round discovering
which surface drifted. The sync docstring and the disk state agree; only
AGENTS.md is wrong.

## Fix

Rewrite the sentence at `AGENTS.md:261-262` to claim only the
`templates/skills/` omission, e.g.:

> but **deliberately omits** `templates/skills/`: the bundled engine
> refuses `--local-skills` … (hook templates ARE included so the bundled
> engine can derive its hook list from `templates/hooks/`).

No code change; AGENTS.md's non-marker content is human/agent-editable
(it is outside the release tripwire's tracked set).
