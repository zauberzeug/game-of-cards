## 2026-05-26 — Closure

- **What changed**: `goc/schema.yaml` — added `waiting_on` / `waiting_until` to `optional_fields`, introduced `waiting_on_values: [external, resource, deferred]`. `goc/engine.py` — extended `Schema` dataclass + `load_schema`; added `Card.waiting_on` / `Card.waiting_until` properties; added enum + ISO-date validation to `validate_card`; added `waiting_impedes()` predicate and wired it into `card_is_ready` so a future `waiting_until` or open-ended `waiting_on` hides the card from `--ready` / `next-card` / `pull-card`; added `validate_waiting_overlay()` emitting `WAITING_OVERDUE` BlockerWarnings for non-terminal cards whose `waiting_until` has elapsed; wired the new warning class into `_cmd_validate`; added `_cmd_wait` + `wait` subparser (`--reason {external,resource,deferred}`, `--until ISO`, `--clear`, `--commit`/`--no-commit`). Both fields round-trip via the existing `emit_frontmatter`; absence is the default, `--clear` removes them.
- **Verification**: `uv run python .game-of-cards/deck/add-waiting-overlay-with-reason-and-until-date/reproduce.py` exits 0 — a future-dated card is hidden from `--ready`; backdating it to 2001-01-01 resurfaces it AND emits `WAITING_OVERDUE` from `goc validate`. Manual end-to-end of `goc wait sample --reason external --until 2026-06-15` then `goc wait sample --clear` confirms the emitter writes the two fields and `--clear` removes them.
- **Audit**: PASS — implements Decision point 3 of the parent epic ([`blocked-status-conflates-dependency-external-wait-and-deferral`](../blocked-status-conflates-dependency-external-wait-and-deferral/)) per the literature-anchored "stored overlay, not status" verdict. `waiting_until` alone implies `deferred` per the DoD's proposed rule. The overlay composes with `status` — a card may be `active` AND carry `waiting_on` — exactly as designed.
- **Skills updated**: `card-schema` documents the three-axis model (progress status / derived dependency readiness / stored impediment overlay) with the new ready predicate; `advance-card` adds a "Step 6 — set or clear an impediment overlay" section. The template `schema.yaml` shipped under `card-schema` mirrors the new fields.
- **Plugin mirrors**: `python scripts/sync_plugin_assets.py` re-synced the three plugin payloads (claude / codex / openclaw) byte-for-byte with the updated engine + templates.
- **Tests**: no pytest suite — `uv run goc validate --quiet` clean (only pre-existing `STALE_BLOCKED` / `ORPHAN_BLOCKED` warnings unrelated to this card).
- **Bundled with**: none

## Closure verification (2026-05-26T05:52:02Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 7/7 ticked
- [ ] log-md-closure-entry FAIL — no '## 2026-05-26 — Closure' section

## Closure verification (2026-05-26T05:52:36Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 7/7 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present
