---
title: goc-validate-misses-plugin-and-vendored-hook-double-registration
summary: "When a repo has GoC hooks vendored in .claude/ AND the Claude Code GoC plugin is also enabled for that repo, both register the same lifecycle hooks and each fires twice (wasted tokens, double interruption). goc validate has no check for this — add an advisory warning that detects the overlap by resolving the enabledPlugins settings cascade against the repo's vendored .claude/hooks registrations."
status: active
stage: null
contribution: medium
created: "2026-06-26T06:36:40Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] TDD: tests cover the matrix — (plugin enabled + vendored hooks) → warns; (plugin disabled/absent + vendored) → silent; (plugin enabled + no vendored hooks) → silent; malformed/missing settings → silent (no crash) — `tests/test_validate_plugin_hook_double_fire.py`
  - [ ] MECHANICAL: `goc/engine.py` gains `validate_plugin_hook_double_fire(repo_root, home)` returning `BlockerWarning`s, plus helpers to (a) resolve `enabledPlugins` across the user→project→local settings cascade and (b) detect vendored GoC-hook registrations in the repo's `.claude/settings.json`
  - [ ] MECHANICAL: wired into `_cmd_validate` as an ADVISORY warning (printed, NOT appended to `errors` — must not gate exit 1, since it reads host config absent in CI)
  - [ ] MECHANICAL: the warning names the enabled plugin key, the overlapping hooks, and both remediations (disable the plugin for this repo, or switch to `skills_source: plugin` + drop `.claude/hooks/`)
  - [ ] PROCESS: asset mirrors synced (engine.py → claude/codex/openclaw `goc/` mirrors); parity + porter checks green
  - [ ] PROCESS: full suite green and `uv run goc validate` clean (self-check: this dogfood repo currently triggers the warning until the plugin is disabled for it — confirm the message reads correctly here)
worker: {who: Rodja Trappe, where: main}
---

# goc-validate-misses-plugin-and-vendored-hook-double-registration

`goc validate` should warn when a repo will **double-fire** its GoC
lifecycle hooks: once from an enabled Claude Code plugin and once from
hooks vendored into `.claude/`.

## What's missing

Two independent registration channels can both be live in one repo:

1. **Vendored** — `.claude/hooks/<script>.py` exist and `.claude/settings.json`
   registers them with commands like
   `python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/pattern_generalization_check.py`.
2. **Plugin** — the Claude Code GoC plugin is *enabled* for the repo
   (`enabledPlugins["game-of-cards@<marketplace>"]: true` somewhere in the
   settings cascade), and its `hooks/hooks.json` registers the same three
   lifecycle hooks via `${CLAUDE_PLUGIN_ROOT}/hooks/...`.

When both are live, every `SessionStart` / `UserPromptSubmit` / `Stop`
fires **twice**. Observed in this very repo: the `Stop` pattern-check hook
emitted two reminders per turn — one `${CLAUDE_PLUGIN_ROOT}` and one
`${CLAUDE_PROJECT_DIR}/.claude/hooks/` — because the plugin was enabled
**user-globally** in `~/.claude/settings.json` while the repo also vendors
its hooks (it is the GoC source repo). `goc validate` reported nothing.

`goc validate` already reads host state for `skills_source: auto`
(`_claude_plugin_present()` walks `~/.claude/plugins`), so a host-aware
advisory here is consistent with the existing design — it just needs the
*enablement* signal, not mere payload presence.

## Why payload-presence is not enough

`_claude_plugin_present()` returns true whenever the plugin payload is
cached on disk, even if the plugin is **disabled**. The double-fire only
happens when the plugin is *enabled* for the repo. So the detector must
resolve `enabledPlugins` across the cascade (most-specific wins):

```
~/.claude/settings.json            (user)     <  lowest precedence
<repo>/.claude/settings.json       (project)
<repo>/.claude/settings.local.json (local)    <  highest precedence
```

Gating on enablement (not presence) avoids a false positive the moment a
user disables the plugin for the repo but leaves the payload cached —
exactly the state this repo is now in after the fix that motivated this card.

## Fix

Add to `goc/engine.py`:

- `_read_enabled_plugins(settings_path) -> dict[str, bool]` — parse one
  settings file's `enabledPlugins`; tolerate missing file / bad JSON / wrong
  shape by returning `{}`.
- `_resolve_enabled_plugins(repo_root, home) -> dict[str, bool]` — merge the
  three sources in precedence order.
- `_enabled_goc_plugin_key(repo_root, home) -> str | None` — first key whose
  name before `@` is `game-of-cards` and whose resolved value is truthy.
- `_vendored_goc_hooks_registered(repo_root) -> list[str]` — GoC hook
  basenames (from `install.GOC_CLAUDE_HOOKS`) whose
  `${CLAUDE_PROJECT_DIR}/.claude/hooks/<basename>` command appears in the
  repo's `.claude/settings.json` `hooks` block.
- `validate_plugin_hook_double_fire(repo_root=REPO_ROOT, home=Path.home())
  -> list[BlockerWarning]` — when an enabled GoC plugin key AND ≥1 vendored
  GoC hook are both present, emit one
  `PLUGIN_AND_VENDORED_HOOKS_DOUBLE_FIRE` warning naming the key, the
  overlapping hooks, and the two remediations.

Wire into `_cmd_validate` in the advisory block (printed via `.message`, NOT
appended to `errors`) so it never gates exit 1 — the check reads host config
that is absent in CI.

All helpers take explicit `repo_root` / `home` for unit-testing against temp
trees.

## Why it matters

Double-firing doubles the token cost and the interruption rate of the very
hooks the user is already wary of (see the just-closed
`make-pattern-generalization-stop-hook-opt-in`). It is silent — nothing in
the deck or `goc validate` surfaces it — so a user only notices via repeated
hook output, then has to reverse-engineer the plugin-vs-vendored settings
cascade by hand (as happened here). A one-line validate warning turns that
investigation into a glance.
