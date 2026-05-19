---
title: refine-deck-fails-to-load-on-the-rot-it-is-meant-to-clean-up
summary: "`/refine-deck` runs `!goc validate` as a hard shell precondition (refine-deck/SKILL.md:58). Any non-zero exit prevents the skill from loading — including the very recovery guidance further down in its own body. Half-edges, broken advances-DAG cycles, plugin-mode false-parity ERRORs all silently block the skill from reaching the user. The chicken-and-egg loop hides the rot it was built to surface."
status: active
stage: null
contribution: medium
created: "2026-05-19T15:02:13Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] `refine-deck/SKILL.md:58` no longer hard-fails skill load when `goc validate` exits non-zero
  - [ ] When validate exits 0, the precondition output is unchanged (no spurious noise)
  - [ ] When validate exits non-zero, the user sees the validator output AND the skill body loads, so the recovery instructions at SKILL.md:60-65 are reachable
  - [ ] The plugin-mirror sync runs cleanly (claude-plugin, codex-plugin, openclaw-plugin templates updated)
  - [ ] `uv run goc validate` passes
worker: {who: Rodja Trappe, where: main}
---

# refine-deck-fails-to-load-on-the-rot-it-is-meant-to-clean-up

## What's broken

`/refine-deck`'s skill body opens with a precondition (`goc/templates/skills/refine-deck/SKILL.md:58`):

```markdown
## Step 1 — sanity floor

!`goc validate`
```

Claude Code processes the `!`<cmd>`` block at skill-load time by executing the shell pipeline and interpolating its output. **Any non-zero exit kills the entire skill load** — none of the skill body executes, and the user sees raw validator stderr instead of the skill's guidance.

The skill body two lines below (SKILL.md:60-65) explicitly anticipates this scenario:

```markdown
If validate fails with half-edge errors, run `goc repair-edges` to
preview the missing reverse-edge writes, then `goc repair-edges
--apply` and re-run `goc validate`. If repair reports a structural
cycle, park that card for human review instead of guessing which edge
is wrong. Fix unknown tags / missing required fields FIRST too.
Hygiene runs on a valid deck.
```

That guidance is for exactly the failure mode that kills the skill load. The precondition gates the body behind the very check it's meant to recover from. Chicken-and-egg.

## Real-world reproduction

A consumer running goc CLI v0.0.17 with Claude Code plugin v0.0.18 reports the failure on a real deck of ~830 cards. Their `goc validate` correctly surfaces:

- One dangling `advanced_by` reference (citing an unknown card)
- A 7-card cycle in `advanced_by` violating the DAG invariant
- ~5 half-edges (cards listing `advances` targets that don't list them back in `advanced_by`)

Plus, on v0.0.17, the `validate_skill_dir_parity()` false-positive (separate card: `plugin-auto-detection-misses-versioned-marketplace-paths`) fires because the consumer installed via the marketplace plugin without running `goc upgrade --keep-local-skills`. Even after the auto-detect card lands and is released, the genuine deck-rot issues above would STILL hard-block `/refine-deck` from loading.

The two fixes are complementary: the auto-detect fix reduces the false-positive ERROR rate; this card removes the chicken-and-egg loop for genuine deck rot.

## Why it matters

`/refine-deck` is the recovery tool for deck hygiene. Its job is to surface and triage exactly the failure modes that make `goc validate` ERROR. Gating its load on a clean validator means the tool is unusable precisely when it's needed most.

The deeper architectural lesson: **validators that run as skill preconditions need a different severity ladder than validators that run pre-commit**. Pre-commit `goc validate` is a quality gate (any ERROR = block the commit). Skill-load `goc validate` is a workspace probe (ERROR could just mean "this is the rot you came here to fix"). Mixing the two roles into one binary exit code is what creates the loop here.

## Fix

Soft-gate the precondition so the skill loads regardless of exit code, but the user still sees the validator output and an explicit framing:

Replace `goc/templates/skills/refine-deck/SKILL.md:58` from:

```markdown
!`goc validate`
```

…to:

```markdown
!`goc validate 2>&1 || echo "[refine-deck] validate found rot; the skill body below will route you through fixing it"`
```

`|| echo …` makes the pipeline exit 0 on validator failure, while the echo provides visible framing that the rot is the input to this skill, not a blocker. The `2>&1` ensures stderr (where validator errors go) is captured in the skill-load output rather than spilling separately.

This is the user-suggested wrapper pattern from the bug report and matches the convention already used by other skill preconditions (`pull-card/SKILL.md:26-34`, `next-card/SKILL.md:13`, all the `cat ... || true` patterns).

## Out of scope

- Broader validator severity ladder (errors vs warnings) — orthogonal architectural question, leave for a separate card if needed.
- Auto-detect for plugin-installed skills — already covered by `plugin-auto-detection-misses-versioned-marketplace-paths` (committed, awaits release).
- Other skills' preconditions — surveyed and confirmed they already use tolerant patterns (`|| true`, `2>&1`, listing commands that exit 0 on empty deck).
