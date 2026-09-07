## 2026-09-07 — closed

Two rules added to the citation-repair recipe, twelve corrupt cites
repaired by hand, and a guard that proves the recipe declines what it must
decline.

### The recipe

`goc/templates/skills/refine-deck/reference.md` § Citation anchor check
lost the sentence "A range (`file.py:120-140`) maps its endpoints
independently and is rewritten only when both resolve" and gained two
paragraphs in its place: the pair a repair is about to write must be
ordered and still narrow enough to be a block, and a range that ARRIVES
incoherent is earlier damage rather than drift, so it is reported and
never re-mapped. The residue table went from three decline reasons to
four (`incoherent range pair`). `SKILL.md` step 1 carries the same two
rules in short form — it stays in the core, not behind a pointer, for the
same reason the three earlier raises did: the defect IS a pass filling in
a rule the recipe never stated.

`tests/test_skill_body_size.py` raised the `refine-deck` cap 12_300 ->
12_500 with the rationale, following that file's convention.

### The twelve cites

Each re-derived by hand from its own card's prose; the recipe could not
recover any of them, because both endpoints anchored cleanly at unrelated
code.

| Card | README | Was | Now | Block |
|---|---|---|---|---|
| bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes | 25 | `engine.py:3920-3857` | `engine.py:3395-3399` | the `render_table` `-vv` `LIST_REL_FIELDS` raw-dump loop |
| closure-on-integration-check-only-runs-for-done-not-disproved-or-superseded | 28 | `goc/engine.py:5196-5120` | `goc/engine.py:5200-5206` | `_enforce_closure_on_integration_or_exit` docstring |
| goc-new-stamps-goc-worker-queue-filter-into-authored-worker-field | 3 | `engine.py:4020-3788` | `engine.py:4020-4023` | the `advances_wire` / `advanced_by_wire` distinct-dest remedy |
| goc-new-stamps-goc-worker-queue-filter-into-authored-worker-field | 16 | `engine.py:4020-3956` | `engine.py:4020-4023` | same |
| goc-new-stamps-goc-worker-queue-filter-into-authored-worker-field | 96 | `engine.py:4020-3956` | `engine.py:4020-4023` | same |
| goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards | 27 | `goc/engine.py:4611-7123` | `goc/engine.py:4614-4625` | `_apply_summary_rewrite` |
| goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards | 59 | `goc/engine.py:4561-7073` | `goc/engine.py:4614-4625` | same (comment label on the quoted snippet) |
| goc-status-active-preserves-prior-worker-who-on-reclaim | 51 | `goc/engine.py:5843-5733` | `goc/engine.py:5844-5850` | `_auto_populate_worker` docstring |
| goc-status-silently-drops-worker-overrides-on-non-active-transitions | 3 | `engine.py:5917-4014` | `engine.py:5920-5926` | the `--by` / `new_status != "superseded"` reject |
| goc-unadvance-with-self-target-leaves-card-in-half-edge-state | 28 | `goc/engine.py:6274-6176` | `goc/engine.py:6277-6290` | `_mutate_pair` |
| openclaw-plugin-cannot-show-the-deck-queue-through-tool-or-exec | 33 | `goc/engine.py:4166-4100` | `goc/engine.py:4169-4170` | `if args.command is None: _cmd_default(args)` |
| openclaw-plugin-manifest-config-options-do-not-behave-as-documented | 31 | `openclaw-plugin/index.ts:343-341` | `openclaw-plugin/index.ts:343-351` | `resolveDeckDir` |

Two sibling cites naming the SAME block as a repaired one were moved with
it, so no card was left contradicting itself: `bare-string-scalars...`
README:139 (`engine.py:3920-3924`, coherent but drifted, the body cite for
the DoD cite at README:25) and the `goc-quality-pass...` label at
README:59, already counted above. Everything else drifted-but-coherent was
left for a hygiene pass; this card's scope is the incoherent set.

### The guard

`tests/test_refine_deck_citation_anchor.py` — the file that already holds
the two earlier per-shape gaps in this recipe — gained:

- `documented_range_coherence(prose)`, which classifies the shipped prose
  as `COHERENCE_GUARDED` or `PAIR_UNCHECKED`, plus a control that feeds it
  the exact sentence this card replaced and asserts `PAIR_UNCHECKED`, so
  the classifier is shown returning the failing verdict and not only the
  passing one.
- `RangeRepairTest`, a fixture reproducing the endpoint divergence: a
  block cited `6-8` whose line 8 holds an idiom that also sits four lines
  above it, so a four-line insert above the module relocates the START
  anchor while the END anchor still reads unchanged at its own number. The
  unguarded recipe writes `10-8`; the shipped recipe declines. A third
  case re-feeds the inverted `10-8` and asserts it is not re-mapped.

Confirmed red-then-green: reverting `SKILL.md` step 1 to the pre-fix
sentence turns three of these tests red; restoring it turns them green.

### reproduce.py

Now skips this card's own README, documented in the module docstring. The
compounding trace and the pre-fix transcript this card carries are dated
records of numbers past commits emitted — out of repair scope under the
recipe's own rule — so scanning them would fail the guard on its own
evidence, and rewriting them would cost the card its evidence. 747 cards
scanned, 0 findings, exit 0.

### Pre-fix census, for the record

```
scanned 748 cards
incoherent range cites: 12

  engine.py:3920-3857  (start past end)
    card    : bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes  (README:25)
    written : 9bad9881 2026-08-31 chore(deck): hygiene pass — 2026-08-31
  goc/engine.py:5196-5120  (start past end)
    card    : closure-on-integration-check-only-runs-for-done-not-disproved-or-superseded  (README:28)
    written : 9bad9881 2026-08-31 chore(deck): hygiene pass — 2026-08-31
  engine.py:4020-3788  (start past end)
    card    : goc-new-stamps-goc-worker-queue-filter-into-authored-worker-field  (README:3)
    written : 9bad9881 2026-08-31 chore(deck): hygiene pass — 2026-08-31
  engine.py:4020-3956  (start past end)
    card    : goc-new-stamps-goc-worker-queue-filter-into-authored-worker-field  (README:16)
    written : 9bad9881 2026-08-31 chore(deck): hygiene pass — 2026-08-31
  engine.py:4020-3956  (start past end)
    card    : goc-new-stamps-goc-worker-queue-filter-into-authored-worker-field  (README:96)
    written : 9bad9881 2026-08-31 chore(deck): hygiene pass — 2026-08-31
  goc/engine.py:4611-7123  (span 2512 lines)
    card    : goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards  (README:27)
    written : 9bad9881 2026-08-31 chore(deck): hygiene pass — 2026-08-31
  goc/engine.py:4561-7073  (span 2512 lines)
    card    : goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards  (README:59)
    written : e8449764 2026-08-24 chore(deck): hygiene pass — 2026-08-24
  goc/engine.py:5843-5733  (start past end)
    card    : goc-status-active-preserves-prior-worker-who-on-reclaim  (README:51)
    written : 9bad9881 2026-08-31 chore(deck): hygiene pass — 2026-08-31
  engine.py:5917-4014  (start past end)
    card    : goc-status-silently-drops-worker-overrides-on-non-active-transitions  (README:3)
    written : 9bad9881 2026-08-31 chore(deck): hygiene pass — 2026-08-31
  goc/engine.py:6274-6176  (start past end)
    card    : goc-unadvance-with-self-target-leaves-card-in-half-edge-state  (README:28)
    written : 9bad9881 2026-08-31 chore(deck): hygiene pass — 2026-08-31
  goc/engine.py:4166-4100  (start past end)
    card    : openclaw-plugin-cannot-show-the-deck-queue-through-tool-or-exec  (README:33)
    written : 9bad9881 2026-08-31 chore(deck): hygiene pass — 2026-08-31
  openclaw-plugin/index.ts:343-341  (start past end)
    card    : openclaw-plugin-manifest-config-options-do-not-behave-as-documented  (README:31)
    written : e8449764 2026-08-24 chore(deck): hygiene pass — 2026-08-24
```

### Left open

The convention-level question — whether a bare line number should address
code at all — stays parked on
[file-line-citations-drift-again-within-days-of-every-repair-pass](../file-line-citations-drift-again-within-days-of-every-repair-pass/).
This card holds only the narrower invariant, which any convention has to
keep: a range must bound something.

## 2026-09-07T04:52:00Z — Closure

- **What changed**: `goc/templates/skills/refine-deck/reference.md:157-186` +
  `SKILL.md:123-130` — a range repair now checks the PAIR it is about to
  write (ordered, span still a block) and refuses to re-map a range that
  arrives incoherent; both refusals report as a fourth decline reason.
  Twelve corrupt cites across eight cards repaired by hand.
- **Verification**: `reproduce.py` 747 cards scanned, 0 incoherent range
  cites, exit 0 (was 12, exit 1). Reverting `SKILL.md` step 1 to the
  pre-fix sentence turns 3 of the new tests red; restoring it turns them
  green.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: 1095 passed / 0 failed / 0 xfailed (16 in
  `tests/test_refine_deck_citation_anchor.py`, up from 8).
- **Bundled with**: n/a

## Closure verification (2026-09-07T04:44:31Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 7/7 ticked
- [x] log-md-closure-entry — '## 2026-09-07 — Closure' present
