# Log — finish-card-records-implicit-dod-attestation

## 2026-05-03 — Filed

Spawned by user discussion on DoD layering (May 3, 2026). User framing:
"Is Game of Cards currently understanding DoD as a list always fully
executable? I think that's the wrong concept. The DoD can be advanced
step by step. And the list of DoDs in the front matter is incomplete
(GoC and a project itself has implicit DoDs as well). Here: all
blocked_by cards are closed. Should we make that explicit in each
frontmatter? Maybe at time of closing add them so we see that the
closer has 'checked against implicit DoDs'?"

Resolution: don't bloat frontmatter — instead, finish-card appends
a "Closure verification" attestation block to log.md at closure time,
covering layer-2 (project, from CLAUDE.md) and layer-3 (GoC universal)
implicit DoDs alongside the visible layer-1 (frontmatter) checklist.

Companion card filed for the orthogonal move:
[`rename-blocks-to-advances-and-design-value-sort`](../rename-blocks-to-advances-and-design-value-sort/).

## 2026-05-03: decision recorded

Proceed now in full; on automated-check failure (pytest/ruff/etc.) finish-card blocks closure outright — closure-audit gap is the highest-leverage GoC improvement and ~1 day of skill+config work; closure-rigor is the contract and waivers normalise drift. Gate session → none.

## 2026-05-03 — Closure

Closure-attestation contract shipped via commit 8b84d635 +
this closure:

- **Layer-1 (card-specific)** — frontmatter `definition_of_done` checklist
  already in place since v1; `deck.py done` enforces 100%-ticked.
- **Layer-2 (project-wide)** — `.claude/deck-config.yaml`
  `layer_2_project_dod` extracts five named checks from CLAUDE.md prose:
  `tests-pass` (pytest -x), `ruff-check`, `ruff-format`, `mindset-audit`
  (manual), `no-debug-code` (manual), `doc-consistency-checker` (agent).
- **Layer-3 (GoC-wide)** — `.claude/deck-config.yaml` `layer_3_goc_dod`
  defines four universal checks: `deck-validate` (automated),
  `advanced-by-closed`, `dod-100-percent`, `log-md-closure-entry`
  (all derived from card state).
- **Runner** — `deck.py attest <title>` walks both layers, prompts
  manual/agent checks interactively, and appends a
  `## Closure verification (YYYY-MM-DD)` block to the card's log.md.
  Per the May 3 decision, automated/derived failures block closure;
  no silent waivers (`--skip` recorded explicitly as `[~] SKIPPED`).
- **Skill alignment** — `Skill(finish-card)` Step 5 invokes attest;
  `Skill(prepare-commit)` references the attestation by date in
  the generated commit message.
- **Schema documentation** — `Skill(card-schema)` "Definition of Done
  — three implicit layers" section (lines 185–209) names the layers,
  their storage, visibility-at-closure, and which command records each.

**Pilot closure (DoD item 6):** the closure of `auto-validate-card-titles-summaries-and-dods`
in this same commit IS the first real-world finish-card closure
under the new attestation contract. The block it carries reads
useful, not boilerplate (the layer-2 checks are concrete and the
manual prompts captured the bio-faithfulness audit + no-debug
attestation in plain prose). This closure is the second.

**Backfill (DoD item 7):** confirmed forward-only. Past closures keep
their existing log.md format; only finish-card invocations from
2026-05-03 onward carry the attestation block.

**DoD: 7/7 ticked.**

## Closure verification (2026-05-03)

### Layer-2 (project DoD)

- [x] tests-pass — 724 passed, 3 xfailed in 76.05s (0:01:16)
- [x] ruff-check — All checks passed!
- [x] ruff-format — 594 files already formatted
- [x] mindset-audit — no axiom touched, mechanical tooling work (extends deck.py with Sonnet runner + interactive triage; no framework primitive change)
- [x] no-debug-code — OK
- [x] doc-consistency-checker — N/A — no framework or topic doc edits — only deck skill prose, deck-config.yaml, and deck.py changes

### Layer-3 (GoC DoD)

- [x] deck-validate — OK
- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 7/7 ticked
- [x] log-md-closure-entry — '## 2026-05-03 — Closure' present
