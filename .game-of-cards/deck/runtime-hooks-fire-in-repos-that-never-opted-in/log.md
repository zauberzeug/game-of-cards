
## 2026-10-22T05:56:49Z — Claim released after an aborted autonomous run

The scheduled pull-card run 39722531484 (2026-10-22 04:28Z) claimed this card (c9406ad6) and then stopped at "Reached maximum number of turns (120)" before pushing any work. Nothing was lost on main. The claim is released back to `open` so the next run, or a human session, can pick it up again.

## 2026-10-24T04:36:20Z — Closure

- **What changed**: `goc/templates/hooks/deck_prompt_router.py` — `main()` prints `REMINDER` only when the root `goc` resolves for the session (`_find_project_dir`, spliced byte-for-byte from the two sibling hooks, fed the hook input's `cwd`, then `CLAUDE_PROJECT_DIR` / `CODEX_PROJECT_DIR`, then the process cwd) holds `.game-of-cards/deck/` or the legacy `deck/` — the pair session-start reads, which settles the filing's legacy-fallback question. Synced to all five mirrors. `tests/test_project_root_from_subdirectory.py` now pins the router's resolver to `engine._resolve_deck_root` beside the other two hooks. The opt-in rule is stated in AGENTS.md, `goc.md`, `claude-plugin/README.md` and `codex-plugin/README.md`.
- **Verification**: new `tests/test_prompt_router_opt_in.py` (9 tests) drives the hook over stdin. 6 of them fail against the pre-fix router (every silence case). All 9 pass after the fix, and the 3 reminder cases (opted-in repo, its subdirectory, legacy `deck/`) pass on both. `scripts/sync_plugin_assets.py --check` is OK, and all six router copies are byte-identical.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1358 passed / 0 failed (`uv run python -m unittest discover -s tests`)
- **Surfaced**: the OpenClaw TypeScript port of the router (`before_prompt_build` in `openclaw-plugin/index.ts`) has the same gap. Fixing it needs a `dist/` rebuild, so it is filed as `openclaw-prompt-hook-fires-in-workspaces-without-a-deck` (gate none) rather than fixed through. The router now also reads `cwd`, so it shares its siblings' malformed-`cwd` exposure. `hook-scripts-keep-spawning-one-crash-fix-per-malformed-input-shape` already lists that shape for the whole family.

## Closure verification (2026-10-24T04:36:20Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-10-24 — Closure' present
