---
title: openclaw-skill-porter-claude-substitutions-emit-doubled-articles
summary: "port_skills_to_openclaw.py rewrites `\\bClaude Code\\b` → \"the host\" and `\\bClaude\\b` → \"the agent\" with no awareness of a preceding article or sentence-initial position, so the committed ported skills contain \"the the agent-specific\", \"a the host-style\", and a sentence starting with lowercase \"the host gates\". The --check drift guard reproduces the same corruption, so CI stays green on the corrupt output."
status: open
stage: null
contribution: medium
created: "2026-07-09T01:36:08Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] PROCESS: decision recorded — article/case-aware substitution patterns in the porter vs rewording the source templates to avoid article+Claude collisions
  - [ ] TDD: reproduce.py exits zero (no doubled-article or mid-sentence-lowercase artifacts in openclaw-plugin/skills/)
  - [ ] TDD: a regression test asserts the porter's substitution of "the Claude-specific …", "a Claude Code-style …", and sentence-initial "Claude Code …" yields grammatical host-neutral text
  - [ ] MECHANICAL: openclaw-plugin/skills/ re-ported; `python3 scripts/port_skills_to_openclaw.py --check` green
  - [ ] MECHANICAL: `uv run goc validate` passes
---

# OpenClaw skill porter's Claude substitutions emit doubled articles and mid-sentence case errors

## Location

`scripts/port_skills_to_openclaw.py:64-68` — the host-neutral substitution
table:

```python
    # Claude Code references — drop or rephrase.
    (re.compile(r"\bClaude Code\b"), "the host"),
    # Standalone Claude (NOT followed by " Code" — that's caught above).
    (re.compile(r"\bClaude\b(?! Code)"), "the agent"),
```

## What's broken

Both replacements always inject the article "the", ignoring whether the
source already has an article before "Claude", and always emit lowercase,
ignoring sentence-initial position. The corruption is committed in the
shipped plugin payload today:

- `openclaw-plugin/skills/kickoff/SKILL.md:123` — "the **the agent**-specific"
  (source `goc/templates/skills/kickoff/SKILL.md:123`: "the Claude-specific")
- `openclaw-plugin/skills/kickoff/SKILL.md:133` — "plus the **the agent**-specific extras"
- `openclaw-plugin/skills/kickoff/SKILL.md:172` — "is the **the agent**-only path"
- `openclaw-plugin/skills/openclaw-kickoff/SKILL.md:81` — "hunting for a
  **the host**-style analog" (source: "a Claude Code-style analog")
- `openclaw-plugin/skills/openclaw-kickoff/SKILL.md:83` — "**No permission
  grant required.** the host gates …" — sentence begins lowercase (source:
  "Claude Code gates")

The drift guard cannot catch this class: `--check` re-runs the same
substitution table and compares against the committed output, so
deterministic corruption is *certified* rather than flagged, and
`tests/test_plugin_mirror_parity.py`'s porter parity test stays green.

## Why it matters

Reachability: every template edit followed by the documented re-port
workflow (`python3 scripts/port_skills_to_openclaw.py`) regenerates the
corrupt text, which ships in the npm/ClawHub OpenClaw plugin payload as
instructions consumer agents load verbatim. "a the host-style analog" is
the kind of mangled phrasing that erodes trust in generated skill text and
can confuse weaker agent models parsing the instruction. AGENTS.md's own
rationale for hand-reviewing porter output ("the porter applies non-trivial
normalization worth eyeballing") presumes the normalization is at least
grammatical.

## Decision required

Two credible fix paths:

1. **Make the porter article/case-aware.** Add higher-priority patterns
   before the generic pair, e.g. `\b[Tt]he Claude\b(?! Code)` → "the agent",
   `\b[Aa] Claude Code\b` → "a host", and capitalize the replacement when
   the match starts a sentence (preceded by `^`, `.` + space, or `**` bold
   opener). Keeps templates untouched; the porter owns grammar.
2. **Reword the source templates** so no "the/a Claude…" collision exists
   ("the Claude-specific extras" → "the extras specific to Claude", etc.),
   keeping the porter's table minimal. Cost: contorts the Claude-facing
   source text to serve the port, and future template edits can silently
   reintroduce collisions (no guard).

Option 1 localizes the fix in the tool that owns the rewrite and is
testable; option 2 leaves the porter simple. A hybrid (option 1 plus a
porter-output lint that greps for `\bthe the\b|\ba the\b|[.!?] the (host|agent)\b`)
gives a durable tripwire either way.

## Empirical evidence

```
$ grep -rnE '\bthe the\b|\ba the\b' openclaw-plugin/skills/
openclaw-plugin/skills/kickoff/SKILL.md:123:> instructions plus, when CLAUDE.md is the home, the the agent-specific
openclaw-plugin/skills/kickoff/SKILL.md:133:>    plus the the agent-specific extras live inline. **Cross-runtime
openclaw-plugin/skills/kickoff/SKILL.md:172:briefing. `--briefing-target CLAUDE.md` is the the agent-only path: the
openclaw-plugin/skills/openclaw-kickoff/SKILL.md:81:hunting for a the host-style analog:
```

`reproduce.py` scans `openclaw-plugin/skills/` for doubled-article and
mid-sentence-lowercase artifacts and exits non-zero while any are present
(currently: 4 doubled-article hits + 2 sentence-initial lowercase hits — the
second at `openclaw-plugin/skills/openclaw-kickoff/SKILL.md:88`, "**No
host-specific private-notes file.** the host conventions").
