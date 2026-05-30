---
title: append-marker-block-loses-content-between-stacked-begin-markers
summary: "`_append_marker_block` matches the first `<!-- BEGIN GOC v... -->` to the first `<!-- END GOC -->` with a non-greedy `.*?`. When a file ends up with two BEGIN markers and one END (e.g., resolved merge conflict, interrupted release-rewrite, manual user duplication), the regex consumes everything between them and the substitution silently discards the intermediate content — including any text the user authored between the two BEGIN tags."
status: open
stage: null
contribution: medium
created: "2026-05-30T03:43:27Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [ ] PROCESS: human picks one of the three fix paths in `## Decision required`; the choice is recorded inline.
  - [ ] TDD: `reproduce.py` exits zero (intermediate content preserved OR malformed input rejected with a clear error, per the chosen option).
  - [ ] TDD: regression test in `tests/test_install.py` covers the two-BEGIN-one-END input shape against `_append_marker_block` AND `_strip_goc_block` (sibling sweep).
  - [ ] TDD: existing one-BEGIN-one-END install/upgrade tests still pass (no regression in the happy path).
  - [ ] MECHANICAL: `goc validate` passes; plugin mirrors re-synced if the engine changed.
---

# `_append_marker_block` discards intermediate content when a file has two BEGIN markers

## Location

`goc/install.py:934`

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

Where `GOC_BEGIN_RE` (`goc/install.py:32`) is:

```python
GOC_BEGIN_RE = re.compile(r"<!-- BEGIN GOC v[\w.+!-]+ -->")
GOC_END = "<!-- END GOC -->"
```

The same non-greedy shape appears at `goc/install.py:200` inside
`_strip_goc_block`, so the sibling sweep below covers both.

## What's broken

The pattern is `<!-- BEGIN GOC v... -->.*?<!-- END GOC -->\n?` with
`re.DOTALL` and **non-greedy** `.*?`. When the briefing file contains
two `<!-- BEGIN GOC ... -->` markers and a single `<!-- END GOC -->`,
the regex matches from the **first** BEGIN to the only END — pulling
the second BEGIN marker AND every byte between the two BEGIN markers
into the match. `pattern.sub(lambda _: block, text)` then replaces the
whole match with one fresh marker block. Anything the user wrote
between the two BEGINs is gone with no warning, no diff, no backup.

The function is documented as a "marker-bounded merge" that preserves
content above and below the markers (see `AGENTS.md` § "Marker-bounded
merge for AGENTS.md / CLAUDE.md": *"Content above or below those
markers is preserved across goc install / goc upgrade. … the block
below it is generated from goc/templates/AGENTS_GOC.md and round-trips
cleanly."*). The contract assumes exactly one BEGIN+END pair; the code
does not validate that assumption before clobbering the region.

## Empirical evidence

`uv run python deck/append-marker-block-loses-content-between-stacked-begin-markers/reproduce.py`:

```
=== input file (3 marker lines, 2 BEGINs + 1 END) ===
# Header

User text above the block.

<!-- BEGIN GOC v0.1.0 -->
old-block-1 content
<!-- BEGIN GOC v0.2.0 -->
USER-AUTHORED CONTENT BETWEEN BEGINS (will be lost)
<!-- END GOC -->

User text below the block.

=== number of regex matches: 1
=== matched region (verbatim):
<!-- BEGIN GOC v0.1.0 -->
old-block-1 content
<!-- BEGIN GOC v0.2.0 -->
USER-AUTHORED CONTENT BETWEEN BEGINS (will be lost)
<!-- END GOC -->

=== file after _append_marker_block writes the current version:
# Header

User text above the block.

<!-- BEGIN GOC v0.0.20.post1.dev361 -->
fresh briefing body
<!-- END GOC -->

User text below the block.

=== "USER-AUTHORED CONTENT BETWEEN BEGINS" survived? False
=== second BEGIN marker survived? False
=== FAIL: silent data loss
```

## Why it matters

The reachability path is the standard `goc install` / `goc upgrade`
flow — every consumer runs this function against `AGENTS.md`,
`CLAUDE.md`, or `CLAUDE.local.md`. The trigger preconditions are
narrow but plausible:

- **Resolved merge conflict that kept both sides' BEGIN line.** A
  conflict in the briefing block during a long-lived branch merge can
  leave two `<<<<<<< HEAD` BEGINs and one consolidated END after the
  human picks "accept both" or hand-resolves carelessly. The next
  `goc upgrade` quietly deletes the half they wanted to keep.
- **Interrupted release-rewrite.** `scripts/release_rewrite_versions.py`
  rewrites the BEGIN tag's version literal. If the process is killed
  between writing the new BEGIN and removing the old (e.g., a
  concurrent `goc upgrade` race in a worktree), the file briefly
  contains two BEGIN tags. A subsequent rewrite then loses the
  intermediate content.
- **User authored a literal example.** A `CLAUDE.local.md` that
  documents the GoC marker convention by quoting `<!-- BEGIN GOC
  v0.0.1 -->` as an example will look to the regex like a real second
  marker. The next `goc upgrade` swallows the user's commentary
  between their example and the real marker.

Closure is not frozenness for sibling cards in this family:
[append-marker-block-treats-briefing-text-as-regex-replacement-template](../append-marker-block-treats-briefing-text-as-regex-replacement-template/)
hardened the replacement against backreference injection;
[install-marker-merge-rewrites-crlf-briefing-files-to-lf](../install-marker-merge-rewrites-crlf-briefing-files-to-lf/)
hardened newline handling;
[strip-goc-block-collapses-blank-lines-around-marker-during-upgrade](../strip-goc-block-collapses-blank-lines-around-marker-during-upgrade/)
hardened the strip regex's blank-line greedy boundary. None of them
detect multiple BEGIN tags.

## Sibling sweep

The same non-greedy `.*?` pattern lives in `_strip_goc_block`:

```python
# goc/install.py:200
pattern = re.compile(rf"\n*{GOC_BEGIN_RE.pattern}.*?{re.escape(GOC_END)}\n*", re.DOTALL)
new = pattern.sub("\n\n", text).strip()
```

On the same corrupted input, this regex consumes the same region and
removes it — losing user content between the two BEGIN markers in
exactly the same way. Whatever fix lands for `_append_marker_block`
should be applied to `_strip_goc_block` too (or both should call a
shared helper).

## Decision required

Three credible fix paths:

1. **Fail loudly.** If `len(GOC_BEGIN_RE.findall(text)) != 1` (or
   != number of `<!-- END GOC -->`), raise a clear error pointing
   the user at the malformed marker pair and asking them to clean
   up by hand. Refuses to silently lose data; costs the user a
   manual repair step when corruption occurs.
2. **Anchor to last END.** Switch the regex to greedy (`.*` not
   `.*?`) so the match spans from the **first** BEGIN to the **last**
   END. Eats all intermediate markers and the content between them —
   which is the same data loss, just deterministic across N pairs.
   No better than today for the two-BEGIN-one-END case.
3. **Detect-and-consolidate.** When multiple BEGIN markers are
   detected, walk them, keep the union of the regions, and emit a
   warning that the file had a malformed marker pair. Preserves
   intent; harder to get right (what does "union" mean if the second
   BEGIN comes after the END?).

Recommendation: **option 1** — symmetry with the project's general
preference (e.g., `goc validate` errors loudly on schema drift rather
than silently fixing) and the fact that the precondition is
malformed input the user should know about. The current behavior is
the worst of both worlds: it doesn't tell the user, and it doesn't
preserve their data.

The picked option determines the DoD shape:

- Option 1 → `TDD: malformed input raises; existing one-marker tests
  still pass`.
- Option 2 or 3 → `TDD: two-BEGIN-one-END input preserves <X> on
  rewrite`.
