## 2026-09-25T04:47:27Z — Resumed a stale claim

Claimed 2026-09-24T04:29:27Z (commit `6443449f`) by an autonomous run that
landed nothing after the claim; local `main` matched `origin/main` with a clean
tree 24h later, and the ready queue was otherwise empty. Resumed under the same
worker identity rather than left as a dead soft lock.

## 2026-09-25T04:47:27Z — The TDD item passed before the fix

`reproduce.py` exited 0 on the first run of this session, before anything was
edited: all three cites now verdict `(not current)` over their full history,
because `goc/engine.py` grew under them after the 2026-09-21 pass. The item
measured the live deck, not the recipe, so it could not tell the fixed text
from the broken one. It was struck as moot and replaced by a fixture-based
test that can.

Running it also exposed an overcount in its simulation. It withheld the
writing commit alone and kept every later commit, so on a card touched again
afterwards the next commit read as a fresh absent-to-present turn. Today's run
listed 34 cites across 28 cards that way, and all 31 outside the original
three had a withheld anchor NEWER than their writing commit (checked by
script, not by eye). With the history cut at the
writing commit, the census is 3 today (0 false repairs, exit 0). Run in a
throwaway worktree at the filing commit `79de4b8d`, it reports the same 3 as
false repairs (targets :5386, :2780, :5238, matching the README table) and
exits 1, so the corrected census is still sensitive to the defect. The
README's "21 cites across 19 cards" claim was rewritten in place.

## 2026-09-25T04:47:27Z — Closure

- **What changed**: `goc/templates/skills/refine-deck/reference.md`
  § "Citation anchor check" — re-run paragraph now commits first, a new
  paragraph gives the reason, the measurement, what a pass that cannot commit
  yet does (throwaway-worktree commit, or hold the step open), and the
  rejected working-tree alternative; residue table gains the sixth row
  "retired occurrence (re-run before the commit)". `SKILL.md` § "Defunct
  file:line citations" — closing step commits, then re-runs, with the reason;
  decline list names six. Mirrors: `.claude/`, `.codex/`, `claude-plugin/`,
  `codex-plugin/` via `scripts/sync_plugin_assets.py`, and
  `openclaw-plugin/skills/refine-deck/` via the porter.
  `tests/test_refine_deck_citation_anchor.py` — `documented_rerun_order`
  classifier, `DocumentedRerunOrderTest` (6), `RetiredOccurrenceRerunTest`
  (3). `reproduce.py` — history cut at the writing commit.
- **Verification**: against the pre-fix templates (throwaway worktree at
  `6443449f` with the new test file) 3 tests fail — core-skill order, residue
  row, and the fixture, whose second round reads `{'src/app.py:11': 21}`, the
  false repair. With the fix the second round is `{}`. `SKILL.md` is 14,198
  bytes against its 14,200 cap, so no cap raise.
  `sync_plugin_assets.py --check` and `port_skills_to_openclaw.py --check`
  both OK.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1195 passed / 0 failed / 0 xfailed (`uv run python -m unittest
  discover -s tests`)
- **Bundled with**: none. Forward pointer on the closed predecessor
  `citation-repair-pass-gives-two-cites-in-one-card-the-same-anchor-when-their-numbers-collide`
  updated from "Tracked by" to "Fixed by".

## Closure verification (2026-09-25T04:49:14Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-09-25 — Closure' present
