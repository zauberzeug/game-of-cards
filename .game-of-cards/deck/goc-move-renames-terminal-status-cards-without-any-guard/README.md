---
title: goc-move-renames-terminal-status-cards-without-any-guard
summary: "`goc move <old> <new>` renamed a `done` / `disproved` / `superseded` card and rewrote every reference to its slug across the repo with no terminal-status check, retitling the deck's record — directly, or through the `goc move` subprocess that applies a `goc quality-pass --llm` title rewrite. Fixed 2026-10-29 per the parent epic's decision: `_cmd_move` refuses a closed card through the shared `_refuse_terminal_mutation` guard, ahead of the new-title checks and `--dry-run`, and `--force` renames one anyway for a deliberate correction of the record; the refusal names the flag. Last open child of `terminal-status-guard-missing-across-mutation-verbs`."
status: done
stage: null
contribution: medium
created: "2026-06-01T05:26:39Z"
closed_at: "2026-10-29T04:40:34Z"
human_gate: none
advances:
  - terminal-status-guard-missing-across-mutation-verbs
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [x] PROCESS: pick the guard shape from `## Decision required` and record the choice via `Skill(decide-card)` (lowers the gate to `none`). — decided 2026-10-22 via the parent epic: (c), reject unless `--force`.
  - [x] TDD: reproduce.py exits zero — a two-card fixture (one `done`, one `open`) runs `goc move <done> <new>` and the chosen guard either rejects with a non-zero exit + clear error (option a) or refuses to write while letting Layer-1 prose stay legible (option b); the done card's directory is unchanged on disk; the open-card rename path remains green via a paired positive case. — 2026-10-29: the decided (c) is (a)'s rejection plus `--force`, so the reproducer also requires the refusal to name `--force` and a forced rename of the closed card to succeed.
  - [x] MECHANICAL: implement the chosen guard in `goc/engine.py` (`_cmd_move`, now line 7300) and re-sync plugin mirrors via `python scripts/sync_plugin_assets.py`.
  - [x] PROCESS: sibling sweep — confirm `_apply_verdict_interactive` (now engine.py:5117) inherits the new guard via its `goc move` subprocess call (defense-in-depth — the parent quality-pass card has its own entry-point guard but the move subprocess hop is a second seam); add a regression test if the inheritance is not obvious from code reading. — confirmed: the subprocess never passes `--force`; pinned by `test_quality_pass_retitle_of_a_card_closed_mid_run_is_refused_by_move`.
  - [x] PROCESS: `uv run python -m unittest discover -s tests` stays green; `uv run goc validate` clean.
worker: {who: "claude[bot]", where: main}
---

# `goc move` renames terminal-status cards without any guard

## Location

- `goc/engine.py:7300` — `_cmd_move`, which renamed the card directory
  and ran the repo-wide reference rewrite (`_move_text_rewrite` /
  `_move_rewrite_tracked_files`, `goc/engine.py:7212` / `:7271`)
  without ever reading the card's status.
- `goc/engine.py:5117` — `_apply_verdict_interactive`, which applies a
  `goc quality-pass --llm` title rewrite by running `goc move` in a
  subprocess, so the unguarded verb was also the seam through which
  quality-pass could retitle a closed card.

## What was broken

`_cmd_move` never loaded the card it renamed. Its pre-mutation checks
were the jargon-antipattern guard and the title-pattern regex on the
*new* title, the self-rename guard, title containment, source-exists
and destination-does-not-exist. Then it ran `git mv` (falling back to
`shutil.move`) and `_move_rewrite_tracked_files`, which rewrites every
tracked text file naming the old slug:

```python
    if dst.exists():
        print(f"ERROR: {dst} already exists", file=sys.stderr)
        sys.exit(2)
    ...
    try:
        subprocess.run(["git", "mv", str(src), str(dst)], cwd=DECK_ROOT, check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        shutil.move(str(src), str(dst))
    _move_rewrite_tracked_files(old_title, new_title)
```

A `done` / `disproved` / `superseded` card was renamed exactly like a
live one. `_cmd_status` refuses every terminal card, and `goc wait`,
`goc attest` and `goc quality-pass`'s rewrite helpers adopted the
shared `_refuse_terminal_mutation` guard on 2026-10-24 and 2026-10-25.
That left `move` as the last member of the family with no guard.

## Empirical evidence

Reachable in two ways:

1. **Direct.** `uv run goc move <closed-title> <new-title>` printed
   `<old> → <new>` and exited 0. The closed card's directory name,
   frontmatter title and log.md heading changed, and so did every
   cross-reference to it in the tracked tree. The rewrites were left
   uncommitted, a separate defect tracked in
   `goc-move-leaves-cross-reference-rewrites-uncommitted`.
2. **Via quality-pass.** `_apply_verdict_interactive` shells out to
   `goc move` when the Sonnet pass proposes a title rewrite. The
   quality-pass card's DoD step 4 commissioned this audit because its
   own guards (the Layer-2 sample filter and the summary/DoD rewrite
   helpers) do not cover that subprocess hop.

`reproduce.py` (this directory) is the canonical reproducer. It runs
three scenarios, each against a fresh two-card deck holding a `done`
card and an `open` card whose body links to it:

- `goc move` on the closed card;
- `goc move` on the open card;
- `goc move --force` on the closed card.

On `main` before the fix (2026-10-29), the first scenario exited 0
with five deck paths changed: the closed card's two files moved to the
new directory and the open card's link was rewritten. The third failed with exit 2 because
`--force` was an unknown argument. After the fix, the first exits 2
with the deck byte-identical and a terminal refusal naming `--force` on
stderr, and the other two rename. Exit codes: 0 = defect no longer
fires, 1 = defect fires, 2 = harness or precondition broken.

## Why it matters

A closed card is the kanban system's durable artefact. It records the
title the work was filed under, and with it the slug, the directory
name, the URL fragments and every backref in the tracked tree. The
deck-as-record axis depends on stable identifiers: a reader following
a closed card's `superseded_by` pointer, or scanning `log.md` for
archived deliberation, expects the slug they were given to still
resolve. Silently retitling a closed card breaks every existing
pointer to it.

The same principle was codified in `closed-cards-stay-editable-with-cross-references`
(closed): *appending* to `log.md` when new evidence surfaces is
encouraged; silently rewriting the frontmatter contract is not. The
move verb goes further. Its reference-rewrite pass edits other cards'
bodies and arbitrary tracked files to substitute the new slug, so a
single `goc move` call on a closed card can rewrite history across the
whole repo.

## Decision

*Resolved 2026-10-22T05:17:58Z:* Decided via parent terminal-status-guard-missing-across-mutation-verbs: (c) — reject terminal targets by default with a --force escape hatch; the quality-pass move subprocess inherits the rejection via the exit code

*Reasoning:* The maintainer approved the parent's recommended bundle in a human session on 2026-10-22, which resolves exactly this card's question; implement through the parent's shared _refuse_terminal_mutation helper, whose message is written fresh because _cmd_decide has stopped refusing terminal cards

## Fix

Applied 2026-10-29 per the decision:

- **Guard.** `_cmd_move` resolves the source card first. Unless
  `--force` is passed, it calls
  `_refuse_terminal_mutation(load_card_or_exit(src, old_title), "move", override="--force")`
  (`goc/engine.py:7316`), which exits 2 with the whole deck
  byte-identical. The guard runs before the checks on the new title,
  because no new title could get a closed card past it: a jargon or
  malformed title would otherwise report an error the user fixes only
  to hit this one. It also runs before `--dry-run`, so the preview
  never lists a rename the real run would refuse.
- **Escape hatch.** `goc move --force` (`goc/engine.py:4491`) renames
  a closed card anyway, for a deliberate correction of the record such
  as a slug normalization. The rename appends its usual `renamed from`
  entry to the card's log.md, so the correction is itself on the
  record. `--force` bypasses only the status guard: the checks on the
  new title still apply, and `--allow-jargon` stays the only bypass
  for the antipattern one.
- **Message.** The parent's agreed shape puts the hint in the shared
  helper rather than inline. `_refuse_terminal_mutation`
  (`goc/engine.py:5631`) gained a keyword-only `override` that appends
  "`--force` overrides this refusal; keep it for a deliberate
  correction of the record." Verbs without an escape hatch pass none,
  so they are told of no flag they lack.
- **quality-pass inheritance.** `_apply_verdict_interactive` needed no
  change. Its `goc move` subprocess (`goc/engine.py:5129`) never passes
  `--force`, so the guard's exit 2 fails its `r.returncode == 0` check.
  The refusal is relayed verbatim as `move failed: ERROR: <title>:
  status is 'done' (terminal); ...`, and the title bookkeeping is
  skipped. That text already says the card is closed, which settles the
  decision-time question of whether the closed-card path needed its own
  log line. The path is reachable only for a card closed while the LLM
  call is in flight, because the Layer-2 sample already leaves closed
  cards out.
- **Skill.** `Skill(refine-deck)`'s title-antipattern step reads a
  `goc quality-pass --status all` report, which lists closed cards too.
  It now renames only unclosed cards' titles.
- **Tests.** `tests/test_terminal_status_guard.py` gains five tests:
  - The helper names an override only when it is given one.
  - `goc move` refuses every terminal status, plain, under `--dry-run`
    and with an invalid new title. The deck stays byte-identical and
    the refusal names `--force`. `_assert_refused` now snapshots the
    whole deck rather than the one card, because a move rewrites other
    cards' references.
  - A live card still renames.
  - `--force` renames each closed card and rewrites a reference to it.
  - A quality-pass title rewrite of a card closed mid-run is refused by
    move. A fake `claude` closes the card before it replies.

  Against the pre-fix engine every one of them except the live-card
  control fails, with 13 failures and 2 errors across their subtests.

## Sibling sweep

The same root cause, a mutation verb with no terminal-status guard,
was collected under the epic
[terminal-status-guard-missing-across-mutation-verbs](../terminal-status-guard-missing-across-mutation-verbs/),
which decided one shared guard for the whole family. This card was its
last open child:

- [goc-decide-accepts-decisions-on-already-closed-cards](../goc-decide-accepts-decisions-on-already-closed-cards/) (closed; decide's guard has since become a terminal gate-repair path)
- [goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard](../goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard/) (closed 2026-10-24; introduced the shared helper)
- [goc-attest-mutates-log-md-on-already-closed-cards](../goc-attest-mutates-log-md-on-already-closed-cards/) (closed 2026-10-25)
- [goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards](../goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards/) (closed 2026-10-25; its DoD step 4 commissioned this audit)
