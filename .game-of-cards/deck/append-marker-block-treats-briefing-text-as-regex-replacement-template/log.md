## 2026-05-26T00:00:00Z — Closure

- **What changed**: `goc/install.py:222,884,1040` — switched the three
  dynamic-content `re.sub` replacement arguments to callable replacements
  (`lambda _: block` / `lambda _: replacement`) so briefing/import/value text is
  treated literally, never parsed for backreferences.
- **Verification**: `reproduce.py` raised `IndexError: unknown group name 'name'`
  at install.py:884 before the fix (a `\g<name>` in the briefing body); exits 0
  with the literal preserved after. Smoke `goc install` + `goc upgrade` into a
  temp repo: marker block lands once, upgrade's replace branch runs clean.
- **Audit**: PASS — no principle touched, mechanical fix (correctness-in-depth;
  no project rubric configured in `.game-of-cards/hooks/finish-card.md`).
- **Project impact**: n/a
- **Tests**: no pytest suite; reproduce.py passes, `goc validate` clean, plugin
  mirrors re-synced.
- **Bundled with**: n/a

## Closure verification (2026-05-26T21:24:09Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present
