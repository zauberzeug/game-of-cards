# Log

## 2026-06-26 — closed (implemented)

Added an advisory `goc validate` check that warns when a repo will
double-fire its GoC lifecycle hooks.

**Implementation (`goc/engine.py`, grouped with the existing plugin-detection
helpers):**

- `_read_enabled_plugins(settings_path)` — one settings file's
  `enabledPlugins`, `{}` on missing/bad-JSON/wrong-shape.
- `_resolve_enabled_plugins(repo_root, home)` — merges user
  `~/.claude/settings.json` < project `.claude/settings.json` < project-local
  `.claude/settings.local.json`, most-specific wins (matches Claude Code).
- `_enabled_goc_plugin_key(repo_root, home)` — first enabled key whose name
  before `@` is `game-of-cards`.
- `_goc_hook_basenames()` — derived from `install.GOC_CLAUDE_HOOKS`.
- `_vendored_goc_hooks_registered(repo_root)` — GoC hook basenames whose
  `.claude/hooks/<name>` command appears in the repo's `.claude/settings.json`
  `hooks` block (the vendored form; the plugin uses `${CLAUDE_PLUGIN_ROOT}`).
- `validate_plugin_hook_double_fire(repo_root, home)` — one
  `PLUGIN_AND_VENDORED_HOOKS_DOUBLE_FIRE` `BlockerWarning` when an enabled GoC
  plugin key AND ≥1 vendored hook coexist; names the key, the hooks, and both
  remediations.

Wired into `_cmd_validate`'s advisory block (printed via `.message`, NOT
appended to `errors`) so it never gates exit 1 — the check reads host config
absent in CI.

**Design choice — gate on enablement, not payload presence.** The existing
`_claude_plugin_present()` returns true whenever the payload is cached, even
when the plugin is disabled. Using it here would false-positive the moment a
user disables the plugin but leaves the cache. The new validator resolves
`enabledPlugins` instead, so it goes silent exactly when the misconfiguration
is actually resolved.

**Live verification.** This is the card's own dogfood demonstration: after the
sibling fix disabled `game-of-cards@zauberzeug-claude` for this repo (in
`~/.claude/settings.json`), `goc validate` here is now SILENT — the
enablement-gating working end-to-end. A synthetic-enabled probe
(`home` → temp settings with the plugin `true`, `repo_root` → this repo)
prints the full warning naming all three vendored hooks
(`deck_prompt_router.py`, `deck_session_start.py`,
`pattern_generalization_check.py`) and both escape hatches.

**Verification:** new test file 8/8 green; `sync_plugin_assets.py --check`
and `port_skills_to_openclaw.py --check` clean; `goc validate` clean. Full
`unittest discover` green except the one pre-existing macOS-local
`test_git_auto_commit_rebase_guard` setup failure (needs `git rebase -i`,
blocked in this sandbox; unrelated; passes in CI).

**Origin:** filed after diagnosing the live double-fire reported while closing
`make-pattern-generalization-stop-hook-opt-in` — the GoC plugin was enabled
user-globally in `~/.claude/settings.json` while this source repo also vendors
its hooks. The user-config half (disabling the global enablement) was handled
directly; this card is the durable tool-side guard so `goc validate` surfaces
the condition for anyone, instead of leaving it to be reverse-engineered by
hand.
