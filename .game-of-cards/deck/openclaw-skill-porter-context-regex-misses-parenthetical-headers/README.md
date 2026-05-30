---
title: openclaw-skill-porter-context-regex-misses-parenthetical-headers
summary: "`scripts/port_skills_to_openclaw.py`'s `CONTEXT_BLOCK_RE` requires a bare `## Context\\n\\n` header, so any Context section whose heading carries a parenthetical qualifier (`## Context (read but distrust …)`, `## Context (project-local extension)`) is silently skipped. The host-neutral `Run these via the goc tool …` paragraph is never injected — the ported skills under `openclaw-plugin/skills/{audit-deck,refine-deck}/SKILL.md` end up with bare backticked commands and no instruction for an OpenClaw agent on how to obtain that context. The porter's idempotence drift guard does not catch this: the wrong output is stable, so re-port is a no-op."
status: done
stage: null
contribution: medium
created: "2026-05-30T01:49:53Z"
closed_at: "2026-05-30T01:56:07Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero on a fixed checkout — currently exits 1 because `CONTEXT_BLOCK_RE` matches 3 of 5 Context-bearing source skills; the fix makes it match all 5.
  - [x] MECHANICAL: `CONTEXT_BLOCK_RE` accepts an arbitrary suffix on the `## Context` heading line (e.g. `r"## Context\b[^\n]*\n\n((?:!`[^`]+`\n\n?)+)"`), and the replacement preserves the original heading verbatim (so `## Context (project-local extension)` round-trips, not collapses to `## Context`).
  - [x] MECHANICAL: `python scripts/port_skills_to_openclaw.py` re-ports `openclaw-plugin/skills/audit-deck/SKILL.md` and `openclaw-plugin/skills/refine-deck/SKILL.md` with the host-neutral guidance paragraph + bulleted command list under the Context heading; diff reviewed and committed.
  - [x] MECHANICAL: `python scripts/port_skills_to_openclaw.py --check` is green (porter is idempotent over the new output).
  - [x] PROCESS: a regression test under `tests/` asserts that every source skill containing `## Context` produces a ported output whose Context section contains the guidance paragraph (catches the next variation of the same regex-too-narrow drift).
worker: {who: "claude[bot]", where: main}
---

# OpenClaw skill porter Context regex misses parenthetical headers

## Location

- `scripts/port_skills_to_openclaw.py:84-87` — the regex.
- `scripts/port_skills_to_openclaw.py:121` — the call site
  (`CONTEXT_BLOCK_RE.sub(transform_context_block, text)`).
- `goc/templates/skills/audit-deck/SKILL.md:11`,
  `goc/templates/skills/refine-deck/SKILL.md:10` — the two source
  skills whose Context heading carries a parenthetical qualifier and is
  consequently skipped.
- `openclaw-plugin/skills/audit-deck/SKILL.md:6-16`,
  `openclaw-plugin/skills/refine-deck/SKILL.md:6-…` — the ported
  outputs missing the host-neutral guidance paragraph.

## What's broken

The porter strips Claude Code's `!`backtick`` pre-execute syntax inside
`## Context` sections and replaces it with a host-neutral paragraph
explaining how an OpenClaw agent should obtain that context (call the
`goc` tool, or shell out for bare listings). The trigger is a regex
keyed on a bare heading:

```python
# scripts/port_skills_to_openclaw.py:84-87
CONTEXT_BLOCK_RE = re.compile(
    r"## Context\n\n((?:!`[^`]+`\n\n?)+)",
    re.MULTILINE,
)
```

Two of the five source skills carry a parenthetical qualifier on the
Context heading:

```
goc/templates/skills/audit-deck/SKILL.md:11
    ## Context (read but distrust — these are hypotheses, not ground truth)

goc/templates/skills/refine-deck/SKILL.md:10
    ## Context (project-local extension)
```

Because the regex requires `## Context\n\n` (no characters between
`Context` and the first newline), it does not match those headings. The
`CONTEXT_BLOCK_RE.sub(...)` call returns the text unchanged at that
section, and processing falls through to the generic
`INLINE_BANG_BLOCK_RE` which strips the leading `!` from each backtick
block. The bullets are still preserved as `` `command` `` lines — but
the explanatory paragraph an OpenClaw agent needs is never injected.

Verbatim contrast — `openclaw-plugin/skills/standup/SKILL.md` (bare
`## Context` header, matched by the regex):

```
## Context

Before running the body of this skill, the agent should see current
deck state. Run these via the `goc` tool (top-level filters like
`--status` / `--tag` / `--worker` map to the tool's `flags`
parameter; the subcommand maps to `verb`). For bare-queue listings
with no subcommand, shell out via the `exec` tool:

- `git fetch --quiet 2>/dev/null; behind=$(...) ...`
- `goc --status active -v`
- ...
```

vs. `openclaw-plugin/skills/audit-deck/SKILL.md` (parenthetical
heading, skipped):

```
## Context (read but distrust — these are hypotheses, not ground truth)

`goc`

`goc --done`

`goc --status disproved`

`goc --tag unverified`

`cat .game-of-cards/hooks/audit-deck.md 2>/dev/null || true`
```

No guidance paragraph; no bullet list; no acknowledgement that these
are commands the agent must invoke rather than text to read.

## Empirical evidence

`reproduce.py` compiles the porter's `CONTEXT_BLOCK_RE` and runs it
against every source skill that contains a `## Context` heading. With
the current regex it prints:

```
Skill            REGEX MATCH    EXPECTED
audit-deck       MISS           MATCH
next-card        MATCH          MATCH
refine-deck      MISS           MATCH
retrospective    MATCH          MATCH
standup          MATCH          MATCH

Misses: 2 of 5 — porter silently skipped audit-deck, refine-deck.
exit 1
```

After loosening the regex to accept a parenthetical suffix
(`r"## Context\b[^\n]*\n\n(...)"`), all five skills match and
`reproduce.py` exits 0.

## Why it matters

The OpenClaw plugin under `openclaw-plugin/skills/` ships these skill
bodies verbatim to consumers. An OpenClaw agent invoking the
`audit-deck` or `refine-deck` skill reads bare backticked commands
under the Context heading with no instruction on how those commands
are meant to be executed (the host has no `!`backtick`` pre-execute
semantics — Claude Code's affordance — so the agent must be told
explicitly to call the `goc` tool). The standup/next-card/retrospective
skills already carry that instruction; audit-deck and refine-deck do
not.

Reachability: the porter is the only mechanism that produces
`openclaw-plugin/skills/<name>/SKILL.md`. Every consumer who installs
the OpenClaw plugin gets the buggy output. The
[openclaw-plugin-ported-skills-drift-silently-from-templates](../openclaw-plugin-ported-skills-drift-silently-from-templates/)
remediation added a `--check` drift guard, but the guard asserts the
porter is **idempotent**, not **correct** — re-running the porter
produces byte-identical (wrong) output, so the guard stays green while
the bug persists. The CI parity test in
`tests/test_plugin_mirror_parity.py` is similarly fooled.

Two source skills already hit this today; any future skill author who
adopts the `## Context (qualifier)` shape — a reasonable readability
choice that one card body
([refine-deck-skill-missing-consuming-repo-hook-override](../refine-deck-skill-missing-consuming-repo-hook-override/))
explicitly recommends — will silently regress.

## Fix

Loosen `CONTEXT_BLOCK_RE` so the heading line accepts any text after
the literal `Context` word boundary, then have `transform_context_block`
preserve whatever the actual heading was (so `## Context (project-local
extension)` round-trips intact rather than collapsing to `## Context`):

```python
# Suggested rewrite.
CONTEXT_BLOCK_RE = re.compile(
    r"^(## Context\b[^\n]*)\n\n((?:!`[^`]+`\n\n?)+)",
    re.MULTILINE,
)


def transform_context_block(match: re.Match[str]) -> str:
    heading = match.group(1)        # e.g. "## Context (project-local extension)"
    raw = match.group(2)
    commands = re.findall(r"!`([^`]+)`", raw)
    bullet = "\n".join(f"- `{cmd}`" for cmd in commands)
    return (
        f"{heading}\n\n"
        "Before running the body of this skill, the agent should see current "
        "deck state. Run these via the `goc` tool (top-level filters like "
        "`--status` / `--tag` / `--worker` map to the tool's `flags` "
        "parameter; the subcommand maps to `verb`). For bare-queue listings "
        "with no subcommand, shell out via the `exec` tool:\n\n"
        f"{bullet}\n\n"
    )
```

Then re-run `python scripts/port_skills_to_openclaw.py` and commit the
two refreshed ported files. The CI parity test
(`tests/test_plugin_mirror_parity.py`) will fail until the re-port is
committed; the `--check` flag of the porter mirrors that signal locally.

Add a regression test that asserts every source skill containing
`## Context` produces a ported output whose Context section contains
the marker phrase `Before running the body of this skill` — that
catches the next "regex too narrow" variant of this drift class.

## Cross-references

- [openclaw-plugin-ported-skills-drift-silently-from-templates](../openclaw-plugin-ported-skills-drift-silently-from-templates/) (done) — added the porter's idempotence guard; idempotence is the necessary-but-not-sufficient half of correctness, which this card completes.
- [openclaw-skill-porter-drops-sibling-asset-files-from-skill-directories](../openclaw-skill-porter-drops-sibling-asset-files-from-skill-directories/) (open) — sibling defect in the same porter; only `SKILL.md` is copied, sibling asset files are dropped.
- [openclaw-skill-porter-never-prunes-orphaned-ported-skills](../openclaw-skill-porter-never-prunes-orphaned-ported-skills/) (open) — sibling defect; deletions in source don't propagate.
- [refine-deck-skill-missing-consuming-repo-hook-override](../refine-deck-skill-missing-consuming-repo-hook-override/) (done) — the closure that introduced `## Context (project-local extension)`; the closing log notes the heading shape but the porter wasn't re-checked.
