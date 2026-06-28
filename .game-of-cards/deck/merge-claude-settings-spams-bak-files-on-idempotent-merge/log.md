## 2026-06-24 — filed and fixed (fix-through during pull-card)

Surfaced while draining the queue (no ready cards; audit hunter found
it in `goc/install.py`). Sibling of the closed card
`merge-claude-settings-rewrites-settings-json-on-idempotent-merge`,
which gated the final `write_text` on a `changed` flag but left the
no-op non-object-items branch's `_ensure_backup()` side effect ungated.

Fix: introduced `non_object_item_events` to collect (deduped) the
events whose `hooks[event][].hooks` list holds non-dict items, and moved
the backup + warning into the existing `if changed:` block so they only
fire when GoC actually rewrites the file. The backup uses the pristine
`original` bytes captured before any mutation, so a real rewrite still
produces the safety copy; an idempotent merge is now silent.

Verified: `reproduce.py` flips FAIL → PASS (0 `.bak` on a no-op merge).
Two new tests in `tests/test_install.py` —
`test_merge_claude_settings_idempotent_merge_with_non_object_item_makes_no_backup`
(no backup, file unchanged) and
`test_merge_claude_settings_backs_up_non_object_item_when_rewriting`
(backup still made + non-object item preserved on a real write).
Full suite green (556 tests); `goc validate` clean after syncing the
plugin mirrors of `install.py`.
