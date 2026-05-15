---
title: create-card-skill-fails-with-shell-parse-error-on-title-placeholder
summary: |-
  Invoking `Skill(create-card)` from Claude Code fails immediately with
  `Shell command failed for pattern "!`goc show <title> 2>&1 | head
  -3`": [stderr] (eval):1: parse error near '>&'`. The skill body at
  `goc/templates/skills/create-card/SKILL.md:65` contains a `!cmd`
  fence with a literal `<title>` placeholder; the host substitutes
  `!cmd` lines by executing them in zsh, and zsh parses `<title>` as
  an input redirection from a file whose name starts with `title`,
  fails on the trailing `>` inside `<title>`, and the whole skill load
  aborts before the user-facing flow begins. Same bug exists in
  `advance-card/SKILL.md:30` and `finish-card/SKILL.md:43` (verified
  via `grep -rn '!\`goc show <title>' goc/templates/skills/`).
  Workaround today: bypass the skill and call `uv run goc new` /
  `goc status` / `goc done` directly. The fix is to make the
  placeholder substitution happen *before* the host executes the
  `!cmd` line — either by interpolating the skill arg into the fence
  at load time, or by replacing the executable fence with prose
  guidance that the agent runs themselves with the real title bound.
status: done
stage: null
contribution: medium
created: "2026-05-15T11:49:06Z"
closed_at: 2026-05-15T13:40:12Z
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] Reproduce: from a Claude Code session in any goc-using repo,
    invoke `Skill(create-card)` with any args. Capture the
    `parse error near '>&'` stderr; confirm the skill terminates
    before reaching its dedup step.
  - [x] Fix `goc/templates/skills/create-card/SKILL.md:65` so the
    line either (a) interpolates the title arg before host execution,
    (b) is rewritten as prose with the agent expected to run
    `goc show <real-title>` itself, or (c) uses a fence form the host
    does NOT auto-execute. Pick the option that keeps the dedup check
    actually getting performed (option (b) only works if the rest of
    the skill flow strongly prompts the agent to do it).
  - [x] Apply the same fix to `goc/templates/skills/advance-card/SKILL.md:30`
    and `goc/templates/skills/finish-card/SKILL.md:43` — same bug,
    same `!`goc show <title>`` pattern.
  - [x] Pre-commit `sync-plugin-assets` regenerates the three
    `.claude/skills/<name>/SKILL.md` mirrors and the
    `claude-plugin/skills/<name>/SKILL.md` payload copies; OpenClaw
    skills re-ported via `scripts/port_skills_to_openclaw.py` if the
    port script preserves the fix shape (otherwise hand-port).
  - [x] Add a regression check: a `grep` in CI (or a small test in
    `tests/`) that fails the build if any
    `goc/templates/skills/**/SKILL.md` line matches
    `!`.*<[a-z]+>.*`` (executable fence containing an
    angle-bracket placeholder). Catches re-introduction of the same
    pattern across all current and future skills.
  - [x] `uv run goc validate` passes; manual smoke: invoke
    `Skill(create-card)` from Claude Code and confirm it walks the
    dedup → file flow without the parse error.
worker: {who: "claude[bot]", where: main}
---

# create-card-skill-fails-with-shell-parse-error-on-title-placeholder

## Reproduction

From any Claude Code session in a repo with the goc plugin enabled:

```
Skill(create-card) <any args>
```

Observed:

```
Shell command failed for pattern "!`goc show <title> 2>&1 | head -3`":
[stderr] (eval):1: parse error near `>&'
```

The skill never proceeds past its preflight load. Every downstream
step (dedup grep, title-shape check, file scaffold) is skipped.

## Root cause

`goc/templates/skills/create-card/SKILL.md:65`:

```markdown
Verify it doesn't already exist:

!`goc show <title> 2>&1 | head -3`

Existence (frontmatter dump returned) → pick a different title.
```

The host treats `!`...`` as a shell-execute fence and runs the
contents in zsh. zsh parses `goc show <title> 2>&1` as
`goc show < title > 2>&1` — an input redirect from a file named
`title`, then a stdout redirect to a file whose name starts with `2`
followed by `>&1` which fails the parse near `>&`.

The literal `<title>` is meant as a documentation placeholder
(matching the convention used in prose lines like `goc new <title>`
elsewhere in the same file at line 135). The placeholder convention
is fine for prose but breaks when used inside an auto-executed
fence.

## Affected skills

`grep -rn '!\`goc show <title>' goc/templates/skills/` returns three
matches:

| Skill | Line | Purpose of the broken fence |
|---|---|---|
| `create-card/SKILL.md` | 65 | dedup-check before filing |
| `advance-card/SKILL.md` | 30 | preflight existence check before status flip |
| `finish-card/SKILL.md` | 43 | preflight existence check before close |

All three skills are blocked at preflight when invoked via the host's
`Skill(...)` mechanism. Direct CLI use (`uv run goc new`,
`uv run goc status`, `uv run goc done`) is unaffected — that's the
current workaround.

## Fix options

Three plausible shapes; the right one depends on host substitution
semantics that need confirming:

**Option A — pre-substitute the placeholder.** Teach the skill loader
(or the `!cmd` substitution layer in the host) to fill `<title>` from
a bound skill arg before evaluating the fence. Most invisible to the
end user. Requires understanding whether Claude Code's skill runtime
has a hook for arg-binding into `!cmd` fences. May also need an
OpenClaw port if its TypeScript skill body parser does the same
auto-execute on `!`fences.

**Option B — drop the executable fence; use prose.** Replace with:

```markdown
Verify it doesn't already exist by running `goc show <your-title>`.
If frontmatter prints, the title is taken — pick another. If you
get `ERROR: ... not found`, proceed.
```

Cheap, works today, no host changes needed. Cost: dedup is now
agent-discipline rather than enforced — easy to skip. Mitigation:
make the subsequent step explicitly say "having confirmed
non-existence above, …".

**Option C — change fence form.** Use a fenced code block (` ``` `)
instead of a backticked inline `!`fence``, since the host
auto-executes only the latter. Still informational rather than
executed. Equivalent to option B in semantics, just different
presentation.

Recommendation in card body, not committed: Option B for v1
(immediate, host-agnostic, ports cleanly to OpenClaw); revisit with
Option A if a host-substitution mechanism becomes available later.

## Cross-references

- `goc/templates/skills/create-card/SKILL.md:65` — primary site
- `goc/templates/skills/advance-card/SKILL.md:30` — same bug
- `goc/templates/skills/finish-card/SKILL.md:43` — same bug
- `scripts/sync_plugin_assets.py` — auto-syncs the fix to
  `.claude/skills/` and `claude-plugin/skills/` consumer copies
- `scripts/port_skills_to_openclaw.py` — re-port the three skills
  after fixing; verify the port doesn't reintroduce the executable
  fence

## What this card is NOT

- Not a host bug report. The host's `!cmd` auto-execute behaviour is
  documented and intentional; the bug is in the skill template
  abusing the fence with an unsubstituted placeholder.
- Not a refactor of the skill flow. Scope is the three preflight
  lines only — don't restructure the dedup or close-check logic.
- Not a regression test that audits *all* `!cmd` fences for any
  shell-unsafe content. The DoD adds a narrow grep that catches the
  specific `<placeholder>` pattern; broader fence-safety auditing is
  a separate (much larger) card if anyone wants it.
