## 2026-05-26T12:52:38Z: decision recorded

Engine recognizes OpenClaw plugin context and defaults to no harness — write .game-of-cards/ + AGENTS.md only, never CLAUDE.md (card option 1). — Keyed on the same _PACKAGE_DIR.parent.name signal _is_plugin_context() already trusts, so it is automatic and correct regardless of how install is invoked; needs no new flag (a user-facing --no-harness flag was previously rejected); honors the kickoff promise that plain goc install is host-agnostic on OpenClaw.. Gate session → none.

## 2026-05-26 — Closure

Implemented card option 1: the bundled engine now recognizes the OpenClaw
plugin context (`_is_openclaw_plugin_context()` in `goc/install.py`) and, when
no `--agents` is given, defaults `install`/`upgrade` to *no harness* — shared
`.game-of-cards/` + `AGENTS.md` only, never `CLAUDE.md`. Auto-detection is
suppressed in that context so a pre-existing `AGENTS.md` is not misread as a
Codex surface; explicit `--agents` still overrides.

Project closure audit: no project rubric defined (`.game-of-cards/hooks/finish-card.md`
is an empty stub). Mechanical/host-detection fix — closest principle binding is
the existing `_is_plugin_context()` package-location convention, which this
extends host-aware rather than introducing a new signal.

Verification:
- `reproduce.py` inverted into a guard against the bundled OpenClaw engine —
  exits 0 on the fixed contract (`agents: none`, `AGENTS.md`, no `CLAUDE.md`);
  exits 1 if the Claude default returns.
- `OpenClawPluginContextTest` added to `tests/test_install.py`; full suite
  144 passed.
- `scripts/sync_plugin_assets.py --check` clean (the three `install.py` plugin
  mirrors re-synced byte-for-byte); `goc validate` clean.

Follow-up filed (out of scope): `openclaw-plugin-ported-skills-drift-silently-from-templates`
— the porter-maintained `openclaw-plugin/skills/` copies have drifted from the
templates and aren't covered by the byte-for-byte sync tripwire.

## Closure verification (2026-05-26T13:03:41Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [ ] log-md-closure-entry FAIL — no '## 2026-05-26 — Closure' section

## Closure verification (2026-05-26T13:04:07Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present
