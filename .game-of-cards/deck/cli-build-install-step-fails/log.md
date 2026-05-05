## 2026-05-04 - Closure

- **What changed**: `.github/workflows/ci.yml` - removed `--system` from the editable package install so uv uses the virtual environment activated by `setup-uv`.
- **Verification**: `uv run python deck/cli-build-install-step-fails/reproduce.py` -> PASS; `uv pip install --python /private/tmp/goc-cli-build-venv-check -e .` installed `game-of-cards==0.0.2`; `/private/tmp/goc-cli-build-venv-check/bin/goc --version` -> `goc, version 0.0.2`.
- **Audit**: PASS - no principle touched, mechanical fix.
- **Project impact**: CI package install reaches the CLI smoke-test path instead of failing on Ubuntu's externally managed `/usr` Python.
- **Tests**: `uv run python -m unittest discover -s tests` -> 33 passed; `uv run goc validate --quiet` -> exit 0; `git diff --check` -> exit 0.

## Closure verification (2026-05-04)
