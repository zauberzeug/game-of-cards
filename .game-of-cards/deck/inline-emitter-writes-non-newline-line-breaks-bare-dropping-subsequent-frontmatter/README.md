---
title: inline-emitter-writes-non-newline-line-breaks-bare-dropping-subsequent-frontmatter
summary: "`_yaml_inline` (engine.py:237) guards only against the LF newline before emitting a scalar bare, but the vendored parser splits the document with `str.splitlines()`, which treats nine other characters (CR, VT, FF, FS, GS, RS, NEL, LS, PS) as line breaks. A single-line field such as `summary` carrying an interior CR is emitted bare; on the next mutating verb's re-parse the value is truncated at the break and every field below it (tags, advances, definition_of_done) is silently dropped, passing goc validate the whole way. Sibling shape of the closed multi-line-newline card under the emitter quote-trigger meta-fix."
status: active
stage: null
contribution: high
created: "2026-06-22T19:48:28Z"
closed_at: null
human_gate: none
advances:
  - frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — none of the nine non-LF line-break characters round-trips lossily through `emit_frontmatter` -> `parse_frontmatter`.
  - [ ] TDD: a regression test asserts the emitter's behaviour for a scalar containing a non-LF line break (CR/VT/FF/FS/GS/RS/NEL/LS/PS) — either it raises a `FrontmatterError` like the existing `\n` case, or it round-trips faithfully; it must NOT emit the value bare and silently drop trailing fields.
  - [ ] MECHANICAL: the line-break detection lives in one place (not a fresh hand-maintained char list copied near the existing `"\n" in s` check) — derive the dangerous set from `str.splitlines()` behaviour so it cannot drift from the parser, consistent with the meta-fix this card advances.
  - [ ] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green; `python scripts/sync_plugin_assets.py --check` green (the vendored parser/emitter is mirrored into the plugin payloads).
worker: {who: "claude[bot]", where: main}
---

# inline-emitter-writes-non-newline-line-breaks-bare-dropping-subsequent-frontmatter

## Location

- Emitter guard: `goc/engine.py:237` (`_yaml_inline`) — `if "\n" in s:`.
- Block-routing guard: `goc/engine.py:332` (`emit_frontmatter`) — `if isinstance(value, str) and "\n" in value:`.
- Parser line-split: `goc/_vendor/yaml_lite.py` — `_Parser(text.splitlines())`.

## What's broken

`_yaml_inline` decides whether a scalar must be quoted (or rejected) before
emitting it bare. Its line-break guard checks a single character:

```python
s = str(value)
if "\n" in s:
    # ... emitting bare destroys every frontmatter field below this one
    # (the trailing lines are read as top-level non-key text and end the
    # mapping early). ...
    raise FrontmatterError(
        "multi-line frontmatter values are not supported by _yaml_inline; ..."
    )
```

But the vendored parser splits the whole document into lines with
`str.splitlines()`, and Python's `str.splitlines()` treats **nine other
characters** as line boundaries in addition to `\n`: carriage return
(`\r`), vertical tab (`\x0b`), form feed (`\x0c`), the information
separators `\x1c`/`\x1d`/`\x1e`, NEL (`\x85`), and the Unicode line/paragraph
separators U+2028 / U+2029. None of these appears in `_YAML_NEEDS_QUOTE`,
none is matched by the `s != s.strip()` test for *interior* occurrences, and
none is caught by the `"\n"` guard — so a single-line scalar containing one
of them is emitted **bare**.

When that document is parsed back, `splitlines()` breaks the scalar at the
embedded character. The value is truncated at the break, and the remainder
plus every subsequent `key: value` line is consumed as stray text — exactly
the failure mode the line-237 comment describes for `\n`, but reached
silently because the guard never fires.

Quoting alone would not rescue these characters either: the escape table at
`engine.py:256` emits only `\\` and `\"`, and `_parse_double_quoted` decodes
only `n`/`t`/`"`/`\\`, so a raw `\r` inside `"..."` still would not
round-trip. The faithful options are to **reject** the character at the
boundary (consistent with how `\n` and float values are already refused) or
to teach both emitter and parser a real escape for it.

## Empirical evidence

`uv run python deck/<title>/reproduce.py`:

```
  CR: summary_preserved=False tail_fields_preserved=False emitted_quoted=False  -> FAIL
  VT: summary_preserved=False tail_fields_preserved=False emitted_quoted=False  -> FAIL
  FF: summary_preserved=False tail_fields_preserved=False emitted_quoted=False  -> FAIL
  FS: summary_preserved=False tail_fields_preserved=False emitted_quoted=False  -> FAIL
  GS: summary_preserved=False tail_fields_preserved=False emitted_quoted=False  -> FAIL
  RS: summary_preserved=False tail_fields_preserved=False emitted_quoted=False  -> FAIL
 NEL: summary_preserved=False tail_fields_preserved=False emitted_quoted=False  -> FAIL
  LS: summary_preserved=False tail_fields_preserved=False emitted_quoted=False  -> FAIL
  PS: summary_preserved=False tail_fields_preserved=False emitted_quoted=False  -> FAIL

DEFECT REPRODUCED
```

For each character: a card with `summary: line one<CHAR>line two` followed by
`tags` and `advances` loses the summary's tail **and** both subsequent fields
after one parse/emit cycle.

## Why it matters

`summary` and `worker.who` / `worker.where` are free-form single-line string
fields emitted through `_yaml_inline` (directly at `emit_frontmatter:342`, via
`_emit_worker`, and as block-list items at `:327`). Reachability: an agent or
human pastes a `summary:` containing a stray CR (a Windows-clipboard or
classic-Mac copy) or an embedded NEL / line-separator (copied from a PDF or
rich-text source). The card **parses fine** (truncated) and passes
`goc validate`, so it sits as a time bomb. The next mutating verb — `goc
advance` / `goc status` / `goc done` / `goc decide` / `goc move`, all of which
route through `parse_frontmatter` -> `emit_frontmatter` — re-emits the value
bare, and the re-parse drops the card's edges (`advances` / `advanced_by`)
and its `definition_of_done` silently. That breaks edge referential integrity
and DoD enforcement with no diagnostic.

This is the same root-cause shape as the closed sibling
[inline-emitter-writes-multi-line-strings-bare-destroying-subsequent-frontmatter](../inline-emitter-writes-multi-line-strings-bare-destroying-subsequent-frontmatter/)
(the `\n` case), one of nine per-shape cards wired under the meta-fix
[frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting](../frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting/):
the emitter re-enumerates, in a hand-maintained predicate, the value shapes
the parser reinterprets, and the two drift. The `\n` guard caught one of the
ten characters `splitlines()` breaks on; this card is the other nine.

Distinct from the open card
[cards-with-windows-line-endings-vanish-from-the-deck-as-unterminated](../cards-with-windows-line-endings-vanish-from-the-deck-as-unterminated/),
which is whole-file CRLF tripping `FRONTMATTER_RE`'s LF-only terminator match
(a loud "unterminated" error). This card is a *lone interior* non-LF break
inside a *scalar value*, causing *silent* truncation and downstream field
loss — a different mechanism (`splitlines`, not the frontmatter regex) and a
different symptom (silent corruption, not rejection).

## Fix (proposed — do not apply here)

Derive the dangerous-character set from `str.splitlines()` rather than
hand-listing it, and apply the same rejection the `\n` case already uses.
Concretely, replace the `if "\n" in s:` test at `engine.py:237` (and the
companion block-routing test at `:332`) with a check that fires for any
character `str.splitlines()` treats as a line break — e.g. a string round-trips
iff `len(s.splitlines()) <= 1` and it ends in no trailing break — and raise the
existing `FrontmatterError`, so the boundary refuses values the vendored parser
cannot represent. A unifying mechanism that closes the parent meta-fix would
fold this into a single emitter-derives-from-parser source of truth and a
`parse(emit(s)) == s` property test over a corpus that includes these
characters.

