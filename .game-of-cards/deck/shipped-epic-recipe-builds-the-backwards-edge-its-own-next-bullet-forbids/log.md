## 2026-09-21T02:35:00Z — Closure

- **What changed**: `goc/templates/skills/advance-card/reference.md:108` —
  the aggregation-epic recipe's verb read `goc advance <child> --by <epic>`,
  which builds `epic.advances: [children]`; it now reads
  `goc advance <epic> --by <child>`, which builds the `child.advances: [epic]`
  encoding the line above it states. Regenerated into all five mirrors
  (`.claude/`, `.codex/`, `claude-plugin/`, `codex-plugin/` via
  `scripts/sync_plugin_assets.py`; `openclaw-plugin/` via
  `scripts/port_skills_to_openclaw.py`). Added
  `tests/test_skill_advance_example_direction.py`, which runs every
  role-named `goc advance` example in a shipped skill body against a scratch
  deck and compares the edge it builds with the `<role>.advances: [<role>]`
  claim in the same markdown block. Corrected the two propagated citations in
  `auto-commit-publishes-dangling-edges-when-counterpart-endpoint-is-a-draft`,
  rewrote the sibling sweep in
  `validate-backwards-epic-edge-fix-suggestion-has-swapped-command-arguments`
  (its "no other instances found" was scoped to warning strings), added the
  instance row on
  `doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them`,
  and amended the closed `relationship-modeling-has-no-discoverable-home` —
  which authored the fork in commit 175058ff — with a forward pointer.
- **Verification**: `reproduce.py` exits 0 (was 1); it was re-derived to read
  both the encoding and the verb out of the shipped text, so it now fails on a
  swap in either direction rather than on one hard-coded argument order. The
  new guard, run against the unsynced tree mid-fix, named all five stale
  mirrors and stayed green on the fixed template — and its third test feeds the
  pre-fix bullet back in and requires rejection. 1175 tests pass;
  `uv run goc validate`, `sync_plugin_assets.py --check` and
  `port_skills_to_openclaw.py --check` all clean.
- **Audit**: no rubric configured (`.game-of-cards/hooks/finish-card.md` is
  empty). Not purely mechanical, though: the closure binds this repo's
  doc-accuracy convention that a shipped instruction must be derived from — or
  executed against — the engine rather than restated beside it, and it adds the
  second implementation of the run-it-against-a-fixture technique that
  `doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them`
  names as a third guard class its decision has yet to adopt.
- **Project impact**: the documented aggregation-epic recipe now builds the
  edge it promises in all six skill trees, so a consumer's first epic no longer
  inherits the broken value chain, the spurious `advanced-by-closed` attest
  FAILs, or the `BACKWARDS_EPIC_EDGE` warning. One shipped text still gets this
  verb's argument order backwards — `goc validate`'s own remedy string, tracked
  by `validate-backwards-epic-edge-fix-suggestion-has-swapped-command-arguments`
  (open, gate `decision`) — and the new guard does not reach it, since it walks
  skill bodies rather than `engine.py` strings.
- **Tests**: 1175 passed / 0 failed / 0 xfailed.
- **Bundled with**: none.

## Closure verification (2026-09-21T05:01:44Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-09-21 — Closure' present
