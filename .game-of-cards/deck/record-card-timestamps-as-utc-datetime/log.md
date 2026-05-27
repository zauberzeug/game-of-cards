## 2026-05-10: decision recorded

Accept both date and datetime shapes in created/closed_at; write datetime going forward; no backfill of existing date-only cards. — lexicographic sort handles mixed formats and synthetic midnight-UTC backfill would be misleading precision.. Gate decision → none.

## 2026-05-11 — Closure

- **What changed**: `goc/engine.py:465-499` — `_is_iso_date` accepts both `YYYY-MM-DD` and `YYYY-MM-DDTHH:MM:SSZ`; new helpers `_utc_now_iso()` and `_date_part()` added; `goc new` (line 2547) and `goc done` (line 1932) now write UTC datetime; `_cmd_triage`'s `aged_days` (line 2839) normalizes via `_date_part` so it still works on legacy date-only cards. Validator error messages updated to mention both shapes. `goc/templates/skills/card-schema/SKILL.md` gained a "Timestamps (`created`, `closed_at`)" section explaining the two shapes and lexicographic-order compatibility; same section ported to the OpenClaw plugin's hand-maintained copy.
- **Verification**: smoke test parsed mixed-shape deck, sorted correctly (`"2026-05-10" < "2026-05-11T12:34:56Z"`), `goc new` wrote `created: "2026-05-11T03:38:22Z"`, `goc done` wrote `closed_at: 2026-05-11T03:38:27Z`, `goc validate` green on both new and legacy cards. Full dogfood deck (159+ cards, all legacy date-only) still validates green.
- **Audit**: PASS — backwards-compat preserved (legacy cards untouched); UTC-only enforced (no local-tz drift); lexicographic ordering invariant explicitly documented in skill body so future readers don't reintroduce timezone offsets.
- **Project impact**: n/a
- **Tests**: 112 passed / 0 failed / 0 xfailed (full `uv run pytest`).
- **Bundled with**: none

## Closure verification (2026-05-11)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 8/8 ticked
- [x] log-md-closure-entry — '## 2026-05-11 — Closure' present

## 2026-05-27 — Later evidence: read-side gap the audit missed

The 2026-05-11 audit claimed "UTC-only enforced (no local-tz drift)",
but that covered only the WRITE side plus lexicographic sort / `--since`
reads. Three read-time guards still defaulted their `today` base to
`date.today()` (the LOCAL civil date): `waiting_impedes`,
`validate_waiting_overlay`, and `_cmd_triage`'s `aged_days`. On a
non-UTC runner near midnight that disagrees with the UTC write base by
a full civil day, so a deferred card could un-defer (or an overdue wait
surface, or an age compute) up to one day early. Fixed under
[read-time-date-guards-compare-utc-stamps-to-local-date](../read-time-date-guards-compare-utc-stamps-to-local-date/)
by adding `_utc_today()` next to `_utc_now_iso()` and defaulting the
three guards to it.
