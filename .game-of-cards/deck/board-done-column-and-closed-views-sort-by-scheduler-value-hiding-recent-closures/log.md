## 2026-10-08T05:02:15Z — Closure

- **What changed**: `goc/engine.py:3344` `sort_default` now returns live cards in the unchanged scheduler order followed by terminal cards most recently closed first (`_closed_recency_key`, `goc/engine.py:3313`: `closed_at` instant descending, a missing or unparseable stamp last, title as the tie-break). The board's terminal columns, `--done`, `--status <terminal>`, `--closed-since`, and the terminal tail of `--status all` all inherit the order through the one entry point. `standup` § 3 and `retrospective` Step 1 drop their Python `closed_at` re-sorts and now read the engine order (`standup`'s list flips from oldest-first to newest-first).
- **Verification**: `reproduce.py` exits 1 on the pre-fix engine (all three views bury the recent closures) and 0 after the fix. `tests/test_closed_card_views_sort_by_recency.py` has 9 cases: all fail against a `git archive HEAD` copy of the pre-fix package and all pass now. In this repo the board's DONE column now opens on the newest closures instead of `install-command-scaffolds-repo` (2026-05-04).
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1259 passed / 0 failed / 0 xfailed (`uv run python -m unittest discover -s tests`); `goc validate` 0 errors; `sync_plugin_assets.py --check`, `port_skills_to_openclaw.py --check`, `check_card_language.py`, `check_card_frontmatter_yaml.py` clean.
- **Bundled with**: none
- **Design note**: the card left open whether terminal views get their own key in `sort_default` or at each caller. I put the split in `sort_default`, so no caller can reintroduce the value order for closed cards. As a result `--status all` lists the queue first and the record after it, where it used to mix them by value. The pull path, the leverage line, and the active banner only sort live cards, so their order is unchanged.
- **Related, not changed**: `backfill-terminal-closed-at-stamps-latest-edit-date-as-closure-date` (parked on a decision) corrupts the `closed_at` stamps this order now reads. That defect also feeds the board's terminal-column order, so the stakes of that card are slightly higher.
- **Dropped edit**: adding "newest first" to the `deck` skill's `--closed-since` row pushed `deck/SKILL.md` to 10108 bytes, over its 10100 `test_skill_body_size` cap. I reverted that edit; the row was already accurate as written.

## Closure verification (2026-10-08T05:02:29Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-10-08 — Closure' present
