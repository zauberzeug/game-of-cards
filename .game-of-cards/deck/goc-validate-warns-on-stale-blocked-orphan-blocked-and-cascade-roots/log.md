## 2026-05-21 — Closure

- **What changed**: `goc/engine.py:1104-1196` adds `BlockerWarning` + `validate_blocker_coherence`; `_cmd_validate` (`goc/engine.py:1974-1975`) prints the warnings to stderr without affecting the error/exit accounting.
- **Verification**: 8 new unit tests pass; full suite 139/139; self-validate on this repo surfaced 2 real state-coherence defects (STALE_BLOCKED on `llms-txt-still-recommends-uv-tool-install-as-preferred`, ORPHAN_BLOCKED on `openclaw-subagent-plugin-tools-alsoallow-ignored`).
- **Audit**: PASS — no rubric configured; additive validator feature, no project principle touched.
- **Project impact**: `goc validate` now emits state-coherence warnings (non-fatal). Consumers see triage signal without CI gating impact.
- **Tests**: 139 passed / 0 failed / 0 xfailed.
- **Bundled with**: none.

## 2026-05-21 — implementation lands

`validate_blocker_coherence` added to `goc/engine.py` after
`_would_create_advance_cycle`. `_cmd_validate` calls it after the
existing bidirectional-edge check; warnings print to stderr without
contributing to the error count or exit code.

Test coverage in `tests/test_validate_blocker_coherence.py` (8 cases):
each warning class fires when expected, partial-blocked stays silent,
ORPHAN_BLOCKED is suppressed for both `decision` and `session` gates,
CASCADE_CHAIN_ROOT walks transitive `advances` chains, threshold N=3
is enforced, and warnings never raise exit code.

Self-validation on this repo's own deck surfaced two pre-existing
state-coherence defects (filed as discovery, not fixed here):

- `STALE_BLOCKED llms-txt-still-recommends-uv-tool-install-as-preferred`:
  its only blocker `validate-plugin-mirror-fails-when-openclaw-omits-hooks-dir`
  is `done`. Card should re-open or refresh its blocker list.
- `ORPHAN_BLOCKED openclaw-subagent-plugin-tools-alsoallow-ignored`:
  blocked on an upstream OpenClaw release named only in the body;
  should raise gate to `session` (waiting on external release) or wire
  an upstream-stub blocker card.

These follow-ups are out of scope for this card — discovered via the
new warning, recorded here for whoever picks them up.

## Closure verification (2026-05-21T08:36:42Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-05-21 — Closure' present
