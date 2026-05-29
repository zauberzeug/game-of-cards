---
title: inline-emitter-writes-multi-line-strings-bare-destroying-subsequent-frontmatter
summary: "`_yaml_inline` documents (engine.py:208-209) that \"Multi-line strings are NOT supported here — emit_frontmatter detects them and uses literal-block style (`|-`) instead,\" but does not enforce the contract: its quote-trigger set (`_YAML_NEEDS_QUOTE`, `_parser_coerces_scalar`, `_YAML_BLOCK_TOKENS`, `_YAML_INDICATOR_FIRST`, `s != s.strip()`) contains no newline test, so a multi-line value falls through to a bare unquoted emit at `engine.py:239`. `_apply_summary_rewrite` (engine.py:3053-3058) feeds the result straight into `mutate_frontmatter_field` without going through `emit_frontmatter`, so any multi-line summary the human accepts via `goc quality-pass --llm` writes `summary: line1\\nline2` to disk — and `line2` (plus every frontmatter field below it) becomes garbage outside any key. The next `parse_frontmatter` silently drops `status`, `contribution`, `tags`, etc.; subsequent `goc validate` reports the card as missing required fields with no hint that the rewrite is the cause."
status: open
stage: null
contribution: high
created: "2026-05-29T23:38:41Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] PROCESS: decide between (a) `_yaml_inline` refuses multi-line input — raises `FrontmatterError`, parallel to the existing float-refusal branch (engine.py:219-227) — and the caller falls back to a full re-emit through `emit_frontmatter`, or (b) the `_apply_summary_rewrite` caller stops bypassing `emit_frontmatter` and instead re-emits the whole frontmatter so a multi-line summary goes out as a `|-` block (the same path `_apply_dod_rewrite` already takes at engine.py:3077-3078). Record the call in log.md. See `## Decision required` below.
  - [ ] TDD: `deck/<title>/reproduce.py` exits zero — a card with `status`, `contribution`, `tags` after `summary` survives a `_apply_summary_rewrite(card, "Line one.\nLine two.")` call: every field is still present in the parsed frontmatter, and the summary's two lines round-trip.
  - [ ] TDD: a sibling assertion confirms `_yaml_inline` no longer falls through to a bare unquoted multi-line emit (under choice (a): raises; under choice (b): unreached on this caller path because `_apply_summary_rewrite` no longer routes through it for multi-line input).
  - [ ] MECHANICAL: `uv run goc validate` passes on the modified deck.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` is green.
---

# Inline frontmatter emitter writes multi-line strings bare, destroying subsequent frontmatter

## Location

- `goc/engine.py:205-239` — `_yaml_inline` (the inline frontmatter emitter
  whose docstring promises that multi-line input is NOT supported here).
- `goc/engine.py:3053-3058` — `_apply_summary_rewrite` (the caller that
  routes an LLM-authored summary straight through `_yaml_inline` +
  `mutate_frontmatter_field`, bypassing `emit_frontmatter`'s block-scalar
  path).

## What's broken

`_yaml_inline`'s docstring at `engine.py:205-210`:

```python
def _yaml_inline(value) -> str:
    """Render a scalar/list as inline YAML for flat-frontmatter use.

    Multi-line strings are NOT supported here — emit_frontmatter detects
    them and uses literal-block style (`|-`) instead.
    """
```

But the body at `engine.py:228-239` never tests for a newline:

```python
s = str(value)
if (
    _YAML_NEEDS_QUOTE.search(s)
    or _parser_coerces_scalar(s)
    or s in _YAML_BLOCK_TOKENS
    or (s and s[0] in _YAML_INDICATOR_FIRST)
    or s != s.strip()
):
    # Escape \ and " for safe inclusion in "..." YAML scalar.
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
return s
```

`_YAML_NEEDS_QUOTE` (engine.py:194-197) is the character class
``[:#'"\[\]\{\},`@]`` — no `\n`. The `s != s.strip()` trigger only
catches leading/trailing whitespace, not an interior newline. So
`_yaml_inline("Line1\nLine2")` returns the literal string `Line1\nLine2`
(bare, unquoted). The neighboring float branch at engine.py:219-227
already shows the intended posture for unsupported value shapes — it
raises `FrontmatterError("float frontmatter values are not supported")`
rather than silently emitting an unround-trippable value. Newlines were
left out of the same posture.

The downstream caller at `engine.py:3053-3058`:

```python
def _apply_summary_rewrite(card: Card, new_summary: str) -> None:
    """In-place YAML-safe rewrite of the `summary:` field on this card's README.md."""
    readme = card.path / "README.md"
    text = readme.read_text()
    rewritten = mutate_frontmatter_field(text, "summary", _yaml_inline(new_summary))
    readme.write_text(rewritten)
```

writes the unquoted multi-line value to disk verbatim through
`mutate_frontmatter_field`, which simply does
``f"{field_name}: {new_value}"`` substitution (engine.py:347).

## Empirical evidence

```
$ uv run python deck/inline-emitter-writes-multi-line-strings-bare-destroying-subsequent-frontmatter/reproduce.py
--- rewritten readme on disk ---
---
title: t
summary: Line1
Line2
status: open
contribution: medium
tags: [bug]
---
body

--- parsed frontmatter keys ---
['title', 'summary']
--- parsed frontmatter dict ---
{'title': 't', 'summary': 'Line1'}

FAIL: status/contribution/tags vanished from parsed frontmatter
      summary truncated to 'Line1' (Line2 dropped)
```

## Why it matters

The reachability path is live in shipping code:

1. The user runs `goc quality-pass --llm` on a card whose summary the
   LLM flags for rewrite (`_cmd_quality_pass`, engine.py:3134 onward).
2. `_apply_verdict_interactive` (engine.py:3081) asks the human to
   accept the rewrite (`apply summary rewrite?`); under `--yes` the
   accept is automatic.
3. The accepted `sv["rewrite"]` string flows into
   `_apply_summary_rewrite` at engine.py:3114. The LLM prompt at
   engine.py:2942-2949 includes a multi-sentence "Good" summary example,
   so the model is free to emit a `\n` between sentences (and routinely
   does on real cards).
4. The newline-bearing summary lands on disk as
   `summary: line1\nline2`, with `line2` treated as a top-level
   key-less line that ends the YAML mapping early.
5. Every frontmatter field below `summary` (`status`, `stage`,
   `contribution`, `created`, `closed_at`, `human_gate`, `advances`,
   `advanced_by`, `tags`, `definition_of_done`, `worker`) is silently
   dropped on the next `parse_frontmatter`.
6. The next `goc validate` reports the card as missing required fields
   with no hint that an LLM-driven `quality-pass` is the cause.

The parallel `_apply_dod_rewrite` (engine.py:3061-3078) does NOT have
this defect: it re-emits the full frontmatter through `emit_frontmatter`,
which detects multi-line strings and routes them through
`_emit_block_field`'s `|-` indicator (engine.py:242-259). The summary
caller is the single bypass.

The closed sibling
[mutate-frontmatter-field-corrupts-backslashes-via-regex-replacement-template](../mutate-frontmatter-field-corrupts-backslashes-via-regex-replacement-template/)
covers a different gap on the same caller path (backslash escapes are
mis-interpreted as `re.sub` template metacharacters). That fix targets
the regex-template injection; it does not change the newline-handling
behavior of `_yaml_inline`, so this defect remains after that one
lands.

## Decision required

The fix has two credible paths. Both close the defect; they differ in
which layer takes responsibility.

**(a) Refuse multi-line input at the `_yaml_inline` boundary.** Add a
sibling branch alongside the float refusal (engine.py:219-227):

```python
if "\n" in s:
    raise FrontmatterError(
        f"multi-line frontmatter values are not supported by _yaml_inline; "
        "route through emit_frontmatter for literal-block style."
    )
```

`_apply_summary_rewrite` then catches the error and falls back to a
full `emit_frontmatter` re-emit. Pro: enforces the docstring contract
at the function boundary, matches the float-refusal posture, surfaces
every bypassing caller as a loud failure. Con: every existing call site
that might pass a free-form string has to be audited and possibly
wrapped — `worker` rewrites (engine.py:3468), `closed_at`/`status`
(throughout), `human_gate` (engine.py:4359, 4579), and any future
caller.

**(b) Rewire the caller to go through `emit_frontmatter`.** Replace
`_apply_summary_rewrite`'s body with a parse-mutate-re-emit pattern
parallel to `_apply_dod_rewrite` (engine.py:3061-3078):

```python
def _apply_summary_rewrite(card: Card, new_summary: str) -> None:
    readme = card.path / "README.md"
    text = readme.read_text()
    fm, body = parse_frontmatter(text)
    fm["summary"] = new_summary
    readme.write_text(emit_frontmatter(fm, body=body))
```

Pro: `emit_frontmatter` already handles every value shape correctly
(including multi-line via `_emit_block_field`); the fix is local and
mechanical. Con: the broader `_yaml_inline` contract violation remains
latent — any *other* caller that bypasses `emit_frontmatter` keeps the
silent-data-loss footgun.

The two are not mutually exclusive: (b) is the minimal local fix, (a)
is the structural guard that prevents the family from spawning siblings.

## Fix (after decision lands)

Implement the chosen approach. If (a): add the multi-line guard to
`_yaml_inline` and update every direct caller (the audit list above) to
catch or pre-check. If (b): rewrite `_apply_summary_rewrite` to use
`emit_frontmatter`; consider an optional ratchet test that asserts no
direct `mutate_frontmatter_field(..., _yaml_inline(<free-form>))`
pattern exists in `engine.py` outside controlled-enum callers.
