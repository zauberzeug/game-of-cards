## 2026-05-30T18:09:43Z — Closure

- **What changed**: `goc/install.py:586-621` and `goc/install.py:653-686` — added `isinstance(_, dict)` guards on `hooks` and `isinstance(_, list)` guards on `hooks[event]` in both `_merge_claude_settings` and `_strip_goc_settings_entries`. The merge path backs up the original bytes once on the first wrong-shape detection (via a nonlocal `_ensure_backup` helper) and coerces the offending value to a safe default. The strip path warns and leaves the offending event (or the whole file) untouched, fixing the silent char-explode regression.
- **Verification**: `reproduce.py` exits 0; all three sub-shapes (`hooks: []`, `hooks.<event>: "oops"` on merge, `hooks.<event>: "oops"` on strip) behave per the DoD. Two new unittest cases (`test_merge_claude_settings_handles_non_dict_nested_hooks_shapes`, `test_strip_goc_settings_entries_handles_non_dict_nested_hooks_shapes`) cover four wrong shapes each, asserting no `AttributeError` escapes and that the user's bytes are preserved verbatim (or backed up).
- **Audit**: PASS — no rubric configured; mechanical fix mirroring the closed sibling `claude-settings-json-that-parses-to-a-non-dict-crashes-install-with-attributeerror` one layer deeper. Approach B (per-callsite guard) per the meta-fix parent's precedent #2.
- **Project impact**: n/a
- **Tests**: 330 passed / 0 failed (full `uv run python -m unittest discover -s tests`).
- **Bundled with**: none

## Closure verification (2026-05-30T18:10:29Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-30 — Closure' present
