---
title: pull-card-defers-small-gate-free-defects-it-surfaces-to-a-separate-run
summary: "When a pull-card session surfaces a small, `human_gate: none`, mechanically-clear defect (during its work or on an empty queue), the skill files a card and exits — leaving the fix for a *separate* fresh-context run to rediscover, reload, and close minutes later. The session that found the defect already had the code in context, so the second run is pure overhead. Add an explicit fix-through path: file the card (preserving the record + TDD test), then claim → implement → close it in the SAME session when it clears a small/mechanical/gate-free threshold. `audit-deck`'s 'flag, don't fix' breadth-hunt is untouched."
status: active
stage: null
contribution: high
created: "2026-05-30T12:28:30Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] MECHANICAL: `goc/templates/skills/pull-card/SKILL.md` gains an explicit fix-through path defining the eligibility threshold (all of: `human_gate: none` / no decision; mechanically clear + bounded single-site diff; NOT a sibling/architectural meta-fix; closely related to the context already loaded) and the action (file the card via `Skill(create-card)`, then claim → implement → close in the same session). The card is still created — record axis + DoD/TDD test preserved.
  - [ ] MECHANICAL: the "Queue empty" bullet in pull-card's "When to stop without finishing" stops saying "file one card … then exit. The next invocation can work it" unconditionally; instead it routes fix-through-eligible findings to the fix-through path and only files-and-exits when the finding is NOT eligible (decision-class, cross-cutting, or unrelated to loaded context).
  - [ ] MECHANICAL: the body states the explicit non-goals — (a) `audit-deck` stays "flag, don't fix" (breadth-first spike, unchanged); (b) fix-through does NOT mean "drain the whole queue in one run" — at most the entangled small defect(s) plus the pulled card, then exit so fresh context stays the default per the workflow's one-pull-per-run intent.
  - [ ] MECHANICAL: the change lands in the source-of-truth template only; `python scripts/sync_plugin_assets.py` regenerates the claude/codex/.claude/.codex mirrors and `python3 scripts/port_skills_to_openclaw.py` re-ports the OpenClaw skill, all staged.
  - [ ] PROCESS: `python scripts/sync_plugin_assets.py --check` and `python3 scripts/port_skills_to_openclaw.py --check` both report no drift; `uv run python -m unittest discover -s tests` and `uv run goc validate` pass.
  - [ ] PROCESS: decision provenance (Rodja chose "fix-through, keep the card" over inline-no-card / overhead-only / defer) recorded in `log.md`.
worker: {who: Rodja Trappe, where: main}
---

# pull-card defers small gate-free defects it surfaces to a separate run

## What's wasteful

`pull-card`'s job is to pull one card, work it, close it. But while
working card X — or when the queue is empty — the session routinely
**surfaces** new small defects (sibling bugs in the same function, an
adjacent one-liner, a missing guard). The current skill body files
those as fresh cards and **exits**, deferring the fix to a *separate*
future run.

The "Queue empty" branch in `## When to stop without finishing` states
the pattern explicitly:

> **Queue empty.** No ready cards. Invoke `Skill(audit-deck)` to file
> one new card from emergent codebase observations, **then exit. The
> next invocation can work it.**

The session that surfaced the defect already had the relevant code
loaded in context and had already done the diagnosis. Filing it for a
fresh-context run to rediscover, re-load, claim, and fix is pure
overhead for the *small* cases.

## Empirical evidence (deck state on 2026-05-30)

Measured across the 281 closed cards carrying both `created` and
`closed_at`:

- **Median time-to-close: 6.3 min. 60% close within 10 min, 68% within 30.**
  (Mean is 715 min — a small tail of genuinely hard cards. The
  workload is bimodal; this card targets the median population.)
- **Authored fix size: median ~48 lines across 2 files** (excluding the
  plugin-mirror auto-sync duplication). The 2 files are almost always
  *the fix + a regression test* (the DoD enforces TDD). These are small.
- **Filing rate is 28–53 cards/day** while the dedicated `audit-deck.yml`
  cron files only **1/day**. So ~97% of new cards are filed by
  `pull-card` sessions as a side effect of their work — the lever is
  pull-card's filing behavior, not audit's.
- Each small fix currently costs a full separate run (checkout + `uv
  sync` + cold-start) plus inter-run latency plus 3 commits
  (`new card` / `deck: … → active` / `fix … closes`).

## Decision (resolved)

Rodja chose **"fix-through, keep the card"** over three alternatives
(inline-fix-with-no-card; reduce-commit/run-overhead-only;
analysis-only-defer). Rationale: the card artifact carries real,
load-bearing value even for a 5-line fix — the **record axis** (this
repo *is* goc dogfooding its own "deck as record") and the **TDD/DoD
gate** (the regression test). What's waste is the *separate run* and
inter-run latency, not the card. So: keep filing the card; just let
the session that filed it close it in place when the fix is small.

The "if they are small" qualifier is the control surface: a small,
mechanical fix gains nothing from a fresh-context second look; a
subtle or cross-cutting one genuinely benefits from the
separation (a fresh agent reading the briefing cold). The threshold
preserves that benefit where it matters.

## Fix proposal (skill-body edit only — no engine change)

Edit `goc/templates/skills/pull-card/SKILL.md`:

1. Add a **fix-through** subsection defining eligibility. A surfaced
   defect is fix-through-eligible when **all** hold:
   - it would file at `human_gate: none` (the fix is determined — no
     decision/taste call between credible alternatives);
   - the fix is mechanically clear and **bounded / single-site**
     (rule of thumb: ~one source file + its test);
   - it is **not** a sibling/architectural **meta-fix** candidate
     (4+ instances of one root shape → that's a deliberate
     architectural card; file it, don't inline it);
   - it is **closely related to the context already loaded** (a defect
     spotted in a far-off module is better fixed by a fresh run with
     that module in focus — file it).

   When eligible: `Skill(create-card)` to file it (record + DoD/TDD
   test preserved), then claim → implement → close it in the **same
   session**, as its own card + commit. When not eligible: file it and
   leave it in the queue (current behavior).

2. Rewrite the **"Queue empty"** bullet so it routes a
   fix-through-eligible finding through the same-session path instead
   of unconditionally "file … then exit."

3. State the **non-goals** explicitly:
   - `audit-deck` stays **"flag, don't fix"** — it is a breadth-first
     spike and must keep hunting the *biggest* defect, not stop at the
     first small one. This card does not touch `audit-deck`.
   - Fix-through is **not** "drain the queue in one run." It closes the
     pulled card plus at most the entangled small defect(s) it
     surfaced, then exits — fresh context per pull stays the default,
     consistent with `pull-card.yml`'s one-pull-per-run / self-retrigger
     design.

## Why it matters

This is the dominant inefficiency in the autonomous loop, and the
skill is a **shipped template** — every consumer's loop inherits it.
Reducing two fresh-context runs to one for the median (6.3-min, ~48-line)
card cuts CI-minutes, token spend, inter-run latency, and commit noise
across every install, while preserving the record + test that justify
the card in the first place. It also helps drain the backlog growth
(on 2026-05-29: 53 filed vs 23 fixed).

## Out of scope

- Squashing the 3 commits per card into fewer (separate overhead-only lever).
- Changing `audit-deck` (stays a pure breadth-first flagger).
- Any `goc` engine change — this is a skill-body/methodology edit.
