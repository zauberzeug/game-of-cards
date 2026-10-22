
## 2026-10-22T05:20:16Z — Closure

- **What changed**: `goc/engine.py` `_auto_populate_worker` — `who` resolves from `--worker-who`, the existing designation, `GOC_WORKER_WHO`, then `git config user.name`; `where` from `--worker-where`, `GOC_WORKER_WHERE`, then the branch. `_cmd_status` refuses a claim no source can name (exit 2, before the write) and runs the flags' boundary check (`_reject_invalid_worker_flag`) on the two variables.
- **Verification**: `tests/test_claim_identity_from_env.py` 6/6 (identity-less claim refused and card byte-identical; blank variable = unset; variables stamp `{who: sandbox-worker, where: "container:probe"}`; flag beats variable; existing designation beats variable; line break refused without traceback).
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: containerised workers claim with an identity from their environment; a claim nobody is named for can no longer be written.
- **Tests**: 1345 passed / 0 failed (`uv run python -m unittest discover -s tests`); `goc validate` OK; `sync_plugin_assets.py --check` and `port_skills_to_openclaw.py --check` OK.
- **Source**: the identity part of PR #11, split out. The PR's release-lifecycle changes went to `parked-claims-stay-active-under-goc-wait-and-release-has-no-rule-for-the-worker` (decision). Not fixed here: `worker-mapping-with-only-a-branch-emits-invalid-empty-who` (its `reproduce.py` still reports the emitter defect).

## Closure verification (2026-10-22T05:20:39Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-10-22 — Closure' present
