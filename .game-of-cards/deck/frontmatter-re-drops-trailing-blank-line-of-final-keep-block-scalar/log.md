## 2026-06-25: filed and fixed (pull-card fix-through)

Surfaced by a defect-hunt while the pull-card ready queue was empty (every
`human_gate: none` open card carried an active `waiting_on` overlay). Fixed
through in the same session — small, single-site, gate-free.

**Root cause.** `FRONTMATTER_RE = r"^---\n(.*?)\n---\n?(.*)$"` let the `\n---`
closing delimiter consume the trailing-blank-line newline that belongs to a
final `|+` (keep) block scalar, so `yaml_lite` saw one content line fewer and
read the value back one newline short. This is the parse-side mirror of the
closed emitter-side card
`emit-frontmatter-drops-trailing-blank-lines-from-multi-line-string-fields`,
whose `reproduce.py` explicitly scoped this boundary out: the emitter now
writes `|+` correctly, but the parser could not round-trip it as the last field.

**Fix.** Split the blank-line run into its own group:
`r"^---\n(.*?)(\n+)---[ \t]*(?:\n(.*))?$"`. `parse_frontmatter` now feeds
`group(1) + group(2)` to `safe_load` (so the keep indicator decides the blank
line's fate) and uses `group(3) or ""` as the body.

**Second consumer caught during verification.** `mutate_frontmatter_field`
(the line-anchored field replacer used by `goc decide`/`status`/`wait`) was the
*other* `FRONTMATTER_RE` consumer; it read `m.group(2)` as the body. Left as-is
it destroyed the entire body on every gate flip (caught by
`test_decide_blank_line_before_section` / `test_decide_archives_deliberation`).
Updated it to read `group(2)` as the blank run and `group(3)` as the body, and
to re-emit the blank run between the frontmatter and `---`. For the common
single-newline separator this reconstruction is byte-identical to the prior
two-group behavior, so existing cards are unaffected.

**Tests.** Added `FinalKeepScalarParseBoundaryTest` to
`tests/test_yaml_lite.py` (final keep scalar round-trip, with-body round trip,
mutate-field preservation, body-with-`---` split, EOF-without-trailing-newline).
`reproduce.py` exits zero; full suite 599 green; `goc validate` clean. Plugin
mirrors re-synced (`sync_plugin_assets.py`, `port_skills_to_openclaw.py`).

## 2026-06-25T20:10:00Z — Closure

- **What changed**: `goc/engine.py:136` (`FRONTMATTER_RE` 3-group split) +
  `engine.py:439` (`mutate_frontmatter_field` reads group(2) as blank run,
  group(3) as body) — a final `|+` keep scalar now round-trips through both
  `FRONTMATTER_RE` consumers.
- **Verification**: `reproduce.py` exits 0; `'ends with blank\n\n'` round-trips
  faithfully (was `'ends with blank\n'`).
- **Audit**: PASS — no principle touched, mechanical fix (field-symmetric
  serialization boundary).
- **Project impact**: n/a
- **Tests**: 599 passed / 0 failed / 0 xfailed
- **Bundled with**: n/a

## Closure verification (2026-06-25T20:09:44Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-25 — Closure' present
