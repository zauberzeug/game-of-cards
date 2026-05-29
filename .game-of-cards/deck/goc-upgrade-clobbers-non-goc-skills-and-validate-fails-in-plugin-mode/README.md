---
title: goc-upgrade-clobbers-non-goc-skills-and-validate-fails-in-plugin-mode
summary: "Two upstream bugs surfaced 2026-05-14 in a consuming repo mid plugin-mode cutover. (1) Bare `goc upgrade` from a pipx install, on a repo with a `.claude/skills/` directory (even one containing only non-GoC skills) and no `--keep-local-skills` flag, enters the interactive migration prompt and — on decline or non-TTY default-N — silently re-vendors 15 SKILL.md trees + 3 hook scripts + 3 `.claude/settings.json` hook wirings AND `shutil.rmtree`s every non-GoC skill directory in `.claude/skills/` (collateral via `replace_skills=True` at `install.py:743-749`). The announced message says 'defaults to the plugin path' while the prompt default is `[y/N]`. (2) `goc validate`'s `validate_skill_dir_parity` (`engine.py:519-548`) treats `.claude/skills/` existence as proof of GoC ownership and demands all template skills be present, false-positiving every commit in a plugin-mode repo with any non-GoC skill. Both bugs share one root cause: no per-repo signal that says 'this repo is plugin-mode,' so pipx-goc assumes `.claude/skills/` is GoC's territory. Fix shape: per-repo config (`.game-of-cards/config.yaml` `skills_source: plugin|vendored|auto`) read by both `upgrade` and `validate_skill_dir_parity` — repo-local, not machine-state, so the contract is unambiguous across contributors and CI."
status: done
stage: null
contribution: high
created: "2026-05-14T04:17:31Z"
closed_at: "2026-05-14T04:37:27Z"
human_gate: none
advances: []
advanced_by:
  - refuse-local-skills-flag-when-running-under-plugin
tags: [bug, api-contract]
definition_of_done: |
  - [x] `.game-of-cards/config.yaml` schema gains a `skills_source` key with values `plugin` | `vendored` | `auto`; template ships with `auto` documented as the unset default (effective value is resolved at runtime by plugin-presence detection)
  - [x] `goc upgrade` reads `skills_source` before the migration prompt. `plugin` mode: skip the prompt entirely, do not call `_sync_agent_harness` for claude with `replace_skills=True`, do not rewrite `.claude/settings.json` GoC entries, do not touch `.claude/skills/` or `.claude/hooks/`. `vendored` mode: refresh in place, no prompt. `auto` (or absence): detect plugin presence (via `${CLAUDE_PLUGIN_ROOT}` or `~/.claude/plugins`) and behave as `plugin` when found, else as `vendored`
  - [x] `_sync_skill_tree(replace_skills=True)` at `goc/install.py` no longer deletes skill directories whose names aren't in the GoC template eligible set — destructive cleanup of user content removed entirely; only the eligible-skill replace remains for refresh semantics
  - [x] `validate_skill_dir_parity` at `goc/engine.py` reads `effective_skills_source()` and short-circuits to `[]` when value is `plugin`. Error message in vendored mode now points at both `goc upgrade --keep-local-skills` and the config-pin alternative
  - [x] Migration prompt text and prompt-default no longer contradict — the old conflated prompt is gone. The new cleanup prompt is opt-in (only fires when `skills_source: plugin` is set AND leftover `.claude/skills/` exists), has a non-destructive default, and the decline path is a strict no-op (never re-vendors)
  - [x] Non-TTY context detection: addressed by design — no prompt has a destructive default any longer, so non-TTY `_confirm` returning False is safe everywhere it can fire
  - [x] `goc install` writes `skills_source: plugin` to the project config when the Claude plugin-path is the chosen install mode (i.e. no `--local-skills`); writes `skills_source: vendored` when `--local-skills` is passed (verified by `test_install_default_writes_skills_source_plugin` / `test_install_local_skills_writes_skills_source_vendored`)
  - [x] `goc upgrade --keep-local-skills` continues to work in pipx context as today (forces `vendored` mode regardless of config, re-syncs templates in place); existing tests still pass
  - [x] `_strip_claude_vendored_harness` only deletes GoC-owned skill directories during the plugin-mode cleanup, preserving user-authored skills in `.claude/skills/` (verified by `test_plugin_mode_cleanup_confirm_preserves_user_skills`)
  - [x] Regression tests cover: (a) plugin-mode upgrade on a repo with non-GoC skills leaves user content untouched; (b) plugin-mode validate on the same repo passes; (c) vendored-mode upgrade does not prompt; (d) `replace_skills=True` no longer deletes non-eligible skill dirs; (e) cleanup confirm/decline both preserve user skills; (f) install writes the right `skills_source` for both plugin and vendored modes
  - [x] CLAUDE.md updated with a new `skills_source` subsection documenting the three values, install-time write behavior, and the manual config-edit migration path
  - [x] `uv run goc validate` passes; full pytest suite passes except the pre-existing `test_board_and_open_queue_surface_active_cards` failure on main (unrelated to this card)
worker: {who: human, where: main}
---

# `goc upgrade` clobbers non-GoC skills and `goc validate` fails in plugin-mode repos

## Why

Two upstream bugs surfaced 2026-05-14 during a consuming repo's
cutover from vendored skills to plugin-mode. Both are rooted in the
same gap: the pipx-installed `goc` engine has no signal that says
"this repo is plugin-mode," so it treats `.claude/skills/` as GoC's
exclusive territory in code paths where that assumption is now wrong.

The closed predecessor card
`refuse-local-skills-flag-when-running-under-plugin` (2026-05-09)
added a refusal for **explicit** `--local-skills` / `--keep-local-skills`
flags in **plugin-engine** context (`_is_plugin_context() = True`).
This failure mode is the inverted quadrant — **no flag** in
**pipx-engine** context — so neither refusal precondition fires.

## Bug 1 — `goc upgrade` re-vendors and deletes user skills

### Reproduction

Pipx-installed `goc`. Repo has `.claude/skills/` (with or without
GoC skills inside; the directory's presence is sufficient). Claude
Code plugin is installed at the user level and provides GoC skills
via `${CLAUDE_PLUGIN_ROOT}/skills/`.

```
goc upgrade
```

### What gets announced

```
This repo has vendored GoC skills. goc upgrade now defaults to the plugin path —
this will remove .claude/skills/, .claude/hooks/ (GoC-managed), and GoC
entries from .claude/settings.json. Pass --keep-local-skills to skip.

Migrate to plugin path? [y/N]:
```

### What actually happens on decline (or non-TTY default-N)

- 15 GoC skill directories written to `.claude/skills/` from the
  bundled template set (full SKILL.md tree).
- `_goc-bootstrap.sh` wrapper written to `.claude/skills/`.
- 3 hook scripts copied to `.claude/hooks/`.
- 3 hook wirings (`SessionStart`, `UserPromptSubmit`, `Stop`) written
  into `.claude/settings.json`, pointing at
  `${CLAUDE_PROJECT_DIR}/.claude/hooks/`.
- **Any non-GoC skill directory containing a `SKILL.md` is
  `shutil.rmtree`-deleted** by `_sync_skill_tree(replace_skills=True)`
  at `goc/install.py:743-749`. The eligibility filter is "is the
  directory name in the GoC template set"; anything outside that set
  is collateral damage.

The "decline migration" branch at `install.py:1156-1159`:

```python
confirmed = _confirm("Migrate to plugin path?", default=False)
if not confirmed:
    agents_to_migrate = frozenset()
    local_skills_agents = local_skills_agents | frozenset(["claude"])
```

adds `claude` to `local_skills_agents`, which makes the subsequent
`_sync_agent_harness` call use `guidance_only=False, replace_skills=True`.
End state: the same as `--keep-local-skills`, reachable without the
flag.

### Severity

High. Documented plugin-install path
(`/plugin install game-of-cards` + `goc install` + later
`goc upgrade`) walks straight into this on the next routine upgrade.
Loss of user-owned skill content under a flag the user never set.

## Bug 2 — `goc validate` parity check false-positives in plugin-mode

### Reproduction

Same repo state as Bug 1, after the plugin provides GoC skills via
`${CLAUDE_PLUGIN_ROOT}/skills/` and the user keeps non-GoC skills in
`.claude/skills/`.

```
goc validate
```

### What happens

```
ERROR: .claude/skills: missing skills ['advance-card', 'audit-deck',
'card-schema', 'claude-kickoff', 'create-card', 'decide-card', 'deck',
'finish-card', 'kickoff', 'next-card', 'pull-card', 'refine-deck',
'retrospective', 'scan-deck', 'standup'] that goc templates ship; run
`goc upgrade --keep-local-skills` to resync
```

Exit 1. The pre-commit hook fails every commit.

### Root cause

`validate_skill_dir_parity` (`goc/engine.py:519-548`):

```python
for relative, agent in ((".claude/skills", "claude"), (".codex/skills", "codex")):
    consumer_dir = REPO_ROOT / relative
    if not consumer_dir.exists():
        continue
    expected = {s for s in all_template if skill_for_agent(s, agent)}
    actual = {p.name for p in consumer_dir.iterdir() if (p / "SKILL.md").is_file()}
    missing = expected - actual
    if missing:
        errors.append(...)
```

The check skips when `.claude/skills/` is absent but otherwise treats
any subdirectory shortfall against the template set as an error. In
plugin-mode, `.claude/skills/` exists *because the user has non-GoC
skills there* — GoC's own skills live under `${CLAUDE_PLUGIN_ROOT}`,
which the check never inspects. Every commit fails until the user
disables the pre-commit hook (which the consumer did, losing the
validate safety net for cards).

## Shared root cause

Both bugs hard-code the assumption "GoC owns `.claude/skills/` and
`.claude/hooks/`." That assumption was true before the plugin path
shipped; with the plugin providing skills at a different on-disk
location, the assumption is wrong whenever a repo has elected
plugin-mode. The pipx-installed engine has no way to know which mode
the repo is in.

## Fix shape

**Per-repo config**, not machine-state detection. A
`.game-of-cards/config.yaml` key (e.g. `skills_source: plugin |
vendored | auto`) read by both `upgrade` and
`validate_skill_dir_parity`. Read from source control, so:

- A teammate without the plugin installed sees the same behavior as
  one with the plugin installed.
- CI without the plugin doesn't false-positive into "vendored mode"
  and re-introduce the bug.
- The contract is unambiguous and reviewable in PRs.

Machine-state detection (the contributor's Option 1) can remain as a
*suggestion* path (`auto` mode: "plugin appears installed; want me
to pin `skills_source: plugin` in the config?"), but the
source-of-truth for "this repo is plugin-mode" should be checked-in
config.

Secondary fixes layered on top:

- `_sync_skill_tree(replace_skills=True)` at `install.py:743-749`
  must stop deleting non-eligible skill directories. Destructive
  cleanup of user content needs an explicit opt-in flag (e.g.
  `--purge-non-goc-skills`) — never a side effect of bare upgrade.
- Migration prompt text and default must agree. Decline path must
  abort or no-op, not re-vendor.
- Non-TTY detection: abort the interactive prompt with a recovery
  hint rather than silently choosing the destructive branch.

## Decision

*Resolved 2026-05-14:* Add skills_source key (plugin|vendored|auto) to .game-of-cards/config.yaml; default for new installs and unset-key reads is 'auto' which performs real plugin-presence detection

*Reasoning:* config.yaml already holds project state and the existing audience reads it; skills_source matches the noun it controls; 'auto' that actually auto-detects matches its name, and the safer-default reading was rejected — existing repos transitioning to plugin-mode will benefit from detection rather than continuing the wrong behavior
