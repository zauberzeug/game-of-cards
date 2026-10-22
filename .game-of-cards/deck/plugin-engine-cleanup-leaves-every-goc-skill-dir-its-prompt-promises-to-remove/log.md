## 2026-10-15T04:29:04Z — Resumed a stale claim

Claimed 2026-10-11T04:57:51Z (commit `988cb0f9`) by iteration 2 of Pull
Card run 38113205569. That run's agent step failed at about 05:03Z
(`Claude execution failed: result is_error:true`). Its last action was an
uncommitted edit to `tests/test_install.py`, and it landed nothing after
the claim. Four days later, local `main` matched `origin/main` with a clean
tree, and no commit had touched the card since the claim. Pull Card runs
share one concurrency group (`pull-card-${{ github.ref }}`), and this run
was the only one in progress, so no live session could hold the claim.
Resumed under the same worker identity instead of leaving a dead soft lock,
as the deck has done three times before (listed on
[session-start-hook-says-resume-active-cards-that-pull-card-says-to-leave-alone](../session-start-hook-says-resume-active-cards-that-pull-card-says-to-leave-alone/),
which tracks the missing rule). `reproduce.py` still exits 1, with 16 of 16
GoC skill dirs left behind.

## 2026-10-15T04:39:37Z — Closure

- **What changed**: `goc/install.py` — new `_goc_skill_names(templates, agent)`
  reads GoC's skill names from `templates/skills/` or, when a plugin payload
  omits that tree, from the payload's own `skills/` beside its bundled `goc/`
  (SKILL.md dirs only, filtered through `skill_for_agent`).
  `_strip_claude_vendored_harness` takes its GoC-owned set from it, and the
  `upgrade()` cleanup prompt promises skill-dir removal only when the helper
  has names. Otherwise it says the skill dirs stay. `goc.md` drops the
  standalone-`goc` caveat, and `AGENTS.md` says where the bundled engine reads
  the names. Mirrors re-synced into `claude-plugin/`, `codex-plugin/` and
  `openclaw-plugin/`.
- **Deviation from the sketch**: the fallback keys on the payload's
  `skills/` tree, not on `_is_plugin_context()`. That predicate is False on
  every versioned marketplace install
  ([plugin-context-detection-never-fires-on-real-marketplace-installs](../plugin-context-detection-never-fires-on-real-marketplace-installs/)),
  so gating on it would have fixed this source tree only. The parked card's
  `log.md` now points here.
- **Verification**: `reproduce.py` exit 1 (16 of 16 GoC skill dirs left) → 0
  (0 of 16, repo's own skill kept, `.claude/hooks/` gone).
  `test_bundled_engine_caveat_matches_its_cleanup` went red after the engine
  fix and green once `goc.md` dropped the caveat. Four injected mutations
  each turn at least one new test red: gating the fallback on
  `_is_plugin_context()`, removing the fallback, dropping the `SKILL.md`
  filter, and always printing the promise.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1319 passed / 0 failed / 0 xfailed
  (`uv run python -m unittest discover -s tests`; 2 new tests, 1 rewritten)
- **Also green**: `uv run goc validate` exit 0;
  `scripts/sync_plugin_assets.py --check` and
  `scripts/port_skills_to_openclaw.py --check` clean; card-language and
  card-frontmatter-YAML guards clean.
- **Known gap, accepted by the card**: from the Codex or OpenClaw payload the
  names lack `claude-kickoff` (those trees carry their own kickoff
  complement), so that one dir stays. Before the fix, all 16 stayed.
- **Bundled with**: none

## Closure verification (2026-10-15T04:39:51Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-10-15 — Closure' present
