## 2026-09-20T05:07:38Z — Closure

- **What changed**: `goc/engine.py` — added `_YAML_FLOW_HAZARDS` (YAML 1.2
  §7.4 `c-flow-indicator` + the flow-context key indicator), gave
  `_yaml_inline` a keyword-only `flow=` that widens the quote trigger by that
  set, passed `flow=True` from the list branch's own recursion and from
  `_emit_worker`'s mapping members, and made `_auto_populate_worker` delegate to
  `_emit_worker` instead of restating its flat-vs-mapping branch.
- **Verification**: reproduce.py section 2 sweeps printable ASCII and now
  reports `offending characters: []  (0 shapes)` (was `['?']  (3 shapes)`);
  section 3 drives the real `goc status … active` verb with `git user.name =
  who?knows` and all three readers — `goc validate`, `yaml_lite`, PyYAML —
  now agree (PyYAML previously raised `ParserError: while parsing a flow
  mapping`, losing the whole frontmatter block).
- **Audit**: no rubric configured; mechanical fix.
- **Third site found during verification**: `_emit_worker` alone did not fix the
  claim verb — `_auto_populate_worker` carried a hand copy of the flow-mapping
  construction, so section 3 of reproduce.py stayed REJECT after the shared
  emitter was correct. The regression suite now pins the *delegation*, not just
  today's bytes. The card's Location / What's broken / Fix sections were
  rewritten in place to name all three sites.
- **Scope check**: block context is provably untouched — a `?`-bearing
  `summary` and the flat `worker: who?knows` form stay bare, and no card in
  this deck carries a `?` in a tag or in `worker`, so the change rewrote
  nothing on re-emit.
- **Not retired by this fix**: the guard blind spot
  (`card-summary-with-broken-quoting-passes-both-guards-that-should-catch-it`)
  is structurally unable to see any `{`-opening value and stays open — which is
  why this had to be fixed at the producer. The emitter's type-resolution gap
  (`goc-writes-frontmatter-values-a-standard-yaml-reader-retypes-silently`) is
  the other half of the union and is untouched. The proposed factoring in
  `frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting`
  would not have caught this defect at all: `yaml_lite` accepts the value, so
  deriving the trigger from parser behaviour stays silent on it.
- **Tests**: 1170 passed / 0 failed (up 5); `goc validate` clean across 766
  cards; `scripts/sync_plugin_assets.py --check` and
  `scripts/port_skills_to_openclaw.py --check` both green.

## Closure verification (2026-09-20T05:07:41Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-09-20 — Closure' present
