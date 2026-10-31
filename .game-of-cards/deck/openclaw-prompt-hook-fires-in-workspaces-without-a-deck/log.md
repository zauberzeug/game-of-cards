## 2026-10-31T05:22:52Z — Closure

- **What changed**: `openclaw-plugin/index.ts:771`. The `before_prompt_build` handler returns before appending `DECK_REMINDER` unless `hasDeck(sessionProjectDir ?? process.cwd())`, the dir `session_start` reads. It is looked up only after a prompt is found to be work-shaped. `dist/` was rebuilt (`npm ci` + `npm run build`): the `index.js` diff is that one line, and a rebuild of the unedited source was byte-identical. The AGENTS.md sentence and the hook row in `openclaw-plugin/README.md` are updated.
- **Verification**: `reproduce.py` went from exit 1 to exit 0. The new `tests/test_openclaw_prompt_hook.py` extracts the handler, the patterns, `DECK_REMINDER`, `hasDeck` and `pathExists` from `index.ts` and runs them under `node --experimental-strip-types`. Against the pre-fix source 3 of its 7 subtests fail (no deck, `.game-of-cards/` without `deck/`, cwd fallback without a deck). All 7 pass after.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: 1454 passed / 0 failed / 0 xfailed (`uv run python -m unittest discover -s tests`). `sync_plugin_assets.py --check` and `port_skills_to_openclaw.py --check` are clean, and `goc validate` exits 0.
- **Surfaced, filed, not fixed through**: `npm ci` installed the pinned `openclaw@2026.5.7`. Its hook types and runner call every typed hook as `handler(event, ctx)` and read only the return value, and none of the plugin's three handlers uses that shape. On a real host this handler reads `event.userPrompt` (absent) and returns before the new guard, so the deck-first reminder never fires in any workspace. Filed as `openclaw-plugin-hooks-never-deliver-their-reminders-on-a-real-host` (`human_gate: decision`). Two of the three hooks are void and need a delivery channel someone has to choose, and fixing the shapes switches on reminders live deployments have never seen. The guard landed here still matters once that port happens. The port should then look the deck up on `ctx.workspaceDir` first.

## Closure verification (2026-10-31T05:22:54Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-10-31 — Closure' present
