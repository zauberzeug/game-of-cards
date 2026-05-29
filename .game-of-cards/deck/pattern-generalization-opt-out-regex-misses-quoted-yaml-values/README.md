---
title: pattern-generalization-opt-out-regex-misses-quoted-yaml-values
summary: "The pattern-generalization Stop hook's opt-out check parses `.game-of-cards/config.yaml` with `re.search(r\"pattern_generalization_check\\s*:\\s*(false|true)\", ...)`. The group does not accept surrounding quotes, so `pattern_generalization_check: \"false\"` and `pattern_generalization_check: 'false'` — both valid YAML scalar forms of the bare boolean — fail to match. The hook then treats the user as NOT opted out and fires its Stop reminder on every code-mutating turn."
status: open
stage: null
contribution: medium
created: "2026-05-29T22:39:59Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] PROCESS: Decision recorded in the body's `## Decision required` section (regex-extend vs PyYAML-parse vs strip-quotes-then-compare) and gate lowered to `none`.
  - [ ] TDD: reproduce.py exits zero — all three YAML scalar forms (bare, double-quoted, single-quoted) are detected as opt-out.
  - [ ] MECHANICAL: the fix lands in `goc/templates/hooks/pattern_generalization_check.py` and the three plugin/consumer mirrors are re-synced (pre-commit `sync-plugin-assets` covers `.claude/hooks/`, `claude-plugin/hooks/`, `codex-plugin/hooks/`).
  - [ ] TDD: a regression test under `tests/` exercises `_opted_out` against the three YAML scalar forms and asserts `True` for each.
  - [ ] TDD: `uv run goc validate` passes and `uv run python -m unittest discover -s tests` is green.
---

# Pattern-generalization opt-out regex misses quoted YAML values

## Location

`goc/templates/hooks/pattern_generalization_check.py:38-42`

```python
m = re.search(
    r"pattern_generalization_check\s*:\s*(false|true)", config.read_text()
)
return bool(m and m.group(1) == "false")
```

## What's broken

The opt-out check uses a regex whose capture group, `(false|true)`,
does not accept surrounding quotes. YAML 1.2 allows scalars to be
written bare, double-quoted, or single-quoted; all three are
equivalent for boolean-style values (with a caveat — see below).

The docstring at the top of the same file documents the format as:

```yaml
hooks:
  pattern_generalization_check: false
```

— the bare form. But a user who writes:

```yaml
hooks:
  pattern_generalization_check: "false"
```

is doing something perfectly reasonable: they may be defensive about
YAML 1.1's surprising boolean coercions (where `no`, `off`, `n`, `false`
all parse as `False`), or they may have copied the line from another
config that quoted it. The hook silently rejects this form.

## Empirical evidence

Running the regex against the three scalar forms:

```text
quoted false:        matched=False, opted_out=False
bare false:          matched=True,  opted_out=True
single-quoted false: matched=False, opted_out=False
```

So a user who opts out with either quoted form ends up still
receiving the `[GoC | pattern-check]` reminder on every code-mutating
turn. The opt-out is silently inert.

A YAML semantic caveat worth flagging in the decision: in YAML 1.2,
`"false"` is a *string*, not a boolean. A strict YAML parser would
read `pattern_generalization_check: "false"` as the string `"false"`
and `pattern_generalization_check: false` as the boolean `False`. The
strip-quotes-then-compare approach intentionally treats them as
equivalent — matching user intent over YAML-spec purity. The decision
section below explicitly asks which contract the fix should hold.

## Why it matters

This hook ships in three places (the source-of-truth at
`goc/templates/hooks/`, the consumer copy at `.claude/hooks/`, the
plugin payload at `claude-plugin/hooks/`, and the Codex mirror at
`codex-plugin/hooks/`). All four are byte-identical via the
`sync-plugin-assets` pre-commit hook; the bug is shipped to every
consumer.

The reachability path is concrete:

1. A user invokes `goc install` (or installs the Claude Code /
   Codex plugin), which scaffolds `.game-of-cards/config.yaml`.
2. The user edits the file to opt out of the pattern-generalization
   reminder using a quoted value (a normal YAML habit, not a typo).
3. On every Claude Code or Codex turn that includes an `Edit`,
   `Write`, or `git commit` bash call, the Stop hook reads
   `config.yaml`, fails to parse the opt-out, and prints the
   reminder anyway.

The user has no signal that their opt-out is being ignored — the
hook does not log, does not warn, and does not surface a parse
error. The contract "this hook can be turned off in
`.game-of-cards/config.yaml`" is silently violated.

## Sibling drift (related, separate card recommended)

While reading this file I noticed a second asymmetry vs. the
just-fixed `deck_session_start.py`:

- `pattern_generalization_check.py:126` reads only
  `CLAUDE_PROJECT_DIR`, never `CODEX_PROJECT_DIR`.
- `deck_session_start.py:153-154` reads both env vars, with a
  helper `_project_dir_from_hook_input()`.

Under a Codex host that sets `CODEX_PROJECT_DIR` and does not pass
`cwd` in the hook payload, the Stop hook falls back to `.` (current
working directory) for resolving `.game-of-cards/config.yaml`. This
is a sibling defect with a different reproduction path; it should
be filed as its own card rather than absorbed into this fix.

## Distinct from existing open cards

- `pattern-generalization-stop-hook-reminder-never-reaches-the-agent`
  (open, `decision`): about Stop-hook stdout *not being injected into
  the model's context* at all — a separate defect that lives after
  the opt-out check. Even if the present opt-out bug is fixed and a
  user does not opt out, that card's question (whether the reminder
  is actually delivered) is still open. The two cards interact but
  are independent.
- `deck-session-start-hook-strips-quotes-asymmetrically-across-frontmatter-readers`
  (closed 2026-05-29, commit `1ec1986`): the analogous fix for the
  *session-start* hook's frontmatter readers. The fix shape there
  was symmetric quote-stripping. The present card extends that
  family to the Stop-hook opt-out parser.

## Decision required

Three credible fix paths:

1. **Extend the regex** to accept optional surrounding quotes:
   `r'pattern_generalization_check\s*:\s*["\']?(false|true)["\']?'`.
   Cheapest, no new dependency, matches the strip-quotes precedent
   in `deck_session_start.py` (commit `1ec1986`).

2. **Strip outer quotes after capture.** Capture a wider group, then
   strip a matched leading-trailing quote pair before comparing to
   `"false"`. Slightly more code, identical behavior to option 1.

3. **Replace the regex with `yaml.safe_load`** and read
   `data["hooks"]["pattern_generalization_check"]` properly. Honors
   YAML 1.2 semantics strictly (`"false"` is a string, not a bool —
   would NOT count as opt-out under this contract). Requires
   importing `yaml` in a hook that today has no third-party
   dependencies (the engine already requires PyYAML, but Stop hooks
   run as standalone scripts under whatever Python the host
   provides). Most expressive, highest blast radius.

Open question: should the contract be "match user intent" (1 or 2,
treats quoted `"false"` as equivalent to bare `false`) or "match
YAML semantics" (3, treats `"false"` as a string and ignores it)?
The sibling fix `1ec1986` chose user-intent matching; the
consistent default is option 1 or 2 unless there's a reason to
diverge.

Recommended: **option 1** (regex extension). Matches the just-shipped
sibling fix's user-intent posture, no new dependency, mechanical
diff, easy to test.

## Fix proposal (assuming option 1)

```python
m = re.search(
    r'pattern_generalization_check\s*:\s*["\']?(false|true)["\']?',
    config.read_text(),
)
return bool(m and m.group(1) == "false")
```

Plus a regression test under `tests/` that exercises all three
scalar forms (bare, `"false"`, `'false'`) and asserts opt-out.
