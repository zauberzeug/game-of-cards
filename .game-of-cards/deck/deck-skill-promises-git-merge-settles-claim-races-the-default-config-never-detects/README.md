---
title: deck-skill-promises-git-merge-settles-claim-races-the-default-config-never-detects
summary: "The shipped deck skill (SKILL.md and reference.md) and ABOUT.md said git's merge handles a simultaneous claim race, whichever commits first wins, while a default claim stays in the claimer's clone and both racing claims succeed. All three passages now state that default, how the race surfaces under distinct and shared identities, and the workflow.claim_push opt-in, with the claim table in DECK_LOCATION.md linked by absolute URL because that page ships to no consumer. tests/test_claim_race_reassurance.py sweeps every tracked file outside the deck and tests for the reassurance while a default claim does not push, and checks the three passages both ways."
status: done
stage: null
contribution: high
created: "2026-10-04T06:13:07Z"
closed_at: "2026-10-04T07:01:49Z"
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — no sentence in the deck skill's `SKILL.md` or `reference.md`, or in `ABOUT.md`, says git's merge handles a claim race or that whichever commits first wins
  - [x] MECHANICAL: the three passages state the shipped behavior — by default a claim stays in the claimer's clone, so a race surfaces at the earliest when the second worker integrates, as a conflict over the claim under distinct identities and only through the finished work under one shared identity; `workflow.claim_push: true` pushes the claim and refuses a later conflicting claimer — and point at `DECK_LOCATION.md`'s claim table for the detail (the size-capped `SKILL.md` through the `reference.md` section it cites, since `DECK_LOCATION.md` ships to no consumer)
  - [x] TDD: a regression guard in `tests/` fails when any doc or shipped skill template says git's merge handles or settles a claim race while a default claim does not push
  - [x] MECHANICAL: mirrors re-synced (`python scripts/sync_plugin_assets.py --check` green) and OpenClaw skills re-ported (`python3 scripts/port_skills_to_openclaw.py --check` green)
worker: {who: "claude[bot]", where: main}
---

# The deck skill promised git's merge settles claim races the default config never detects

## What was broken

Three passages told every reader that git settles a simultaneous claim race:

- `goc/templates/skills/deck/SKILL.md`, shipped to every consumer:
  > `status: active` is the soft lock; git's merge handles the rare
  > simultaneous-claim race (whichever commits first wins).
- `goc/templates/skills/deck/reference.md`:
  > git's merge handles the rare race when two sessions claim the same card
  > simultaneously (whichever commits first wins).
- `ABOUT.md`: "git's merge handles claim-races."

The five regenerated copies (`.claude/skills/deck/`, `.codex/skills/deck/`,
`claude-plugin/skills/deck/`, `codex-plugin/skills/deck/` and the ported
`openclaw-plugin/skills/deck/`) carried the same sentences.

A claim is a local commit. `claim_push_enabled()` (`goc/engine.py:5405`)
defaults to off, and the shipped config template leaves `claim_push: true`
commented out, so `goc status <title> active` never pushes. Two workers on
separate clones both claim the card and both get exit 0. Nothing merges at
claim time:

- **Distinct identities.** The second worker's `git pull --rebase` conflicts
  on the card's `worker` line, but only after both claims were made. In
  practice that is after both workers did the work.
- **One shared identity**, the normal setup for a bot fleet. Both claims write
  the same `worker`, so the second claim commit is patch-identical. The rebase
  drops it and exits 0. The race shows up, if at all, as conflicts between the
  two workers' finished work.

The protection the passages promised exists only as the opt-in
`workflow.claim_push: true`, which pushes the claim and refuses a later
conflicting claimer. That opt-in has its own same-identity hole, tracked on
[claim-push-reports-success-when-rebase-drops-identical-racing-claim](../claim-push-reports-success-when-rebase-drops-identical-racing-claim/).
[deck-location-doc-says-claims-push-by-default-and-last-writer-wins](../deck-location-doc-says-claims-push-by-default-and-last-writer-wins/)
had already removed the same reassurance from `DECK_LOCATION.md`, but its
guard reads only that page.

## What changed

- **`reference.md` § Game of Cards as the runtime** states the shipped
  behavior. Sessions sharing a checkout see a claim at once. By default a
  claim stays in the claimer's clone, so two clones can both claim the same
  card and both succeed. The race surfaces at the earliest when the second
  worker integrates: as a conflict over the claim under distinct identities,
  and under one shared identity only through the finished work.
  `workflow.claim_push: true` in `.game-of-cards/config.yaml` pushes each claim
  and refuses a later conflicting claimer. The passage links `DECK_LOCATION.md`'s
  claim table by absolute GitHub URL, because `DECK_LOCATION.md` does not ship
  and a bare filename would dangle in every consuming repo.
- **`SKILL.md`** keeps one sentence: by default a claim stays in your clone, so
  two clones can both claim one card, and `workflow.claim_push: true` pushes
  the claim and refuses a later conflicting one. It points at that
  `reference.md` section for the rest. The skill had 35 bytes of headroom
  under its 10,000-byte cap, and no sentence naming the default and the opt-in
  fit, so the cap is now 10,100. The rationale is recorded beside it in
  `tests/test_skill_body_size.py`.
- **`ABOUT.md`** item 4 states the same behavior and links the claim table by
  absolute URL. `.github/workflows/pages.yml` rewrites only a fixed set of
  repo-relative links for the rendered site, and `DECK_LOCATION.md` is not
  among them, so a relative link would break on /about/.
- **Guard: `tests/test_claim_race_reassurance.py`.** It observes a default
  claim against a scratch bare remote seeded with the shipped config template.
  While that claim does not push, no tracked file outside the deck's cards and
  `tests/` may say a merge or rebase handles, settles, resolves or decides a
  claim race, or that whichever commits first wins. The sweep is keyed to the
  claim, not to a file, so it covers the mirrors and plugin payloads too. Each
  of the three passages must also say a claim stays in the clone by default
  and name `workflow.claim_push`. Once a default claim pushes, that passage
  check runs the other way. Fed the pre-fix wording, both checks fire on all
  three passages. With the observation flipped, the passage check fires on the
  current wording.
- Mirrors re-synced; OpenClaw skills re-ported.

## Evidence

`reproduce.py` races two claims on one card from two clones of a bare remote
under the shipped config, once with distinct identities and once with one
shared identity, then checks the three surfaces. It exited 1 before the fix,
listing five contradicted sentences. After the fix (2026-10-04):

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

No surface says git's merge settles the race.
```

## Artifacts

- reproduce.py
