---
title: dry-run-plan-promises-full-install-that-the-real-run-refuses-as-already-installed
summary: "`install()` returned the dry-run plan before the `_find_installed_deck_dir` already-installed guard ran, so on a repo that already had GoC, `goc install --dry-run` printed a full write plan and exited 0 while the real run performed zero writes and exited 1 with \"already installed\". Fixed by moving the guard ahead of the dry-run short-circuit: the preview now reports the same refusal as the real run. Fifth instance of the dry-run/executor drift family."
status: done
stage: null
contribution: medium
created: "2026-07-06T01:20:22Z"
closed_at: "2026-07-07T01:46:22Z"
human_gate: none
advances:
  - dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py lands and exits non-zero on current code (dry-run predicts writes the real run refuses), zero after the fix; drop the `unverified` tag when it lands
  - [x] TDD: on an already-installed repo, `goc install --dry-run` reports the already-installed refusal (matching the real run) instead of a write plan
worker: {who: "claude[bot]", where: main}
---

# dry-run-plan-promises-full-install-that-the-real-run-refuses-as-already-installed

## Verdict

CONFIRMED and FIXED. `install()` in `goc/install.py` short-circuited on
`dry_run` *before* the `_find_installed_deck_dir` already-installed guard,
so on a repo that already had GoC installed, `goc install --dry-run`
printed `goc install (dry-run) — ... N writes planned` (exit 0) while the
real run performed zero writes and exited 1 with `already installed`.
`reproduce.py` in this card dir confirmed the drift (dry-run exit 0 with
an 18-write plan; real run exit 1) before the fix landed.

## Fix

The already-installed guard now runs before both `_plan_writes` and the
dry-run short-circuit, so the preview and the real run refuse identically
(same stderr message, same exit 1). Regression test:
`tests/test_install.py::ClaudeHarnessInstallTest::test_install_dry_run_reports_already_installed_refusal`.
`reproduce.py` exits 0 on the fixed code.

## Why it matters

The preview flow exists so agents/users can check what install would do
before doing it. In exactly the case where the answer matters most —
"does this repo already have GoC?" — the preview affirmed an install that
could not happen. This is the fifth instance of the
[dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting](../dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting/)
family (wired via `advances`): the hand-written plan path re-enumerates
executor conditionals and missed this guard entirely. Reachability: any
consumer running the documented `goc install --dry-run` in a repo carrying
`.game-of-cards/deck/.goc-version`.

## Distinct from existing cards

- [dry-run-plan-promises-pre-commit-append-that-real-install-skips-in-non-git-dir](../dry-run-plan-promises-pre-commit-append-that-real-install-skips-in-non-git-dir/)
  (done) — a different skipped conditional (non-git pre-commit append);
  the already-installed guard is not among the four instances enumerated
  on the meta card.
- [goc-upgrade-omits-pre-commit-hook-append-promised-by-dry-run](../goc-upgrade-omits-pre-commit-hook-append-promised-by-dry-run/)
  (done) — upgrade's plan path, different guard.
