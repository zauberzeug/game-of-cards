## 2026-06-04T05:35:35Z — Closure

- **What changed**: `goc/engine.py:485-525` — added `DOD_FENCE_DELIM` + `_dod_fenced_mask`, routed `count_dod_boxes`, `_dod_box_indices`, and `untagged_dod_items` through it so `- [ ]`/`- [x]` lines inside ```- or ~~~-fenced code blocks in `definition_of_done` are not counted as DoD checkboxes.
- **Verification**: reproduce.py now exits 0 (`count_dod_boxes` → `(0, 1)` for the fenced-example DoD, was `(1, 1)`); new `tests/test_dod_fenced_checkbox.py` (6 cases) passes.
- **Audit**: PASS — no principle touched, mechanical fix (parser correctness; honors universal markdown fenced-code semantics, matching the direction the sibling `decide-misparses-fenced-double-hash-line` card establishes).
- **Project impact**: n/a
- **Tests**: 384 passed / 0 failed / 0 xfailed (`uv run python -m unittest discover -s tests`); `uv run goc validate` clean (plugin mirrors re-synced).
- **Bundled with**: n/a

## Closure verification (2026-06-04T05:35:53Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-06-04 — Closure' present
