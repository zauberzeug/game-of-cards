---
title: install-docstring-still-claims-second-install-exits-clean
summary: "The `goc/install.py` module docstring promises second runs \"detect existing installs … and exit clean\", but the code refuses with `sys.exit(1)` and tests pin that refusal. The closed card `second-install-exits-nonzero` closed on the opposite contract (exit zero) and was silently reversed with no forward pointer — violating the closure-is-not-frozenness convention."
status: done
stage: null
contribution: low
created: "2026-07-19T04:08:07Z"
closed_at: "2026-07-22T00:57:17Z"
human_gate: none
advances: []
advanced_by: []
tags: [documentation, api-contract]
definition_of_done: |
  - [x] MECHANICAL: `goc/install.py` module docstring states the actual second-run contract (refuse with exit 1 + `goc upgrade` hint).
  - [x] MECHANICAL: closed card `second-install-exits-nonzero` amended with a forward pointer to this card (README note + `log.md` entry), per the closure-is-not-frozenness convention.
  - [x] MECHANICAL: grep confirms no other doc surface (templates, skills, READMEs) repeats the "exit clean"/exit-zero reinstall claim.
worker: {who: "claude[bot]", where: main}
---

# `install.py`'s docstring still claims a second install "exits clean" — the code refuses with exit 1

## Location

- `goc/install.py:11-12` — "Idempotent — second runs detect existing
  installs via `.game-of-cards/deck/.goc-version` (or legacy
  `deck/.goc-version`) and exit clean."
- `goc/install.py:1538-1544` — the actual behavior: prints
  "already installed (…)" + "Run `goc upgrade` to re-sync templates."
  and `sys.exit(1)`.
- `tests/test_install.py:~2070, ~2086` — tests assert the
  "already installed" refusal (current contract is deliberate).
- Closed card
  [second-install-exits-nonzero](../second-install-exits-nonzero/)
  (done 2026-05-05) — checked DoD items include "Re-running
  `goc install` in an already-installed repo exits zero when it makes
  no changes".

## What's broken

Three surfaces disagree. The module docstring and the closed card's
DoD both document an exit-zero idempotent reinstall; the shipped code
and its tests implement an exit-1 refusal with an upgrade hint. The
code+tests are the deliberate current contract (the refusal block even
carries a design comment about dry-run parity, `goc/install.py:1535-1537`),
which means the closed card's conclusion was reversed after closure
with no forward pointer — exactly the situation the
"closure is not frozenness" rule (AGENTS.md always-loaded rules;
`Skill(finish-card)` § After closure) says must leave a trail.

## Why it matters

An agent or script author reading the docstring (or the closed card)
will treat a non-zero exit from a second `goc install` as a failure
and retry or abort — the exact confusion the original card was filed
to fix, now reintroduced at the documentation layer. The fix is
mechanical: docs follow code.

## Fix (applied 2026-07-22)

1. Reworded the `goc/install.py` module docstring to state the refusal
   contract: second runs detect the existing install via the
   `.goc-version` sentinel, refuse with exit status 1 and a
   `goc upgrade` hint, and scripts should treat "already installed" as
   a refusal, not a crash. Plugin engine mirrors resynced via
   `scripts/sync_plugin_assets.py`.
2. Amended `second-install-exits-nonzero`: README carries a
   contract-reversed forward pointer to this card, and its (previously
   empty) `log.md` records when and why the exit-zero conclusion was
   reversed.
3. Swept the repo for other "exit clean"/exit-zero reinstall claims:
   the only remaining occurrences are historical deck-card records
   (`second-install-exits-nonzero`, `install-command-scaffolds-repo`),
   which are journal history, not live documentation.

No code change — `tests/test_install.py` pins the current behavior as
intended. (If a maintainer instead wants the exit-zero contract
restored, that is a new decision-gated card — the tests and the
refusal block's comment indicate the reversal was deliberate.)
