## 2026-05-24T04:05:00Z: decision recorded

A1 (typed bidirectional superseded_by/supersedes field) + B1+B2 (compute_values warns AND goc validate errors on dangling advances targets) — Typed successor link matches ADR/issue-tracker convention and makes supersession machine-navigable; surfacing dangling edges both at compute time (warn) and in validate (error) makes edge rot impossible to miss, not merely visible.. Gate decision → none.

### Deliberation archived (options the decision resolved)

Archived here because `goc decide` replaces the README's `## Decision
required` section with the one-line `## Decision` block and does not yet
journal the deliberation itself (see open card
goc-decide-loses-deliberation-history-by-not-archiving-replaced-section).

**A. Successor-pointer modelling** — chosen: **A1**.

- A1 — new typed bidirectional field (`superseded_by` / `supersedes`),
  auto-symmetric like `advances`. Cleanest semantics, matches
  ADR/issue-tracker convention. Cost: schema + skill + emitter + validator
  + a new invariant. **(chosen)**
- A2 — reuse the `advances` graph, distinguished by status. No new field,
  but overloads value-flow semantics with succession and risks the GRPW
  value walk composing priority through supersession edges. (rejected)
- A3 — prose-only status quo. Zero build cost; rejected-by-default given
  the prior art. (rejected)

**B. `compute_values` behaviour on a dangling `advances` target** — chosen:
**B1 + B2** (both).

- B1 — keep walking but emit a warning (and surface in `goc validate`).
  **(chosen)**
- B2 — `goc validate` errors on any dangling `advances` target, forcing
  repair (consistent with half-edge treatment). **(chosen)**
- B3 — silent skip (status quo). This is the bug. (rejected)

Original card recommendation was A1 + B2; the decision additionally adopts
B1, so a dangling target both warns at compute time AND fails validation —
rot is impossible to miss at either entry point.

## 2026-05-24T05:45:00Z — Closure

- **What changed**:
  - `goc/schema.yaml` — `supersedes` and `superseded_by` added to `optional_fields`.
  - `goc/engine.py` — `LIST_REL_FIELDS`, `_BLOCK_LIST_FIELDS`, and `INVERSE_REL` extended to cover the supersedes pair; `compute_values` emits a stderr `WARN dangling advances edge` once per (src,dest) pair instead of silent-skipping; new `validate_supersedes_targets` plus a `superseded_by ⇒ status: superseded` invariant in `validate_card`; `goc status <title> superseded --by <successor>` writes both endpoints atomically via `_mutate_pair`; `_repair_edge_cycle_problem` skips non-advance edges via new `HalfEdge.is_advance` predicate; `render_json` exposes both new fields.
  - `goc/templates/skills/card-schema/SKILL.md` — new "Deck as scheduler vs deck as record" section + "Replacement axis (supersedes graph)" subsection replacing the old prose-only "Replacement" note.
  - `goc/templates/skills/advance-card/SKILL.md` — `* → superseded` row points at `--by`; "Superseded" subsection rewritten for the typed-link contract.
  - `goc/templates/skills/deck/SKILL.md` — lifecycle ASCII mentions the typed `superseded_by` link.
  - `goc/templates/AGENTS_GOC.md` + in-repo `AGENTS.md` — new "deck is both a scheduler and a record" paragraph.
  - Plugin mirrors (`claude-plugin/`, `codex-plugin/`, `openclaw-plugin/`) re-synced by `scripts/sync_plugin_assets.py`.
- **Verification**: `goc new` + `goc status <old> superseded --by <new>` smoke test in a scratch deck wrote `superseded_by: [new]` on the old card and `supersedes: [old]` on the new card with no validate errors. `goc validate --quiet` reports only the two pre-existing warnings (`STALE_BLOCKED` / `ORPHAN_BLOCKED`) unrelated to this card.
- **Audit**: PASS — no rubric configured in `.game-of-cards/hooks/finish-card.md`; the work aligns with the deck-as-scheduler-and-record dual-purpose principle this card itself adds to AGENTS.md.
- **Project impact**: n/a (no project status dashboard configured).
- **Tests**: `goc validate` clean; no pytest suite in repo (CI runs `goc validate` + build smoke).
- **Bundled with**: none.

## Closure verification (2026-05-24T05:35:49Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — all 1 done
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-24 — Closure' present
