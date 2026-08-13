## 2026-08-13T05:52:00Z — Closure

- **What changed**: `goc/engine.py` — `validate_plugin_hook_registration` (plus
  `_plugin_registered_hook_scripts` and `PLUGIN_HOOK_REGISTRIES`) compares each
  plugin payload's hand-maintained `hooks.json` against the hook scripts that
  payload ships, in both directions, and is wired into `_cmd_validate`.
  `AGENTS.md` now describes three registries with three checks instead of
  implying one guard covered them all.
- **Verification**: `reproduce.py` exits 0 (was 1); re-running it with
  `validate_plugin_hook_registration` deleted from the module reproduces the
  original verdict, so the guard demonstrably discriminates rather than
  reporting a clean tree. `tests/test_plugin_hook_json_registration.py`: 7
  tests, covering both drift directions, the Codex shell-wrapper command shape,
  8 malformed-registry shapes, the absent-payload case, and the live payloads.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 971 passed / 1 failed / 0 xfailed. The one failure is
  `test_canonical_tag_rows.test_live_cards_satisfy_every_state_row`, red on
  `main` since commit `1ed2ddb2` (2026-08-04) and already filed as
  [regression-suite-red-on-main-over-the-unverified-tag-row](../regression-suite-red-on-main-over-the-unverified-tag-row/),
  which is parked on a human decision. It is unrelated to this card and neither
  caused nor cleared by it — this closure does not absorb it. `goc validate`
  exits 0.
- **Bundled with**: n/a

### Scope note

The defect was surfaced by a `Skill(audit-deck)` pass run because the ready
queue was empty, and fixed through in the same session under
`Skill(pull-card)` § "Fixing what you surface": gate-free (the fix is a guard
next to two existing ones, with generation explicitly ruled out by AGENTS.md's
recorded hand-maintained decision), single-site, not a meta-fix family, and
sitting in code the session already had loaded and had already probed.

The closed predecessor
[derive-claude-hook-manifest-from-templates](../derive-claude-hook-manifest-from-templates/)
was amended with a forward pointer rather than reopened: its three-site
enumeration was complete when it closed, and the two plugin `hooks.json` files
are registration sites that appeared afterwards.

## Closure verification (2026-08-13T05:37:30Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-08-13 — Closure' present
