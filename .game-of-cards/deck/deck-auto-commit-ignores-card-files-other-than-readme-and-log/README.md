---
title: deck-auto-commit-ignores-card-files-other-than-readme-and-log
summary: "Every goc auto-commit path routes through `_git_auto_commit`, which stages a hardcoded `(\"README.md\", \"log.md\")` pair per card dir. Sibling artifact files in the same directory — the `reproduce.py` that `Skill(create-card)` Step 6 requires for bug-class cards, and the rich artifacts Step 7 endorses — are never staged, so `goc publish` / `goc status active` / `goc done` report a committed card while its evidence stays untracked. The skills mandate the sibling files; the engine's commit path does not know they exist."
status: open
stage: null
contribution: medium
created: "2026-07-30T05:27:21Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] PROCESS: decision recorded below — which files in a card dir the auto-commit stages (whole dir, allowlist, or tracked-plus-new)
  - [ ] TDD: `reproduce.py` exits 1 (auto-commit stages the sibling `reproduce.py`)
  - [ ] TDD: a regression test asserts that after `goc publish <title> --commit` on a card dir containing a sibling file, `git status --porcelain --untracked-files=all` is clean for that card path
  - [ ] TDD: a regression test pins the chosen exclusion contract (whatever the decision excludes — e.g. `__pycache__`, `*.pyc` — stays unstaged) so the fix cannot commit build droppings
  - [ ] MECHANICAL: the fix lands in `_git_auto_commit` (`goc/engine.py:4502`) so all seven callers inherit it, not per-verb
  - [ ] MECHANICAL: full regression suite green; `uv run goc validate` clean; plugin-asset sync `--check` clean
---

# Deck auto-commit ignores card files other than README.md and log.md

## Location

- `goc/engine.py:4502-4536` — `_git_auto_commit` docstring and draft filter
- `goc/engine.py:4569-4574` — the hardcoded filename pair
- `goc/engine.py:5451, 5489, 5660, 5917, 5939, 5954, 6283` — the seven
  callers: `_cmd_status`, `_cmd_publish`, `_cmd_new`, `_cmd_wait`,
  `_cmd_advance`, `_cmd_unadvance`, `_cmd_decide`
- `goc/templates/skills/create-card/SKILL.md` § Step 6 and § Step 7 — the
  contract that mandates sibling files

## What's broken

`_git_auto_commit` is the single commit path behind every auto-committing
verb. It builds its pathspec from a hardcoded filename tuple
(`goc/engine.py:4569`):

```python
paths: list[str] = [
    str(p.relative_to(DECK_ROOT))
    for d in card_dirs
    for fname in ("README.md", "log.md")
    if (p := d / fname).exists()
]
```

Anything else in the card directory is invisible to it. The docstring is
candid about the mechanism — "Stage README.md + log.md across the given
card dirs and commit" (`goc/engine.py:4503`) — but no caller, and no
skill, tells the author that the rest of the directory is left behind.

That directly contradicts what `Skill(create-card)` requires of card
authors. Step 6:

> For bug / measurement / regression cards, ship a
> `deck/<title>/reproduce.py` that, on a clean checkout, prints output an
> outside reader would accept as proof.

and Step 7:

> When markdown can't express the content — colored option grids, state
> diagrams, interactive decision forms, screenshots — ship the artifact
> as a sibling file in the card directory and link it from the README.

So the documented card shape is "README + log + evidence", while the
engine's commit shape is "README + log". The gap is silent in the worst
way: the verb prints `committed`, the commit lands, and the card's
evidence is still untracked. A `reproduce.py` that never reaches the
remote is worse than none — the README quotes its output as proof and
tells the next reader to run a file that is not there.

Both `publish` and `done` are affected, so the gap spans the card
lifecycle: filing publishes a card whose evidence is missing, and closing
publishes a closure whose artifacts are missing.

## Empirical evidence

`uv run python .game-of-cards/deck/deck-auto-commit-ignores-card-files-other-than-readme-and-log/reproduce.py`
scaffolds a throwaway git repo, files a card, drops the mandated
`reproduce.py` sibling next to it, and runs `goc publish --commit`:

```
goc/engine.py _git_auto_commit stages a hardcoded filename pair
  'for fname in ("README.md", "log.md")' present : True

goc publish --commit output:
  [master 4be0b9a] deck: publish probe-card-with-a-sibling-artifact
   2 files changed, 19 insertions(+)
   create mode 100644 .game-of-cards/deck/probe-card-with-a-sibling-artifact/README.md
   create mode 100644 .game-of-cards/deck/probe-card-with-a-sibling-artifact/log.md
  probe-card-with-a-sibling-artifact: published (draft flag cleared); now visible in the queue
    committed

files in the commit goc publish created:
  .game-of-cards/deck/probe-card-with-a-sibling-artifact/README.md
  .game-of-cards/deck/probe-card-with-a-sibling-artifact/log.md
git status after the 'committed' message:
  ?? .game-of-cards/deck/probe-card-with-a-sibling-artifact/reproduce.py

sibling reproduce.py in the commit    : False
sibling reproduce.py left untracked   : True

DEFECT PRESENT — auto-commit reported success, evidence file untracked
```

This also reproduced in this repo, unprompted: `goc publish` on
[openclaw-plugin-manifest-config-options-do-not-behave-as-documented](../openclaw-plugin-manifest-config-options-do-not-behave-as-documented/)
committed 2 files and printed `committed`, leaving that card's
`reproduce.py` untracked until it was committed by hand.

## Why it matters

The reachability path is the ordinary filing flow, not an edge case.
`Skill(create-card)` Step 4 scaffolds the card, Step 6 writes
`reproduce.py`, and the author then either runs `goc publish` or claims
the card with `goc status <title> active` — both auto-commit. On any repo
with `workflow.auto_commit: true` (the configuration the deck's own
guidance recommends), the author sees `committed` and reasonably stops.
Nothing warns them. The evidence file survives only if someone notices
the stray `??` line in a later `git status`.

This is the second instance of one shape: **the engine treats a card
directory as exactly `README.md` + `log.md` and forgets the rest.** The
first is
[goc-migrate-silently-destroys-card-files-other-than-readme-and-log](../goc-migrate-silently-destroys-card-files-other-than-readme-and-log/),
where the same two-file assumption drives a byte-comparison that then
`rmtree`s legacy-only siblings. Two instances is not yet a family worth
an architectural meta-fix, but the two cards should be decided together
— a shared "what constitutes a card directory" helper would fix both,
and picking different answers in each place would be the worse outcome.
Deliberately filed as a separate card rather than an edge on the migrate
card: different verb, different failure mode (silent omission vs. data
loss), independently fixable.

## Decision required

The fix site is unambiguous — `_git_auto_commit` (`goc/engine.py:4569`),
so all seven callers inherit it. What to stage is the open question.

**Option A — stage the whole card directory.** Replace the filename loop
with the directory path (`git add -- <card_dir>`). Simplest, and matches
the mental model that a card *is* its directory. Risk: it sweeps in
anything that happens to sit there — `__pycache__/` and `*.pyc` from
running `reproduce.py`, editor swap files, downloaded screenshots kept
as scratch. A repo-level `.gitignore` handles the common droppings, but
goc cannot assume the consumer wrote one.

**Option B — allowlist by extension.** Stage `README.md`, `log.md`, plus
a documented set (`*.py`, `*.html`, `*.md`, `*.svg`, `*.png`). Keeps
control, but every new artifact kind needs an engine change — the same
hand-maintained-enumeration shape this deck already tracks elsewhere, and
the reason the current two-file tuple is a bug in the first place.

**Option C — whole directory minus a documented exclusion set.** Option A
with a small explicit denylist (`__pycache__/`, `*.pyc`, `.DS_Store`).
Gets A's "a card is its directory" semantics and closes A's main
practical hole. Costs one small constant that grows far more slowly than
B's allowlist.

**Recommendation: Option C**, with the exclusion set stated in
`Skill(card-schema)` so authors know what will and will not be committed.

Whichever is chosen, apply the *same* answer to
`goc-migrate-silently-destroys-card-files-other-than-readme-and-log`; a
shared helper naming the card-directory file set is the durable fix, and
it is what stops instance three.
