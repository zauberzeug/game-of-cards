---
title: canonical-tags-loader-iterates-bare-string-scalar-character-by-character
summary: "`_load_consuming_repo_tags()` in `goc/engine.py:457` reads project-local tags from a consuming repo's `.game-of-cards/canonical-tags.md`, then does `out.update(block.get('canonical_tags') or [])` with no `isinstance(..., list)` guard. A user who writes `canonical_tags: my-tag` (bare scalar, not a list) makes `set.update()` iterate the string character-by-character, adding individual chars as canonical tags. Same antipattern shape as the four closed sibling cards on card-frontmatter fields, but on the deck-extension surface — neither approach A (parse_frontmatter shape rejection) nor approach B (centralized `_field_as_list` helper on card frontmatter) in the open meta-fix card would cover this site, because the canonical-tags file does not flow through `parse_frontmatter` at all."
status: done
stage: null
contribution: medium
created: "2026-05-30T04:56:35Z"
closed_at: "2026-05-30T05:01:59Z"
human_gate: none
advances:
  - bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — `_load_consuming_repo_tags()` called against a `canonical-tags.md` whose block contains `canonical_tags: my-tag` returns either `{"my-tag"}` (coerce single scalar to one-element list) or `set()` (reject malformed shape silently), but NOT a set of single characters.
  - [x] MECHANICAL: `_load_consuming_repo_tags()` (engine.py:455-457) guards the `out.update` call with `isinstance(..., list)` (or routes through a shared shape-coercing helper), matching the pattern already present in the four closed sibling sites.
  - [x] TDD: regression test in `tests/` covers both the bare-string scalar case and the canonical list case (mirroring `test_card_tags.py` / `test_find_half_edges.py` shape from the sibling fixes).
  - [x] MECHANICAL: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green; `pre-commit run --all-files` clean (plugin mirrors auto-sync).
worker: {who: "claude[bot]", where: main}
---

# `_load_consuming_repo_tags` iterates a bare-string `canonical_tags` scalar character-by-character

## Location

`goc/engine.py:437-458` — `_load_consuming_repo_tags()`:

```python
def _load_consuming_repo_tags() -> set[str]:
    """Merge tags declared in `.game-of-cards/canonical-tags.md`.

    Consuming repos extend goc's canonical_tags set by adding a fenced
    YAML block:

        ```yaml
        canonical_tags:
          - my-project-tag
          - another-tag
        ```

    Multiple blocks accumulate. Missing or empty file: no-op (returns set()).
    """
    extension_file = DECK_ROOT / ".game-of-cards" / "canonical-tags.md"
    if not extension_file.exists():
        return set()
    out: set[str] = set()
    for match in _FENCED_YAML.finditer(extension_file.read_text()):
        block = yaml.safe_load(match.group(1)) or {}
        out.update(block.get("canonical_tags") or [])
    return out
```

## What's broken

Line 457: `out.update(block.get("canonical_tags") or [])` has no
`isinstance(..., list)` guard. The `or []` fallback only fires when
the value is falsy (`None`, missing key, empty string). A user who
writes a single tag without the list dash:

```yaml
canonical_tags: my-tag
```

parses to a truthy string `"my-tag"`. `set.update("my-tag")` then
iterates the *string* (a Python iterable of single characters), adding
each char to the set.

This is exactly the same antipattern as the closed family on card
frontmatter list fields:

- `tags-property-iterates-bare-string-tags-character-by-character`
  (Card.tags property)
- `supersedes-and-superseded-by-walkers-iterate-bare-string-scalars-character-by-character`
  (three supersession walkers)
- `dependency-blockers-iterates-non-list-advanced-by-character-by-character`
  (`dependency_blockers` + 3 renderer sites)
- `compute-values-iterates-non-list-advances-character-by-character`
  (priority walker)

…and the still-open meta-fix
[`bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes`](../bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes/)
proposes three approaches (A: loader-time shape rejection in
`parse_frontmatter`, B: centralized `_field_as_list` helper, C:
per-consumer guards). None of those approaches would cover *this*
site, because the canonical-tags.md extension file does not flow
through `parse_frontmatter` at all — `_load_consuming_repo_tags`
calls `yaml.safe_load` directly on a fenced block.

## Empirical evidence

`uv run python .game-of-cards/deck/canonical-tags-loader-iterates-bare-string-scalar-character-by-character/reproduce.py`:

```
Parsed block: {'canonical_tags': 'my-tag'}
canonical_tags value type: <class 'str'>
canonical_tags value: 'my-tag'
Loaded canonical_tags set: ['-', 'a', 'g', 'm', 't', 'y']
Number of tags: 6
Expected: 1 tag ('my-tag')
Actual: split into characters
```

## Why it matters

Reachability — the canonical-tags.md file is the *documented* extension
surface for consuming-repo tag vocabularies. The docstring at line 443
shows the canonical list form, but users following the schema
familiar to YAML elsewhere ("a single value need not be wrapped in a
list") will eventually write `canonical_tags: my-tag`. The bug then
silently poisons the canonical-tags set: `goc new <card> --tag a`
suddenly succeeds (because `'a'` is now a member of the extended
set), and the *intended* tag (`my-tag`) fails validation because the
original string was never preserved.

This is the same failure mode the sibling cards already documented on
card-frontmatter fields. It surfaces here because the canonical-tags
loader is a parallel ingestion path — adding an `isinstance` guard
or routing through a shared coercion helper closes the new site.

## Fix

Two equivalent shapes, both one line:

```python
# Option A — defensive guard, drops malformed scalars silently.
for match in _FENCED_YAML.finditer(extension_file.read_text()):
    block = yaml.safe_load(match.group(1)) or {}
    value = block.get("canonical_tags") or []
    if not isinstance(value, list):
        continue
    out.update(value)
```

```python
# Option B — coerce a single scalar to a one-element list, matching the
# common YAML convention "a list of one needs no dash".
for match in _FENCED_YAML.finditer(extension_file.read_text()):
    block = yaml.safe_load(match.group(1)) or {}
    value = block.get("canonical_tags") or []
    if isinstance(value, str):
        value = [value]
    elif not isinstance(value, list):
        continue
    out.update(value)
```

Option A matches the existing sibling guards (silent drop on
unexpected shape — `goc validate` is the place to surface the error).
Option B is more user-friendly for the single-tag case but introduces
divergent behavior between card frontmatter (strict) and the
canonical-tags extension (coercive). Recommend A for consistency.
