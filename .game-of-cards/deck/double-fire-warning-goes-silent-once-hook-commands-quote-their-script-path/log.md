## 2026-10-18T04:37:22Z — Closure

- **What changed**: `goc/engine.py:5851` — `_goc_hook_basenames` now returns
  the script names `claude_hook_bindings()` yields. It no longer splits each
  `GOC_CLAUDE_HOOKS` command on "/" itself. `goc/install.py:618` — the
  `claude_hook_bindings` docstring names all three readers instead of "both
  hook validators". `tests/test_validate_plugin_hook_double_fire.py` gets
  three new cases:
  - the shipped registry installed through `_merge_claude_settings` must
    raise the warning and name every script;
  - the same check with the registry patched to the quoted form;
  - `_goc_hook_basenames()` pinned to the walk's names under both forms.

  The plugin engine mirrors are regenerated.
- **Verification**: `reproduce.py` exit 1 → 0. Under the quoted registry,
  the double-fire warning count goes from 0 to 1 and the names lose their
  trailing `"`. On the old parse, 2 of the new cases fail (`0 != 1` on the
  quoted install, and the pin shows quote-suffixed names). After the fix the
  module passes 11 of 11. `sync_plugin_assets.py --check`,
  `port_skills_to_openclaw.py --check`, `goc validate` and the card-language
  and strict-YAML guards are green.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1339 passed / 0 failed / 0 xfailed
- **Bundled with**: none
- **Related**: this card advances
  `hook-command-registrations-word-split-on-install-paths-with-spaces`. That
  card's quoting change would have silenced this check, and the edge records
  that it no longer does. A forward pointer is appended to that card's
  `log.md`. Its Decision-required options are unchanged.

## Closure verification (2026-10-18T04:38:53Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-10-18 — Closure' present
