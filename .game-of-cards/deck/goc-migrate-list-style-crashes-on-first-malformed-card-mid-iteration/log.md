## 2026-05-29T17:59:15Z — Closure

- **What changed**: `goc/engine.py:_cmd_migrate_list_style` — wrapped `parse_frontmatter(original)` in a `try/except FrontmatterError` net mirroring `load_all_cards` at engine.py:625-631. A malformed card now surfaces `WARNING: <slug>: <exc>` on stderr and the loop continues to the next card instead of aborting the whole bulk rewrite with a Python traceback. The reproduce.py exit logic was inverted to match the fixed contract (exit 0 means fix in place; exit 1 means defect still present or fix regressed).
- **Sibling sweep**: 10 direct `parse_frontmatter(` call sites in `goc/engine.py`. Four already-netted (`load_card` → `load_all_cards`, `_cmd_show`, `load_card_or_exit`, `validate_deck_directories`). One netted by `try/except Exception: pass` in the claim-race diagnostic (engine.py:3607). Four single-card mutation helpers (`_apply_dod_rewrite`, `_add_to_list_field`, `_remove_from_list_field`, `_cmd_wait`, `_cmd_decide`) are preceded by `load_card_or_exit` on the same operation — raise here is documented contract (engine.py:4184-4186 explicitly documents this for the list-field helpers). `_cmd_migrate_list_style` was the only outlier; it is now netted. No follow-up cards filed.
- **Verification**: reproduce.py exits 0 with both `--dry-run` and live runs reporting exit 0, the broken card surfaced as `WARNING: card-b: …`, and the valid `card-a` listed in the would-rewrite / rewrote output. Plugin mirrors re-synced via `python scripts/sync_plugin_assets.py`.
- **Tests**: 235 passed / 0 failed.
- **Bundled with**: none.

## Closure verification (2026-05-29T18:00:19Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-29 — Closure' present
