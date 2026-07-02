## 2026-07-02T02:30:00Z — Closure

- **What changed**: `goc/engine.py:4648` (`load_deck_config`) — loop over the two config paths, wrap `yaml.safe_load` in try/except, and return `data if isinstance(data, dict) else {}` so a bare-list / scalar / unparseable config.yaml coerces to `{}` instead of being returned as a list/str (or raising). Mirrors the guards in `_resolve_deck_root` and `_load_consuming_repo_tags`.
- **Verification**: reproduce.py now exits 0 (was exit 1 on `bare list` + `scalar string`); `get_skills_source()` returns `auto` instead of raising `AttributeError: 'list' object has no attribute 'get'`.
- **Audit**: PASS — no principle touched, mechanical fix (defensive input guard on a user-owned file).
- **Project impact**: n/a
- **Tests**: 690 passed / 0 failed (added `tests/test_load_deck_config_non_mapping.py`, 5 cases); plugin mirrors re-synced so `test_plugin_mirror_parity` stays green.

## Closure verification (2026-07-02T02:25:00Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-07-02 — Closure' present
