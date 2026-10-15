---
title: engine-still-names-the-deck-script-and-schema-file-goc-replaced
summary: "goc/engine.py still names the two files the move to a package retired. The quality-pass prompt sent to the model says its title antipatterns are the set that deck.py new rejects, so the model is briefed on a script no install has; the frontmatter-parser banner comment says the parser reads SCHEMA.md, while load_schema reads schema.yaml through yaml_lite. The retired-name sweep added by shipped-skills-still-point-at-the-deck-script-and-schema-file-goc-replaced stops at the template trees, so nothing catches either line."
status: active
stage: null
contribution: low
created: "2026-10-14T04:44:48Z"
closed_at: null
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — neither the prompt `_build_quality_prompt` builds nor any file under `goc/` names `deck.py` or `SCHEMA.md`
  - [ ] MECHANICAL: `_QUALITY_PROMPT_TEMPLATE` attributes the listed title antipatterns to `goc new`; the frontmatter-parser banner comment in `goc/engine.py` names what the parser reads (card READMEs) instead of `SCHEMA.md`
  - [ ] TDD: `test_no_shipped_template_names_a_retired_deck_file` in `tests/test_skill_template_deck_links.py` also sweeps the `goc/` package outside its template trees, and `retired_files` is fed both pre-fix engine lines verbatim to prove it fires
  - [ ] MECHANICAL: plugin engine mirrors re-synced (`python scripts/sync_plugin_assets.py --check` green)
worker: {who: "claude[bot]", where: main}
---

# The engine still names the deck script and schema file goc replaced

## Location

- `goc/engine.py:4789-4791`, inside `_QUALITY_PROMPT_TEMPLATE`, the prompt
  `goc quality-pass --llm` sends to the model:
  ```
     - Bad: "pong-late-hr-stuck-below-50-after-bug-140-path-2"
       (engineer's-jargon: rN refs, path-N, bug-N, math symbols, _md_/_py_,
       camelCase tokens — same antipattern set as deck.py `new` rejects)
  ```
- `goc/engine.py:200-201`, the banner over `FRONTMATTER_RE` and
  `parse_frontmatter`:
  ```python
  # ────────────────────────────────────────────────────────────────────────────
  # Frontmatter parser — used for SCHEMA.md AND every card's README.md
  ```
- Byte-identical copies ship in `claude-plugin/goc/engine.py`,
  `codex-plugin/goc/engine.py` and `openclaw-plugin/goc/engine.py`.

## What's broken

Both lines describe goc as it was before it became a package, when a vendored
`deck.py` script and a `SCHEMA.md` file sat inside the deck directory.

- No `deck.py` exists anywhere a consumer can reach. The verb that rejects
  those antipatterns is `goc new`, which runs `TITLE_ANTIPATTERNS`
  (`goc/engine.py:6394`). Every item the prompt lists has a row there: rN, path-N,
  bug-N, `_md_`/`_py_`, camelCase, and math symbols.
- `parse_frontmatter` reads no `SCHEMA.md`. The schema is
  `goc/schema.yaml`, and `load_schema` (`goc/engine.py:767-771`) parses it
  whole with `yaml.safe_load` from the vendored yaml_lite; it never passes
  through the frontmatter parser:
  ```python
  def load_schema() -> Schema:
      if not SCHEMA_FILE.exists():
          ...
      fm = yaml.safe_load(SCHEMA_FILE.read_text()) or {}
  ```

[shipped-skills-still-point-at-the-deck-script-and-schema-file-goc-replaced](../shipped-skills-still-point-at-the-deck-script-and-schema-file-goc-replaced/)
removed the same two names from the shipped skill templates and added a
`retired_files` sweep to `tests/test_skill_template_deck_links.py`. The sweep
covers the six skill trees and the four project-state template trees, and
neither of these lines sits in one, so both stayed.

## Empirical evidence

`uv run python .game-of-cards/deck/engine-still-names-the-deck-script-and-schema-file-goc-replaced/reproduce.py`
(2026-10-14) builds the quality-pass prompt through the engine's own
`_build_quality_prompt` and sweeps every text file under `goc/`:

```
quality-pass prompt lines naming a retired file: 1
  - camelCase tokens — same antipattern set as deck.py `new` rejects)
goc/ package lines naming a retired file: 2
  - goc/engine.py:201: # Frontmatter parser — used for SCHEMA.md AND every card's README.md
  - goc/engine.py:4791: camelCase tokens — same antipattern set as deck.py `new` rejects)
```

Exit 1. These two are the only lines left in the package naming either file.

## Why it matters

The prompt line reaches a model on every run. `goc quality-pass --llm` →
`_build_quality_prompt` → `_run_sonnet_quality_pass` sends the template to
`claude --model sonnet -p` in any repo that runs the layer-2 pass. The model is
told the jargon list is whatever a `deck.py` rejects, and that script is
nowhere in the repo it is auditing. The rewrite reasons it returns are printed
to the user and can repeat the name. The harm is small, since the prompt
spells the list out in full and does not ask the model to open the file. It
is still the executed-rather-than-read surface that
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/)
tracks. The banner comment misleads contributors only: it says the frontmatter
parser carries the schema, so a reader changing the schema format looks at
the wrong function.

## Fix

- `goc/engine.py:4791`: replace "same antipattern set as deck.py `new`
  rejects" with "all rejected by `goc new`". Every listed item is rejected
  there. The current "same set" overstates it slightly, because
  `TITLE_ANTIPATTERNS` also rejects phase-N and underscores, which the prompt
  does not list.
- `goc/engine.py:201`: "Frontmatter parser — used for every card's README.md".
  Before changing it, check that the `parse_frontmatter` callers all read
  card READMEs.
- Widen the sweep in `tests/test_skill_template_deck_links.py`, not a new file:
  `test_no_shipped_template_names_a_retired_deck_file` also walks `goc/`
  outside its template trees (or the whole package, deduplicated against
  `SWEPT_TREES`). Feed `retired_files` the two pre-fix lines verbatim. The plugin
  `goc/` copies are held byte-identical by `sync_plugin_assets.py --check`, so
  sweeping the source package covers them.
- Re-sync the mirrors.

## Artifacts

- reproduce.py
