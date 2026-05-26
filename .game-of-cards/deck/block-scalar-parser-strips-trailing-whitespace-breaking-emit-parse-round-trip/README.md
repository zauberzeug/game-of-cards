---
title: block-scalar-parser-strips-trailing-whitespace-breaking-emit-parse-round-trip
summary: "The frontmatter emitter writes `definition_of_done` (always) and multiline `summary` (when it contains a newline) as literal block scalars, preserving each content line verbatim including trailing whitespace. The vendored yaml-lite parser rstrips every block-scalar content line, so a value goc emits does NOT survive being parsed back by goc. Because goc rewrites frontmatter on most verbs, a DoD/summary line ending in whitespace (e.g. a Markdown hard-break) is silently mutated. This is a distinct, unfixed code path from the closed inline-scalar quoting fixes."
status: active
stage: null
contribution: medium
created: "2026-05-26T21:56:30Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — a block-scalar content line with trailing whitespace survives an emit->parse round-trip unchanged (modulo the single clip-mode trailing newline, which is correct).
  - [ ] TDD: the fix preserves trailing whitespace on every content line of a multi-line block scalar, not just the first.
  - [ ] MECHANICAL: fix lands in `goc/_vendor/yaml_lite.py` `_parse_block_scalar`; leading-indent stripping (`raw[block_indent:]`) is retained, only the trailing `.rstrip()` of meaningful content is reconsidered.
  - [ ] TDD: `uv run goc validate` passes on this repo's deck (no regression in existing block-scalar parsing — empty-block-scalar, three-way chomping, and indentation handling all still correct).
worker: {who: "claude[bot]", where: main}
---

# Block-scalar parser strips trailing whitespace, breaking the emit->parse round-trip

## Location

- Emit side: `goc/engine.py:225` — `_emit_block_field`. Content lines are
  written verbatim (indented by 2), trailing whitespace preserved:

  ```python
  def _emit_block_field(key: str, value: str, *, indicator: str) -> list[str]:
      text = (value or "").rstrip("\n")
      out = [f"{key}: {indicator}"]
      for ln in text.splitlines():
          out.append(f"  {ln}" if ln else "")   # <- `ln` keeps trailing spaces
      return out
  ```

  `definition_of_done` always uses this path (`engine.py:268`, indicator `|`);
  any multiline string field — e.g. `summary` with a newline — uses it too
  (`engine.py:278-279`, indicator `|-`).

- Parse side: `goc/_vendor/yaml_lite.py:173` — `_parse_block_scalar`:

  ```python
  if block_indent is None:
      block_indent = curr
  chunks.append(raw[block_indent:].rstrip())   # <- drops trailing whitespace
  ```

  Every content line is `.rstrip()`-ed, silently discarding trailing
  whitespace.

## What's broken

The emitter preserves trailing whitespace on block-scalar content lines; the
parser drops it. The emit->parse round-trip is therefore lossy for block
fields. This is the same "round-trip is not closed" family the team has been
draining (`frontmatter-emitter-does-not-quote-integer-null-or-case-variant-boolean-values`,
`frontmatter-emitter-does-not-quote-indicator-or-whitespace-padded-values`,
`frontmatter-emitter-does-not-quote-empty-string-scalar-that-parses-as-null`),
but those fixes all live in the **inline-scalar** path (`_yaml_inline` /
`_YAML_NEEDS_QUOTE`, whose trailing-whitespace trigger is `s != s.strip()` at
`engine.py:217`). Block scalars never pass through `_yaml_inline`, so none of
those fixes touch this case. It is a genuinely distinct, still-open code path.

The closed card `frontmatter-emitter-does-not-quote-indicator-or-whitespace-padded-values`
even states the principle this card extends: "A whitespace-padded value is
emitted bare and silently stripped on re-parse — silent data loss." That card
closed it for single-line inline values; block-scalar content lines remain
unfixed.

## Empirical evidence

`uv run python deck/<this-card>/reproduce.py`:

```
emitted frontmatter:
---
title: x
definition_of_done: |
  - [ ] item with hard break  
  - [ ] second item
---

orig DoD: '- [ ] item with hard break  \n- [ ] second item'
got  DoD: '- [ ] item with hard break\n- [ ] second item'

ROUND-TRIP PRESERVES TRAILING WHITESPACE: False

FAIL: emitter wrote the trailing two spaces but the parser stripped them.
The emit->parse round-trip is not closed for block-scalar content.
```

The two trailing spaces (a Markdown hard line break) present in the emitted
frontmatter are gone after `parse_frontmatter` reads them back.

## Why it matters

`goc` rewrites a card's frontmatter on most state-changing verbs (`status`,
`advance`, `unadvance`, `done`, `decide`, ...). Each rewrite is an
emit-from-memory after a parse-from-disk. A DoD or multiline summary line that
ends in whitespace — most realistically a Markdown hard-break (two trailing
spaces), but also any incidental trailing space introduced by a hand-edit — is
silently mutated the next time any verb touches the card. The change is
invisible to `goc validate` (it is well-formed YAML either way), so the drift
accrues unnoticed. The whole point of the recently-closed quoting family is to
guarantee that what goc writes, goc reads back identically; this path violates
that guarantee.

## Fix (do NOT apply — proposal only)

The trailing `.rstrip()` at `yaml_lite.py:173` over-normalizes. YAML literal
block scalars preserve trailing whitespace on content lines; only the
*leading* indentation is stripped (`raw[block_indent:]`). Drop the trailing
`.rstrip()` so content is `raw[block_indent:]` with at most a trailing
line-ending normalization.

Care points the fix must respect (covered by the DoD's no-regression item):

- The blank-line short-circuit at `yaml_lite.py:163-167` already uses
  `raw.rstrip() == ""` to detect blank lines for chomping — that logic is
  separate and should stay.
- `curr = self._indent(rstripped)` at `:168` computes indent from the
  rstripped line; that is fine for indent detection and unaffected.
- Trailing-blank-line chomping (`clip`/`strip`/`keep`) at `:181-190` operates
  on whole-line emptiness and must remain correct.

The narrowest change is at the single `chunks.append(...)` line; verify the
existing block-scalar regression cards (empty-block-scalar-consumes-next-key,
keep-chomping-indicator-treated-as-clip) still pass.
