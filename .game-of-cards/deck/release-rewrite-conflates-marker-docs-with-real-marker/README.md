---
title: release-rewrite-conflates-marker-docs-with-real-marker
summary: "The release version-rewrite script's AGENTS.md regex matches not only the real `<!-- BEGIN GOC v… -->` block opener but also documentation that mentions the marker syntax in prose. Once AGENTS.md gained doc references to the marker, every release dispatch fails at the \"Rewrite version literals\" step with \"expected 1 replacement(s), made 3\"."
status: done
stage: null
contribution: medium
created: "2026-05-19T17:48:17Z"
closed_at: "2026-05-19T17:59:24Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] release_rewrite_versions.py only rewrites the real marker, never doc mentions
  - [x] running the script locally against current AGENTS.md succeeds with exactly 1 replacement
  - [x] release dispatch for v0.0.20 reaches the "Create and push release tag" step
worker: {who: Rodja Trappe, where: main}
---

# release-rewrite-conflates-marker-docs-with-real-marker

## Location

`scripts/release_rewrite_versions.py:118-123` — the AGENTS.md rewrite block.

## What's broken

The script's final pattern matches the dogfood marker:

```python
_replace(
    ROOT / "AGENTS.md",
    r"<!-- BEGIN GOC v[^>]+ -->",
    f"<!-- BEGIN GOC v{version} -->",
    expected=1,
)
```

The character class `[^>]+` is "anything but `>`", which matches not only
real semver markers (`v0.0.19`) but also the literal placeholder text
`vX.Y.Z` that AGENTS.md uses when **documenting** the marker syntax. As
of HEAD, AGENTS.md contains three matches:

- Line 166 — `` per repo. The `<!-- BEGIN GOC vX.Y.Z -->` marker in `AGENTS.md` and ``
- Line 307 — `` `<!-- BEGIN GOC vX.Y.Z -->` and `<!-- END GOC -->`. Content above or below ``
- Line 368 — `<!-- BEGIN GOC v0.0.19 -->` (the real block opener written by `goc install`)

Only line 368 should be rewritten. The other two are prose mentions in
backticks, explaining the marker convention to readers.

The script's docstring already states the rewrite intent:

> The rewrite is surgical: each match is anchored on enough surrounding
> context that bumping a real release version cannot collide with
> unrelated `"version"` fields…

So this AGENTS.md pattern is the only one in the script that violates
its own contract. Every other pattern is line-anchored (`^…$`) or
context-anchored (`"name": "game-of-cards"`).

## Empirical evidence

`gh run view --log-failed 26114783065` (the v0.0.20 dispatch):

```
Rewrite version literals
  ERROR: AGENTS.md: expected 1 replacement(s), made 3.
  Pattern: '<!-- BEGIN GOC v[^>]+ -->'
##[error]Process completed with exit code 1.
```

Local repro:

```bash
$ uv run python -c "import re; \
  text = open('AGENTS.md').read(); \
  print(len(re.findall(r'<!-- BEGIN GOC v[^>]+ -->', text)))"
3
```

## Why it matters

Every release dispatch will fail until this is fixed — `gh workflow run
release.yml -f version=…` no longer produces a release. v0.0.20 is
already blocked. The two prose mentions of `vX.Y.Z` were added during
recent AGENTS.md reorganization (load-claude-instructions-from-agents
landed the bulk of the documentation cross-references). The regression
was latent: v0.0.19's release ran before those mentions existed.

## Fix

Tighten the pattern so it matches only the real block opener written by
`goc install`. Two structural anchors apply to `goc install`'s output
but never to prose mentions inside backticks:

1. The real marker is **at line start** (column 0, no indentation,
   no backticks before it).
2. The real marker contains a **real semver triple** (`\d+\.\d+\.\d+`),
   not the placeholder `X.Y.Z`.

Applying both gives a pattern that's robust to future doc additions:

```python
_replace(
    ROOT / "AGENTS.md",
    r"^<!-- BEGIN GOC v\d+\.\d+\.\d+ -->$",
    f"<!-- BEGIN GOC v{version} -->",
    expected=1,
)
```

`re.MULTILINE` is already set in `_replace`, so `^` and `$` anchor at
line boundaries. Combining the two anchors is belt-and-suspenders: line
start alone would suffice today, but a future doc block that puts the
marker syntax at column 0 (e.g. inside a fenced code block) would
re-trigger the bug. Requiring real digits closes that escape hatch.
