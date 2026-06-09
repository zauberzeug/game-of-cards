## 2026-06-05T04:36:48Z — Closure

- **What changed**: `goc/engine.py:490-531` — `_dod_fenced_mask` now tracks the opening fence's character (`` ` `` vs `~`) and run length, closing a fenced code block only on a same-character fence whose run length is >= the opener's (CommonMark §4.5). A `~~~` line inside a backtick block (or a shorter same-character run) is content, not a close, so the mask no longer desynchronizes on mismatched fences. `DOD_FENCE_DELIM` gained capture groups for the run.
- **Verification**: reproduce.py now exits 0 (`count_dod_boxes` → `(1, 1)` and `_dod_box_indices` → `[0, 5]` for a backtick block illustrating a `~~~` fence with a real open item after; was `(0, 1)` / `[0]`, which silently hid the unfinished item from `goc done`).
- **Audit**: PASS — mechanical parser-correctness fix honoring universal markdown fenced-code semantics; no project principle touched. Single shared function fixes all three DoD scanners at once (not a meta-fix family). Adjacent to the closed card `dod-checkbox-inside-fenced-code-block-counts-as-real-item-and-blocks-closure`, which introduced the mask without fence-character matching.
- **Project impact**: n/a
- **Tests**: 390 passed / 0 failed (`uv run python -m unittest discover -s tests`); 4 new cases in `tests/test_dod_fenced_checkbox.py` (`DodMismatchedFenceTest`); `uv run goc validate` clean (plugin mirrors re-synced).
- **Bundled with**: n/a
