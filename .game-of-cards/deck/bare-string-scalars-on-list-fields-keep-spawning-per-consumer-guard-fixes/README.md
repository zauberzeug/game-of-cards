---
title: bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes
summary: "The loader tolerates bare-string scalars on list-typed frontmatter fields (`advances`, `advanced_by`, `supersedes`, `superseded_by`, `tags`). Each read-time consumer that forgets the `isinstance(..., list)` guard then iterates the string character-by-character or substring-matches via Python's string `in`. Six closed sibling cards have already patched specific consumers one at a time; a seventh unguarded site (`_remove_from_list_field`, engine.py:4172) and then an eighth (`render_table` verbose `-vv` raw-dump loop, engine.py:2552) have now surfaced. A 2026-06-21 audit added a second failure mode in the same root cause — a non-string *scalar* on a field whose consumer assumes a string (`contribution: 42`; a non-string element in `tags`) crashes the queue/board renderer with a hard TypeError before validate runs, and `contribution` is a scalar field outside the five list-typed ones, so the family is broader than list fields alone. The family will keep recurring until the loader rejects/coerces the malformed shape at the source (approach A, generalized to all schema-typed fields) or every consumer routes through a shared shape-coercing helper."
status: open
stage: null
contribution: medium
created: "2026-05-29T14:20:32Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - canonical-tags-loader-iterates-bare-string-scalar-character-by-character
  - goc-unadvance-rewrites-bare-string-edge-field-as-character-list
  - goc-validate-crashes-with-typeerror-on-non-string-element-in-tags-list
  - render-json-emits-bare-string-edge-fields-as-json-strings-not-lists
  - repair-edges-crashes-with-traceback-on-bare-string-inverse-edge-field
  - consuming-repo-tags-loader-crashes-or-pollutes-on-non-string-list-element
  - board-and-table-renderers-crash-on-a-card-with-null-status
  - table-renderer-crashes-on-a-card-with-null-human-gate
  - canonical-tags-loader-crashes-on-yaml-block-that-is-not-a-mapping
  - verbose-table-render-crashes-on-non-string-definition-of-done
tags: [bug, api-contract, meta-fix, infra]
definition_of_done: |
  - [ ] PROCESS: pick one of approach A (loader-time shape rejection), B (centralized `_field_as_list` helper routing all reads), or C (continue per-consumer guards) — record in log.md with the rationale. See `## Decision required` below.
  - [ ] MECHANICAL: implement the chosen approach. For A: extend `parse_frontmatter` / `Card` construction to reject (or coerce) non-list scalars on the schema's list-typed fields (`advances`, `advanced_by`, `supersedes`, `superseded_by`, `tags`). For B: introduce a single helper and migrate every documented consumer (the six closed-sibling sites plus `_remove_from_list_field` and the `render_table` verbose `-vv` raw-dump loop, engine.py:2552-2556) through it; a regression test asserts no `frontmatter.get("<list-field>") or []` pattern remains outside the helper. For C: just file the one outstanding sibling (`_remove_from_list_field`).
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

But the guard `_add_to_list_field` "DOES carry" is not even safe: its
`raise ValueError(f"{field}: not a list")` propagates uncaught and
**crashes `goc repair-edges`** (both the dry-run diff path at
`engine.py:_repair_edge_diff` and the `--apply` path via `_mutate_pair`)
with a Python traceback. The trigger is exactly the half-edge that
sibling #6 (`repair-edges-misses-half-edge-when-inverse-side-is-a-bare-string`)
taught `find_half_edges` to *detect*: card A has `advances: [card-b]`
while card B has a bare-string `advanced_by: card-a`. The detection fix
now reports that half-edge as repairable, and the repair path then feeds
the bare-string card into `_add_to_list_field`, whose "guard" turns the
repair into a crash. So the per-consumer-guard model isn't merely
incomplete (silent char-iteration on the unguarded sites) — on a guarded
site it actively breaks a shipping verb, and two already-shipped fixes
contradict each other. This is direct evidence against approach C
(continue per-consumer guards): a load-time normalization/rejection
(approach A) or a shared shape-coercing helper (approach B) would let
`repair-edges` heal the half-edge instead of aborting on it.

## An eighth unguarded site (surfaced by a later audit)

`goc/engine.py:2552-2556` — the verbose (`-vv`) branch of
`render_table` dumps every relationship field raw:

```python
if verbose >= 2:
    for field in LIST_REL_FIELDS:          # advances, advanced_by, supersedes, superseded_by
        v = t.frontmatter.get(field) or []
        if v:
            out_lines.append(f"    {field}: {list(v)}")   # list(v) on a bare string
```

This is a *distinct* site from sibling #3: that card patched the
`dependency_blockers` "awaiting" line and the per-field renderers it
named, but this `LIST_REL_FIELDS` raw-dump loop at `verbose >= 2`
carries no `isinstance(v, list)` guard. On a card hand-edited to
`advances: some-card` (bare scalar), `goc --status open -vv` renders:

```text
    advances: ['s', 'o', 'm', 'e', '-', 'c', 'a', 'r', 'd']
```

Reproduced directly against `LIST_REL_FIELDS` on 2026-06-08 — the
char-list output above is verbatim. The display is read-only (no file
corruption), so the impact is lower than the mutating siblings, but it
is one more consumer that joins the family, and it must be on the
migration checklist for whichever central fix (A or B) is chosen.

## A second failure mode — non-string *scalars* crash the render path (closed render-path siblings)

The eight sites above all share one failure mode: a *bare string where a
list is expected*, iterated character-by-character. A later audit
(2026-06-21) surfaced a **second failure mode in the same root cause** —
the loader equally tolerates a *non-string scalar* on a field whose
read-time consumer assumes a string, and the queue/board renderers then
crash with a hard `TypeError` (not silent char-iteration) before
`validate` ever runs. Two closed render-path siblings:

- [goc-queue-and-board-crash-on-a-non-string-contribution-value](../goc-queue-and-board-crash-on-a-non-string-contribution-value/)
  — `contribution: 42` (a **scalar** field, outside the five list-typed
  fields above) reaches `render_table` (`len()`/`.ljust()`) and
  `render_board` (`c[0]`) and crashes the whole deck view. Fixed by
  coercing in the `Card.contribution` getter.
- [goc-queue-table-crashes-on-a-non-string-tag-element](../goc-queue-table-crashes-on-a-non-string-tag-element/)
  — `tags: [bug, 42]` (a correct list, but a **non-string element**)
  crashes `render_table`'s `",".join(...)`. This is the render-path twin
  of the already-tracked `advanced_by` sibling
  `goc-validate-crashes-with-typeerror-on-non-string-element-in-tags-list`
  (same shape, different consumer). Fixed by coercing each element in the
  join.

Both were fixed at their consumer (the audit's fix-through), but they
matter to *this* card because they widen the root cause: the parser
accepts **any scalar shape on any field**, and each read-time consumer
independently (and inconsistently) assumes the shape it wants — the same
disease as the bare-string-on-list family, a different symptom.
**Approach A, generalized to validate/coerce every schema-typed field's
shape at load time (not only the five list-typed fields), closes both
failure modes at once;** a per-field-type approach-B helper would need a
scalar variant too. The render-path coercions already shipped are
per-consumer guards — i.e. more instances of exactly the model this card
argues against.

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
