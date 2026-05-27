## 2026-05-27T13:35:48Z — Closure

- **What changed**: `goc/engine.py` `validate_card` — added a `definition_of_done: must be a string` type check alongside the existing `tags` check, so a card hand-edited to `definition_of_done: []` / `null` (any non-string) now fails `goc validate`. Mirrors synced to the three plugin payloads.
- **Verification**: `reproduce.py` exits 1 before the fix (both `[]` and `null` accepted), exit 0 after (both rejected, string control still accepted).
- **Audit**: PASS — no principle touched, mechanical fix (field type-check, mirrors the existing `tags` validation).
- **Project impact**: n/a
- **Tests**: 171 passed / 0 failed / 0 xfailed (`uv run python -m unittest discover -s tests`).

Chose to reject `null` as well as `[]`/mappings — `definition_of_done` is a required field, and the card's own "Why it matters" names `null` as a bypass case. The card's proposed `dod is not None` guard would have let `null` through; tightened to reject any present non-string value.

## Closure verification (2026-05-27T13:36:06Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present
