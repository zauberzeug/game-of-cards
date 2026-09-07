## 2026-09-02T05:22:38Z — Closure

- **What changed**: `AGENTS.md:285-290` — the closing sentence of the
  "already at goc X — nothing to do is derived" paragraph now says *three*
  remaining terms covering "work the plan does not model", names all three
  (vendored-cleanup prompt, legacy-briefing strip, `skills_source` pin), and
  says outright that the pin does gate a write while asking
  `_write_skills_source` in `probe=True` mode. Added a "holdover rather than a
  shape to copy" clause so the pin no longer reads as a counter-example to the
  "do not reintroduce a `pending_*` allowlist term" rule two sentences above.
  New `UpgradeNoOpGuardParagraphAccuracyTest` in
  `tests/test_guidance_accuracy.py` (3 tests) pins the sentence to the source.
- **Verification**: `reproduce.py` exits 0 (was 1, 3 of 3 assertions failing).
  Both the term list and the writer set are derived from `goc/install.py` with
  `ast` — terms are the `pending_*` names negated beside `plan_has_effect`;
  writers are the `pending_*` terms assigned from a call carrying
  `probe=True`, which yields exactly `pending_skills_source ->
  _write_skills_source`. So neither the guard nor `reproduce.py` carries the
  hand-maintained register the paragraph forbids. Negative control: ran the new
  test class against four synthetic AGENTS.md trees — stale two/non-write
  sentence fails 3/3, count-fixed-but-still-"non-write" fails 1/3,
  writer-unnamed fails 1/3, sentence-deleted fails 3/3.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: 1076 passed / 0 failed / 0 xfailed (1073 before, +3 new)
- **Also fixed**: `reproduce.py`'s second assertion fired on the mere presence
  of a writing term, independent of what AGENTS.md actually claimed — so the
  script could not have exited zero for any wording short of removing
  `pending_skills_source` from the guard, and DoD item 1 was unsatisfiable as
  written. It is now conditional on the sentence containing "non-write", with a
  third assertion requiring every writing term to be named.

## Closure verification (2026-09-02T05:28:30Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-09-02 — Closure' present
