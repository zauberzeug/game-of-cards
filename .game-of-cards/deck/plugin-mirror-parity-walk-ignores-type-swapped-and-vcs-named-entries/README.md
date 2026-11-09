---
title: plugin-mirror-parity-walk-ignores-type-swapped-and-vcs-named-entries
summary: "validate_plugin_mirror_parity's _walk reads only left_only/right_only/diff_files/subdirs from filecmp.dircmp: it never reports common_funny (file-vs-directory type swaps, stat failures like broken symlinks) or funny_files, and _DeepDircmp inherits filecmp.DEFAULT_IGNORES so directories named tags, CVS, RCS, .hg etc. are skipped wholesale — all three shapes pass the byte-for-byte parity tripwire clean."
status: open
stage: null
contribution: medium
created: "2026-07-24T01:57:31Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] TDD: reproduce.py lands and exits non-zero on current code for all three shapes (type swap, broken symlink, DEFAULT_IGNORES-named dir), then zero after the fix — drop the unverified tag when it lands
  - [ ] TDD: regression test asserts validate_plugin_mirror_parity reports common_funny / funny_files entries and drift inside a directory named `tags`
  - [ ] MECHANICAL: _DeepDircmp passes ignore=[] (or equivalent) so filecmp.DEFAULT_IGNORES names are compared
  - [ ] MECHANICAL: uv run goc validate passes
---

# plugin-mirror-parity-walk-ignores-type-swapped-and-vcs-named-entries

## Summary

`validate_plugin_mirror_parity`'s `_walk` reads only `left_only` /
`right_only` / `diff_files` / `subdirs` from `filecmp.dircmp`: it never
reports `common_funny` (file-vs-directory type swaps, stat failures such as
broken symlinks) or `funny_files`, and `_DeepDircmp` inherits
`filecmp.DEFAULT_IGNORES`, so directories named `tags`, `CVS`, `RCS`, `.hg`,
etc. are skipped wholesale. All three shapes pass the "byte-for-byte" parity
tripwire clean.

## Location

`goc/engine.py:1444-1472` (`_walk`); `_DeepDircmp` instantiation without an
`ignore=` override near `goc/engine.py:1857`.

## Hypothesis (confirmed 2026-11-09 — see § Empirical evidence)

```python
out += [
    f"{prefix}{n} (differs)"
    for n in cmp.diff_files            # engine.py:1703 — common_funny/funny_files never read
    if (prefix + n) not in exclude
]
```

A hunter-run probe (temp `goc/` + byte-identical `claude-plugin/` tree,
patched `engine.REPO_ROOT`) reported `validate_plugin_mirror_parity()` → `[]`
for (a) `claude-plugin/goc/engine.py` replaced by a *directory*, (b) a broken
symlink in the mirror, and (c) content drift under a `goc/tags/` subtree,
while plain content drift correctly returned
`['plugin mirror drift: goc vs claude-plugin/goc: engine.py (differs)']`.
The committed [`reproduce.py`](reproduce.py) re-ran all three shapes, plus
the fourth below, on 2026-11-09.

### Fourth shape: a *valid* outside-pointing symlink (verified 2026-07-26)

An audit round confirmed a fourth shape that the `common_funny` /
`funny_files` fix above would **not** catch. A mirror entry that is a
*working* symlink to a file outside the payload, whose target content matches
the source, is reported as `same_files`:

```
mirror/engine.py -> ../outside/engine.py   (valid link, identical content)

left_only  : []      right_only : []      diff_files : []
common_funny: []     funny_files: []      same_files : ['engine.py']
=> parity walk reports drift: False
```

`filecmp` follows the link and compares the target's bytes, so nothing lands
in the "funny" buckets — they only collect stat failures and type mismatches.
This matters more than the broken-symlink case: AGENTS.md singles this shape
out as the one that breaks consumers silently — "those assets must be **real
files** (not symlinks pointing outside the subtree, which silently disappear
on consumer install)" — because Claude Code's marketplace install extracts
only the `./claude-plugin` subtree, so the link target is simply absent on the
consumer's disk while every local check stays green. Whatever fix this card
takes should therefore assert entry *type* (`Path.is_symlink()` / `os.lstat`)
across the mirror trees, not just read the extra `dircmp` buckets.

## Empirical evidence

[`reproduce.py`](reproduce.py) copies this repo's real `goc/` and
`claude-plugin/` trees into a temp dir, points `engine.REPO_ROOT` at the copy,
and applies each shape to a fresh copy. On main at `92f8bb55` (2026-11-09) it
exits 1:

```text
control 1 — untouched copy        : no drift
control 2 — one-byte content edit : ['plugin mirror drift: goc vs claude-plugin/goc: engine.py (differs)']
a. type swap (file -> directory)        : passes clean
b. broken symlink in the mirror         : passes clean
c. content drift under goc/tags/        : passes clean
d. working symlink to an outside file   : passes clean

DEFECT PRESENT: 4 of 4 mirror shapes pass the parity walk clean.
```

The two controls show the walk is live on the copy before any shape is
judged. Shape (c) uses a `tags/` directory, which `goc/` does not have today,
so it pins the `DEFAULT_IGNORES` skip rather than a drift that exists now.

## Why it matters

The validator's whole contract (established by the closed card
[extend-skill-parity-tripwire-to-claude-plugin-mirrors](../extend-skill-parity-tripwire-to-claude-plugin-mirrors/)
and deepened by
[validate-plugin-mirror-parity-uses-shallow-filecmp-missing-content-drift](../validate-plugin-mirror-parity-uses-shallow-filecmp-missing-content-drift/))
is drift detection between `goc/` and the shipped plugin mirrors. A mirror
shipping a dir-for-file swap or a dead symlink ships broken payloads to
consumers while `goc validate` stays green. Reachability: the mirrors are
real checked-in trees; a bad merge, a crashed sync, or a hand edit produces
exactly these shapes, and `scripts/sync_plugin_assets.py --check` only guards
this repo's CI — `goc validate` is the tripwire consumers and pre-push hooks
run.

## Falsification recipe

Build a minimal `goc/` + byte-identical mirror in a temp dir, patch
`engine.REPO_ROOT`, apply each of the three mutations above, and call
`validate_plugin_mirror_parity()`. The claim is falsified for any mutation
that produces a non-empty error list on current code.

## Decision required

Whether `common_funny` / `funny_files` entries should render as a distinct
message shape (e.g. `(uncomparable)` / `(type mismatch)`) or reuse
`(differs)`, and whether `ignore=[]` should also drop `hide=` defaults —
cosmetic, but it defines the error contract tests pin.
