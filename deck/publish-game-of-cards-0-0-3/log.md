# Log — publish-game-of-cards-0-0-3

## 2026-05-04 — Release prep

- **What changed**: bumped package/version surfaces to `0.0.3` and added the release card.
- **Verification**: `uv run pytest` -> 33 passed; `uv run goc validate --quiet` -> exit 0; `uv run goc --version` -> `goc, version 0.0.3`; `uv build` -> built `dist/game_of_cards-0.0.3.tar.gz` and `dist/game_of_cards-0.0.3-py3-none-any.whl`.
- **Release state**: ready to commit, tag `v0.0.3`, push `main`, and push the tag.
