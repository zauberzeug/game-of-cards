---
title: bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes
summary: "The loader tolerates bare-string scalars on list-typed frontmatter fields (`advances`, `advanced_by`, `supersedes`, `superseded_by`, `tags`). Each read-time consumer that forgets the `isinstance(..., list)` guard then iterates the string character-by-character or substring-matches via Python's string `in`. Six closed sibling cards have already patched specific consumers one at a time; a seventh unguarded site (`_remove_from_list_field`, engine.py:4172) has now surfaced — the family will keep recurring until the loader rejects the malformed shape at the source or every consumer routes through a shared shape-coercing helper."
status: open
stage: null
contribution: medium
created: "2026-05-29T14:20:32Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix, infra]
definition_of_done: |
  - [ ] PROCESS: pick one of approach A (loader-time shape rejection), B (centralized `_field_as_list` helper routing all reads), or C (continue per-consumer guards) — record in log.md with the rationale. See `## Decision required` below.
  - [ ] MECHANICAL: implement the chosen approach. For A: extend `parse_frontmatter` / `Card` construction to reject (or coerce) non-list scalars on the schema's list-typed fields (`advances`, `advanced_by`, `supersedes`, `superseded_by`, `tags`). For B: introduce a single helper and migrate every documented consumer (the six closed-sibling sites plus `_remove_from_list_field`) through it; a regression test asserts no `frontmatter.get("<list-field>") or []` pattern remains outside the helper. For C: just file the one outstanding sibling (`_remove_from_list_field`).
  - [ ] TDD: a reproduce.py builds a card with `advanced_by: "A"` (bare scalar) and exercises `_remove_from_list_field` via `goc unadvance` — currently produces a list of single characters in the rewritten card; after the fix, either the load fails cleanly (A) or the helper treats the bare scalar as empty / shape-coerces (B). Same reproducer demonstrates the family is closed at the chosen layer.
  - [ ] PROCESS: cross-link the six closed siblings via `advanced_by` (or document them in the body) so a cold reader sees the family this card retires.
  - [ ] PROCESS: `uv run goc validate` passes and `uv run python -m unittest discover -s tests` is green.
---

# Bare-string scalars on list-typed frontmatter fields keep spawning per-consumer guard fixes

## What's broken

`parse_frontmatter` accepts any YAML-lite scalar for the list-typed
frontmatter fields (`advances`, `advanced_by`, `supersedes`,
`superseded_by`, `tags`). A hand-edited card like:

```yaml
advanced_by: A-card
```

(bare scalar instead of `[A-card]`) parses to a `str`. The Card
object then exposes the field as a `str`, not a `list`. Every
read-time consumer that pattern-matches without an `isinstance(...,
list)` guard either:

- iterates the string character-by-character (`for ref in v`), or
- substring-matches via Python's `in` operator (`if x in v`).

Both silently corrupt the consumer's behavior. `goc validate`
*does* reject this shape (`engine.py:1246`), but the read-time
consumers run on cards that have not been gated through validate
(in-flight CLI commands, hooks, board rendering) — so the per-
consumer guard is load-bearing every time.

## The family (closed siblings — same root cause)

Each of these is a closed card that added an `isinstance(..., list)`
guard to one specific consumer:

1. `tags-property-iterates-bare-string-tags-character-by-character` —
   `Card.tags` property + tag-filter substring match.
2. `supersedes-and-superseded-by-walkers-iterate-bare-string-scalars-character-by-character` —
   three supersession walkers in `validate_supersedes_targets`,
   `detect_supersedes_cycles`, `_would_create_supersedes_cycle`.
3. `dependency-blockers-iterates-non-list-advanced-by-character-by-character` —
   `dependency_blockers` + three sibling sites in the verbose /
   JSON / board renderers.
4. `compute-values-iterates-non-list-advances-character-by-character` —
   `compute_values` priority walker.
5. `advances-and-advanced-by-cli-filters-substring-match-bare-string-scalars` —
   the top-level `--advances` / `--advanced-by` CLI filter.
6. `repair-edges-misses-half-edge-when-inverse-side-is-a-bare-string` —
   `find_half_edges`' INNER inverse-list walk.

The closed body of card #2 explicitly flagged the meta-fix as
out-of-scope and worth filing separately:

> A separate question (out of scope here, file as a sibling card if
> pursued): should `goc validate` upstream-reject bare-string scalars
> on list-typed fields entirely, so the read-time backstops aren't
> load-bearing? `_BLOCK_LIST_FIELDS` already encodes which fields are
> list-typed; a single shape-check at parse time would close the
> family at the source.

That suggestion never got filed. This card is that filing.

## The latest unfixed sibling (the trigger to file the meta-fix)

`goc/engine.py:4172` — `_remove_from_list_field`:

```python
def _remove_from_list_field(text: str, field: str, title_to_remove: str) -> str:
    fm, body = parse_frontmatter(text)
    cur = fm.get(field) or []
    if title_to_remove not in cur:       # substring match on a string
        return text
    fm[field] = [s for s in cur if s != title_to_remove]   # char-by-char iteration
    return emit_frontmatter(fm, body=body)
```

Compare to the sibling `_add_to_list_field` at `engine.py:4159`,
which DOES carry the guard:

```python
def _add_to_list_field(text: str, field: str, title_to_add: str) -> str:
    fm, body = parse_frontmatter(text)
    cur = fm.get(field) or []
    if not isinstance(cur, list):
        raise ValueError(f"{field}: not a list")
    ...
```

The asymmetry between the add and remove paths is the most direct
evidence the per-consumer-guard model is failing — even paired
helpers in the same file drifted apart.

## Reachability path

`_remove_from_list_field` is called from `_mutate_pair` (engine.py:4181),
which is called by:

- `_cmd_unadvance` — `goc unadvance <title> <advancer>` removes
  the bidirectional advance edge.
- `_cmd_status` — when called with `--by`, removes via the
  supersession path through `_mutate_pair` (status flip with
  successor).

So `goc unadvance` or `goc status … superseded --by …` on a card
with a hand-edited bare-string `advanced_by` / `advances` /
`supersedes` / `superseded_by` will trigger the bug. `goc validate`
on the deck *before* the mutation would catch it, but in-flight
sessions routinely run `unadvance` without a fresh validate.

## Falsification / reproducer

`tests/<this-card>/reproduce.py`-style demonstration (works in a
tempdir without touching the live deck):

```python
# Card A has advanced_by: "B-card" (bare string, hand-edited)
fm = {"advanced_by": "B-card", ...}
text = emit_frontmatter(fm, body="...")
new_text = _remove_from_list_field(text, "advanced_by", "B-card")
fm2, _ = parse_frontmatter(new_text)
# Expectation under fix A: load_card_or_exit raises before this point.
# Expectation under fix B: fm2["advanced_by"] == [] (helper treats scalar as empty).
# Currently: fm2["advanced_by"] == ["B", "-", "c", "a", "r", "d"]
assert fm2["advanced_by"] == [] or fm2["advanced_by"] == ["B-card"]
```

A regression test asserting the failing output is what closes the
family.

## Why it matters

The fix family is now six closed cards deep, and a seventh unguarded
site has surfaced. Every new code path that reads one of the five
list-typed fields is at risk of joining the family. The fix-per-
consumer model:

- doubles the surface area for review on every new read site;
- silently rots when a paired helper (add ↔ remove) drifts;
- pushes the safety contract onto the consumer instead of the
  loader, even though `_BLOCK_LIST_FIELDS` already encodes the
  shape information needed at load time.

A central fix retires the family.

## Decision required

Three credible approaches; the choice is architectural.

**Option A — Load-time shape rejection (or coercion).**
Extend `parse_frontmatter` (or `Card` construction) to consult the
schema's list-typed-field set and either:
- (A1) raise `FrontmatterError` on a non-list scalar, refusing to
  return a Card from a malformed file; or
- (A2) silently coerce a bare scalar to `[]` and surface a stderr
  warning, matching `compute_values`' dangling-advances behaviour.

Pros: closes the family at the source; per-consumer guards become
redundant (could be removed in a follow-up). Cons: A1 changes the
behaviour of any tool that currently reads malformed cards (e.g.
`goc show`); A2 silently discards data, which the project has
historically disliked elsewhere.

**Option B — Centralized `_field_as_list(fm, field) -> list` helper.**
Introduce one helper that returns `fm.get(field)` if it's a list,
else `[]`. Migrate the six closed-sibling sites and the new
`_remove_from_list_field` site through it. A test asserts no
`fm.get("<list-field>") or []` patterns remain outside the helper.

Pros: explicit, mechanical, doesn't change loader behaviour. Cons:
requires a sweep across the engine; new code can still bypass the
helper unless the test is strict.

**Option C — Status quo: file the one outstanding sibling.**
File a card specifically for `_remove_from_list_field` and close it
by adding an `isinstance(cur, list)` guard. Leave the family open
for the next sibling to surface.

Pros: smallest diff. Cons: doesn't retire the family; the next
unguarded read site will trigger the eighth filing.

**Recommendation:** Option B. It matches the project's documented
preference for explicit, surveyable mechanism (per the closed
`derive-dependency-readiness-instead-of-storing-blocked-status`
spirit — derive the safe shape from the schema rather than depend on
each consumer remembering the contract), and the migration is
mechanical enough that `goc validate`-style regression tests can
enforce it. Option A is the more aggressive fix but changes
read-anywhere behaviour in ways that need a separate analysis.

Decide before claiming this card.
