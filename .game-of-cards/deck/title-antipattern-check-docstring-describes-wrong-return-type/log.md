## 2026-06-28 — filed and fixed (fix-through)

Surfaced during a `pull-card` run whose ready queue was empty (every open
card sat at `human_gate: decision`), so an `audit-deck` hunt ran instead.
The hunt's top candidate (an inverted trailing-newline condition in
`_apply_dod_rewrite`) turned out to be a re-discovery of the already
`disproved` card `dod-rewrite-trailing-newline-reconstruction-is-inverted`
— its re-promotion condition (emit-time `rstrip` masking removed) still
does not hold, so it was not re-filed. This docstring-drift finding was
the next candidate and is a clean, determined, single-site fix.

Fix landed:
- `goc/engine.py`: corrected the `_check_title_antipatterns` docstring
  from "Return list of (matched_substring, reason) tuples" to describe
  the actual return value — a list of antipattern reason strings,
  matching the `-> list[str]` annotation and both call sites
  (`_cmd_quality_pass`, `_cmd_new`/`_cmd_move`).
- `tests/test_title_antipattern_return_type.py`: regression test pinning
  that every returned element is a `str` (not a tuple) for a jargon
  title, and that a clean title returns `[]`.
- Regenerated the three plugin engine mirrors via
  `scripts/sync_plugin_assets.py`.

Both DoD items satisfied; closing.
