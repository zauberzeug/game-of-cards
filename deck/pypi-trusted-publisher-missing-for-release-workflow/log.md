# Log — pypi-trusted-publisher-missing-for-release-workflow

## 2026-05-04 — Filed

- **Evidence**: GitHub Actions run `25322155017` built release artifacts but PyPI rejected the trusted-publishing exchange with `invalid-publisher`.
- **Manual fallback**: local `uv publish --trusted-publishing never ...0.0.3...` reached PyPI but no token or `.pypirc` credentials were configured.

## Closure verification (2026-05-05)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [ ] dod-100-percent FAIL — 2 unchecked boxes
- [ ] log-md-closure-entry FAIL — no '## 2026-05-05 — Closure' section

## 2026-05-05 — Closure

- Rodja added the trusted-publisher row at https://pypi.org/manage/project/game-of-cards/settings/publishing/ with owner `zauberzeug`, repo `game-of-cards`, workflow `release.yml`, environment `pypi`.
- Bumped `pyproject.toml` to `0.0.4`, tagged `v0.0.4`, pushed. First publish attempt still failed with `invalid-publisher` (publisher row not yet saved on PyPI's side); after Rodja confirmed, the failed `Publish to PyPI` job was re-run via `gh run rerun 25380106971 --failed` and succeeded.
- `game-of-cards 0.0.4` is now on PyPI; OIDC trusted-publishing exchange completed without `UV_PUBLISH_TOKEN`.
- All three DoD items checked. Card closes.
