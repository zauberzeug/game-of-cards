## 2026-06-23 — fixed

Threaded a `changed` flag through `_merge_claude_settings`
(`goc/install.py`), mirroring the sibling `_strip_goc_settings_entries`:
set True at each genuine mutation site (the non-dict-settings,
non-dict-hooks, non-list-event, and non-list-group-hooks
backup-and-reset branches, plus the `not already` hook append) and
guarded the final `write_text` with `if changed:`.

Result: an idempotent merge (every GoC hook already registered) now
leaves the user-owned `.claude/settings.json` byte-identical —
indentation, key order, and trailing newline preserved — instead of
reflowing it through `json.dumps(..., indent=2)`. A merge that genuinely
adds a missing hook still writes as before.

Added two direct-function regression tests in `tests/test_install.py`:
`test_merge_claude_settings_idempotent_merge_leaves_file_untouched`
(4-space user file with all hooks present → unchanged) and
`test_merge_claude_settings_writes_when_a_hook_is_missing` (missing hooks
→ written, user keys preserved). Regenerated the three plugin engine
mirrors via `scripts/sync_plugin_assets.py`.

`reproduce.py` exits 0; full suite (551 tests) green; `goc validate`
clean.
