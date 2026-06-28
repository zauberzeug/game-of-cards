## 2026-05-30T12:50:17Z — Closure

- **What changed**: `scripts/release_rewrite_versions.py:45-66` — added `_VERSION_PATTERN = re.compile(r"\A\d+\.\d+\.\d+\Z")` and a guard at the top of `rewrite_all` that exits non-zero with `ERROR: invalid version {version!r}: expected X.Y.Z` before any `_replace` or `.goc-version` write fires. Docstring sentence updated from "fails loudly on any expected-vs-actual mismatch" to "validates input format before writing any file".
- **Verification**: `reproduce.py` now exits 0 (post-fix verdict) with 0 mutated files for malformed input `1.0`; the new `tests/test_release_rewrite_version_format.py` sweeps six malformed shapes (`1.0`, `v1.2.3`, `1.2.3-rc1`, `1.2.3 `, ``, `1.2.3.4`) and confirms each is rejected with zero file mutations, plus one positive test that `99.88.77` rewrites all 8 targets end-to-end.
- **Audit**: PASS — no principle touched, mechanical fix (defense-in-depth at the rewriter rather than relying on downstream `npm install --package-lock-only` to catch format drift).
- **Project impact**: n/a
- **Tests**: 286 passed / 0 failed / 0 xfailed (full `python -m unittest discover -s tests`, including the 2 new tests).
- **Bundled with**: none

## Closure verification (2026-05-30T12:50:31Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-30 — Closure' present
