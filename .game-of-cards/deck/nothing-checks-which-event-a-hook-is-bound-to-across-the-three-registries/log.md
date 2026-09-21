## 2026-09-21T05:31:45Z — Falsification run

The card was filed `unverified` off a static read. `reproduce.py` builds a
throwaway `REPO_ROOT`-shaped tree per case and runs both hook validators over
it. All three cases returned `[]` from `validate_hook_registration` AND
`validate_plugin_hook_registration` before the fix — exit 1, gap CONFIRMED:

- codex payload swaps `SessionStart` and `Stop` (the primer fires on `Stop`,
  the pattern check on `SessionStart`): nothing reported;
- claude payload binds the primer to `Resume`, an event no registry names:
  nothing reported;
- `GOC_CLAUDE_HOOKS` swapped with both payloads left correct — the recipe's
  control: nothing reported, so the vendored path was no stronger.

The static reading was exact: the event reached error strings for malformed
shapes and nowhere else. `unverified` dropped.

## 2026-09-21T05:31:45Z — Closure

- **What changed**: `goc/engine.py` — `_plugin_registered_hook_scripts` →
  `_plugin_registered_hook_bindings`, returning `(event, script)` pairs;
  `validate_plugin_hook_registration` compares each payload's event set per
  script against `GOC_CLAUDE_HOOKS`, for scripts both registries name.
  `goc/install.py` gains `claude_hook_bindings()` — the registry inverted to
  script → events — so both validators read `GOC_CLAUDE_HOOKS` through one
  walk instead of a second hand-rolled parse.
- **Verification**: `reproduce.py` 1 → 0; the three cases report 2, 1 and 4
  errors after the fix. `tests/test_plugin_hook_json_registration.py` rewritten
  off synthetic `Event{i}` names onto the reference events, 7 → 11 tests, with
  three new driven offenders (swapped pair, unknown event, extra event on an
  otherwise correct binding) and one case pinning that a template outside
  `GOC_CLAUDE_HOOKS` is `validate_hook_registration`'s finding, not this one's.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: 1186 passed / 0 failed / 0 xfailed; `uv run goc validate` exit 0.

## Closure verification (2026-09-21T05:31:45Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-09-21 — Closure' present
