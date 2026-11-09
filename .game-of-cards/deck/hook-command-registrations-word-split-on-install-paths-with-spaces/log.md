## 2026-10-18T04:37:22Z — Supporting evidence: a registry reader the quoting fix would have silenced

The Decision-required section says `_HOOK_FILE_RE` matches through a leading
quote, so "GoC-managed entry detection survives". That holds for the readers
that use `_HOOK_FILE_RE`. It did not hold for `engine._goc_hook_basenames`,
which feeds `goc validate`'s `PLUGIN_AND_VENDORED_HOOKS_DOUBLE_FIRE` warning.
That function split each `GOC_CLAUDE_HOOKS` command on "/" itself. Under the
quoted form this card prescribes, every name kept the closing `"`, the warning
stopped firing for repos that do double-fire, and its regression suite stayed
green because its fixture was a hand-copied unquoted command.

Fixed and closed in
`double-fire-warning-goes-silent-once-hook-commands-quote-their-script-path`,
which now `advances` this card. `_goc_hook_basenames` reads
`claude_hook_bindings`. `tests/test_validate_plugin_hook_double_fire.py`
installs a quoted registry through `_merge_claude_settings` and asserts the
warning, so the quoting change is now covered for this check. Nothing in the
options below changes. The exact-match readers (`_merge_claude_settings`,
`_strip_goc_settings_entries`) are still the migration leg this card's DoD
already names.

## 2026-11-09T01:58:49Z — Staleness re-check

As-filed anchor gone from HEAD: `codex-plugin/hooks/hooks.json:8`
(`"command": "python3 ${PLUGIN_ROOT}/hooks/deck_session_start.py",`), rewritten by `8e6c9682`
(version-fallback `sh -c` wrapper).
Reproducer: `reproduce.py` → exit 1, "DEFECT: SessionStart hook exits 2 under a spaced project path"
(also UserPromptSubmit and Stop). It exercises `GOC_CLAUDE_HOOKS` only, not the plugin payloads.
Verdict: still live. No rewrite needed: lines 8, 19, 30 are still the three Codex command lines.
The Codex wrapper now double-quotes `${PLUGIN_ROOT}` and `$p`; a scratch run of its SessionStart
command under a spaced `PLUGIN_ROOT` exited 0, so that leg may no longer word-split.
`GOC_CLAUDE_HOOKS`, `claude-plugin/hooks/hooks.json` and `.claude/settings.json` are still unquoted.
Gate unchanged.
