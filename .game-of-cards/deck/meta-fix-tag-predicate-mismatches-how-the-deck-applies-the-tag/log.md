# Log

## 2026-07-08 — resolution picked, predicate widened, sweep verified

**Decision: Option 1 — widen the predicate to match observed deck
practice.** Reasoning:

- The tag's job is the family-filter view (`goc --tag meta-fix`); the
  strict ~2500-char-window predicate failed on **37 of 45** open
  `meta-fix`-tagged cards (measured 2026-07-08), including correctly
  wired family heads and members. A mechanical sweep under the strict
  contract would have mass-stripped a curated filter — the destructive
  outcome the card warned about.
- Family membership in this deck is expressed by **wiring** (edges to
  a tagged head) and by the `summary:` frontmatter field, both of
  which the strict predicate never consulted. Ratifying that practice
  is cheaper and truer than churning ~three dozen card bodies to
  front-load a literal (Option 2), and needs no schema migration
  (Option 3).

**Predicate wording landed** in
`goc/templates/skills/card-schema/SKILL.md` ("Tag application
criteria"): the intro now states the ~2500-char window is the
*default* surface and rows may name a wider one; the `meta-fix` row
(typo "title, title, or body" also fixed) now reads: literal
`meta-fix` / `family meta-fix` anywhere in the title, `summary:`
frontmatter field, or full body (no window cutoff), OR a non-empty
`advances` / `advanced_by` edge to a `meta-fix`-tagged card.

**Refine-deck consistency:** the zero-edge sub-check comment
(Step 2, sub-check 2) now routes the (a)-genuine vs (b)-mistagged
judgment through the card-schema predicate — for a zero-edge card the
edge clause can't fire, so the body/summary/title literal test is
decisive: literal present → wire the family; absent → strip the tag.

**Empirical spot-check (DoD item 3):** ran the widened predicate over
all 45 open `meta-fix`-tagged cards (script over `goc --tag meta-fix
--status open --json` + per-card README read): every card fires on at
least one clause — 45/45 via body-wide literal, 30 additionally via
an edge to a tagged card, 8 additionally via `summary:`. **Zero false
positives.** Under the old strict window predicate the same sweep
fails 37/45 — confirming the mismatch was real and the widening
resolves it.

One evidence correction: the README originally claimed three
umbrella-shaped cards
(`codex-skill-frontmatter-normalization-reimplemented-in-install-and-sync`,
`single-source-pattern-check-reminder-across-host-ports`,
`extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate`)
carry *zero* body-wide literals. As of 2026-07-08 all three DO carry
the literal in the body (past the window) — the bodies gained the
literal after filing. The README Evidence section was rewritten in
place accordingly; the resolution is unaffected (they still fail the
window test, and now pass the widened predicate on the body clause).

Mirrors regenerated (`scripts/sync_plugin_assets.py`), OpenClaw skills
re-ported (`scripts/port_skills_to_openclaw.py` + `--check` green),
`uv run goc validate` exit 0, regression suite 702 tests OK.

## 2026-07-08T01:06:59Z — Closure

- **What changed**: `goc/templates/skills/card-schema/SKILL.md` "Tag application criteria" — intro reworded (window is a per-row-overridable default) and the `meta-fix` row widened to fire on a literal anywhere in title / `summary:` / full body OR a non-empty edge to a `meta-fix`-tagged card (typo "title, title, or body" fixed); `goc/templates/skills/refine-deck/SKILL.md` Step 2 sub-check 2 comment now routes the genuine-vs-mistagged judgment through that predicate. Mirrors regenerated via sync + OpenClaw porter.
- **Verification**: widened predicate fires on 45/45 open meta-fix-tagged cards (zero false positives); old strict window predicate fails 37/45 — mismatch confirmed and resolved.
- **Audit**: PASS — no rubric configured; doc-contract alignment fix (predicate ratified to match the deck's real tagging convention).
- **Project impact**: refine-deck hygiene passes over the meta-fix tag are now mechanical without being destructive.
- **Tests**: 702 passed / 0 failed; `goc validate` exit 0; `sync_plugin_assets.py --check` and `port_skills_to_openclaw.py --check` green.

## Closure verification (2026-07-08T01:07:05Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-07-08 — Closure' present
