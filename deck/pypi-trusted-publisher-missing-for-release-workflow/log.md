# Log — pypi-trusted-publisher-missing-for-release-workflow

## 2026-05-04 — Filed

- **Evidence**: GitHub Actions run `25322155017` built release artifacts but PyPI rejected the trusted-publishing exchange with `invalid-publisher`.
- **Manual fallback**: local `uv publish --trusted-publishing never ...0.0.3...` reached PyPI but no token or `.pypirc` credentials were configured.
