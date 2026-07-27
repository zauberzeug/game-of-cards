## 2026-05-18 — Closure

- **What changed**: `goc/engine.py` — `goc new` now accepts repeatable `--advances` and `--advanced-by` flags, validates targets/cycles before creating a card, and wires accepted edges through `_mutate_pair`.
- **Verification**: `uv run python -m unittest tests.test_new_wires_edges` passed 4 tests; `uv run goc validate` passed; `python3 scripts/sync_plugin_assets.py --check` passed.
- **Audit**: PASS — no rubric configured; mechanical fix.
- **Project impact**: Agents can file already-wired cards without hand-authoring half-edges.
- **Tests**: 4 passed / 0 failed for the focused suite; `uv run python -m unittest discover tests` had 1 unrelated existing failure in `test_board_and_open_queue_surface_active_cards`.
- **Bundled with**: n/a

## Closure verification (2026-05-18T03:54:15Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 8/8 ticked
- [x] log-md-closure-entry — '## 2026-05-18 — Closure' present

## 2026-07-27 — Deck hygiene: defunct sibling-card reference corrected

`Skill(refine-deck)`'s defunct-reference sweep found the body pointing twice
at `goc-repair-edges-fixes-half-edge-validator-errors` — a slug that has never
existed in the deck (`git log --all --diff-filter=A` on that path returns
nothing). The sibling card actually filed alongside this one in commit
`ea154625 deck: file two cards for half-edge prevention and repair` is
`half-edge-repair-requires-manual-multi-file-edits`, whose summary is the
`goc repair-edges` cleanup tool this body describes. The link and the
Cross-references bullet were rewritten in place to the real slug. No claim in
this card changed; the citation was wrong at filing time, not rotted by a
later rename.
