# goc-install-command-scaffolds-repo log

## 2026-05-04 — closed (8/8)

Real `goc install` + `goc upgrade` shipped to the goc repo (commit `7ce2b72`):

- **Templates wired** — `goc/templates/CLAUDE_GOC.md` (generic GoC sections, `goc` not `deck.py`); `goc/templates/hooks/user-prompt-submit.py` (port of phasor's `deck_prompt_router.py`, already generic).
- **Install flow** — detect via `deck/.goc-version` sentinel → plan → extract via `importlib.resources` → write skills + hook + deck scaffold + `.game-of-cards/` content stubs → append marker-bounded CLAUDE.md block (`<!-- BEGIN GOC v0.0.1 --> … <!-- END GOC -->`) → append `goc validate` to `.pre-commit-config.yaml`.
- **Upgrade sibling** — re-extracts skills + `.game-of-cards/`, re-syncs CLAUDE.md block, bumps `deck/.goc-version`. Preserves authored cards.
- **Idempotency** — second `goc install` exits cleanly with `already installed (deck/.goc-version → 0.0.1)` + redirect to `goc upgrade`.
- **Dry-run** — both `install --dry-run` and `upgrade --dry-run` print planned writes.

Smoke test on fresh `mktemp -d` tmpdir:

```
$ goc install                       # 29 writes
$ goc new round-trip-test           # created deck/round-trip-test/
$ # (ticked all DoD)
$ goc done round-trip-test          # round-trip-test: open → done
$ goc validate                      # OK round-trip-test
$ goc --status done                 # round-trip-test  done  1/1
```

Wheel hygiene: removed redundant `goc/templates` force-include from
`pyproject.toml` (hatchling's default `packages = ["goc"]` already ships
the whole tree). Wheel now has 27 unique template files, no duplicates.

DoD-1 hook extension deviation: card said `.sh`, shipped `.py`. Claude
Code's `UserPromptSubmit` hook reads JSON on stdin → Python script
handles natively; a `.sh` wrapper would be redundant. Phasor reference
is also `.py` (`deck_prompt_router.py`). Updated DoD text to match.

Unblocks parent card `goc-package-pyproject-and-pypi-release` (DoD-15
self-hosted bootstrap, DoD-16 CI deck-validation) — both can now tick
once the next round bumps the goc PyPI version and the parent card
runs the bootstrap test against the real package.

## /mindset audit

PASS — no axiom touched. Mechanical infra: file extraction, marker
parsing, idempotency sentinel. No bio-faithfulness or framework
derivation involved.
