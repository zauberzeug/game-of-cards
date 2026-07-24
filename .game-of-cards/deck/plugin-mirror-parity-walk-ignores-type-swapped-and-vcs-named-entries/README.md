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
tags: [bug, infra, unverified]
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
`ignore=` override near `goc/engine.py:1618`.

## Hypothesis (unverified — parked by an audit round)

```python
out += [
    f"{prefix}{n} (differs)"
    for n in cmp.diff_files            # engine.py:1464 — common_funny/funny_files never read
    if (prefix + n) not in exclude
]
```

A hunter-run probe (temp `goc/` + byte-identical `claude-plugin/` tree,
patched `engine.REPO_ROOT`) reported `validate_plugin_mirror_parity()` → `[]`
for (a) `claude-plugin/goc/engine.py` replaced by a *directory*, (b) a broken
symlink in the mirror, and (c) content drift under a `goc/tags/` subtree,
while plain content drift correctly returned
`['plugin mirror drift: goc vs claude-plugin/goc: engine.py (differs)']`.
Not independently re-run in a committed reproduce.py yet — hence
`unverified`.

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
