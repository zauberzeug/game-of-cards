---
title: pattern-check-hook-binary-misses-connect-to-existing-root
summary: |-
  The Stop-hook `pattern_generalization_check.py` REMINDER offers a BINARY: "file a generalization
  card" OR "no generalization needed". It has no branch for the common mature-deck case — the
  pattern IS general but a root/generalization card ALREADY exists — so the right move is to CONNECT
  the instance (cross-reference or an `advances` edge), not file a duplicate. As written, the hook
  nudges toward the redundant-umbrella anti-pattern that GoC's own deck-hygiene guidance ("filing
  exceeds deciding") and `create-card`'s dedup step warn against. Fix: reword the REMINDER to a
  three-branch form (no / dedup-then-connect / file) and sync the ~9 duplicated copies across host
  ports, then release.
status: active
stage: null
contribution: medium
created: "2026-06-06T06:54:29Z"
closed_at: null
human_gate: session
advances: []
advanced_by: []
tags: [meta-fix, infra]
definition_of_done: |
  - [x] MECHANICAL: the REMINDER string is reworded to a THREE-branch form — (a) NO pattern → "no generalization needed" + stop; (b) YES but a root/generalization card already exists → CONNECT this instance (cross-reference or `advances` edge) and name it, do NOT duplicate; (c) YES and none exists → file via `Skill(create-card)`. The YES path leads with a dedup step (scan the deck). Proposed wording is in the body ("Proposed REMINDER") — keep it ~the same length as today (it is injected on every code-mutating Stop).
  - [x] MECHANICAL: ALL copies of the REMINDER are synced (grep `pattern-check. Before yielding` across the repo). Known sites: `claude-plugin/hooks/pattern_generalization_check.py`, `claude-plugin/goc/templates/hooks/...`, `codex-plugin/hooks/...`, `codex-plugin/goc/templates/hooks/...`, `.claude/hooks/...` (dogfood), top-level `goc/templates/hooks/...`, and the openclaw TypeScript port `openclaw-plugin/index.ts` (then rebuild `openclaw-plugin/dist/index.js` + `.map`). Re-grep after editing → zero stale copies.
  - [x] TDD: any test asserting the REMINDER text is updated to the new wording and asserts the three-branch structure. No prior test asserted the REMINDER text, so a new `ReminderWordingTest` was added to `tests/test_pattern_generalization_hook.py` asserting the no / connect-to-existing / file-only-if-none branches and the dedup-first step.
  - [ ] MECHANICAL: version bump + release so downstream repos (e.g. phasor-agents, currently on cached v0.0.23) pick up the new wording on the next `goc upgrade`.
  - [ ] PROCESS: (stretch — or file separately) the REMINDER is hand-synced across ~9 copies, a DRY smell; consider single-sourcing it (one module/const imported by every host port) so future wording changes touch one place. If deferred, file a follow-on card and cross-reference it here.
worker: {who: "claude[bot]", where: main}
---

# pattern-check-hook-binary-misses-connect-to-existing-root

## Why this card exists

`pattern_generalization_check.py` is a Stop hook that, on any code-mutating turn, blocks the stop
and injects a reminder asking the agent to self-assess whether the change is an instance of a
broader pattern that deserves its own generalization card. The detection logic is sound. The
problem is the **prompt wording** — a static `REMINDER` string offering only two outcomes:

> "…If yes, file a generalization card via `Skill(create-card)`… If no generalization is
> warranted, respond 'no generalization needed' and stop."

This binary (file / don't) is missing the **most common case in a mature deck**: the pattern is
genuinely general, *and a root/generalization card already exists*. The correct action there is to
**connect** the new instance to the existing root — a prose cross-reference or an `advances` edge —
NOT to file a duplicate. By skipping straight to "file", the hook nudges toward the
redundant-umbrella anti-pattern that GoC's own guidance warns against:

- deck-hygiene: "filing exceeds deciding" — over-filing umbrellas is a known deck pathology.
- Occam: one root card, not N symptom cards.
- `create-card` already documents a dedup step ("auto-invoke `scan-deck` to dedup against existing
  titles" before filing) — but the Stop hook's prompt doesn't mention it, so the two disagree.

## Worked instance (the near-miss that motivated this)

In a downstream repo (phasor-agents), an agent's change touched a real, broadly-applicable pattern
("a control that passes with the mechanism causally disconnected" — a random baseline where a
behavior-matched control was required). The hook fired and, read literally, pushed toward filing a
new generalization card. A dedup pass found the pattern was **already generalized** in existing
cards (`ablation-theatre-canonical-tag-proposal`, `tests-pass-when-mechanism-disconnected-five-sibling-sites`).
The correct action was a cross-reference, not a new card. The binary almost produced a duplicate;
the agent only avoided it by overriding the prompt's framing.

## Proposed REMINDER (three-branch)

> `[GoC | pattern-check]` Before yielding: did your recent change touch a pattern with broader
> applicability? If **NO**, respond "no generalization needed" and stop. If **YES**, dedup first
> (scan the deck): if a generalization/root card **already exists**, CONNECT this instance to it
> (cross-reference or an `advances` edge) and name it — do **not** file a duplicate; **only if none
> exists**, file a new card via `Skill(create-card)`.

Same shape/length as today; preserves the opt-out phrase and the detection logic. It only adds the
**dedup-then-connect** middle branch.

## Location (sites carrying the REMINDER)

`grep -rl "pattern-check. Before yielding" .` (exclude `.git/`):

- `claude-plugin/hooks/pattern_generalization_check.py` + `claude-plugin/goc/templates/hooks/...`
- `codex-plugin/hooks/pattern_generalization_check.py` + `codex-plugin/goc/templates/hooks/...`
- `openclaw-plugin/index.ts` (TypeScript port) → rebuild `openclaw-plugin/dist/index.js` (+ `.map`)
- `.claude/hooks/pattern_generalization_check.py` (this repo's own dogfooding hook)
- top-level `goc/templates/hooks/pattern_generalization_check.py`

~9 copies of one string across three host ports — see the stretch DoD on single-sourcing.

## Scope guard

Prompt-wording + propagation only. The detection logic (which turns fire the hook, the
`stop_hook_active` re-block guard, the broad-git-mutation matcher) is correct and out of scope.

## Decision required

The reword work (DoD 1–3) is **complete, tested, and committed to `main`** — all 7 Python
copies, the openclaw TS port, and the rebuilt openclaw bundle now carry the three-branch
REMINDER, and `ReminderWordingTest` guards it. The full regression suite (413 tests) and both
sync/porter drift checks pass.

Only **DoD item 4 — version bump + release** remains. That is a maintainer call rather than an
autonomous-puller action: it cuts a fresh public version published irreversibly to PyPI, npm,
and ClawHub, and the choice of whether to cut a release *now* for this one wording change versus
letting it ride the next accumulated release is a release-cadence decision. The deck is also
carrying several `session`-gated cards, suggesting the maintainer is steering outward/release
actions directly at the moment.

**To resolve:** either

- dispatch a patch release so downstream repos (e.g. phasor-agents, on cached v0.0.23) pick up
  the wording on next `goc upgrade` — `gh workflow run release.yml -f version=X.Y.Z` (next patch
  is `0.0.25`), record the run id in `log.md`, tick DoD 4, then `goc done` this card; **or**
- decide the reword rides the next routine release — drop DoD item 4 to a follow-on
  release-propagation card (the established pattern, cf. closed
  `release-fixed-skill-frontmatter-to-codex-plugin-cache`) and close this one.

DoD item 5 (single-sourcing the ~9 REMINDER copies) is deferred to follow-on card
[single-source-pattern-check-reminder-across-host-ports](../single-source-pattern-check-reminder-across-host-ports/).
