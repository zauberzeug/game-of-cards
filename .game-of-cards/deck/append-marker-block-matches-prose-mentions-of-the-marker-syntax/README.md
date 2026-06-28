---
title: append-marker-block-matches-prose-mentions-of-the-marker-syntax
summary: "`_append_marker_block`'s regex is unanchored across `re.DOTALL`. When a briefing file's user-authored prose explains the marker convention by quoting the literal `<!-- BEGIN GOC vX.Y.Z -->` and `<!-- END GOC -->` strings (e.g., AGENTS.md teaching consumers how the merge works), the regex matches the prose mention as if it were a real block opener. `pattern.sub` then rewrites the prose with the freshly-rendered GoC block, silently corrupting user documentation. Distinct from the two sibling open cards (which assume a malformed prior install state) — this one fires on a well-formed input file that merely *mentions* the marker syntax. This repo's own `AGENTS.md` line 368 is a live trigger."
status: open
stage: null
contribution: medium
created: "2026-06-01T04:42:20Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [ ] PROCESS: human picks one of the fix paths in `## Decision required`; the choice is recorded inline. Coordinate with the two sibling cards (`append-marker-block-loses-content-between-stacked-begin-markers`, `append-marker-block-duplicates-content-when-file-has-two-complete-marker-blocks`) — a single regex hardening can close all three at once.
  - [ ] TDD: `reproduce.py` exits zero (prose mention preserved verbatim; real block rewritten in place).
  - [ ] TDD: regression test in `tests/test_install.py` covers the prose-mention input shape against `_append_marker_block` AND `_strip_goc_block` (sibling sweep — same unanchored shape at `goc/install.py:200`).
  - [ ] TDD: existing one-block install/upgrade tests still pass (no regression in the happy path); existing two-BEGIN-one-END and two-complete-blocks regressions from the sibling cards still pass.
  - [ ] MECHANICAL: `goc validate` passes; plugin mirrors re-synced if the engine changed.
---

# `_append_marker_block` rewrites user prose that quotes the marker syntax

## Location

`goc/install.py:1193`

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

The same unanchored-regex shape appears at `goc/install.py:200`
inside `_strip_goc_block`, so the sibling sweep below covers both
call sites.

`GOC_BEGIN_RE` (`goc/install.py:32`):

```python
GOC_BEGIN_RE = re.compile(r"<!-- BEGIN GOC v[\w.+!-]+ -->")
GOC_END = "<!-- END GOC -->"
```

The version character class `[\w.+!-]+` accepts the placeholder
literal `vX.Y.Z` that consumers (and this repo's own `AGENTS.md`)
use when documenting the marker convention.

## What's broken

The combined pattern is:

```python
rf"{GOC_BEGIN_RE.pattern}.*?{re.escape(GOC_END)}\n?"
```

with `re.DOTALL`. With no line anchors (`^...$` MULTILINE) and no
strict-semver predicate on the version part, any line that quotes
the marker text as prose — even inside a backtick code-span,
heading, or docstring — is a valid starting point. `pattern.sub`
then replaces **every** non-overlapping match with the freshly-rendered
block, so:

1. If user prose contains both `<!-- BEGIN GOC vX.Y.Z -->` and
   `<!-- END GOC -->` (on the same line or close enough that the
   lazy `.*?` reaches an END before the real block), the prose span
   is rewritten as the new block — corrupting the user's
   documentation and producing a duplicate block in the file.
2. If user prose contains only the BEGIN mention (no nearby prose
   END), the regex matches from the prose BEGIN all the way to the
   real block's END, consuming everything in between (real block
   opener, the entire briefing the user authored above it that is
   *supposed* to be preserved).

## Empirical evidence

`uv run python .game-of-cards/deck/append-marker-block-matches-prose-mentions-of-the-marker-syntax/reproduce.py`:

```
# of matches: 2
match 0: span=(94, 142), text='<!-- BEGIN GOC vX.Y.Z -->` and `<!-- END GOC -->'
match 1: span=(177, 243), text='<!-- BEGIN GOC v0.0.23 -->\nREAL BRIEFING CONTENT\n<!-- END GOC -->\n'

=== AFTER REWRITE ===
# Project notes

The marker block below is rewritten by goc upgrade.

Don't edit between the `<!-- BEGIN GOC v0.0.24 -->
NEW BRIEFING CONTENT
<!-- END GOC -->
` markers.

More user prose here.

<!-- BEGIN GOC v0.0.24 -->
NEW BRIEFING CONTENT
<!-- END GOC -->

Footer text.
```

The prose mention on line 5 of the input — a perfectly reasonable
sentence a consumer might write to explain the GoC convention — is
shredded by the rewrite: the new block is injected inside the user's
backticks, the surrounding sentence is broken across multiple lines,
and the file now contains two copies of the briefing block.

## Reachability — this repo's own AGENTS.md is a live trigger

`AGENTS.md` line 368 in HEAD:

```
`<!-- BEGIN GOC vX.Y.Z -->` and `<!-- END GOC -->`. Content above or below
```

is a prose explanation of the marker convention. The regex matches it
today. The only reason this repo's own `goc install` runs do not
visibly corrupt `AGENTS.md` is that the release workflow rewrites the
marker block via `scripts/release_rewrite_versions.py` (which was
already hardened — see closed sibling
[release-rewrite-conflates-marker-docs-with-real-marker](../release-rewrite-conflates-marker-docs-with-real-marker/)),
not via `_append_marker_block`. Any consumer who:

- runs `goc upgrade` (which calls `_sync_methodology_blocks` →
  `_append_marker_block` on AGENTS.md / CLAUDE.md), AND
- has authored prose in their briefing file that quotes the marker
  literals (a natural thing to do when documenting one's own setup)

trips this defect silently. The corruption is path-dependent on user
documentation style, which makes it especially insidious — the
project that *teaches* the convention gets bitten when it explains it.

## Why it matters

Reachability path: `goc install` and `goc upgrade` both call
`_sync_methodology_blocks` (`goc/install.py:1234`) → `_append_marker_block`
(`goc/install.py:1181`). Every consumer who runs `goc upgrade` after
adding documentation about the marker convention to their AGENTS.md
or CLAUDE.md is vulnerable. The bug is silent — the rewrite "succeeds"
and the file is left in a state where the user's prose is corrupted
and a duplicate block exists.

The marker-bounded merge is the engine's safety contract for
AGENTS.md / CLAUDE.md (per AGENTS.md § "Marker-bounded merge for
AGENTS.md / CLAUDE.md"):

> Content above or below those markers is preserved across `goc
> install` / `goc upgrade`.

This defect violates the contract: content above the marker is *not*
preserved if it happens to mention the marker syntax.

## Family context

This is the third instance of the same root-cause shape on
`_append_marker_block`. The first instance was filed and **fixed** on
a sibling surface (release script, closed); two more instances were
filed on `_append_marker_block` itself and are open, waiting on a
decision:

- CLOSED: [release-rewrite-conflates-marker-docs-with-real-marker](../release-rewrite-conflates-marker-docs-with-real-marker/) — same root cause on `scripts/release_rewrite_versions.py`. The fix was line-anchored `^...$` with `re.MULTILINE` plus a strict `\d+\.\d+\.\d+` version part. That fix recipe applies here, but was never replicated on `_append_marker_block`.
- OPEN: [append-marker-block-loses-content-between-stacked-begin-markers](../append-marker-block-loses-content-between-stacked-begin-markers/) — 2 BEGINs + 1 END (malformed prior state).
- OPEN: [append-marker-block-duplicates-content-when-file-has-two-complete-marker-blocks](../append-marker-block-duplicates-content-when-file-has-two-complete-marker-blocks/) — 2 complete BEGIN+END blocks (malformed prior state).
- OPEN (this card): well-formed file + user prose that quotes the marker syntax.

Distinct in failure mode: the two existing open cards both assume the
input is *malformed* (recovering from an interrupted upgrade, a hand-
merged conflict, a botched manual edit). This card fires on **well-
formed input** — the file has exactly one real block, and the only
"anomaly" is that the user wrote prose explaining how the convention
works.

The four instances together suggest the meta-fix: harden
`_append_marker_block` (and the sibling shape at `goc/install.py:200`
in `_strip_goc_block`) so prose mentions and malformed states are
both excluded by construction.

## Decision required

The fix recipe is partially established by the closed sibling
([release-rewrite-conflates-marker-docs-with-real-marker](../release-rewrite-conflates-marker-docs-with-real-marker/)),
but the install-side regex needs to match a multi-line span (BEGIN
through END) rather than a single line, so the fix needs adaptation.
Three credible paths, all line-anchored:

### Option A — line-anchor + strict semver

Tighten `GOC_BEGIN_RE` itself to require line-start / line-end and
strict semver:

```python
GOC_BEGIN_RE = re.compile(r"^<!-- BEGIN GOC v\d+\.\d+\.\d+ -->$", re.MULTILINE)
```

Then in `_append_marker_block`, anchor the full-block pattern on
both ends and use `count=1`:

```python
pattern = re.compile(
    r"^<!-- BEGIN GOC v\d+\.\d+\.\d+ -->\n.*?^<!-- END GOC -->\n?",
    re.DOTALL | re.MULTILINE,
)
new_text, n = pattern.subn(lambda _: block, text, count=1)
if n > 1:
    raise ...  # multiple-blocks guard, see Option C
```

Trade-off: tightens the BEGIN-line grammar to strict semver, which
breaks any consumer who hand-edited the version literal (unlikely
but possible). The closed sibling already chose this trade-off on
the release script side.

### Option B — line-anchor only, keep permissive version grammar

Same as Option A but keep `[\w.+!-]+` in the version class to
accept dev / rc / post versions if hatch-vcs ever emits them into a
marker block. The `^...$` MULTILINE anchor is what excludes
prose-in-backticks; the strict-semver tightening is independent.

Trade-off: less defensive than Option A (a dev-build prose mention
quoted in backticks at column 0 would still match), but preserves
forward compatibility with whatever version literal the installer
might one day emit.

### Option C — line-anchor + validate exactly-one-match guard

Either A or B, **plus** validate that the regex matched exactly once
before rewriting. Raise (or warn + skip) if zero matches found, or
if two or more matches found. This also closes both existing open
sibling cards (the two-BEGIN-one-END case becomes
"multiple-matches-detected, refuse to rewrite, surface the conflict
to the user"; the two-complete-blocks case becomes the same).

Trade-off: refuses to rewrite when the input is genuinely malformed,
instead of silently doing the wrong thing. Requires a clear error
message that tells the user how to recover.

### Recommendation (non-binding)

Option C + Option B as the substrate (line-anchored, permissive
version, exactly-one-match guard). Closes this card and both
existing siblings in one fix. Strict-semver (Option A) is a separate
tightening that can be added later if a real dev-build prose-mention
defect surfaces.

## Fix sketch (illustrative — for the C+B choice)

```python
# goc/install.py:32
GOC_BEGIN_RE = re.compile(r"^<!-- BEGIN GOC v[\w.+!-]+ -->$", re.MULTILINE)

# goc/install.py:1193
pattern = re.compile(
    rf"{GOC_BEGIN_RE.pattern}\n.*?^{re.escape(GOC_END)}\n?",
    re.DOTALL | re.MULTILINE,
)
matches = list(pattern.finditer(text))
if not matches:
    _write_text_keep_newline(target, text.rstrip() + "\n\n" + block, newline)
    return
if len(matches) > 1:
    raise InstallError(
        f"{target}: found {len(matches)} marker blocks; refusing to "
        "rewrite. Reconcile manually to a single block, then re-run."
    )
_write_text_keep_newline(target, pattern.sub(lambda _: block, text, count=1), newline)
```

Mirror the same anchoring + exactly-one-match guard on
`_strip_goc_block` (`goc/install.py:200`) so the sibling sweep is
complete.
