## 2026-06-15: sibling cross-link

Adjacent surface to [goc-decide-leaves-prior-decision-block-when-the-body-already-has-one](../goc-decide-leaves-prior-decision-block-when-the-body-already-has-one/): that card dedups duplicate `## Decision` *headings* the engine itself emits when a gate is re-raised; this card reconciles the *other* verdict surfaces (`summary`, body banner, DoD wording, neighbor references) that `goc decide` never touches on a re-scope. Both compose cleanly — the prior-decision-block fix operates inside `replace_or_append_decision`; this fix is a print-time reminder plus an advisory validator, with no overlap in the mutated code path. Contrast also `goc status … superseded --by …`, which already records a typed forward link; `goc decide` has no in-place equivalent, which is the gap this card closes with a reminder rather than an auto-rewrite (decide must not silently rewrite authored verdict prose).

## 2026-06-15T03:49:43Z — Closure

- **What changed**: `goc/engine.py` — added shared `RESCOPE_MARKERS_RE` + `NEGATIVE_VERDICT_RE` + `extract_resolved_decision_text` + `_body_banner_lines`; `_cmd_decide` now prints a `_rescope_reconciliation_notice` (stderr) when `--decision` reads like a re-scope; new advisory `validate_decision_verdict_coherence` wired into `_cmd_validate`. Skill: `decide-card/SKILL.md` gained a "Reconcile a re-scope" section (mirrors synced).
- **Verification**: 7 new tests green (test_decide_rescope_reconciliation.py + test_validate_decision_contradicts_verdict.py); regex sanity: 9/9 rescope-match, 0 false-positives on plain decisions; 0 `DECISION_CONTRADICTS_VERDICT` on this repo's own deck; `goc validate` exits 0 (advisory only).
- **Audit**: PASS — no project rubric configured (finish-card hook empty); footgun-prevention feature, no project principle bound. Design choice: reminder + advisory lint rather than auto-rewrite, because `goc decide` must never silently rewrite authored verdict prose.
- **Project impact**: n/a
- **Tests**: 436 passed / 0 failed / 1 skipped
- **Bundled with**: n/a

## Closure verification (2026-06-15T03:49:47Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-06-15 — Closure' present
