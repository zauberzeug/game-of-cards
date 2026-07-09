---
title: openclaw-skill-porter-inline-bang-regex-misses-indented-blocks
summary: "The porter's INLINE_BANG_BLOCK_RE anchors at column 0, so an indented `!`-prefixed pre-exec block (pull-card SKILL.md's consultation-hook cat) survives the port verbatim. OpenClaw has no `!` pre-execute, so the shipped npm payload carries dead Claude Code-only syntax at the Andon-cord consultation step; the --check drift guard compares against the porter's own output and cannot catch it."
status: active
stage: null
contribution: medium
created: "2026-07-09T01:13:57Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — no ported SKILL.md line carries a `!`-prefixed backtick block at any indentation
  - [ ] TDD: a regression test asserts `render_skill` neutralizes an indented inline bang block while preserving its indentation
  - [ ] MECHANICAL: `python3 scripts/port_skills_to_openclaw.py` re-run; the committed openclaw-plugin/skills/pull-card/SKILL.md no longer carries the pre-exec syntax
  - [ ] MECHANICAL: `python3 scripts/port_skills_to_openclaw.py --check` and the regression suite are green
worker: {who: "claude[bot]", where: main}
---

# OpenClaw skill porter's inline-bang stripper is anchored at column 0, so indented pre-exec blocks ship un-neutralized

## Location

`scripts/port_skills_to_openclaw.py:116`

## What's broken

The porter neutralizes Claude Code's `!`-prefixed pre-exec backtick
blocks with a column-0-anchored regex:

```python
INLINE_BANG_BLOCK_RE = re.compile(r"^!`([^`]+)`", re.MULTILINE)
```

Its own comment states the intent it fails to meet: "Inline
`!`backtick`` blocks scattered through the body (outside ## Context).
Claude Code pre-executes these and embeds the output; OpenClaw has no
equivalent. Convert to a plain backticked example."

`goc/templates/skills/pull-card/SKILL.md:126` carries exactly such a
block, indented two spaces because it sits inside a numbered-list
step:

```
  !`cat .game-of-cards/hooks/pull-card.md 2>/dev/null || true`
```

The anchor never matches the indented line, so the committed
`openclaw-plugin/skills/pull-card/SKILL.md:122` (shipped to OpenClaw
consumers via npm) still contains the raw `!`-prefixed block.

## Why it matters

OpenClaw has no `!` pre-execute syntax, so the shipped skill presents
dead Claude Code-only syntax at the decision-class consultation step —
the very next instruction reads "If the consuming repo defined a
consultation skill or rubric in the hook above, follow it", but
nothing was executed and there is no "hook above". The reachability
path is concrete: the porting script is the *only* producer of
`openclaw-plugin/skills/`, and the defective output is already
committed.

The drift guard is structurally blind here:
`python3 scripts/port_skills_to_openclaw.py --check` compares the
committed tree against the porter's *own* output, so a porter logic
bug passes clean — the same failure mode the closed
[openclaw-skill-porter-context-regex-misses-parenthetical-headers](../openclaw-skill-porter-context-regex-misses-parenthetical-headers/)
card documented for the `## Context` heading regex.

## Empirical evidence

```
$ uv run python .game-of-cards/deck/openclaw-skill-porter-inline-bang-regex-misses-indented-blocks/reproduce.py
DEFECT: ported pull-card/SKILL.md line 122 keeps pre-exec syntax: '  !`cat .game-of-cards/hooks/pull-card.md 2>/dev/null || true`'
exit=1
```

## Fix

Widen the anchor to tolerate leading whitespace and preserve the
indentation in the replacement:

```python
INLINE_BANG_BLOCK_RE = re.compile(r"^([ \t]*)!`([^`]+)`", re.MULTILINE)
...
text = INLINE_BANG_BLOCK_RE.sub(r"\1`\2`", text)
```

Then re-run the porter and commit the re-ported
`openclaw-plugin/skills/pull-card/SKILL.md`. Mechanical, single-file,
no credible alternative — filed at `human_gate: none`.
