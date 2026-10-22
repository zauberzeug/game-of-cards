## 2026-09-20T04:52:00Z — Closure

- **What changed**: `goc/templates/game_of_cards/README.md:89-91` — dropped the
  extraction-era `Sub-card 6` bullet (it named a third-party repo and cited
  `deck/goc-package-pyproject-and-pypi-release/audit_catalogue.md`, stale on
  both the rename and the `deck/` → `.game-of-cards/deck/` move);
  `goc/templates/skills/refine-deck/reference.md:390-391` — dropped the pointer
  to `deck/auto-validate-card-titles-summaries-and-dods/log.md`, a card that
  never existed; `tests/test_skill_template_deck_links.py` — widened the
  standing guard on the two axes it was narrow on.
- **Verification**: `reproduce.py` exits 0 (was 1, with 2 offending lines).
  Guard sweep covers 10 trees (was 6) and every file (was `*.md` only);
  0 hits across ~218 files, 0 false positives on the 19-per-tree
  `deck/<title>/` placeholder convention. `sync_plugin_assets.py --check` and
  `port_skills_to_openclaw.py --check` both green.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: 1165 passed / 0 failed / 0 xfailed (was 1161; +4 from this card —
  two sensitivity, one precision, one derive-from-tree).
- **Bundled with**: n/a

Scoped out deliberately: the `deck/<title>/` placeholder shorthand, used
consistently at 19 sites per skill tree and in `game_of_cards/config.yaml`.
The guard added here must keep it passing to stay usable, so respelling it is
a separate convention call — filed as
[`shipped-docs-abbreviate-the-deck-path-to-a-root-install-no-longer-creates`](../shipped-docs-abbreviate-the-deck-path-to-a-root-install-no-longer-creates/)
at `human_gate: decision`.

The widening rather than a twelfth guard file is the point worth keeping: the
rule already existed, already swept the tree holding one of the two offenders,
and still missed it — guards written from one instance inherit that instance's
syntax. Recorded on
[`doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them`](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/)
as the twentieth instance.

## Closure verification (2026-09-20T04:46:33Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-09-20 — Closure' present
