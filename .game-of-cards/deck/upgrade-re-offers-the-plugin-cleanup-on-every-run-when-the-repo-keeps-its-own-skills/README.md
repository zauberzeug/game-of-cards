---
title: upgrade-re-offers-the-plugin-cleanup-on-every-run-when-the-repo-keeps-its-own-skills
summary: "In plugin mode, goc upgrade offers the vendored-layout cleanup whenever a .claude/skills/ directory exists, but the cleanup deliberately keeps the repo's own skills there. So after a completed switch, every later goc upgrade claims a leftover vendored layout and asks again, and its already-at-version no-op verdict can never fire. The reverse also holds: GoC hook scripts and settings registrations left without a .claude/skills/ dir are never offered for removal, so they keep double-firing beside the plugin."
status: active
stage: null
contribution: medium
created: "2026-10-02T04:45:40Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — after a confirmed cleanup that kept a repo-owned skill, the next `goc upgrade` neither offers the cleanup nor announces it under `--dry-run`, and a plugin-mode repo holding GoC hook scripts and settings entries but no `.claude/skills/` is offered the cleanup and ends with none of them
  - [ ] TDD: regression tests in `tests/test_install.py` pin both directions, plus `_strip_claude_vendored_harness(..., probe=True)` reporting the pending removal while changing nothing on disk
  - [ ] MECHANICAL: the offer asks the cleanup executor in `probe=True` mode instead of restating it as a directory test, and the prompt text and dry-run note stop naming `.claude/skills/` as what was found; `AGENTS.md`'s switch paragraph says what the detection keys on
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` pass
worker: {who: "claude[bot]", where: main}
---

# goc upgrade re-offers the plugin cleanup on every run once the repo keeps its own skills

## Location

`goc/install.py`, `upgrade()` — the plugin-mode cleanup offer:

```python
    claude_has_vendored = False
    if "claude" in agents:
        claude_shim = _load_agent_shim(templates, "claude")
        claude_has_vendored = bool(claude_shim.skills and (target / claude_shim.skills.target).is_dir())

    needs_vendored_cleanup = claude_skills_mode == "plugin" and claude_has_vendored
```

`needs_vendored_cleanup` drives the prompt, the `--dry-run` note
("will offer cleanup of leftover .claude/skills/ (plugin mode)"), and
`pending_cleanup`, one of the terms in the "already at goc X — nothing to
do." short-circuit.

The executor it stands in for, `_strip_claude_vendored_harness`, removes
three things: the skill dirs named like GoC's skill templates, the GoC hook
scripts (plus the `_goc-bootstrap.sh` shim file), and the GoC entries in
`.claude/settings.json`. Its docstring says "User-authored skills with
other names in `.claude/skills/` are preserved." The prompt says the same
to the user.

## What's broken

The offer tests whether a directory exists, while the cleanup works on GoC
content. The two disagree in both directions:

1. **A completed switch is offered again, forever.** The cleanup keeps the
   repo's own skills, so `.claude/skills/` survives it whenever the repo
   has one. Every later `goc upgrade` then prints "a leftover
   .claude/skills/ from a prior vendored install was found" and asks
   again. `pending_cleanup` stays true, so the "already at goc X — nothing
   to do." verdict can never fire. On a TTY the user is asked on every
   upgrade; with empty stdin it prints "Skipping cleanup" on every run.
2. **GoC leftovers without a skills dir are never offered.** A repo in
   plugin mode that still has `.claude/hooks/deck_*.py` and the GoC
   registrations in `settings.json`, but no `.claude/skills/`, is never
   offered the cleanup. Those hooks keep firing beside the plugin's.
   `goc validate`'s `PLUGIN_AND_VENDORED_HOOKS_DOUBLE_FIRE` warning tells
   the user to run `goc upgrade` and accept its cleanup, and in this state
   there is no cleanup to accept.

## Empirical evidence

`reproduce.py` builds two scratch `goc install --local-skills` repos and
switches each with `skills_source: plugin`, the documented way:

```
[A] switch upgrade: offered=True; .claude/skills/ now holds ['my-own-skill']
[A] next routine upgrade: offered again=True; no-op verdict=False
[A] --dry-run announces cleanup=True
[B] before upgrade: 3 GoC hook scripts, 3 GoC settings entries
[B] upgrade offered the cleanup=False; after: 3 scripts, 3 entries

FAIL:
  A: the cleanup is re-offered after it ran, for a layout holding only the repo's own skill
  B: GoC hook scripts / settings entries survive because no .claude/skills/ dir triggers the offer
```

## Why it matters

[cli-reference-plugin-switch-recipe-deletes-user-skills-and-the-next-upgrade-reverts-it](../cli-reference-plugin-switch-recipe-deletes-user-skills-and-the-next-upgrade-reverts-it/)
made `goc.md` send consumers through this exact switch, and it stresses
that the cleanup keeps the repo's own skills. Case 1 is therefore the
normal outcome for any repo that keeps a skill of its own. Case 2 is the
state a partial hand cleanup leaves, and it is the state where duplicate
hook firing persists.

## Fix

Ask the executor rather than restating it. This is the repo's convention
for upgrade-time work signals (`_write_skills_source(probe=True)`,
`_sync_skill_tree(probe=True)`; `AGENTS.md` § "`.game-of-cards/` ownership
model and `goc upgrade` contract"):

- `_strip_claude_vendored_harness(target, templates, *, probe=False) -> bool`
  works out the GoC skill dirs, hook/shim files and settings entries it
  would remove. With `probe=True` it returns whether there are any and
  touches nothing.
- `_strip_goc_settings_entries(settings_path, *, probe=False) -> bool`
  returns whether it would change the file. With `probe=True` it skips the
  write and the malformed-file warnings, which the real run prints.
- `upgrade()` sets `needs_vendored_cleanup` from
  `_strip_claude_vendored_harness(target, templates, probe=True)` in plugin
  mode.
- The prompt and the dry-run note say "GoC files from a prior vendored
  install" instead of ".claude/skills/". `AGENTS.md`'s switch paragraph
  says the offer keys on GoC-owned leftovers.

The probe inherits the executor's identification rule (current template
names). Prior-version names stay the business of
[goc-upgrade-cleanup-misses-prior-version-skills-and-hooks-renamed-since-install](../goc-upgrade-cleanup-misses-prior-version-skills-and-hooks-renamed-since-install/).
