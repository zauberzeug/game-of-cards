## 2026-05-31T04:01:07Z — Closure

- **What changed**: `goc/engine.py:4115` — `_cmd_attest` short-circuits with exit 2 and an "ERROR: no closure checks configured" stderr message when both `layer_2_project_dod` and `layer_3_goc_dod` are empty/unset; `log.md` is not touched.
- **Verification**: `reproduce.py` now exits 0 (post-fix verdict); new regression `tests/test_install.py::test_attest_refuses_when_both_layers_are_empty_and_leaves_log_untouched` asserts exit code 2, stderr message, and no `## Closure verification` header in log.md.
- **Audit**: PASS — no rubric configured; mechanical fix to align attest with the refuse-when-prerequisites-unmet posture used elsewhere in the engine.
- **Tests**: 348 passed / 0 failed / 0 xfailed.
- **Bundled with**: none.

## Closure verification (2026-05-31T04:01:17Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-31 — Closure' present

## 2026-10-31T05:46:44Z — Post-close amendment

The README's first "Why it matters" paragraph says the
`log-md-closure-entry` check is satisfied by a `## Closure verification`
heading, i.e. by the stub attest itself writes. That was never true. The
check matches the closer's `## <stamp> — Closure` entry, anchored at a line
start, in every version since the first commit. Since ee682d87,
`tests/test_closure_entry_check_ignores_heading_date.py` also pins that
attest's own blocks cannot satisfy it
([closure-log-attestation-misfires-across-utc-midnight](../closure-log-attestation-misfires-across-utc-midnight/)).
The refusal stands on the paragraph after it: "Attestation OK" with zero
checks run is a contract violation. `_cmd_attest`'s docstring, which
repeated the claim, was corrected in the same commit.
