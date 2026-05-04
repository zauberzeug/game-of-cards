# Log — publish-game-of-cards-0-0-3

## 2026-05-04 — Release prep

- **What changed**: bumped package/version surfaces to `0.0.3` and added the release card.
- **Verification**: `uv run pytest` -> 33 passed; `uv run goc validate --quiet` -> exit 0; `uv run goc --version` -> `goc, version 0.0.3`; `uv build` -> built `dist/game_of_cards-0.0.3.tar.gz` and `dist/game_of_cards-0.0.3-py3-none-any.whl`.
- **Release state**: ready to commit, tag `v0.0.3`, push `main`, and push the tag.

## 2026-05-04 — Publish blocked

- **GitHub Actions**: tag-triggered release run `25322155017` built artifacts successfully but failed in `Publish to PyPI`.
- **Root cause**: PyPI returned `invalid-publisher`; no trusted publisher matched `zauberzeug/game-of-cards`, workflow `release.yml`, environment `pypi`.
- **Manual publish attempt**: `uv publish --trusted-publishing never dist/game_of_cards-0.0.3.tar.gz dist/game_of_cards-0.0.3-py3-none-any.whl` reached PyPI but failed with `Missing credentials for https://upload.pypi.org/legacy/`.
- **Follow-up**: filed `[pypi-trusted-publisher-missing-for-release-workflow](../pypi-trusted-publisher-missing-for-release-workflow/)`.
