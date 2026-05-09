---
title: replace-pyyaml-with-vendored-parser
summary: "Replace the six `yaml.safe_load` sites in `goc/engine.py` with a hand-written ~200 LOC pure-stdlib YAML subset parser at `goc/_vendor/yaml_lite.py`. Round-trip parity with the existing `emit_frontmatter` is the primary contract; unsupported syntax errors with `<file>:<line>: <reason>`. Zero on-disk migration — every existing card stays bit-identical. First and smallest piece of the `drop-third-party-runtime-dependencies-from-goc` epic; ships independently as a low-risk proof-out before the click migration begins."
status: done
stage: null
contribution: medium
created: 2026-05-09
closed_at: 2026-05-09
human_gate: none
advances:
  - drop-third-party-runtime-dependencies-from-goc
advanced_by:
  - split-card-frontmatter-from-body
tags: [story, infra]
definition_of_done: |
  - [x] `goc/_vendor/yaml_lite.py` exists with a `safe_load(text: str) -> Any` entry point.
  - [x] All six `yaml.safe_load` sites in `goc/engine.py` switch to the vendored parser (see survey table in epic body).
  - [x] `pyyaml` is removed from `project.dependencies` in `pyproject.toml`.
  - [x] Round-trip parity: every existing card under `.game-of-cards/deck/` survives parse → emit → parse without a byte-level diff.
  - [x] `goc/schema.yaml`, `.game-of-cards/config.yaml`, and the legacy deck config all load identically to their PyYAML output.
  - [x] Unsupported YAML syntax (anchors, aliases, multi-doc, flow nesting beyond `[a, b]` / `{k: v}`, folded `>` scalars) errors with `<file>:<line>: <reason>` — never silently mis-parses.
  - [x] CI smoke matrix on Python 3.10–3.13 passes with `pyyaml` uninstalled (`pip install --no-deps`).
  - [x] Round-trip smoke test in CI walks the deck and asserts byte-equality.
worker: {who: "claude[bot]", where: main}
---

# replace-pyyaml-with-vendored-parser

Child of `drop-third-party-runtime-dependencies-from-goc`. Read
the epic body for the full survey, alternative analysis (TOML,
NestedText, existing pure-stdlib parsers), and the reasoning behind
choosing "vendor our own" over a format switch.

## Why this is the smallest piece

PyYAML usage in goc is **read-only** — `yaml.safe_dump` is never
called. Emission is already pure-Python (`emit_frontmatter` and
helpers, ~50 LOC). So the work is "write a parser whose acceptance
set is a superset of what `emit_frontmatter` produces" — not a
parser **and** an emitter.

The six call sites:

| Site | Purpose |
|---|---|
| `engine.py:87` | `.game-of-cards/config.yaml` preflight |
| `engine.py:140` | `parse_frontmatter` (per-card) |
| `engine.py:299` | `goc/schema.yaml` schema loader |
| `engine.py:341` | dependency-graph block parser |
| `engine.py:1750` | runtime config |
| `engine.py:1752` | legacy deck config |

## Acceptance set the parser must support

Driven by what `emit_frontmatter` (L201) and the engine-owned config
files actually emit:

- Top-level mapping with string keys.
- Scalar values: strings (plain, single-quoted, double-quoted with
  escapes), integers, dates (`YYYY-MM-DD`), `null`/`~`/empty.
- Block-style lists: `\n  - item\n  - item`.
- Inline-flow lists: `[a, b, c]`.
- Inline-flow maps: `{k: v, k2: v2}` (used by `worker:`).
- Block scalar literals: `|` and `|-` (preserve and strip trailing
  newlines respectively).
- `#` comments at end of line and on their own line.

Out of scope (errors with file+line):
- Anchors (`&foo`), aliases (`*foo`), tags (`!!str`).
- Multi-document streams (`---` separators inside one parse).
- Folded scalars (`>`, `>+`, `>-`).
- Flow-nesting (lists in lists in flow style).
- Tabs as indentation.

## Implementation notes

- Start by reading `emit_frontmatter` and writing a parser that
  round-trips its output before tackling any wider acceptance set.
  The existing deck is the primary test corpus.
- A line-oriented parser (track indent, dispatch by sigil) is
  enough — no full lexer/event-driven architecture needed.
- Vendor under `goc/_vendor/yaml_lite.py` so the namespace makes
  the "we own this" status obvious. Keep it under 250 LOC.
- The single public surface is `safe_load(text: str) -> Any`.
  Match PyYAML's return-type discipline (mapping → dict, list →
  list, etc.) so the call sites don't need rewriting beyond the
  import line.
- Add a smoke test that walks `.game-of-cards/deck/**/README.md`,
  parses with `yaml_lite.safe_load`, parses the same text with
  PyYAML in dev (or with the engine's own emitter as oracle), and
  asserts byte-equal round-trip via `emit_frontmatter`.
