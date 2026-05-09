---
title: drop-third-party-runtime-dependencies-from-goc
summary: "Epic: make the goc runtime pure-python by removing `click` and `pyyaml` from `project.dependencies`, so `claude-plugin/bin/goc` can invoke the bundled engine with system `python3` directly (no `uv`, no venv). Decided 2026-05-09: split into three children — `replace-pyyaml-with-vendored-parser` (smallest, ships first), `replace-click-with-argparse` (mechanical, ~245 call sites), `plugin-wrapper-drops-uv` (the prize, sequenced last). Closes when all three children land and the integrated outcome is verified end-to-end."
status: open
stage: null
contribution: high
created: 2026-05-09
closed_at: null
human_gate: none
advances: []
advanced_by:
  - replace-pyyaml-with-vendored-parser
  - replace-click-with-argparse
  - plugin-wrapper-drops-uv
tags: [epic, story, infra]
definition_of_done: |
  - [ ] `project.dependencies` in `pyproject.toml` is empty (no third-party runtime packages).
  - [ ] `import goc.engine` and `goc <verb>` succeed in a venv whose only installed package is the goc wheel.
  - [ ] CI smoke matrix on Python 3.10–3.13 passes; `goc validate --quiet` exits zero against the repo's own deck.
  - [ ] Round-trip parity: every existing card under `.game-of-cards/deck/` survives parse → emit → parse without a byte-level diff.
  - [ ] Unsupported frontmatter syntax produces a clear error naming the file and line; never a silent mis-parse.
  - [ ] `claude-plugin/bin/goc` runs the bundled engine with `python3` directly — no `uv`, no venv materialization — on a host that has Python 3.10+ on PATH.
  - [ ] README / CHANGELOG note the dependency drop and the plugin's new `python3`-only runtime contract.
---

# drop-third-party-runtime-dependencies-from-goc

## Why

`goc` declares two runtime dependencies in `pyproject.toml`:
`click>=8.1` and `pyyaml>=6.0`. Dropping both unlocks a concrete
prize: the plugin wrapper at `claude-plugin/bin/goc` can stop
shelling out to `uv run --project ${PLUGIN_ROOT}` and just invoke
`python3` against the bundled engine. Python 3.10+ is broadly
distributed on developer machines and CI runners; `uv` is not.
Secondary wins: faster `pipx install`, smaller supply-chain
surface, simpler vendoring story for future embeds.

## Click usage — survey corrects an earlier assumption

A quick grep settles whether click is actually doing color work
in this codebase:

| API | Calls (engine + install + cli) |
|---|---|
| `click.secho` / `click.style` | **0** |
| `click.echo` (no color) | 153 |
| `@click.command/group/option/argument/pass_context` | 75 |
| `click.confirm` | 3 |
| `click.BadParameter` / `UsageError` / `ClickException` / `Abort` | 11 |
| `click.Choice` | 7 |

Color is already pure-stdlib. `engine.py:929-941` defines ANSI
escape constants; `_color_enabled` (L945) honors `NO_COLOR` and
TTY-detection. Dropping click puts zero color rendering at risk.

Click is purely doing what `argparse` does, just with a
decorator-based API. The migration is mechanical: `@click.option`
→ `parser.add_argument`, `click.Choice` → `choices=[...]`,
`click.echo` → `print`, `click.confirm` → small TTY-aware helper
that auto-declines on non-interactive stdin (matching click's
behavior so CI flows don't hang). Volume is in the ~245 call sites,
not in design.

## PyYAML replacement — three angles, with a leader

PyYAML usage is **read-only**. Six `yaml.safe_load` sites in
`goc/engine.py`:

| Site | Purpose |
|---|---|
| L87 | `.game-of-cards/config.yaml` preflight |
| L140 | `parse_frontmatter` (per-card) |
| L299 | `goc/schema.yaml` schema loader |
| L341 | dependency-graph block parser |
| L1750 | runtime config |
| L1752 | legacy deck config |

Emission is already pure-Python (`emit_frontmatter` and helpers,
~50 LOC). `yaml.safe_dump` is never called.

External research on stdlib-only alternatives (2026-05):

### A. Stay with YAML, vendor an existing pure-stdlib parser

- **`strictyaml`**: depends on `python-dateutil` and ruamel internals. Not stdlib-only.
- **`poyo`** (MIT, ~700 LOC, unmaintained since 2019): supports `>` block scalar but **not** `|` literal scalar and **not** flow-style `[a, b]`. Wouldn't round-trip our shape. Dead end.
- **`pyyaml-pure`** (Jan 2026, single-author, MIT): brand new, unproven — track but don't depend.

**Verdict: no mature vendorable pure-stdlib YAML parser exists today.**

### B. Switch format

- **TOML via `tomllib`**: stdlib for *read* on Python 3.11+ only. Currently we support 3.10. Switching either drops 3.10 or pulls in third-party `tomli` for the fallback (defeats the goal). Stdlib has no TOML *writer* — `tomli-w` (third-party, zero-dep, MIT) or hand-rolled. Plus every existing card on disk migrates `---`-fenced YAML to `+++`-fenced TOML (breaking change for consumer repos). GitHub renders `---` frontmatter as hidden metadata; `+++` frontmatter shows up as a raw code block — mild aesthetic regression.
- **JSON**: stdlib both ways. Ugly for hand-edit (no comments, mandatory quotes, no native multiline). Loses the readability the cards were designed around.
- **`configparser` (INI)**: stdlib but flat — can't model `tags: [a, b]` or `worker: {who, where}` cleanly.
- **NestedText** (`py-nestedtext` fork is MIT, zero-dep, vendorable): strings-only spec means the engine needs a coercion layer for ints/dates/null. Possible but adds friction.

**Verdict: TOML is the only credible format switch and its costs are real (3.11+ floor or third-party fallback, full corpus migration, breaking change for consumer repos).**

### C. Roll our own — vendor a ~200 LOC parser

The engine already emits a tightly constrained YAML subset by
hand: top-level dict, scalar values, inline-flow lists, block-style
lists, one block scalar (`|`), one inline-flow map. A line-oriented
parser that round-trips that emitter's output is roughly **150–250
LOC** with no anchors, no aliases, no multi-doc, no flow nesting,
no tags. The emitter *is* the spec the parser must satisfy.

Zero migration cost for consumer repos: every existing card stays
bit-identical on disk. The strictness contract is honest: "we
accept what `emit_frontmatter` produces, plus a documented set of
hand-edit conveniences (comments, single-line block scalars,
common quoting). Anything outside that errors with file + line."

**Verdict: vendoring a `goc/_vendor/yaml_lite.py` is the pragmatic
leader — preserves the on-disk format, zero consumer-side
migration, smallest reasoning surface.**

## Decisions (all resolved 2026-05-09)

All four open questions are answered. The epic now exists only to
hold the integrated end-state DoD; the actual work lives in the
children.

1. ✅ **Plugin wrapper end-state**: drop `uv` outright. `python3`
   is the runtime contract. No fallback. Captured by
   `plugin-wrapper-drops-uv`.

2. ✅ **Click is not blocking color**: zero `secho`/`style` calls;
   `engine.py:929-941` already owns its own ANSI escapes. The
   argparse swap puts no color rendering at risk. Captured by
   `replace-click-with-argparse`.

3. ✅ **PyYAML replacement path**: vendor our own ~200 LOC parser
   at `goc/_vendor/yaml_lite.py`. The full reasoning and the
   survey of alternatives (existing pure-stdlib parsers, format
   switch to TOML / NestedText / JSON / INI) lives in the
   "PyYAML replacement — three angles, with a leader" section
   above. The decisive factor: a format switch would force every
   consumer repo's existing cards through a `---` → `+++`
   migration, while a vendored parser keeps every card
   bit-identical on disk. Captured by
   `replace-pyyaml-with-vendored-parser`.

4. ✅ **One umbrella PR vs split**: split. PyYAML ships first as
   the low-risk proof-out of the vendoring approach; click
   follows; wrapper-drops-uv ships last after the engine is
   genuinely pure-stdlib. Three children created and wired via
   `advances` / `advanced_by`.

## Children

| Card | Contribution | Sequencing |
|---|---|---|
| `replace-pyyaml-with-vendored-parser` | medium | First — smallest piece, well-bounded |
| `replace-click-with-argparse` | high | Second — mechanical churn across ~245 call sites |
| `plugin-wrapper-drops-uv` | low | Last — blocked until both prerequisites close |

This epic stays open while the children land. Close it once the
integrated DoD (above) is verified end-to-end on a clean Python
3.10–3.13 install.

## Notes for the implementer

- Start with PyYAML. Read `emit_frontmatter` (L201) and write a
  parser that round-trips its output before tackling any wider
  acceptance set. Existing cards are the test corpus.
- Click's `Choice` is the only validator that has no one-line
  argparse equivalent — model it as `choices=[...]` plus a custom
  `ArgumentTypeError`.
- `click.confirm` in `goc upgrade` and the kickoff path must
  auto-decline on non-tty stdin, or interactive flows hang in CI.
- Add a CI job that installs the wheel into a clean venv with
  `pip install --no-deps` and exercises the matrix to prove the
  dep drop. Without that job the regression is untested.
- The Claude Code plugin currently ships a vendored `goc/`
  package under `claude-plugin/goc/` and a `bin/goc` wrapper that
  uses `uv run --project ${PLUGIN_ROOT}`. Once the engine is
  pure-stdlib, the wrapper becomes a one-liner that execs
  `python3 -m goc.cli "$@"` against the bundled package — no
  `.venv/`, no `uv`, no first-call latency.

## Decision

*Resolved 2026-05-09:* Vendor a ~200 LOC pure-stdlib YAML subset parser at goc/_vendor/yaml_lite.py; split into three child cards; replace click with argparse; plugin wrapper drops uv outright (python3-only, no fallback).

*Reasoning:* Vendoring our own parser preserves the on-disk YAML format for every consumer card (zero migration), keeps the 3.10 floor, and avoids the GitHub frontmatter rendering regression that TOML's +++ fence would cause. Splitting lets the smallest piece (pyyaml replacement, ~6 read sites, well-bounded shape) ship first as a low-risk proof-out before the click migration begins. Click is doing zero color work in this codebase (engine.py:929-941 already owns ANSI escapes), so argparse is a clean swap. python3 is broadly distributed; uv is not — dropping it is the prize this whole effort is aimed at.
