## 2026-10-04T06:40:00Z — Claimed; two constraints on the fix

Claimed from the ready queue. Two constraints shaped the fix beyond the card's
Fix section:

- **`DECK_LOCATION.md` does not ship.** It sits at this repo's root, outside
  `goc/`, so a shipped skill naming it by filename points at a file no
  consuming repo has. That is the class
  `card-schema-reference-links-to-a-deck-card-no-consumer-repo-has` and
  `installed-files-point-readers-at-a-deck-folder-install-never-creates` fixed
  for deck links. The shipped `reference.md` therefore links the claim table
  by absolute GitHub URL. `ABOUT.md` does too: `.github/workflows/pages.yml`
  rewrites README, goc, ABOUT, AGENTS and LICENSE links plus `goc/`,
  `.game-of-cards/` and `deck/` paths for the rendered site, so a relative
  `DECK_LOCATION.md` link would 404 on /about/.
- **The deck skill's core had 35 bytes of headroom** under its 10,000-byte cap
  (`tests/test_skill_body_size.py`, 9965 bytes). Every candidate sentence that
  names both the default and the opt-in measured +116 to +127 bytes. The core
  keeps one sentence plus a pointer to its `reference.md` section, which
  carries the per-identity detail and the `DECK_LOCATION.md` link. The cap
  moved to 10,100 with a dated rationale, the precedent the other capped skills
  follow. DoD item 2 is reworded to say the size-capped core reaches the claim
  table through its sibling.

A claim-keyed sweep (`git grep` over every tracked file outside the deck) found
no further copy of the reassurance. `PERSONAS.md`, `site/index.html` and
`advance-card/reference.md` call `status: active` the soft lock without saying
anything settles a race.

## 2026-10-04T07:00:30Z — Closure

- **What changed**:
  - `goc/templates/skills/deck/reference.md` § Game of Cards as the runtime
    states the shipped claim behavior. By default a claim stays in the
    claimer's clone and two clones can both claim one card. The race surfaces
    at the earliest when the second worker integrates, as a claim conflict
    under distinct identities and only through the finished work under one
    shared identity. `workflow.claim_push: true` pushes the claim and refuses
    a later conflicting claimer. The passage links `DECK_LOCATION.md`'s claim
    table by absolute URL.
  - `goc/templates/skills/deck/SKILL.md`: one sentence (the default, and the
    opt-in by name) plus a pointer to that section. The deck cap in
    `tests/test_skill_body_size.py` is now 10,100 (SKILL.md is 10,094 bytes),
    with the rationale beside it.
  - `ABOUT.md` item 4: the same statement and the absolute link.
  - New guard `tests/test_claim_race_reassurance.py` (4 tests). It observes a
    default claim on a scratch bare remote with the shipped config template.
    While that claim does not push, it sweeps every tracked file outside
    `.game-of-cards/deck/` and `tests/` for "merge/rebase handles|settles|
    resolves|decides … race|claim" and "whichever commits first wins". It also
    requires each of the three passages to say a claim stays in the clone by
    default and to name `workflow.claim_push`, and runs that passage check the
    other way once a default claim pushes.
  - Mirrors re-synced (8 files) and OpenClaw skills re-ported (2 files).
  - `doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them`:
    the 27th instance's row names the guard, and its paragraph records the
    closure.
- **Verification**:
  - `reproduce.py` exited 1 before the fix (five contradicted sentences) and
    exits 0 after it.
  - On the pre-fix tree (`git show HEAD:<path>` for every swept file, live
    observation), the guard reports 31 problems. That is 25 sentence hits
    across the three sources and their ten mirror files, plus both passage
    checks on each source.
  - With the config template mutated to `claim_push: true`, the observation
    flips to "pushes" and the passage check fires on all three current
    passages.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: every agent that loads the deck skill, and every reader
  of `ABOUT.md`, now learns that parallel claims across clones go undetected
  by default. They also learn the opt-in that refuses a later conflicting
  claim, where before they were told the race was handled.
- **Tests**: 1227 passed / 0 failed (`uv run python -m unittest discover -s
  tests`). `sync_plugin_assets.py --check` and `port_skills_to_openclaw.py
  --check` are green.
- **Surfaced**: the same skill's "The deck layout" block lists `SCHEMA.md`,
  `README.md` and `deck.py` as deck files. `deck/reference.md` calls `deck.py`
  the engine, and `refine-deck` sends new tags to "a SCHEMA.md PR". All of
  these are pre-package engine files no install creates. Another doc-accuracy
  instance, so it is filed separately and not fixed through.

## Closure verification (2026-10-04T07:01:47Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-10-04 — Closure' present
