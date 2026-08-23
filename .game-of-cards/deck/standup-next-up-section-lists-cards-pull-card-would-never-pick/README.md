---
title: standup-next-up-section-lists-cards-pull-card-would-never-pick
summary: "The standup skill's Section 5 (\"Next up\") prose promises \"the top 3 open `human_gate: none` cards by value score (the cards `Skill(pull-card)` would pick next)\", but the shipped command is bare `goc 2>/dev/null | head -5`, which applies no gate and no impediment filter. On this repo's own deck it lists three `human_gate: session` cards with `ready=false` while the true ready count is 0 — precision 0/3, and it hides the fact that nothing is pullable. Fix is the one-token substitution `goc --ready`, the predicate `pull-card` and `next-card` already use."
status: open
stage: null
contribution: medium
created: "2026-08-23T04:49:50Z"
closed_at: null
human_gate: none
advances:
  - extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate
advanced_by: []
tags: [bug, api-contract, documentation]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — Section 5 of `goc/templates/skills/standup/SKILL.md` selects with `goc --ready`; it exits 1 on the pre-fix template.
  - [ ] TDD: a regression test under `tests/` asserts that the Section 5 bash block in the standup template AND in every shipped mirror (`.claude/`, `.codex/`, `claude-plugin/`, `codex-plugin/`, `openclaw-plugin/`) uses `--ready`, so a future template edit cannot reintroduce the drift silently.
  - [ ] MECHANICAL: only `goc/templates/skills/standup/SKILL.md` is hand-edited; the five mirrors are regenerated (`python scripts/sync_plugin_assets.py`, `python3 scripts/port_skills_to_openclaw.py`) and `--check` is clean for both.
  - [ ] EMPIRICAL: the fixed command is run against this repo's own deck and its output recorded in `log.md` — it must report the ready queue, not the three `human_gate: session` epics the bare queue shows today.
  - [ ] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green.
---

# standup "Next up" lists cards pull-card would never pick

## Location

`goc/templates/skills/standup/SKILL.md:107-115` — Section 5, and the five
mechanical mirrors of the same block:

| Copy | Line |
|---|---|
| `goc/templates/skills/standup/SKILL.md` (source of truth) | 113 |
| `.claude/skills/standup/SKILL.md` | 113 |
| `.codex/skills/standup/SKILL.md` | 136 |
| `claude-plugin/skills/standup/SKILL.md` | 113 |
| `codex-plugin/skills/standup/SKILL.md` | 136 |
| `openclaw-plugin/skills/standup/SKILL.md` | 106 |

## What's broken

The section states its own contract, then ships a command that does not
honour it:

````markdown
## Section 5 — Next up

Show the top 3 open `human_gate: none` cards by value score (the cards
`Skill(pull-card)` would pick next), as a forward look.

```bash
goc 2>/dev/null | head -5 || true
```
````

Bare `goc` is `--status open` and nothing else: no gate filter, no
impediment filter, no draft exclusion. The predicate the prose names —
"the cards `Skill(pull-card)` would pick next" — is `card_is_ready`
(`goc/engine.py:2582`), which the engine exposes as `goc --ready` and
documents as four conjuncts:

> Ready iff `status == open` AND not a draft scaffold (`card_is_draft`)
> AND `human_gate == none` AND no active impediment overlay (`waiting_on`
> unset, `waiting_until` absent or past).

Bare `goc` satisfies the first conjunct only. Because the queue is
value-sorted and gated epics carry the deck's highest values, the three
rows Section 5 surfaces are systematically the *least* pullable cards in
the deck: a `human_gate: session` epic outranks every `none`-gated card
that shares its contribution tier, and a `waiting_on: external` card
keeps its full value while being invisible to the picker.

`Skill(pull-card)` and `Skill(next-card)` both already select with
`goc --ready` (`goc/templates/skills/pull-card/SKILL.md:42`,
`goc/templates/skills/next-card/SKILL.md:19`), so the drift is confined
to this one restatement.

## Empirical evidence

`reproduce.py` builds a hermetic scratch deck with one card per readiness
class and runs both predicates:

```
Scratch deck — one card per readiness class:
  deferred-card-parked-until-next-year   value=9.0  gate=none    ready=false
  gated-epic-blocks-the-queue            value=9.0  gate=session ready=false
  impeded-card-waiting-on-a-vendor       value=9.0  gate=none    ready=false
  ready-low-value-typo-fix               value=1.0  gate=none    ready=true

Section 5 as shipped (`goc | head -5` → top 3 rows):
  deferred-card-parked-until-next-year   ready=false
  gated-epic-blocks-the-queue            ready=false
  impeded-card-waiting-on-a-vendor       ready=false

`goc --ready` (what pull-card would actually pick):
  ready-low-value-typo-fix

False positives (shown, never pullable): 3/3
False negatives (pullable, not shown):   1

Shipped Section 5 command: 'goc 2>/dev/null | head -5 || true'
[FAIL] Section 5 does not use `goc --ready`; the drift is live.
```

Not a synthetic-only result — the same inversion holds on this repo's own
deck at filing time:

```
$ goc | head -5              # Section 5 as shipped
ship-game-of-cards-as-cross-agent-cli                  ... session
integrate-github-issues-discussions-and-pull-requests  ... session
support-custom-card-workflows-and-statuses             ... session

$ goc --ready
No cards match (ready: status open, gate none, no active impediment; ...)
```

Precision 0/3, and the one fact a reader needs — *nothing is pullable* —
is the fact the section suppresses.

## Why it matters

Section 5 is the forward look a human reads to decide whether the
autonomous loop has fuel. Getting it backwards is worse than omitting it:
it reports "here are the next three" precisely when the honest answer is
"the queue is empty and your decision gates are the bottleneck" — the
condition Section 4 ("Waiting on you") exists to escalate. A standup that
shows three gated epics under "Next up" tells the human the loop is fed
while it is in fact starving on their own unmade decisions, so the gates
sit unlowered for another day.

The one-token fix (`goc` → `goc --ready`) also makes the section
self-correcting: `goc --ready`'s zero-match line names the predicate and
its hidden-draft count, and its trailing leverage comparison points at the
highest-value gated card — exactly the handoff Section 4 wants.

## Fix

`goc/templates/skills/standup/SKILL.md:113`:

```diff
-goc 2>/dev/null | head -5 || true
+goc --ready 2>/dev/null | head -5 || true
```

Then regenerate the five mirrors (`python scripts/sync_plugin_assets.py`
for the four Claude/Codex copies, `python3
scripts/port_skills_to_openclaw.py` for the OpenClaw port) — per AGENTS.md
§ "Skill and hook files have two copies", the template is the only
hand-edited file.

**Out of scope:** `head -5` assumes exactly two header lines, so an
`ACTIVE:` notice line shrinks the section to two rows. That miscount is
identical before and after this change (bare `goc` prints the same
notice), so it is a separate display concern, not part of this drift.

## Family

Sixth confirmed copy of the pull-readiness predicate, and the second of
the six that lives outside `goc/engine.py` (the other is the CI shell
copy below; copies 1-3 and 5 are all engine functions). Tracked as an instance of
[extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate](../extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate/),
which owns the structural guard; this card is the substitution that card
already prescribes for non-Python copies ("expose the engine predicate,
don't re-roll it"). Sibling instances:
[pull-card-workflow-launches-agent-sessions-when-the-ready-queue-is-empty](../pull-card-workflow-launches-agent-sessions-when-the-ready-queue-is-empty/)
(the CI shell copy) and
[standup-impeded-filter-drifts-from-engine-on-elapsed-and-bare-waits](../standup-impeded-filter-drifts-from-engine-on-elapsed-and-bare-waits/)
(Section 2 of this same skill, a two-cell divergence in the overlay half
of the predicate). Distinct from this card: that one re-rolls
`waiting_impedes` in Python inside a Context block; this one omits three
of four conjuncts in the shell command.
