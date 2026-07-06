---
title: dry-run-plan-promises-full-install-that-the-real-run-refuses-as-already-installed
summary: "`install()` returns the dry-run plan before the `_find_installed_deck_dir` already-installed guard runs (install.py:1542-1552), so on a repo that already has GoC, `goc install --dry-run` prints a full write plan and exits 0 while the real run performs zero writes and exits 1 with \"already installed\". Fifth instance of the dry-run/executor drift family; parked unverified pending a reproduce.py."
status: open
stage: null
contribution: medium
created: "2026-07-06T01:20:22Z"
closed_at: null
human_gate: none
advances:
  - dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting
advanced_by: []
tags: [bug, api-contract, unverified]
definition_of_done: |
  - [ ] TDD: reproduce.py lands and exits non-zero on current code (dry-run predicts writes the real run refuses), zero after the fix; drop the `unverified` tag when it lands
  - [ ] TDD: on an already-installed repo, `goc install --dry-run` reports the already-installed refusal (matching the real run) instead of a write plan
---

# dry-run-plan-promises-full-install-that-the-real-run-refuses-as-already-installed

Parked `unverified`: surfaced and empirically exercised by the audit-round
hunter agent, but no committed `reproduce.py` this round. Hypothesis and
falsification recipe below.

## Hypothesis

`goc/install.py:1542-1552` — `install()` short-circuits on `dry_run`
*before* the already-installed guard:

```python
if dry_run:
    _print_plan("install", target, writes, agents)
    return

existing_dir = _find_installed_deck_dir(target)
if existing_dir is not None:
    existing = _detect_existing(existing_dir)
    rel = existing_dir.relative_to(target)
    print(f"already installed ({rel}/.goc-version → {existing})", file=sys.stderr)
    print("Run `goc upgrade` to re-sync templates.", file=sys.stderr)
    sys.exit(1)
```

On a repo that already has GoC installed, `goc install --dry-run` therefore
prints `goc install (dry-run) — ... N writes planned` and exits 0, while
`goc install` performs zero writes and exits 1 with `already installed`.
The `--dry-run` help text promises a preview of "planned writes"; planning
writes the real run can never perform breaks that contract.

## Why it matters

The preview flow exists so agents/users can check what install would do
before doing it. In exactly the case where the answer matters most —
"does this repo already have GoC?" — the preview affirms an install that
cannot happen. This is the fifth instance of the
[dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting](../dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting/)
family (wired via `advances`): the hand-written plan path re-enumerates
executor conditionals and misses this guard entirely. Reachability: any
consumer running the documented `goc install --dry-run` in a repo carrying
`.game-of-cards/deck/.goc-version`.

## Falsification recipe

In a temp dir containing only `.game-of-cards/deck/.goc-version` (any
version string), run `goc install --dry-run` then `goc install`. The
hypothesis is falsified if the dry-run already reports the
already-installed refusal (or plans zero writes); it is confirmed if the
dry-run prints a multi-write plan with exit 0 while the real run exits 1.
The hunter's in-round check observed: dry-run printed
`goc install (dry-run) — agents: claude — 18 writes planned` (exit 0);
real run printed `already installed (.game-of-cards/deck/.goc-version →
0.0.30)` (exit 1).

## Distinct from existing cards

- [dry-run-plan-promises-pre-commit-append-that-real-install-skips-in-non-git-dir](../dry-run-plan-promises-pre-commit-append-that-real-install-skips-in-non-git-dir/)
  (done) — a different skipped conditional (non-git pre-commit append);
  the already-installed guard is not among the four instances enumerated
  on the meta card.
- [goc-upgrade-omits-pre-commit-hook-append-promised-by-dry-run](../goc-upgrade-omits-pre-commit-hook-append-promised-by-dry-run/)
  (done) — upgrade's plan path, different guard.
