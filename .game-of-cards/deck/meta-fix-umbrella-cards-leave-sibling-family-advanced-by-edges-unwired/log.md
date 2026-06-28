# Log

## 2026-06-21 — wired the remaining umbrella sibling-families

Re-read each umbrella body to separate its genuine instance roster (the
family the umbrella retires, "fixed one at a time as separate cards")
from peer-umbrella cross-references ("same shape, other surface"). Wired
`umbrella.advanced_by += sibling` for each family member; left every
peer-umbrella reference UNwired. All 25 sibling cards confirmed present
on disk first; `goc validate` clean after wiring (edge symmetry holds
by construction).

Rosters wired (peer cross-references excluded in each case):

- `frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting`
  — 8 `frontmatter-emitter-*` / `inline-emitter-*` instance cards.
  Excluded peer: `yaml-lite-quote-scanners…` ("same disease, different organ").
- `dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting`
  — 3 instances (`goc-upgrade-omits-pre-commit-hook-append-promised-by-dry-run`,
  `migrate-dry-run-omits-legacy-tree-removal-for-identical-only-trees`,
  `dry-run-plan-promises-pre-commit-append-that-real-install-skips-in-non-git-dir`).
  Excluded peers: `yaml-lite-quote-scanners…`, `frontmatter-emitter-quote-trigger…`,
  `openclaw-hook-predicates…`.
- `sync-mechanisms-reimplement-orphan-pruning-and-drift-detection-and-keep-drifting`
  — 4 instances (the two `sync-plugin-assets-*` and two `openclaw-skill-porter-*`
  orphan-pruning cards). Excluded peers: `dod-fence-mask…`,
  `yaml-lite-quote-scanners…`, `openclaw-hook-predicates…`.
- `session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting`
  — 8 `session-start-hook-*` / `deck-session-start-hook-*` instance cards.
  Excluded peers (listed under the body's "Sibling families" heading, NOT
  instances): `openclaw-hook-predicates…`, `goc-waiting-filter-drifts…`,
  `standup-impeded-filter-drifts…`, `yaml-lite-quote-scanners…`,
  `dod-fence-mask…`, `frontmatter-emitter-quote-trigger…`.
- `openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting`
  — confirmed it DOES have a closed-sibling roster (not purely forward-looking):
  2 named instance cards (`openclaw-session-start-frontmatter-reader-truncates-colon-bearing-values-via-typescript-split-limit`,
  `openclaw-session-start-hook-accepts-calendar-impossible-waiting-until`).
  The body's "instance 2" (bare-deferral backstop drift) is a test-cell
  docstring, not a card, so nothing to wire there. Excluded peers:
  `yaml-lite-quote-scanners…`, `dod-fence-mask…`.

Out of scope (carried over from this card's body, deliberately not wired):
the three `pattern-generalization-mutation-detector-*` cards share a root
cause but are peer instance bugs, not an umbrella+family — naming/filing an
umbrella for them is a judgment call left to a future pass. The post-wiring
zero-edge survey shows them as the only remaining zero-edge `meta-fix`
cards that resemble a cluster; every other zero-edge card is a single-site
defect with no prose roster, which is correct (not rot).

## 2026-06-21T00:00:00Z — Closure

- **What changed**: deck edges — wired `advanced_by` on 5 open `meta-fix` umbrella cards to their 25 genuine sibling-bug instances (frontmatter-emitter ×8, dry-run ×3, sync-mechanisms ×4, session-start ×8, openclaw-hook-predicates ×2), peer-umbrella cross-references left unwired.
- **Verification**: `goc validate` clean (exit 0); post-wiring zero-edge survey shows every remaining zero-edge `meta-fix` card is a single-site defect or the deliberately-out-of-scope `pattern-generalization-mutation-detector-*` trio — no umbrella with a prose roster carries zero edges.
- **Audit**: PASS — no principle touched, mechanical edge hygiene (record/scheduler-axis wiring; finish-card hook empty, no project rubric).
- **Project impact**: n/a
- **Tests**: n/a (no code change; deck-state only)

## Closure verification (2026-06-21T09:33:42Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-06-21 — Closure' present
