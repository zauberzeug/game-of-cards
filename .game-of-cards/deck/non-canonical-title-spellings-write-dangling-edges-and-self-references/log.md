## 2026-08-02T05:50:00Z — Closure

- **What changed**: `goc/engine.py:1044` — `resolve_card_dir` gained a
  `title != Path(title).name` clause, so a title argument that resolves into
  the deck under a non-canonical spelling (`a/`, `./a`, `a//`, `././a`) is
  refused with exit 2 before any read or write. Containment was already
  enforced; canonicality was not, and every caller keeps the raw argument
  string as the card's identity afterwards. No caller changed — all four
  affected doors already routed through the helper.
- **Verification**: `reproduce.py` 1 → 0 (7 findings → none); the three
  edge-writing doors go exit 0 → exit 2 and the scratch deck's `goc validate`
  goes 6 errors → 0; `goc done --bundle a a/` no longer closes one card as
  two members with a doubled attestation block.
- **Audit**: PASS — no rubric configured
  (`.game-of-cards/hooks/finish-card.md` is an empty stub); mechanical fix
  enforcing the contract the function's own docstring already states.
- **Project impact**: n/a
- **Tests**: 888 passed / 0 failed (was 882; +6 in the new
  `CanonicalTitleSpellingTest` class of
  `tests/test_title_resolution_containment.py`, the regression file the
  predecessor card created)

Scope note: rejection was chosen over normalization deliberately. Accepting
`a/` and folding it to `a` would mean threading a canonical title back to
every site that uses `args.title` independently for guards, edge values and
messages — roughly a dozen — whereas rejecting at the single shared resolver
preserves the invariant those sites already assume, that the typed identity
and the stored identity are the same string.

## Closure verification (2026-08-02T05:39:30Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-08-02 — Closure' present
