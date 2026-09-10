---
title: plugin-engine-upgrade-crashes-with-a-traceback-in-vendored-pinned-repos
summary: "In any repo pinned skills_source: vendored (what the documented \"goc install --local-skills\" writes), running \"goc upgrade\" from a plugin-bundled engine dies with an unhandled FileNotFoundError on templates/skills — the directory all three plugin payloads deliberately omit. The plugin-context refusal guards only the explicit --keep-local-skills flag, but upgrade() re-derives the same vendored mode from config.yaml with no such check, and --dry-run crashes identically so the user cannot even preview."
status: open
stage: null
contribution: high
created: "2026-09-10T04:49:51Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] DECISION: pick the behavior for plugin-engine + `skills_source: vendored` — refuse with a message naming the config pin and the edit that resolves it, or degrade to a plugin-mode upgrade that skips the skill tree and does the rest (see `## Decision required`)
  - [ ] TDD: `reproduce.py` exits zero — neither `goc upgrade` nor `goc upgrade --dry-run` tracebacks from a plugin-bundled engine in a vendored-pinned repo
  - [ ] TDD: a regression test covers the config-derived vendored mode under plugin context, not only the `--keep-local-skills` flag
  - [ ] MECHANICAL: if the decision is "refuse", `_KEEP_LOCAL_SKILLS_PLUGIN_REFUSAL` stops advising "omit `--keep-local-skills` here to migrate to the plugin path" — today that instruction leads straight into the traceback
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` pass
---

# `goc upgrade` from a plugin engine tracebacks in vendored-pinned repos

## Location

`goc/install.py:1962-1964` — the plugin-context refusal, which guards only the
explicit flag:

```python
    if keep_local_skills and _is_plugin_context():
        print(_KEEP_LOCAL_SKILLS_PLUGIN_REFUSAL, file=sys.stderr)
        sys.exit(2)
```

`goc/install.py:2007-2012` — the same vendored mode re-derived from
`.game-of-cards/config.yaml`, with no such check:

```python
    if keep_local_skills:
        claude_skills_mode = "vendored"
    elif "claude" in agents:
        claude_skills_mode = effective_skills_source()
    else:
        claude_skills_mode = "vendored"
```

`goc/install.py:1434` — the unguarded walk it reaches, via
`_plan_upgrade_writes` → `_plan_writes` (`goc/install.py:963`):

```python
    for skill_dir in sorted(p for p in skills_src.iterdir() if p.is_dir()):
```

## What's broken

`goc install --local-skills` — the documented way to vendor skills into source
control — writes `skills_source: vendored` into `.game-of-cards/config.yaml`.
That pin is authoritative for every later `goc upgrade`.

If the engine running that upgrade is a plugin-bundled one, the pin sends it to
read `templates/skills/`, which all three payloads deliberately omit. AGENTS.md
states the omission and the reason:

> The nested `claude-plugin/goc/templates/...` mirrors the rest of the package
> (…) but **deliberately omits** `templates/skills/`: the bundled engine refuses
> `--local-skills` on `goc install` and `--keep-local-skills` on `goc upgrade`
> (see `_is_plugin_context` in `goc/install.py`), so the skill templates are
> never read from inside the plugin payload.

"Never read" is the invariant the refusal is supposed to hold. It holds for the
flag and not for the config pin, so the payload is asked for a directory it does
not ship and the walk raises. Verified absent in all three:
`claude-plugin/goc/templates/skills`, `codex-plugin/goc/templates/skills`,
`openclaw-plugin/goc/templates/skills`.

The refusal message compounds it. `_KEEP_LOCAL_SKILLS_PLUGIN_REFUSAL` ends:

```
       Or omit --keep-local-skills here to migrate to the plugin path.
```

Omitting the flag is exactly what produces the traceback, and no migration
happens either way — the config pin still says `vendored`.

## Empirical evidence

`uv run python .game-of-cards/deck/plugin-engine-upgrade-crashes-with-a-traceback-in-vendored-pinned-repos/reproduce.py`:

```
config pin: skills_source: vendored

[upgrade] exit=1 traceback=True
  FileNotFoundError: [Errno 2] No such file or directory: '.../claude-plugin/goc/templates/skills'

[upgrade --dry-run] exit=1 traceback=True
  FileNotFoundError: [Errno 2] No such file or directory: '.../claude-plugin/goc/templates/skills'

[FAIL] plugin-engine upgrade tracebacks in a vendored-pinned repo: upgrade, upgrade --dry-run
```

Full frame, from a hand run:

```
  File ".../claude-plugin/goc/install.py", line 2031, in upgrade
    upgrade_plan = _plan_upgrade_writes(
  File ".../claude-plugin/goc/install.py", line 1100, in _plan_upgrade_writes
    for write in _plan_writes(
  File ".../claude-plugin/goc/install.py", line 963, in _plan_writes
    for rel in _iter_skill_assets(templates / "skills", agent):
  File ".../claude-plugin/goc/install.py", line 1434, in _iter_skill_assets
    for skill_dir in sorted(p for p in skills_src.iterdir() if p.is_dir()):
FileNotFoundError: [Errno 2] No such file or directory: '.../claude-plugin/goc/templates/skills'
```

Controls: `--keep-local-skills` reaches the polite refusal; the same repo
upgraded with a source (pipx-style) engine exits 0. The Codex wrapper fails
identically on `codex-plugin/goc/templates/skills`.

## Why it matters

The plugin is the **default** install channel and `upgrade` is how a consumer
takes a release. Any consumer who followed the documented `--local-skills`
recipe — and later has the plugin enabled — gets an unhandled traceback on the
one verb that keeps their install current. `--dry-run` fails the same way, so
they cannot even preview what upgrade would do, and the printed guidance points
them at the crashing invocation.

## Decision required

Two credible behaviors, and the engine cannot pick without a maintainer call:

1. **Refuse, symmetrically with the flag.** Extend the `_is_plugin_context()`
   guard to the config-derived vendored mode and print a message naming the pin
   plus the resolving edit (`skills_source: plugin`, or install a source
   engine). Honest, but a plugin-mode user with a vendored-pinned repo cannot
   upgrade *anything* until they hand-edit config.
2. **Degrade to a plugin-mode upgrade.** Treat plugin-context + vendored pin as
   "skip the skill tree, upgrade every other surface", warning once. The upgrade
   succeeds, but the pin now silently means something different depending on
   which engine reads it — and the existing vendored `.claude/skills/` quietly
   stops being refreshed.

Whichever is chosen, the refusal text's "omit `--keep-local-skills` here to
migrate to the plugin path" advice needs rewriting: it does not migrate
anything.

The same underlying question is already pending on
[codex-install-from-plugin-payload-vendors-skills-and-crashes-on-omitted-templates-skills](../codex-install-from-plugin-payload-vendors-skills-and-crashes-on-omitted-templates-skills/),
whose DoD carries a `DECISION: pick the intended behavior — refuse or …` item.
That card is scoped to *Codex install* and is tagged `unverified` (it states its
runtime reachability is unproven). This card is the *Claude upgrade* instance,
on the default agent and default channel, and is empirically reproduced. They
share one decision and should be resolved together; no edge is recorded because
neither blocks the other's closure.

## Fix sketch

Whichever branch is chosen, the guard belongs where the mode is finally known —
after `claude_skills_mode` is resolved at `goc/install.py:2007-2012` — rather
than beside the flag at `:1962`, so any future path that arrives at `vendored`
is covered by construction instead of by a second hand-written check.
