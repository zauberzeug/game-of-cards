---
title: hook-catalogue-cites-an-audit-skill-section-that-never-existed
summary: "The deck README's Workflow-hook stubs table routes hooks/audit-deck.md authors to a \"Phase 0 priming reads\" section, but the audit-deck skill has no Phase 0 — its phases start at 1 and the hook is injected under \"## Context\"; git log -S shows the string never appeared in any shipped skill, so the row has been wrong since the catalogue was written on 2026-05-04 and has since been copied into five files. The table calls itself \"the authority\" and is backed by a regression test, but tests/test_readme_hook_catalogue_parity.py pins only the first column (the hook-stub set) — the \"Loaded by\" and \"Workflow point\" columns are unguarded prose."
status: active
stage: null
contribution: medium
created: "2026-09-10T04:36:58Z"
closed_at: null
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation, test, meta-fix]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — every numbered anchor in the Workflow-hook stubs catalogue resolves to a heading in the skill the row names
  - [ ] TDD: `tests/test_readme_hook_catalogue_parity.py` gains a case that fails on a phantom anchor and one that fails when the `Loaded by` cell names a skill that does not `!cat` the stub
  - [ ] MECHANICAL: the `hooks/audit-deck.md` row names the section the hook is actually injected under, in `goc/templates/game_of_cards/README.md` and the hand-maintained dogfood copy `.game-of-cards/README.md`
  - [ ] MECHANICAL: the three auto-synced plugin mirrors of the template README carry the corrected row (`python scripts/sync_plugin_assets.py --check` clean)
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` pass
worker: {who: "claude[bot]", where: main}
---

# The hook catalogue cites an audit-skill section that never existed

## Location

`goc/templates/game_of_cards/README.md:54` — the `hooks/audit-deck.md` row of
the **Workflow-hook stubs** table:

```
| `hooks/audit-deck.md` | `audit-deck` | Phase 0 priming reads + Phase 1 probe recipe + Phase 2 hunter roster |
```

The same row is duplicated in four more files: the hand-maintained dogfood copy
`.game-of-cards/README.md`, and the three auto-synced plugin mirrors under
`claude-plugin/`, `codex-plugin/`, and `openclaw-plugin/goc/templates/game_of_cards/README.md`.

The guard that is supposed to hold this table honest is
`tests/test_readme_hook_catalogue_parity.py`.

## What's broken

The catalogue's third column tells a consumer **where** in the named skill their
`.game-of-cards/hooks/<stem>.md` content lands. For `audit-deck` it promises a
`Phase 0`. The shipped skill has no Phase 0 — its numbered sections start at 1,
and the hook is injected under `## Context`:

```
goc/templates/skills/audit-deck/SKILL.md
 15: ## Context (read but distrust — these are hypotheses, not ground truth)
 25: !`cat .game-of-cards/hooks/audit-deck.md 2>/dev/null || true`
 87: ## Phase 1 — Probe (run BEFORE static hunting)
108: ## Phase 2 — Hunt (parallel agents in a single message)
142: ## Phase 3 — File (one card per confirmed defect)
181: ## Phase 4 — Commit
```

This is not drift from a rename. `git log -S "Phase 0" --all` returns only the
commits that added or copied the catalogue itself (`46bfdfc5`, `d0e1d7c6`,
`9fa3a242`, `004756dd`, `26bfce00`, `ef918ec4`, `f1bd886c`) — never a skill-body
commit. At `46bfdfc5` (2026-05-04, the commit that first wrote the table) the
audit skill did not exist under any name in `goc/templates/skills/`. The anchor
has been fictional since the row was written, and every later payload copied it
forward.

The table states its own authority two sections up:

> This table is the authority — a regression test
> (`tests/test_readme_content_stub_catalogue_parity.py` in the goc repo) holds
> both it and the stub headers to the shipped skill tree.

But the hook table's own guard only pins column 1. From
`tests/test_readme_hook_catalogue_parity.py`:

```python
def _catalogued_hook_stems(readme: Path) -> set[str]:
    """Hook stems listed in the README's 'Workflow-hook stubs' table."""
```

Both of its tests (`test_template_readme_catalogues_every_shipped_hook`,
`test_dogfood_readme_catalogues_every_shipped_hook`) compare that stem set
against `goc/templates/game_of_cards/hooks/*.md`. Columns 2 (`Loaded by`) and 3
(`Workflow point`) are free prose no check reads — so a row can name the wrong
skill, or an anchor that does not exist, and CI stays green.

## Empirical evidence

`uv run python .game-of-cards/deck/hook-catalogue-cites-an-audit-skill-section-that-never-existed/reproduce.py`:

```
[FAIL] goc/templates/game_of_cards/README.md: row `hooks/audit-deck.md` promises 'Phase 0' in the `audit-deck` skill, but goc/templates/skills/audit-deck/SKILL.md has no such heading. Its headings are: When to invoke, Preflight, Context (read but distrust — these are hypotheses, not ground truth), Audit, Mindset (compressed), Phase 1 — Probe (run BEFORE static hunting), Phase 2 — Hunt (parallel agents in a single message), Phase 3 — File (one card per confirmed defect), Park-or-disprove unfollowed candidates (mandatory), Phase 4 — Commit, Output, Cross-references
[FAIL] .game-of-cards/README.md: row `hooks/audit-deck.md` promises 'Phase 0' in the `audit-deck` skill, but goc/templates/skills/audit-deck/SKILL.md has no such heading. Its headings are: ...

2 phantom anchor(s) in the Workflow-hook stubs catalogue.
```

Exit code 1. The check is precise rather than blanket — all six rows parse, and
every other numbered anchor resolves:

```
rows matched: 6
  create-card    -> create-card    anchors=[]
  decide-card    -> decide-card    anchors=[]
  finish-card    -> finish-card    anchors=['Step 2', 'Step 7']
  pull-card      -> pull-card      anchors=[]
  audit-deck     -> audit-deck     anchors=['Phase 0', 'Phase 1', 'Phase 2']
  refine-deck    -> refine-deck    anchors=[]
```

`finish-card`'s `Step 2` and `Step 7` both exist (`## Step 2 — project-specific
closure audit`, `## Step 7 — project-specific post-close action`), as do
`audit-deck`'s `Phase 1` and `Phase 2`. Only `Phase 0` is a phantom.

Column 2 is currently correct on all six rows — each named skill really does
`!cat` its stub — but nothing holds it that way.

## Why it matters

The catalogue is the documented index a consumer scans to discover where
project-local workflow hooks plug in; that is the exact reader
[deck-readme-hook-catalogue-omits-refine-deck-hook](../deck-readme-hook-catalogue-omits-refine-deck-hook/)
was filed to protect. An author writing an `audit-deck` probe recipe reads
"Phase 0 priming reads", opens the skill to find Phase 0, and finds phases
starting at 1 — so the one cell that answers "when does my content get read?"
answers wrong.

This is the same shape as
[five-of-six-content-stubs-promise-inlining-no-shipped-skill-performs](../five-of-six-content-stubs-promise-inlining-no-shipped-skill-performs/),
which repaired the *Content stubs* table and shipped
`tests/test_readme_content_stub_catalogue_parity.py` for it. The sibling
**Workflow-hook stubs** table was left with a stem-set-only guard, and the
phantom anchor survived that pass.

It is a nineteenth instance of
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/),
and specifically of that card's thirteenth-instance sub-shape: a false clause
inside an *already-guarded* surface, where the guard pins a neighbouring fact
and the reader assumes it covers the whole. The generalizable half is therefore
not the row edit but widening the guard to the columns a reader actually acts
on.

## Fix

1. `goc/templates/game_of_cards/README.md:54` — replace `Phase 0 priming reads`
   with the section the hook is really injected under:

   ```
   | `hooks/audit-deck.md` | `audit-deck` | Context priming reads + Phase 1 probe recipe + Phase 2 hunter roster |
   ```

   Apply the identical edit to the hand-maintained dogfood copy
   `.game-of-cards/README.md`; the three plugin mirrors regenerate from the
   template via the `sync-plugin-assets` pre-commit hook.

2. `tests/test_readme_hook_catalogue_parity.py` — extend from the stem set to
   the two columns a reader acts on, for both README copies:

   - **`Loaded by`**: the named skill's `SKILL.md` must contain
     `` !`cat .game-of-cards/hooks/<stem>.md `` — a row cannot point at a skill
     that does not load the stub.
   - **`Workflow point`**: every `Phase N` / `Step N` token in the cell must
     match a heading in that skill's `SKILL.md`.

   Free prose in column 3 stays free; only its numbered anchors — the part that
   makes a checkable promise — become load-bearing. That keeps the guard
   derived from the tree rather than restating the catalogue, so the next row
   added is covered without editing the test.
