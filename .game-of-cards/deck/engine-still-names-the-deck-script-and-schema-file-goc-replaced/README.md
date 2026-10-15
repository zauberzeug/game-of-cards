---
title: engine-still-names-the-deck-script-and-schema-file-goc-replaced
summary: "goc/engine.py named the two files the move to a package retired. The prompt goc quality-pass --llm sends a model attributed its title antipatterns to the set deck.py new rejects, and the frontmatter-parser banner said the parser read SCHEMA.md. The prompt now says goc new rejects them, and the banner names card READMEs, the only thing parse_frontmatter reads. The retired-name sweep in tests/test_skill_template_deck_links.py, which stopped at the template trees, now covers the whole goc/ package and is fed both pre-fix lines verbatim."
status: done
stage: null
contribution: low
created: "2026-10-14T04:44:48Z"
closed_at: "2026-10-15T04:50:12Z"
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — neither the prompt `_build_quality_prompt` builds nor any file under `goc/` names `deck.py` or `SCHEMA.md`
  - [x] MECHANICAL: `_QUALITY_PROMPT_TEMPLATE` attributes the listed title antipatterns to `goc new`; the frontmatter-parser banner comment in `goc/engine.py` names what the parser reads (card READMEs) instead of `SCHEMA.md`
  - [x] TDD: `test_no_shipped_template_names_a_retired_deck_file` in `tests/test_skill_template_deck_links.py` also sweeps the `goc/` package outside its template trees, and `retired_files` is fed both pre-fix engine lines verbatim to prove it fires
  - [x] MECHANICAL: plugin engine mirrors re-synced (`python scripts/sync_plugin_assets.py --check` green)
worker: {who: "claude[bot]", where: main}
---

# The engine still names the deck script and schema file goc replaced

## What was broken

Two `goc/engine.py` lines described goc as it was before it became a package,
when a vendored `deck.py` script and a `SCHEMA.md` file sat inside the deck
directory. Byte-identical copies shipped in `claude-plugin/goc/engine.py`,
`codex-plugin/goc/engine.py` and `openclaw-plugin/goc/engine.py`.

- Inside `_QUALITY_PROMPT_TEMPLATE`, the prompt `goc quality-pass --llm` sends
  to the model:
  ```
     - Bad: "pong-late-hr-stuck-below-50-after-bug-140-path-2"
       (engineer's-jargon: rN refs, path-N, bug-N, math symbols, _md_/_py_,
       camelCase tokens — same antipattern set as deck.py `new` rejects)
  ```
  No `deck.py` exists anywhere a consumer can reach. The verb that rejects
  those antipatterns is `goc new`, which runs `TITLE_ANTIPATTERNS`
  (`goc/engine.py:6395`) and exits 2 on a hit unless `--allow-jargon` is
  passed. Every item the prompt lists has a row there: rN, path-N, bug-N,
  `_md_`/`_py_`, camelCase, and math symbols.
- The banner over `FRONTMATTER_RE` and `parse_frontmatter`:
  ```python
  # ────────────────────────────────────────────────────────────────────────────
  # Frontmatter parser — used for SCHEMA.md AND every card's README.md
  ```
  `parse_frontmatter` reads no `SCHEMA.md`. The schema is `goc/schema.yaml`,
  and `load_schema` (`goc/engine.py:768-772`) parses it whole with
  `yaml.safe_load` from the vendored yaml_lite; it never passes through the
  frontmatter parser.

[shipped-skills-still-point-at-the-deck-script-and-schema-file-goc-replaced](../shipped-skills-still-point-at-the-deck-script-and-schema-file-goc-replaced/)
removed the same two names from the shipped skill templates and added a
`retired_files` sweep to `tests/test_skill_template_deck_links.py`. That sweep
covered the six skill trees and the four project-state template trees, and
neither line sat in one, so both stayed.

## Why it matters

The prompt line reached a model on every run. `goc quality-pass --llm` →
`_build_quality_prompt` → `_run_sonnet_quality_pass` sends the template to
`claude --model sonnet -p` in any repo that runs the layer-2 pass. The model
was told the jargon list is whatever a `deck.py` rejects, and that script is
nowhere in the repo it audits. The rewrite reasons it returns are printed to
the user and could repeat the name. The harm was small, since the prompt
spells the list out in full and does not ask the model to open the file. It
is still the executed-rather-than-read surface that
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/)
tracks. The banner comment misled contributors only: it said the frontmatter
parser carries the schema, so a reader changing the schema format would look
at the wrong function.

## What changed

- `goc/engine.py:4792`: the prompt closes the jargon list with "all rejected
  by `goc new`". That is also more exact than "same antipattern set", since
  `TITLE_ANTIPATTERNS` rejects phase-N and underscores too, which the prompt
  does not list.
- `goc/engine.py:202`: the banner reads "Frontmatter parser — used for every
  card's README.md". Every caller reads a card README: `load_card`,
  `validate_deck_directories`, the quality-pass summary and DoD rewrites,
  `_git_claim_push_with_retry` (the remote branch's copy, via `git show`), the
  edge-list editors, `wait`, `decide`, `show` and `migrate-list-style`, plus
  `scripts/check_card_language.py` outside the package.
- `tests/test_skill_template_deck_links.py`: `sweep` takes a `trees` argument,
  and the new `swept_files` reads a file that sits under two swept trees once.
  `test_no_shipped_template_names_a_retired_deck_file` sweeps
  `RETIRED_FILE_TREES`, the ten template trees plus the whole `goc/` package,
  so the engine, `install.py`, `cli.py`, the vendored YAML parser and
  `schema.yaml` are covered too. The other two predicates keep the template
  scope. `HISTORICAL_RETIRED_FILE_OFFENDERS` gains both pre-fix engine lines
  verbatim, the precision test gains both fixed lines, and
  `test_the_trees_are_actually_being_swept` asserts that the package sweep
  reaches `goc/engine.py` and reads a nested template file once.
- The three plugin engine mirrors re-synced.

## Evidence

`uv run python .game-of-cards/deck/engine-still-names-the-deck-script-and-schema-file-goc-replaced/reproduce.py`
builds the quality-pass prompt through the engine's own `_build_quality_prompt`
and sweeps every text file under `goc/`. Before the fix (2026-10-14), exit 1:

```
quality-pass prompt lines naming a retired file: 1
  - camelCase tokens — same antipattern set as deck.py `new` rejects)
goc/ package lines naming a retired file: 2
  - goc/engine.py:201: # Frontmatter parser — used for SCHEMA.md AND every card's README.md
  - goc/engine.py:4791: camelCase tokens — same antipattern set as deck.py `new` rejects)
```

After the fix (2026-10-15), exit 0:

```
quality-pass prompt lines naming a retired file: 0
goc/ package lines naming a retired file: 0

Neither the quality-pass prompt nor the goc/ package names deck.py or SCHEMA.md.
```

The widened guard fires on the pre-fix package. Pointing the test module's
`ROOT` at a `git archive` of claim commit `c23d5985`,
`sweep((retired_files,), RETIRED_FILE_TREES)` returns
`[('goc/engine.py', 202, 'SCHEMA.md'), ('goc/engine.py', 4792, 'deck.py')]`,
and the old template-only scope returns `[]` there. On the fix the module
passes 15/15 and the full suite 1319/1319.

## Artifacts

- reproduce.py
