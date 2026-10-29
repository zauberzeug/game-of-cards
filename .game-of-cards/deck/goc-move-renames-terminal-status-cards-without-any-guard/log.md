## 2026-06-01T05:26:39Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

The cluster of unguarded mutation verbs has three documented fix shapes (see the sibling cards' decision sections). For `_cmd_move` specifically:

- **(a) Verb-level error**: `_cmd_move` loads the card via `load_card_or_exit`, checks `t.status in TERMINAL_STATUSES`, and rejects with a clear message pointing to the supersede workflow. Matches the post-fix `_cmd_decide` shape — fail loudly. Cost: a `goc move` on a closed card during a legitimate batch retitle (e.g. a deck-wide slug normalization) becomes a per-card override.
- **(b) Verb-level warning + `--force`**: `_cmd_move` warns when the target is terminal but proceeds, with a `--force` flag to silence the warning. Cost: defaulting to `proceed` keeps the silent-mutation hazard; the warning lives only in the operator's terminal scrollback.
- **(c) Verb-level error with `--force` escape hatch**: `_cmd_move` rejects on terminal status by default and accepts `--force` to bypass. Combines (a)'s defense-in-depth with (b)'s ergonomic escape for the deck-wide-rename case. Matches the `goc done` shape (`--force` bypasses DoD-checkbox enforcement for free-form DoD cards).

Recommendation: **(c)** — reject by default with `--force` to bypass. The kanban record-axis defaults to immutability; deliberate retitles of closed cards (slug normalization sweeps, post-hoc clarifications) are rare enough that an explicit `--force` per call is the right ergonomic. Aligns with the `goc done --force` precedent for the orthogonal DoD-enforcement bypass.

Independent of (a/b/c), record the chosen shape's interaction with the quality-pass subprocess (DoD step 4): does the new guard surface back through the subprocess exit code, and does `_apply_verdict_interactive`'s `r.returncode == 0` check at engine.py:4733 already DTRT (printing the failure to stderr and skipping the title-applied bookkeeping) or does it need its own log line clarifying that the closed-card path is the intended rejection rather than a generic move failure?


## 2026-10-22T05:17:58Z: decision recorded

Decided via parent terminal-status-guard-missing-across-mutation-verbs: (c) — reject terminal targets by default with a --force escape hatch; the quality-pass move subprocess inherits the rejection via the exit code — The maintainer approved the parent's recommended bundle in a human session on 2026-10-22, which resolves exactly this card's question; implement through the parent's shared _refuse_terminal_mutation helper, whose message is written fresh because _cmd_decide no longer refuses terminal cards. Gate decision → none.

## 2026-10-29T04:40:07Z — Closure

- **What changed**: `goc/engine.py:7300` — `_cmd_move` resolves the source card first and, unless `--force`, refuses a closed one through `_refuse_terminal_mutation(..., "move", override="--force")` (`:7316`), ahead of the new-title checks and `--dry-run`; `goc/engine.py:4491` — new `goc move --force`; `goc/engine.py:5631` — the shared helper gained a keyword-only `override`, so the `--force` hint lives in the one message rather than inline. `_apply_verdict_interactive` is unchanged: its `goc move` subprocess never passes `--force`, so it inherits the refusal. `Skill(refine-deck)`'s title-antipattern step now renames only unclosed cards' titles (a 20-byte edit: the core sits under a 15,300-byte cap with 68 bytes of headroom, so the `--force` explanation stays in the refusal message). `tests/test_terminal_status_guard.py` adds the helper, refusal, live-card, `--force` and quality-pass-inheritance tests; `_assert_refused` now snapshots the whole deck.
- **Verification**: `reproduce.py` exits 0 — the closed card is refused with exit 2, the deck byte-identical and `--force` named; the live card and the forced retitle both rename. Against the pre-fix engine it exits 1 (exit 0 with five deck paths changed, the open card's link rewritten). The new tests fail against the pre-fix engine (13 failures, 2 errors; the live-card control passes on both).
- **Reproducer contract**: the filed `reproduce.py` returned 0 on its defect-present branch and 1 once fixed, inverting the DoD's "exits zero". It was rewritten to 0 = defect no longer fires, 1 = fires, 2 = harness broken, with the paired positive cases the DoD asked for, and noted on `reproducers-can-exit-zero-while-their-defect-still-fires`.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1416 passed / 0 failed / 0 xfailed; `goc validate` exit 0; `sync_plugin_assets.py --check` and `port_skills_to_openclaw.py --check` clean

## Closure verification (2026-10-29T04:40:33Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-10-29 — Closure' present
