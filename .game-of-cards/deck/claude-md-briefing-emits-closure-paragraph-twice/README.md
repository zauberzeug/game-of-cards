---
title: claude-md-briefing-emits-closure-paragraph-twice
summary: "`goc install --briefing-target CLAUDE.md` writes the `**Closure is not frozenness.**` paragraph into the briefing block twice. The paragraph is byte-identical in both `goc/templates/AGENTS_GOC.md` (line 24-28) and `goc/templates/CLAUDE_GOC.md` (line 15-19), and `_briefing_body` concatenates the two templates without dedup when `briefing_target == \"CLAUDE.md\"`. AGENTS.md and CLAUDE.local.md briefing targets are unaffected (they emit AGENTS_GOC.md alone). User-visible result: a CLAUDE.md sole-home install carries a redundant duplicate paragraph in the marker-bounded GoC briefing block."
status: active
stage: null
contribution: low
created: "2026-05-30T01:02:44Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, documentation]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — the briefing body returned by `goc.install._briefing_body(templates, "CLAUDE.md")` contains exactly one occurrence of the phrase `Closure is not frozenness.`.
  - [ ] TDD: a regression test under `tests/` exercises `_briefing_body` across the three briefing targets (AGENTS.md / CLAUDE.md / CLAUDE.local.md) and asserts the paragraph count is exactly one in each.
  - [ ] MECHANICAL: the duplicate paragraph is removed from `goc/templates/CLAUDE_GOC.md` (or, equivalently, `_briefing_body` is taught to deduplicate); the chosen approach is documented in `log.md`.
  - [ ] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green; `python scripts/sync_plugin_assets.py --check` green.
worker: {who: "claude[bot]", where: main}
---

# CLAUDE.md briefing emits the "Closure is not frozenness" paragraph twice

## Location

- `goc/install.py:127-140` — `_briefing_body(templates, briefing_target)`:

  ```python
  def _briefing_body(templates: Path, briefing_target: str) -> str:
      agents_body = (templates / AGENTS_GUIDANCE.template).read_text().rstrip()
      if briefing_target == "CLAUDE.md":
          claude_body = (templates / CLAUDE_GUIDANCE.template).read_text().rstrip()
          return f"{agents_body}\n\n{claude_body}\n"
      return agents_body + "\n"
  ```

- `goc/templates/AGENTS_GOC.md:24-28` — the host-agnostic copy of the paragraph.
- `goc/templates/CLAUDE_GOC.md:15-19` — a byte-identical duplicate.

## What's broken

The two template paragraphs are exact byte-for-byte clones:

```
$ diff <(sed -n '24,28p' goc/templates/AGENTS_GOC.md) \
       <(sed -n '15,19p' goc/templates/CLAUDE_GOC.md)
$ echo $?
0
```

`_briefing_body` is the only producer of the marker-bounded GoC
briefing block written by `goc install` / `goc upgrade`
(`_sync_methodology_blocks` → `_append_marker_block`). For
`briefing_target == "CLAUDE.md"`, it concatenates AGENTS_GOC.md and
CLAUDE_GOC.md without dedup, so the resulting block carries the
"Closure is not frozenness" paragraph twice — once from each
template.

The function's own docstring frames CLAUDE_GOC.md as **Claude-specific
extras** that are appended to the host-agnostic AGENTS_GOC.md body:

> AGENTS.md and CLAUDE.local.md receive the host-agnostic body
> verbatim. CLAUDE.md (sole-home mode) gets the host-agnostic body
> plus the **Claude-specific extras** appended — option (a) from the
> card body (merge inline rather than maintain a unified template).

The "Closure is not frozenness" paragraph is generic methodology
guidance (it never mentions Claude Code, the plugin, or any
host-specific surface), so its presence in CLAUDE_GOC.md violates the
"Claude-specific extras" contract and is the duplication's
root cause.

## Empirical evidence

`uv run python deck/claude-md-briefing-emits-closure-paragraph-twice/reproduce.py`:

```
AGENTS.md       : 1 occurrence(s) of "Closure is not frozenness"
CLAUDE.md       : 2 occurrence(s) of "Closure is not frozenness"
CLAUDE.local.md : 1 occurrence(s) of "Closure is not frozenness"

DEFECT PRESENT — CLAUDE.md briefing carries the paragraph twice.
```

Exit code 1 (defect present). The AGENTS.md and CLAUDE.local.md
targets are clean — only the CLAUDE.md sole-home target double-prints
the paragraph.

## Why it matters

The marker-bounded GoC briefing block is the durable on-disk briefing
every reader (human or agent) sees on opening the repo's
top-level `CLAUDE.md`. Duplicate paragraphs in a briefing intended to
be picked up cold erode the signal-to-noise that the briefing-target
contract is supposed to guarantee. Low contribution because
the default briefing target is AGENTS.md (unaffected) and the
duplicate is cosmetic — no behavior changes, no test fails, just a
visible redundancy in a path that is documented and exercised by
real installs (`--briefing-target CLAUDE.md`, also reachable via
`goc upgrade` migrations).

Reachability path: a user runs `goc install --briefing-target
CLAUDE.md` (or `goc upgrade --briefing-target CLAUDE.md`).
`_sync_methodology_blocks` calls `_briefing_body(templates,
"CLAUDE.md")`, gets the concatenated body, and writes it via
`_append_marker_block` into the `<!-- BEGIN GOC vX.Y.Z -->` /
`<!-- END GOC -->` block in `CLAUDE.md`. The block lands on disk
with the duplicate paragraph.

## Fix

Mechanical: remove lines 15-19 from `goc/templates/CLAUDE_GOC.md` so
the file contains only **truly** Claude-specific content (plugin install
commands + `Skill(claude-kickoff)` handoff). The AGENTS_GOC.md copy
remains the single source of truth for the generic methodology note,
and the concat in `_briefing_body` stops emitting a duplicate.

Alternative considered: teach `_briefing_body` to dedup paragraphs
between the two templates. Rejected as over-engineering for a single
known overlap — the contract is already documented ("Claude-specific
extras"), and content drift between the two files is what
`scripts/sync_plugin_assets.py --check` catches in CI for the mirror
trees. A targeted content fix is cheaper than a dedup engine and
aligns with the file's stated purpose.
