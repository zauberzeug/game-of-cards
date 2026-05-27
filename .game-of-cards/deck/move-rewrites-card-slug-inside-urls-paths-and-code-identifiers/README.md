---
title: move-rewrites-card-slug-inside-urls-paths-and-code-identifiers
summary: "`goc move`'s bare-slug rewrite anchors only on `[-\\w]`, so a renamed card's slug gets silently rewritten wherever it abuts a `.`, `/`, `(`, or `:` — inside URLs, dotted filenames, and code identifiers — across every tracked file in the repo, not just genuine card cross-references."
status: open
stage: null
contribution: medium
created: "2026-05-27T01:33:24Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] PROCESS: decision recorded in `## Decision required` — which fix path (tighten boundary class / scope rewrite to deck files / drop the bare-slug form) and why.
  - [ ] TDD: `reproduce.py` exits zero — none of the four non-reference contexts (shell function, URL path segment, dotted URL, dotted filename) are rewritten.
  - [ ] TDD: the genuine-prose-mention case in `reproduce.py` still rewrites (`see the card foo-bar for context` → `... baz ...`) — the fix must not throw out legitimate bare-slug references.
  - [ ] EMPIRICAL: a `goc move` dry-run on this repo's own deck still previews the real cross-reference rewrites (H1, markdown link, deck paths) it did before.
  - [ ] MECHANICAL: `goc validate` clean; plugin-asset sync `--check` green.
---

# `goc move` rewrites a card slug inside URLs, paths, and code identifiers

## Location

`goc/engine.py:3944-3956` — `_move_text_rewrite`, the fifth "canonical
text form" (the bare-slug regex), applied repo-wide by
`_move_rewrite_tracked_files` (`engine.py:3985-3993`) over every file
from `git ls-files`.

## What's broken

`_move_text_rewrite` rewrites four explicit reference forms (H1 heading,
`[old](../old/)` markdown link, `.game-of-cards/deck/old/` and `deck/old/`
paths) and then a fifth catch-all bare-slug form:

```python
# Bare slug: not preceded/followed by [-\w] (slug-boundary anchoring)
text = re.sub(rf"(?<![-\w]){esc}(?![-\w])", new, text)
```

The boundary class `[-\w]` excludes `.`, `/`, `(`, and `:`. So the slug is
treated as a standalone token whenever it abuts one of those characters —
exactly the characters that delimit URL path segments, dotted filenames,
and code identifiers. The docstring claims "slug-boundary anchoring," but
a slug embedded in a URL or path is *not* a card cross-reference, yet it
matches.

Compounding the blast radius: `_move_rewrite_tracked_files` runs this over
**every tracked text file in the repo** (`git ls-files`), not just card
bodies under `.game-of-cards/deck/`. So a rename can silently edit
`engine.py`, `schema.yaml`, a shell script, or any doc — anywhere the old
slug happens to appear as a path/URL/identifier token.

The bare-slug form exists to catch genuine prose mentions of a card by its
slug (e.g. "see the card foo-bar for context"). That intent is legitimate;
the over-match is the defect.

## Empirical evidence

`uv run python .game-of-cards/deck/move-rewrites-card-slug-inside-urls-paths-and-code-identifiers/reproduce.py`:

```
=== Non-reference contexts (must NOT be rewritten) ===
  [shell function name]
    in : 'function add-cli() in script.sh'
    out: 'function add-command() in script.sh'
    -> OVER-REWRITTEN (bug)
  [URL path segment]
    in : 'GET /v1/user-api/list'
    out: 'GET /v1/user-rest/list'
    -> OVER-REWRITTEN (bug)
  [URL with dotted file]
    in : 'see http://x.com/foo-bar.html'
    out: 'see http://x.com/baz.html'
    -> OVER-REWRITTEN (bug)
  [dotted filename stem]
    in : 'the file my-tool.py imports'
    out: 'the file renamed.py imports'
    -> OVER-REWRITTEN (bug)

=== Genuine prose mention (SHOULD be rewritten) ===
  in : 'see the card foo-bar for context'
  out: 'see the card baz for context'  (expected 'see the card baz for context')

DEFECT PRESENT: 4 non-reference context(s) over-rewritten: [...]
```

## Why it matters

`goc move` is the supported rename path; agents and humans run it to retitle
cards (the `move-bypasses-title-antipattern-guard` and
`card-rename-leaves-old-title-in-body-and-skips-log-entry` cards show it is
actively exercised). Because the rewrite spans the whole repo and edits
silently, a card slug that collides with a URL segment, a filename stem, or a
kebab-case identifier elsewhere in the tree gets corrupted with no warning —
a data-integrity bug in the rename contract. The `--dry-run` preview
(`_move_preview_sites`) would surface the bogus sites, but only if the
operator reads them, and the default path does not require a dry run.

## Decision required

The bare-slug form's *intent* (rewrite genuine prose mentions of a card by
slug) is worth keeping; the question is how to stop the over-match. Three
credible paths, with trade-offs:

1. **Tighten the boundary class** — extend the negative look-around to also
   reject `.`, `/`, `(`, `:` (and likely `#`, `=`): `(?<![-\w./(:])` /
   `(?![-\w./):])`. Keeps the repo-wide sweep. **Risk:** a slug at the end of
   a sentence ("...see foo-bar.") is followed by `.` and would no longer be
   rewritten — losing a legitimate prose case. Needs a careful boundary set
   that excludes path/URL/identifier delimiters but not sentence punctuation.

2. **Scope the bare-slug rewrite to deck files only** — run forms 1-4
   repo-wide (explicit references can legitimately live anywhere) but restrict
   the bare-slug catch-all to files under `.game-of-cards/deck/`, where bare
   prose mentions of a card by slug actually occur. **Risk:** a bare mention
   in `AGENTS.md` or another doc would no longer be auto-updated; acceptable
   if such mentions are rare and forms 1-4 cover the real cross-links.

3. **Drop the bare-slug form entirely** — rely only on the four explicit
   reference forms. **Risk:** prose mentions of a card by bare slug go stale
   after a rename. Simplest and safest against corruption, but loses the
   feature.

Recommendation leans toward **(2)** — it preserves the feature where it is
actually used and eliminates the cross-tree corruption blast radius — but the
boundary-set details of (1) and the loss-of-coverage trade-off of (2)/(3) are
a human call. Whichever is chosen, the genuine-prose case in `reproduce.py`
encodes the must-still-work contract for paths (1) and (2).
