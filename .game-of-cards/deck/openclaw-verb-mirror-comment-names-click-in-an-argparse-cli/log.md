## 2026-07-26T08:19:43Z — Closure

- **What changed**: `openclaw-plugin/index.ts:44-47` — the `GOC_VERBS` mirror
  comment now names argparse (not click) and points at `_build_parser` in
  `goc/engine.py` instead of a non-existent argparse `commands` field, so both
  halves of the re-sync instruction resolve to real code. It also names the
  existing `OpenClawToolVerbSurfaceTest` drift guard, so an editor reading it
  knows the contract is machine-enforced.
- **Verification**: new guard
  `tests/test_guidance_accuracy.py::CliFrameworkPointerAccuracyTest` is red on
  the pre-fix file (`git show HEAD~1:openclaw-plugin/index.ts` matches
  `/click/i` at line 44) and green after. `npm ci && npm run build`
  regenerated the bundle: `dist/index.js` byte-identical (esbuild strips
  comments), `dist/index.js.map` updated (the sourcemap embeds the TS source in
  `sourcesContent`). `scripts/sync_plugin_assets.py --check` and
  `scripts/port_skills_to_openclaw.py --check` both OK.
- **Audit**: no rubric configured; mechanical fix.
  (`.game-of-cards/hooks/finish-card.md` is comment-only.)
- **Project impact**: n/a
- **Tests**: 772 passed / 0 failed / 0 xfailed
  (`uv run python -m unittest discover -s tests`).

### Side observation (not a defect on this card)

`npm ci` on a clean checkout rebuilt the committed `dist/` with **no diff**
before any source edit — evidence that the esbuild output is reproducible on
Node 22, which is the precondition the open card
`openclaw-plugin-compiled-dist-drifts-silently-from-its-typescript-entry`
needs for a CI drift guard. Recorded here rather than filed separately: that
card already owns the guard.

## Closure verification (2026-07-26T08:20:10Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-07-26 — Closure' present

## 2026-07-26T08:22:29Z — Post-close amendment: connected to its generalization

The Stop-hook pattern check flagged that this fix touches a repeating shape:
a claim restating tree state, unguarded, caught only after it had rotted, then
fixed with one more bespoke guard class in `tests/test_guidance_accuracy.py`.

Deduped against the deck first — a root card already exists
(`doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them`,
filed 2026-07-26 at `human_gate: decision`), so this connects the instance
instead of filing a second umbrella. Cross-reference, not an `advances` edge:
the root closes on its own deliverable, so it is a governing cluster rather than
an aggregation epic — the same call recorded on instances six and seven.

The root's instance table and counts move seven → eight instances, six → seven
guard classes. The substantive addition is not the tally: this instance's stale
claim was *the same* claim the second instance already guarded
(`AgentsArchitectureAccuracyTest`, 2026-05-27 — "goc's CLI is argparse, not
click"), asserted in a file that guard did not cover, and it survived two more
months. That is direct evidence that guards keyed to a *file* leave the same
falsehood live elsewhere; a guard keyed to the *claim* would have caught this
one on the day the first was written. Recorded against the root's Option B.
Forward-pointer added to this card's README. No decision recorded — that stays
the human's pick.
