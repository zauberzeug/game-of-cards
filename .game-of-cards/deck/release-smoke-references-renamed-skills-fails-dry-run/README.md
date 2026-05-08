---
title: release-smoke-references-renamed-skills-fails-dry-run
summary: "After `align-skill-names-with-agile-vocabulary` renamed `bootstrap` → `kickoff` and `extend-deck` → `audit-deck`, three external consumers were left referencing the old names: `.github/workflows/release.yml` (Path A + Path B prompts and `--allowedTools` lists), `scripts/smoke_release.sh` (the local mirror of the workflow), and `goc.md` (the public CLI reference). A dry-run triggered against current main on 2026-05-08 (run 25560080412) failed `Assert Path B` because Path B grants only `Skill(bootstrap)` / `Skill(extend-deck)` plus `Read,Write,Bash(cat:*),Bash(ls:*)` — when those skills don't resolve, the LLM has no fallback and never emits the verbatim remediation text the assertion greps for. Path A passed only because its allowance includes general `Bash`, letting the LLM run `goc install` directly bypassing the missing skill — a false pass that masks the same bug. Replace all stale references with the new names and re-run the dry-run."
status: done
stage: null
contribution: medium
created: 2026-05-08
closed_at: 2026-05-08
human_gate: none
advances:
  - list-game-of-cards-on-anthropic-community-marketplace
advanced_by:
  - align-skill-names-with-agile-vocabulary
tags: [bug, infra]
definition_of_done: |
  - [x] `.github/workflows/release.yml` Path A + Path B prompts reference `Skill(audit-deck)` and `Skill(kickoff)` (not `extend-deck` / `bootstrap`), and the matching `--allowedTools` lists are updated in lockstep
  - [x] `scripts/smoke_release.sh` Path A + Path B mirror the same rename
  - [x] `goc.md` autonomous-loop sentence references `audit-deck` (not `extend-deck`)
  - [x] No `Skill(extend-deck)`, `Skill(bootstrap)`, or `improve-deck` substring remains anywhere outside `.game-of-cards/deck/` (deck history is allowed to keep historical names)
  - [x] Fresh `release.yml` dry-run (`workflow_dispatch` with `dry_run=true`) reaches conclusion `success`, with both Path A and Path B passing on the renamed skill names — run 25560598958 on commit 5353dc4 (build + smoke green, publish correctly skipped)
  - [x] `uv run goc validate` passes
worker: {who: Rodja Trappe, where: main}
---

# Release smoke references renamed skills

## Why

The skill-rename card (`align-skill-names-with-agile-vocabulary`,
done 2026-05-08) updated every on-disk skill directory and the
parity tripwire that enforces consumer-copy lockstep — but did not
sweep callers outside the skill tree. The two stragglers are CI's
release smoke (the gate that must pass before publishing to PyPI
or to the Anthropic community marketplace) and the public CLI
reference page.

The bug is hidden by Path A's permissive `Bash` allowance: when the
LLM hits a non-existent skill, it shells out to `goc install` and
the assertion (`.game-of-cards/deck/` exists + `result.txt` says
`A:passed`) still passes. Path B is intentionally tighter and
exposes the gap: with only `Read,Write,Bash(cat:*),Bash(ls:*)` plus
the two stale skill identifiers, there is no path to emit the
remediation substring the assertion requires.

## Out of scope

- Adding fixture-style explicit assertions on the resolved skill
  names. The byte-for-byte lockstep test in `ci.yml` already
  catches drift between the two on-disk copies; the missing layer
  is "do CI workflows reference skills by their current names",
  which is more naturally enforced by re-running this dry-run on
  every release-relevant change. A separate card may be filed if a
  static-analysis tripwire is desired.
- Hardening Path A. Path A's `Bash` allowance is intentional — it
  exercises end-to-end install. Its false-pass behaviour against a
  missing skill is annoying but not the immediate fix; Path B is
  the canary for routing-text regressions.

## Cross-references

- `align-skill-names-with-agile-vocabulary` (done 2026-05-08) —
  the rename whose sweep missed these callers.
- `list-game-of-cards-on-anthropic-community-marketplace` (open,
  gate=decision) — depends on a green dry-run before the manual
  marketplace smoke + form submission can proceed.
- `release-smoke-test-plugin-auto-bootstrap` (done 2026-05-07) —
  the card that introduced this workflow.
