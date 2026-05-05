## 2026-05-05: filed

CI run https://github.com/zauberzeug/game-of-cards/actions/runs/25378542474 surfaced three install-smoke assertion failures latent on `main` since 65e222b. Status active immediately — pure assertion sync, no design call needed.

## 2026-05-05: closed

Updated `tests/test_install.py:125,184,207` to assert the current "expand the deck" hint. Full local suite green: `uv run python -m unittest discover -s tests` → 46/46 ok. `uv run goc validate` clean.
