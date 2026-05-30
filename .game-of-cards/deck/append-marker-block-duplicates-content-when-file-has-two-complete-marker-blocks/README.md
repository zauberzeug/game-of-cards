---
title: append-marker-block-duplicates-content-when-file-has-two-complete-marker-blocks
summary: "`_append_marker_block` calls `pattern.sub(lambda _: block, text)` with no `count=` limit. When the briefing file already contains two complete BEGIN+END marker blocks (e.g., after a botched manual upgrade, a reverted release-rewrite, or a hand-merge that kept both sides), every block is rewritten with the same new content — the file ends up with two identical GoC marker blocks instead of one. Sibling shape to `append-marker-block-loses-content-between-stacked-begin-markers`: same helper, different malformed-input shape (two-BEGIN+two-END vs. two-BEGIN+one-END), different failure (silent duplication vs. silent loss)."
status: open
stage: null
contribution: medium
created: "2026-05-30T07:35:30Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [ ] PROCESS: human picks the fix path on `append-marker-block-loses-content-between-stacked-begin-markers` (this card's sibling); whichever option lands on that card determines the fix here too.
  - [ ] TDD: `reproduce.py` exits zero — the two-complete-blocks input no longer results in a duplicated block (block consolidated to one, OR malformed input rejected with a clear error, per the chosen option on the sibling card).
  - [ ] TDD: regression test in `tests/test_install.py` covers the two-complete-blocks input shape against `_append_marker_block` (and `_strip_goc_block` if the sibling-card sweep extends to it).
  - [ ] TDD: existing one-BEGIN-one-END install/upgrade tests still pass; existing two-BEGIN-one-END regression (from the sibling card's TDD) still passes.
  - [ ] MECHANICAL: `goc validate` passes; plugin mirrors re-synced if the engine or install template changed.
---

# `_append_marker_block` duplicates GoC content when the file has two complete marker blocks

## Location

`goc/install.py:935-936` — inside `_append_marker_block`.

```python
def _append_marker_block(target: Path, block_body: str, *, header: str) -> None:
    ...
    block = f"{GOC_BEGIN}\n{block_body.rstrip()}\n{GOC_END}\n"
    if not target.exists():
        target.write_text(f"{header}\n\n{block}")
        return
    text, newline = _read_text_keep_newline(target)
    pattern = re.compile(rf"{GOC_BEGIN_RE.pattern}.*?{re.escape(GOC_END)}\n?", re.DOTALL)
    if pattern.search(text):
        _write_text_keep_newline(target, pattern.sub(lambda _: block, text), newline)
        return
    _write_text_keep_newline(target, text.rstrip() + "\n\n" + block, newline)
```

The sister callsite at `goc/install.py:1091-1092` uses `count=1`
explicitly; this one does not.

## What's broken

The regex `<!-- BEGIN GOC v... -->.*?<!-- END GOC -->\n?` is non-greedy
with `re.DOTALL`. When the briefing file already contains **two
complete BEGIN+END marker blocks** (each well-formed and self-contained),
the regex finds **two non-overlapping matches**, and `re.sub` without a
`count=` argument replaces every match. Both old blocks become identical
copies of the new briefing — the file ends up with two duplicate GoC
sections and the user content between them is preserved (because each
match spans only one block).

The intended contract — documented in `AGENTS.md` § "Marker-bounded
merge for AGENTS.md / CLAUDE.md" — is that `goc install` /
`goc upgrade` write exactly one block. The implementation assumes
exactly one BEGIN+END pair exists; it does not validate that
assumption before mutating.

## Empirical evidence

`uv run python deck/append-marker-block-duplicates-content-when-file-has-two-complete-marker-blocks/reproduce.py`:

```
=== BEFORE _append_marker_block ===
# Header

User text above.

<!-- BEGIN GOC v0.1.0 -->
old block one
<!-- END GOC -->

User text between two complete blocks (will be lost? or duplicated?).

<!-- BEGIN GOC v0.2.0 -->
old block two
<!-- END GOC -->

User text below.


=== AFTER _append_marker_block ===
# Header

User text above.

<!-- BEGIN GOC v0.0.21.post1.dev10 -->
NEW briefing content
<!-- END GOC -->

User text between two complete blocks (will be lost? or duplicated?).

<!-- BEGIN GOC v0.0.21.post1.dev10 -->
NEW briefing content
<!-- END GOC -->

User text below.
```

User text between the two original blocks IS preserved. But both old
blocks are silently replaced with the same new content — leaving two
identical GoC sections in one file. Subsequent `goc validate` and
`goc upgrade` runs will treat the file as having two blocks and the
duplication compounds.

## Reachability path

A briefing file can end up with two complete BEGIN+END blocks via
several routes:

- **Manual edit / human duplication.** A user copy-pastes a marker
  block to test or annotate, forgets to remove it.
- **Reverted release-rewrite that recreated the marker.** If a release
  rewrite committed a new BEGIN tag and the rewrite was later
  hand-reverted by appending (not replacing) the old block, the file
  briefly carries both.
- **`AGENTS.md` merge from a long-lived branch.** A three-way merge that
  takes both sides' marker block (rather than picking one) yields two
  full blocks. Unlike the two-BEGIN+one-END shape in the sibling card,
  each side's END is preserved, so this passes a quick visual sanity
  check but trips this bug on the next `goc upgrade`.
- **`CLAUDE.md` example documentation.** A repo that documents the GoC
  marker convention by *quoting* a verbatim block (BEGIN + content +
  END) in its own briefing will look to the regex like a real second
  marker. The next `goc upgrade` overwrites the documentation example
  with a duplicate of the new briefing.

The dogfood repo's own AGENTS.md is single-block today, but the routes
above are present in any consumer that maintains its own briefing.

## Why it matters

- **Silent data corruption** of the briefing file. The user gets two
  identical GoC sections instead of one; downstream readers
  (agents loading AGENTS.md, reviewers, the next upgrade) see
  duplicated guidance with no warning.
- **The duplication compounds.** The pattern matches both copies again
  on the next upgrade, replacing them both — so the file stays in a
  two-block state until a human notices and hand-fixes it.
- **The sibling card's "fail loudly" recommendation would also fix this
  bug.** Option 1 in the decision-required of
  `append-marker-block-loses-content-between-stacked-begin-markers`
  ("error when `GOC_BEGIN_RE.findall(text)` count is not 1") is the
  same backstop both shapes need.

## Sibling sweep

Same root cause family lives across two more sites in `install.py`:

- `_append_marker_block` at line 935 — this card's primary site.
- `_strip_goc_block` at line 200 — same non-greedy pattern, same
  no-`count=1`; `re.sub("\n\n", ...)` replaces every match. The
  symptom is identical (each complete block is replaced with a single
  blank-line separator → file ends up with two collapsed gaps).
- `_sync_methodology_blocks` is the only caller of
  `_append_marker_block`; the same shape would also surface there.

The fix path on the sibling card already calls out `_strip_goc_block`
in its "Sibling sweep" section; this card's fix should extend that
sweep to the two-complete-blocks input shape.

## Relationship to `append-marker-block-loses-content-between-stacked-begin-markers`

Both cards are in the `_append_marker_block` malformed-input family.
The sibling covers the **two-BEGIN-one-END** shape (content between
the two BEGINs is silently DROPPED). This card covers the
**two-BEGIN-two-END** shape (the new block is silently DUPLICATED).
Same root cause (no validation that exactly one BEGIN+END pair exists
before `re.sub` is called), different failure mode.

The recommended fix on the sibling — option 1, "fail loudly when
`len(GOC_BEGIN_RE.findall(text)) != 1`" — would also fix this card.
Option 2 ("anchor to last END") would NOT fix this card cleanly: a
greedy `.*` match would span from the first BEGIN through the last
END, eating the user content between the two blocks AND collapsing
two blocks into one — the duplication goes away but at the cost of
silent data loss. Option 3 ("detect-and-consolidate") would fix
both.

## Decision required

The decision lives on the sibling card
([append-marker-block-loses-content-between-stacked-begin-markers](../append-marker-block-loses-content-between-stacked-begin-markers/));
this card inherits whichever option that card adopts and extends the
regression-test surface to the two-complete-blocks input shape.

This card carries `human_gate: decision` only because the sibling
does — once the sibling lowers its gate via `goc decide`, this card
should be advanced to the same decision via a `## Decision
(inherited)` body section and its gate lowered too.

## Artifacts

- reproduce.py — runs `_append_marker_block` on a temp file with two
  complete BEGIN+END pairs and prints before/after.
