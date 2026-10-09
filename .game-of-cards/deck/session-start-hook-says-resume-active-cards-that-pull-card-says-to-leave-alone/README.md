---
title: session-start-hook-says-resume-active-cards-that-pull-card-says-to-leave-alone
summary: "The SessionStart reminder tells every new session to resume or close any active card with no gate and no wait, while pull-card and next-card tell the same session to treat every active card as a soft lock unless the user asks to continue it. Nothing tells an agent when a claim is orphaned rather than held by a live session, and a claim records no time, so the two instructions cannot be reconciled from the card. Autonomous runs have resolved orphaned claims by hand three times, each a day late, and in a multi-session repo the reminder points one session at another's live claim."
status: open
stage: null
contribution: medium
created: "2026-10-09T04:46:56Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] PROCESS: the `## Decision required` question below is answered and recorded via `Skill(decide-card)`, lowering the gate to `none`
  - [ ] TDD: `reproduce.py` exits 0, so for both the LIVE and the ORPHANED deck the SessionStart reminder and the `pull-card` / `next-card` soft-lock text give the same instruction (update the script's classifier to the chosen wording if it changes, without loosening the verdict)
  - [ ] TDD: `tests/test_session_start_hook.py` and `tests/test_openclaw_session_start_hook.py` pin the chosen rule on one LIVE and one ORPHANED fixture, so the Python hook and its OpenClaw port cannot disagree about which claims a session may resume
  - [ ] MECHANICAL: the chosen rule lands on every surface that speaks about the soft lock (`pull-card/SKILL.md`, `next-card/SKILL.md`, `deck/SKILL.md`, `deck/reference.md`, `deck_session_start.py`, `openclaw-plugin/index.ts`), with mirrors re-synced and `scripts/port_skills_to_openclaw.py --check` clean
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` pass
---

# The session-start hook says resume active cards that pull-card says to leave alone

## Location

- `goc/templates/hooks/deck_session_start.py:340`: the reminder for every
  `status: active` card with `human_gate: none` and no live wait.
- `openclaw-plugin/index.ts:722`: the same reminder in the OpenClaw port.
- `goc/templates/skills/pull-card/SKILL.md:32-34` and `:60`: the soft-lock
  rule, and "the soft lock against parallel sessions".
- `goc/templates/skills/next-card/SKILL.md:35-37`: the same rule for the
  picker.
- `goc/templates/skills/deck/SKILL.md:47` and
  `goc/templates/skills/deck/reference.md:85`: "`status: active` is the
  soft lock".
- `goc/engine.py:6107` (`_auto_populate_worker`): what a claim records.
  It writes `worker: {who, where}`, from git's `user.name` and the
  current branch (or `--worker-who` / `--worker-where`), and nothing
  else.

## What's broken

The hook sorts active cards into three buckets. One bucket is the cards
an agent could act on, and for those it gives an order:

```python
    if resumable:
        cards_str = ", ".join(resumable)
        print(f"[GoC] Active card(s): {cards_str} — resume or close before starting new work.")
```

The two skills a session runs next say the opposite about the same card:

```
pull-card: Treat any listed active card as a soft lock. Do not claim the
same card, or adjacent/conflicting work, unless the user explicitly asks
to continue that active card.

next-card: Active cards are claimed soft locks; avoid recommending the
same card or adjacent/conflicting work unless the user explicitly asks to
continue that active card.
```

Each instruction is right for one case and wrong for the other:

- **Live claim.** Another session holds the card right now. The skills
  are right, and the hook is telling this session to take over a claim
  the soft lock exists to protect. The deck skill says several sessions
  work one deck in parallel, and this repo's own AGENTS.md says several
  agents share local `main`, so the hook in a new session names the
  other sessions' claims.
- **Orphaned claim.** The session that claimed the card died before it
  closed or parked it. The hook is right, and the skills tell every
  later session to leave the card alone. Under the skills' rule the card
  stays stranded forever: it is not `open`, so `--ready` never offers
  it, and its gate is `none`, so `goc triage` never shows it to a human
  either.

Nothing lets an agent tell the two cases apart. A claim records no time,
only `worker: {who, where}`. Autonomous runs and local parallel agents
usually share one `who` (every run here is `claude[bot]` on `main`). And
none of the surfaces that speak about the soft lock says when a claim
counts as orphaned.

## Empirical evidence

`uv run python .game-of-cards/deck/session-start-hook-says-resume-active-cards-that-pull-card-says-to-leave-alone/reproduce.py`
builds two throwaway decks with one gate-free active card each, runs the
shipped hook on each the way Claude Code does (hook JSON on stdin), reads
the shipped skills, and drives a real `goc status <title> active`:

```
=== what the shipped skills say about any active card ===
  pull-card: Treat any listed active card as a soft lock. Do not claim the same card, or adjacent/conflicting work, unless the user explicitly asks to continue that active card.
  next-card: Active cards are claimed soft locks; avoid recommending the same card or adjacent/conflicting work unless the user explicitly asks to continue that active card.

=== what the SessionStart hook says about the same card ===
  LIVE     worker={who: other-agent, where: feature/parallel-work}
           hook: [GoC] Active card(s): claimed-seconds-ago — resume or close before starting new work.
           hook says 'resume'; skills say 'leave'
  ORPHANED worker={who: "claude[bot]", where: main}
           hook: [GoC] Active card(s): claimed-by-a-dead-session — resume or close before starting new work.
           hook says 'resume'; skills say 'leave'

=== what could tell the two cases apart ===
  frontmatter lines a real claim writes: status: active; worker: {who: "claude[bot]", where: main}
  claim records a time: False
  soft-lock surfaces that say when a claim is orphaned: none

=== verdict ===
DEFECT: for 2 of 2 decks (LIVE, ORPHANED) the hook says resume and the skills say leave it alone, and nothing on the card separates a live claim from an orphaned one
exit=1
```

The two decks differ only in `worker`, because a claim records nothing
else. Each deck's name says which case it stands for, but nothing on the
card itself can.

### The orphaned case in this repo

This repo's daily Pull Card workflow has orphaned a claim three times.
Each time its last iteration claimed a card and then died, and each time
the next day's first run resumed the claim. That run reasoned past the
skills' rule using facts only the CI setup supplies, and wrote its
justification into the card's `log.md`:

| Card | Claimed | Resumed |
|---|---|---|
| [citation-idempotence-re-run-reports-false-repairs-until-the-pass-commits](../citation-idempotence-re-run-reports-false-repairs-until-the-pass-commits/) | 2026-09-24T04:29Z | 2026-09-25T04:47Z |
| [kickoff-autonomy-choice-hands-off-to-host-complements-that-carry-no-recipe](../kickoff-autonomy-choice-hands-off-to-host-complements-that-carry-no-recipe/) | 2026-10-07T05:07Z, turn cap | 2026-10-08 |
| [engine-comments-claim-unflagged-placeholder-cards-count-as-drafts](../engine-comments-claim-unflagged-placeholder-cards-count-as-drafts/) | 2026-10-08T05:41Z, agent step failed | 2026-10-09T04:37Z |

The facts used were: the same `who`, local `main` equal to `origin/main`
with a clean tree, no commit since the claim, and Pull Card's single
concurrency group. None of them is on the card, and none is available
to a consuming repo that runs sessions differently. In the third case
the soft-lock table in `pull-card` did not even list the orphan. It was
the seventh active card, and the block's `head -20` cut it (tracked by
[skill-context-blocks-truncate-deck-output-hiding-active-cards-and-breaking-json](../skill-context-blocks-truncate-deck-output-hiding-active-cards-and-breaking-json/)).
The hook was the only surface that named it.

## Why it matters

Each orphan cost a full day, and every recovery depended on an agent
choosing to override a shipped instruction. A more literal agent obeys
the skill and leaves the card stranded for good, invisible to every
queue and to triage. The opposite mistake is just as available. In a
repo where sessions share a checkout, a new session that obeys the hook
picks up a card another session is still working, which is the
double-work race the soft lock exists to prevent. The deck has fixed
three earlier cases of this hook calling the wrong cards resumable
(closed cards, gated cards, impeded cards):
[session-start-hook-flags-closed-cards-as-active](../session-start-hook-flags-closed-cards-as-active/),
[session-start-hook-shows-gated-active-cards-as-resumable](../session-start-hook-shows-gated-active-cards-as-resumable/),
[session-start-hook-frames-waiting-on-active-cards-as-resumable](../session-start-hook-frames-waiting-on-active-cards-as-resumable/).
This is the case those fixes could not reach: a gate-free, unimpeded
card whose resumability depends on who holds it and whether they are
still there.

## Decision required

Which rule decides whether a session may resume a gate-free active card,
and which surface owns it? Credible options:

1. **The hook defers to the soft lock.** Reword the reminder so it names
   the card and its `worker` and says to resume only a claim this
   session holds, leaving everything else alone. The contradiction goes
   away, but orphans stay stranded until a human notices them. Smallest
   change; it solves only the live case.
2. **The skills gain an orphan exception from evidence available
   today.** A session may resume a claim whose `who` matches its own git
   identity when the claim commit is older than some N hours and nothing
   has touched the card since. This matches what this repo's runs
   already do, but it needs a value for N, a git dependency in a rule an
   agent applies by hand, and it cannot separate parallel sessions that
   share one identity.
3. **The engine records the claim time and owns the predicate.** A claim
   writes a time (for example `worker.since` or a `claimed_at` field),
   `.game-of-cards/config.yaml` sets a staleness window, and the engine
   marks stale claims in `goc --status active` and `--json`. The hook
   and the skills then read that one predicate, the way `card_is_draft`
   and `waiting_impedes` own their rules. This is the most robust
   option, at the cost of a schema field, a config default and a
   rendering change, and existing active cards have no claim time. It
   also adds one more engine predicate that the dependency-free hook and
   the OpenClaw port must each copy by hand. That is the drift
   [session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting](../session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting/)
   and
   [openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting](../openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting/)
   track, so their parity guard should cover the new predicate from the
   start.
4. **The consuming repo owns the policy.** The shipped surfaces stop
   contradicting each other (option 1) and point to
   `.game-of-cards/hooks/pull-card.md` as the place a repo writes its
   orphan rule. This repo would then write the CI-specific rule its runs
   already apply.

Whichever option wins, the hook and its OpenClaw port must change
together, because both print the reminder.
