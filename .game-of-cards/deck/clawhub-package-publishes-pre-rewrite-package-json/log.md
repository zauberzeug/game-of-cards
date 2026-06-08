## 2026-06-08T04:12:16Z — Closure

- **What changed**: `.github/workflows/release.yml` — ClawHub publishes now pass `ref: ${{ needs.build.outputs.clawhub_source_ref }}` so package files are fetched from the post-rewrite release tag, while keeping `version: ${{ needs.build.outputs.release_version }}` for registry metadata.
- **Verification**: PyPI latest, npm latest, and the `v0.0.24` tag reported `0.0.24`; the v0.0.24 ClawHub publish log recorded source commit `34806dbcfa772e1f1057218960ea14171e1c3e24`, whose `openclaw-plugin/package.json` was still `0.0.23`, proving the ClawHub payload source ref was the stale surface.
- **Audit**: PASS — no principle touched, mechanical release-workflow fix.
- **Project impact**: Future ClawHub publishes package the same version-literal payload as the release tag instead of only overriding registry metadata.
- **Tests**: `uv run python -m unittest tests.test_release_workflow_clawhub_source_ref tests.test_version_surfaces tests.test_release_rewrite_version_format` passed; `uv run python -m unittest discover -s tests` passed (388 tests, 1 skipped); `uv run goc validate` passed with pre-existing warnings; `python3 scripts/sync_plugin_assets.py --check` passed.
- **Bundled with**: n/a

## Closure verification (2026-06-08T04:12:44Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-06-08 — Closure' present
