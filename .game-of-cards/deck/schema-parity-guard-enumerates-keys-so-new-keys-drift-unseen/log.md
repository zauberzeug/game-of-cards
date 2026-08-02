# Log

## 2026-08-02T05:54:07Z — Closure

- **What changed**: `tests/test_skill_schema_yaml_parity.py:44` — added
  `test_no_unguarded_top_level_key`, a whole-mapping equality between
  `goc/schema.yaml` and the card-schema skill's bundled copy, so parity no
  longer depends on a key being named in the test file; module docstring
  rewritten to say the named tests are diagnostics and the mapping equality
  is the contract.
- **Verification**: `reproduce.py` 2 findings → 0 (exit 1 → 0); both controls
  (`status_values`, `canonical_tags`) still turn the guard red, and both
  drift cases (`required_when` added to engine-only, then skill-only) now do
  too. Suite 888 → 889 tests, green.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: 889 passed / 0 failed / 0 xfailed. `goc validate` exit 0;
  `scripts/sync_plugin_assets.py --check` clean;
  `scripts/port_skills_to_openclaw.py --check` clean.

Neither schema file was edited — they were byte-identical before and after.
The closure is entirely about the guard's shape: an enumerated key list that
happened to cover every key the schema has today, replaced by a comparison
that converges on whatever keys it has tomorrow.

One methodological note worth carrying forward: the first version of
`reproduce.py` reported all four cases as "caught" and would have disproved
the card. `_assert_equal` builds its failure message with
`relative_to(ROOT)` eagerly — on passing calls too — so redirecting
`ENGINE_SCHEMA`/`SKILL_SCHEMA` to a temp dir without also moving `ROOT` made
every test error out on message construction rather than run. The two
controls in the shipped probe exist to make that failure mode visible: a
harness that cannot catch a known-caught drift is not evidence of anything.

## Closure verification (2026-08-02T05:54:35Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-08-02 — Closure' present
