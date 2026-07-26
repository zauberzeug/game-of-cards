---
title: local-release-smoke-script-no-longer-mirrors-the-ci-smoke-job
summary: "`scripts/smoke_release.sh` bills itself as a local-dev mirror of `.github/workflows/release.yml`'s `smoke` job and is the documented pre-tag check, but the two have diverged: Path A grants a narrow six-command Bash allowlist where CI grants bare `Bash`, Path B allows a different command set, and Path B's prompt drops CI's requirement that the agent confirm two literal substrings before writing the pass marker. A green local run therefore does not predict the CI gate, and a red one can be a false alarm caused by the mirror's own narrower allowlist rather than by the plugin payload it is meant to test. The closed card `release-smoke-test-plugin-auto-bootstrap` records the contract as \"mirrors the workflow exactly\"."
status: open
stage: null
contribution: medium
created: "2026-07-26T07:19:21Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - release-smoke-script-launches-path-a-without-putting-goc-on-path
tags: [bug, infra, documentation]
definition_of_done: |
  - [ ] PROCESS: decision recorded — which aspects of the `smoke` job the local script must reproduce exactly, and which may deliberately differ on a developer machine
  - [ ] MECHANICAL: `scripts/smoke_release.sh` and the `smoke` job agree on every aspect the decision marks as must-mirror
  - [ ] MECHANICAL: the header of `scripts/smoke_release.sh` states what it does and does NOT reproduce, replacing the unqualified "Local-dev mirror" claim
  - [ ] TDD: a regression test fails when a must-mirror aspect drifts between `scripts/smoke_release.sh` and the `smoke` job in `.github/workflows/release.yml`
  - [ ] PROCESS: the closed card [release-smoke-test-plugin-auto-bootstrap](../release-smoke-test-plugin-auto-bootstrap/) amended with a forward pointer, since its DoD records the contract as "mirrors the workflow exactly"
  - [ ] PROCESS: `uv run goc validate` passes
---

# local release smoke script no longer mirrors the CI smoke job

## Location

`scripts/smoke_release.sh:1-7` states the contract:

```bash
# Local-dev mirror of .github/workflows/release.yml's `smoke` job.
#
# Runs Path A (kickoff completes when goc + Bash(goc:*) are pre-set) and
# Path B (preflight routes to kickoff when goc is denied) against the
# plugin payload at ./claude-plugin. Use this before pushing a release tag
# to catch regressions without burning CI minutes.
```

The mirrored job is `.github/workflows/release.yml:467-595` (`smoke`),
which gates `publish-pypi` / `publish-npm` (`release.yml:599`,
`needs: [build, smoke]`).

## What's broken

The two have diverged on four aspects. Each row is a real difference in
what the run exercises, not a formatting variance:

| Aspect | CI `smoke` job | `scripts/smoke_release.sh` |
|---|---|---|
| Path A `PATH` setup | extends `PATH` with the uv tool-bin dir (`release.yml:503`) | absent (`smoke_release.sh:43`) |
| Path A `--allowedTools` | `Read,Write,Edit,Bash,Skill(kickoff),Skill(audit-deck)` (`release.yml:540`) | `Read,Write,Edit,Bash(cd:*),Bash(ls:*),Bash(pwd:*),Bash(goc:*),Bash(git:*),Bash(which:*),Skill(kickoff),Skill(audit-deck)` (`smoke_release.sh:54`) |
| Path B `--allowedTools` | `Read,Write,Bash(cat:*),Bash(ls:*),Skill(kickoff),Skill(audit-deck)` (`release.yml:588`) | `Read,Write,Bash(cd:*),Bash(ls:*),Bash(pwd:*),Bash(which:*),Skill(kickoff),Skill(audit-deck)` (`smoke_release.sh:82`) |
| Path B pass condition | agent must confirm the response contains the literal substrings `Bash(goc:*)` **and** `permissions.allow`, and must write the marker with the Write tool, not Bash (`release.yml:577-580`) | "surface verbatim remediation text telling the user to add 'Bash(goc:*)' to permissions.allow" — no two-substring confirmation, no tool restriction on the write (`smoke_release.sh:74-78`) |

The Path A allowlist difference has a concrete consequence. CI grants
bare `Bash`, so every command kickoff runs is permitted. The local
allowlist permits six command prefixes — and `grep` is not among them,
while `Skill(kickoff)` explicitly instructs the agent to run it
(`goc/templates/skills/kickoff/SKILL.md:124-126`):

```
Skip this question if Stage 0 detected `BRIEFING_MERGED` — read the
existing target off disk (`grep -l '<!-- BEGIN GOC' AGENTS.md CLAUDE.md
CLAUDE.local.md`) and pass that file to Stage 4.
```

So the local run can be denied on a step CI permits. The reverse also
holds: the deck already recorded that Path A's bare-`Bash` grant *masks*
failures. From the closed card
[release-smoke-references-renamed-skills-fails-dry-run](../release-smoke-references-renamed-skills-fails-dry-run/):

> Path A passed only because its allowance includes general `Bash`,
> letting the LLM run `goc install` directly bypassing the missing skill
> — a false pass that masks the same bug.

The two paths are therefore inverted relative to each other on exactly
the axis that was already known to decide pass/fail: CI can false-pass
where local false-fails.

## The contradicted record

The closed card that built this script records the contract as exact —
[release-smoke-test-plugin-auto-bootstrap](../release-smoke-test-plugin-auto-bootstrap/),
DoD item at `README.md:21`:

> - [x] Local-dev runner: `scripts/smoke_release.sh` mirrors the workflow
>   **exactly** via `claude` CLI directly; supports
>   `./scripts/smoke_release.sh A`, `B`, or `AB` (default)

That box is ticked, and the script's own header repeats the claim
unqualified. Nothing in either place records a deliberate exception.

## Why it matters

This script is the documented way to check a release before tagging, and
tagging is the repo's critical path — one `gh workflow run release.yml`
publishes to PyPI, npm, and ClawHub. The script's verdict is read as a
prediction of the `smoke` gate that stands in front of those publishes.
Today it is not one, in both directions: a green local run can be
followed by a red CI gate that burns the release dispatch, and a red
local run can be a false alarm produced by the mirror's own narrower
allowlist rather than by the plugin payload.

One instance of the drift is separable and needs no decision — the
missing `PATH` step — and is tracked and fixed on
[release-smoke-script-launches-path-a-without-putting-goc-on-path](../release-smoke-script-launches-path-a-without-putting-goc-on-path/).
This card carries the rest, which does need a human call.

## Decision required

**What must the local script reproduce exactly, and what may
deliberately differ?**

The narrow allowlist may well be intentional rather than drift: bare
`Bash` under `--permission-mode dontAsk` is a different risk posture on
a maintainer's working machine than in a throwaway CI runner, and the
local script runs against `/tmp/smoke-A` inside the developer's own
session. Nothing on record says either way, so the fix direction cannot
be derived — it has to be chosen. Three credible options:

1. **Exact mirror.** Bring `scripts/smoke_release.sh` to CI's tool
   surface and prompts verbatim, including bare `Bash` on Path A.
   Honours the recorded contract and makes the local verdict predictive.
   Cost: accepts unrestricted `Bash` + `dontAsk` on a developer machine.

2. **Documented partial mirror.** Keep the narrow local allowlist,
   rewrite the header to state precisely which aspects are reproduced
   and which are not, and align only the aspects that decide pass/fail
   (prompts, assertions, `PATH` setup). Cost: the local verdict stays
   advisory, and readers must be told so.

3. **Single-source both.** Extract the prompts and allowlists into
   shared files that the workflow and the script both read, so drift
   becomes impossible rather than merely detectable. Strongest, and
   consistent with this deck's single-sourcing preference — but it
   requires editing `.github/workflows/release.yml`, which the
   autonomous bot's `GITHUB_TOKEN` cannot do, so it needs a human
   commit.

Option 2 is implementable by the bot alone; options 1 and 3 need a human
commit for the workflow side (option 1 only if the CI side is what
changes). Whichever is picked, the "mirrors the workflow exactly" claim
in the script header and on the closed predecessor card must be
corrected or substantiated — that part is not optional.

The project-local consultation hook (`.game-of-cards/hooks/pull-card.md`)
is an empty stub, so there is no repo rubric that resolves the
dev-machine tool-posture question. Hence the `decision` gate rather than
a rubric-derived pre-write.
