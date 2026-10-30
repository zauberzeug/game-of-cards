## 2026-10-22T05:56:36Z: decision recorded

Lower the gate: dedupe repeated --tag values the way advances are deduped — Bulk rule approved by the maintainer in a human session on 2026-10-22: a gated card with no written question and a mechanical fix drops to gate none. Gate decision → none.

## 2026-10-30T04:27:18Z — Closure

- **What changed**: `goc/engine.py:6808` — `_cmd_new` reads `--tag` through `_unique_preserving_order`, beside `--advances` / `--advanced-by`, so a repeated tag (subcommand or global flag) lands once in first-seen order. New `tests/test_new_dedupes_repeated_list_flags.py`: three behavior tests plus a tripwire that lists every `action="append"` option on the `new` subparser, so a later repeatable flag cannot skip the dedupe unnoticed.
- **Verification**: `reproduce.py` exits 0 (`tags: [bug, documentation]`); run against a copy of the pre-fix engine it exits 1 (`[bug, bug, documentation, bug]`). 3 of the 4 new tests fail against the pre-fix engine. `uv run goc validate` exit 0.
- **Reproducer contract**: filed inverted — it exited 0 while the defect fired, the pattern `reproducers-can-exit-zero-while-their-defect-still-fires` describes — and was flipped here to 0 = defect no longer fires, 1 = fires.
- **Validate-rule decision (DoD PROCESS box)**: no `goc validate` rule for already-filed duplicate tags and no sibling card. `_cmd_new` is the only writer of `tags`; a scan of all 823 cards found no repeated entry in `tags` or any edge list; the `advances: [B, B]` precedent (`sort-tiebreak-double-counts-duplicate-advances-edges`) fixed the reader and left validate tolerant of repeated entries.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1432 passed / 0 failed / 0 xfailed

## Closure verification (2026-10-30T04:27:27Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-10-30 — Closure' present

## 2026-10-30T04:30:14Z — Reproducer rewritten to the 0/1/2 contract after close

The closure flip covered exit codes 0 and 1 only. The script still had no positive control and no exit 2: its "fixed" verdict was `tags_line.count("bug") <= 1`, which a missing or reshaped `tags:` line also satisfies. A failing `goc` call raised through `check=True` and exited 1, the code for "fires". It also ran whichever `goc` sat in `.venv/bin` or on PATH instead of this source tree. It now runs `python -m goc.cli` from the tree, reads `tags` back through `parse_frontmatter`, and exits 2 unless they are exactly the deduped or the duplicated list. Verified: exit 0 on the fixed engine, 1 against the pre-fix engine (`774a1f6f`), 2 with a `goc.cli` that raises. Recorded as an instance on `reproducers-can-exit-zero-while-their-defect-still-fires`.
