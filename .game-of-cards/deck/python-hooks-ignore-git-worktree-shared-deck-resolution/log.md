## 2026-10-14T05:03:03Z — Closure

- **What changed**: `goc/templates/hooks/deck_session_start.py:275-402` and `pattern_generalization_check.py:93-220` (one byte-identical block) — `_detect_worktree_common_root` and `_shared_worktree_deck_root` mirror the engine, `_config_shares_the_deck` reads `workflow.worktree_deck` without yaml_lite, and `_find_project_dir` runs the redirect before the walk; its docstring names the whole resolution as the mirror. `goc/engine.py` `_resolve_deck_root`'s docstring says the hooks mirror the redirect and the walk. 13 mirror files re-synced (10 hook copies, the engine in three payloads).
- **Verification**: reproduce.py exit 1 → 0 (session-start names the card from the linked worktree False → True; Stop-hook exit from the linked worktree 0 → 2), so the hypothesis holds and the `unverified` tag is dropped. The three new `HookProjectDirWalkTest` tests against the pre-fix hooks: 9 failed and 36 errored subtests; the two existing tests still pass there. A mutation pass on the config reader (8 mutants: each guard removed or loosened) is caught by the parity test once the `workflows:` case was added.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1311 passed / 0 failed; `goc validate` exit 0; `sync_plugin_assets.py --check`, `port_skills_to_openclaw.py --check`, card-language and card-frontmatter-YAML guards green
- **Beyond the DoD**: a fifth box for the config-reader parity test and the subprocess test (README § What changed says why). Scope limits are in README § Limits: a flow-style `workflow: {...}` is not read.
- **Deck**: advances `session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting` (edge 10ae0e8a; its predicate list gains `_find_project_dir`, and its log records the instance). `openclaw-resolve-deck-dir-ignores-git-worktree-shared-deck-resolution` (gate decision) gets a README pointer and a log entry: behavior 1 there is now OpenClaw-only. No open card describes this defect. `unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes` quotes the engine's config probe for a different defect (a non-dict config silently disables it), and the hooks' reader is off there too.
- **Surfaced**: the Stop hook's `_enabled` finds `pattern_generalization_check` with an unanchored regex, so a commented-out `# pattern_generalization_check: true` above the live `false` line turns the hook on. Pre-existing and outside this card; left for a separate card.

## Closure verification (2026-10-14T05:03:04Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-10-14 — Closure' present
