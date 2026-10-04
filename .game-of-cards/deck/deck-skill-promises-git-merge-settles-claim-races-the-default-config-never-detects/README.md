---
title: deck-skill-promises-git-merge-settles-claim-races-the-default-config-never-detects
summary: "The shipped deck skill (SKILL.md and reference.md) and ABOUT.md say git's merge handles a simultaneous claim race, whichever commits first wins. Under the default config a claim never leaves the claimer's clone, so both racing claims succeed and git meets them only when the second worker integrates its finished work; under one shared worker identity the claim commits are identical, so integrating them raises nothing. Every consuming agent loads this reassurance, so multi-agent setups are told parallel claiming is safe without workflow.claim_push."
status: open
stage: null
contribution: high
created: "2026-10-04T06:13:07Z"
closed_at: null
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — no sentence in the deck skill's `SKILL.md` or `reference.md`, or in `ABOUT.md`, says git's merge handles a claim race or that whichever commits first wins
  - [ ] MECHANICAL: the three passages state the shipped behavior — by default a claim stays in the claimer's clone, so a race surfaces at the earliest when the second worker integrates, as a conflict over the claim under distinct identities and only through the finished work under one shared identity; `workflow.claim_push: true` pushes the claim and refuses a later conflicting claimer — and point at `DECK_LOCATION.md`'s claim table for the detail
  - [ ] TDD: a regression guard in `tests/` fails when any doc or shipped skill template says git's merge handles or settles a claim race while a default claim does not push
  - [ ] MECHANICAL: mirrors re-synced (`python scripts/sync_plugin_assets.py --check` green) and OpenClaw skills re-ported (`python3 scripts/port_skills_to_openclaw.py --check` green)
---

# The deck skill promises git's merge settles claim races the default config never detects

## Location

- `goc/templates/skills/deck/SKILL.md:47-49`, shipped to every consumer:
  > Multiple sessions work cards in parallel. `status: active` is the
  > soft lock; git's merge handles the rare simultaneous-claim race
  > (whichever commits first wins).
- `goc/templates/skills/deck/reference.md:84-87`:
  > The `status: active` field is the soft lock; git's merge handles
  > the rare race when two sessions claim the same card simultaneously
  > (whichever commits first wins).
- `ABOUT.md:34`: "N sessions + M scheduled agents working the same project is
  the default mode, not the exception. The `status: active` field is the soft
  lock; git's merge handles claim-races."
- Copies regenerated from the templates: `.claude/skills/deck/`,
  `.codex/skills/deck/`, `claude-plugin/skills/deck/`,
  `codex-plugin/skills/deck/`, and the ported `openclaw-plugin/skills/deck/`.

## What's broken

A claim is a local commit. `claim_push_enabled()` (`goc/engine.py:5405`)
defaults to off, and the shipped `goc/templates/game_of_cards/config.yaml`
leaves `claim_push: true` commented out, so `goc status <title> active` never
pushes. Two workers on separate clones (scheduled agents, other machines) both
claim the card, both get exit 0, and git compares nothing until one of them
integrates. Nobody "wins" at claim time, and nothing that happens at commit time
decides the race:

- **Distinct identities.** The second worker's `git pull --rebase` conflicts on
  the card's `worker` line. git surfaces the race, but only after both claims
  were made. In practice that is after both workers did the work.
- **One shared identity**, the normal setup for a bot fleet. Both claims write
  the same `worker`, so the second worker's claim commit is patch-identical. The
  rebase drops it and exits 0, so git says nothing about the claims. The race
  shows up, if at all, as conflicts between the two workers' finished work.

The skill's reassurance is the claim-time protection the default config does
not have. The protection exists as the opt-in `workflow.claim_push: true`: the
later claimer's push is rejected, it rebases, and on conflict `goc status`
exits 2 naming the racing worker. That opt-in has its own same-identity hole,
tracked on
[claim-push-reports-success-when-rebase-drops-identical-racing-claim](../claim-push-reports-success-when-rebase-drops-identical-racing-claim/).

## Empirical evidence

`uv run python .game-of-cards/deck/deck-skill-promises-git-merge-settles-claim-races-the-default-config-never-detects/reproduce.py`
(2026-10-04):

```
distinct identities:
  claim exit codes (first, second): (0, 0)
  first worker's push exit: 0
  second worker's `git pull --rebase` exit: 1 ['Auto-merging .game-of-cards/deck/race-card/README.md']
  remote card's worker afterwards: {who: agent-A, where: main}
one shared identity:
  claim exit codes (first, second): (0, 0)
  first worker's push exit: 0
  second worker's `git pull --rebase` exit: 0 ['hint: use --reapply-cherry-picks to include skipped commits']
  remote card's worker afterwards: {who: fleet-bot, where: main}

Both racing claims succeed under the default config: no merge happens at claim time,
and with one shared identity the second worker's integration raises nothing at all.

5 sentence(s) still say git's merge settles the race:
  - goc/templates/skills/deck/SKILL.md:48: "git's merge handles the rare simultaneous-claim race"
  - goc/templates/skills/deck/SKILL.md:49: 'whichever commits first wins'
  - goc/templates/skills/deck/reference.md:85: "git's merge handles"
  - goc/templates/skills/deck/reference.md:87: 'whichever commits first wins'
  - ABOUT.md:34: "git's merge handles claim-races"
```

## Why it matters

The deck skill is the front door every consuming agent loads, and `ABOUT.md`
frames parallel sessions plus scheduled agents as the default mode. Both tell
that audience the race is handled, so nobody reaches for `claim_push`. This
repo shows what follows: two agents claimed and closed the same card on
diverged clones, and a human reconciled two complete solutions
([parallel-agents-double-close-cards-because-claim-protections-are-disabled](../parallel-agents-double-close-cards-because-claim-protections-are-disabled/)).

It is the same false reassurance
[deck-location-doc-says-claims-push-by-default-and-last-writer-wins](../deck-location-doc-says-claims-push-by-default-and-last-writer-wins/)
removed from `DECK_LOCATION.md`. That page's claim table now states the shipped
protocol and is guarded by `tests/test_deck_location_claim_rows.py`, but the
guard reads only that page, so these copies kept the claim. It is one more
instance of
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/).
A guard keyed to the claim rather than to the file, as Option B there
describes, would have covered all four surfaces at once.

## Fix

Rewrite the three passages to say what happens. `status: active` is the soft
lock that sessions sharing a checkout see at once. Claims made on other clones
meet only when the second worker integrates, and under one shared identity even
that raises nothing until the two workers' finished work collides. `workflow.claim_push: true` makes the claim push and refuses
a later conflicting claimer. Point at `DECK_LOCATION.md` § "Claim and sync
semantics" for the detail rather than restating it. `goc/templates/skills/deck/SKILL.md`
is size-guarded (`tests/test_skill_body_size.py`), so its sentence should stay
one sentence plus the pointer. Then re-sync the mirrors and re-port OpenClaw. The
guard can reuse the scratch-remote observation in
`tests/test_deck_location_claim_rows.py` and sweep `*.md` plus
`goc/templates/**` for the claim's phrasing.
