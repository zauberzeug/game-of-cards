---
title: goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards
summary: "`goc quality-pass --llm` sent closed cards to its Sonnet rewrite pass whenever `--status` selected them (`all`, `done`, `disproved`, `superseded`), and accepted verdicts — every one under `--yes` — rewrote their `summary` and DoD in place, retconning what a closed card was held to. Closed cards now stay out of the Layer-2 sample whatever `--status` says (Layer 1 still reports on them, read-only), and `_apply_summary_rewrite` / `_apply_dod_rewrite` re-read the card and refuse a closed one through the shared `_refuse_terminal_mutation` helper, which also catches a card closed while the pass runs."
status: done
stage: null
contribution: medium
created: "2026-05-29T18:59:23Z"
closed_at: "2026-10-25T04:52:03Z"
human_gate: none
advances:
  - terminal-status-guard-missing-across-mutation-verbs
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [x] PROCESS: pick the guard shape — (a) `_cmd_quality_pass` filters terminal-status cards out of the LLM sample regardless of `--status` value (Layer-1 antipattern scan still runs over them; Layer-2 LLM rewrites do not), OR (b) `_cmd_quality_pass` errors when `--llm` is combined with a `--status` value that selects terminal cards, OR (c) the mutation helpers (`_apply_summary_rewrite`, `_apply_dod_rewrite`) refuse with a clear error when the target card is terminal. Record the choice + reasoning in `## Decision required` (see body). — decided 2026-10-22 via the parent epic: (a) + (c) combined.
  - [x] TDD: reproduce.py exits zero — a two-card deck (one open, one done) runs `goc quality-pass --status all --llm --yes` with a stub Sonnet response that proposes summary + DoD rewrites for both cards; the open card is rewritten, the done card's `summary` and `definition_of_done` are unchanged on disk. — exits 0; against the pre-fix engine it exits 1 with both done-card fields rewritten. It now also exits 2 when the open card is not rewritten either, so a run that never reached the apply path cannot pass for a fix. `tests/test_terminal_status_guard.py` pins the same contract in CI.
  - [x] MECHANICAL: implement the chosen guard in `goc/engine.py` and re-sync plugin mirrors via `python scripts/sync_plugin_assets.py`. — (a) `_cmd_quality_pass` drops closed cards from the Layer-2 sample before `--limit` applies, prints a skip line, and makes no LLM call when every selected card is closed; (c) both rewrite helpers call `_refuse_terminal_mutation` on a fresh `load_card_or_exit` of the card before writing. Mirrors re-synced.
  - [x] PROCESS: sibling sweep — confirm `_cmd_move` (engine.py:6638) does or does not need its own terminal-status guard; file a follow-up card if the audit reveals `goc move` standalone is also unguarded (the quality-pass path invokes `move` via subprocess and would benefit from defense-in-depth). — `_cmd_move` is still unguarded (2026-10-25: `goc move` renamed a `done` card with exit 0); its follow-up is the already-filed `goc-move-renames-terminal-status-cards-without-any-guard`, so no new card.
  - [x] PROCESS: `uv run python -m unittest discover -s tests` stays green. — 1376 tests OK.
worker: {who: "claude[bot]", where: main}
---

# `goc quality-pass --llm` mutates summary and DoD on terminal-status cards

## Location

- `goc/engine.py` — `_cmd_quality_pass` (engine.py:5061), whose Layer-2
  sample was every card `--status` selected, closed ones included.
- `goc/engine.py` — `_apply_summary_rewrite` (engine.py:4950) and
  `_apply_dod_rewrite` (engine.py:4970), which rewrote a card's README
  without reading its status.
- `goc/engine.py` — `_apply_verdict_interactive` (engine.py:5008), the
  per-verdict accept/reject walk that calls both helpers, and `goc move`
  for a title rewrite.

## What was broken

`_cmd_quality_pass` loads the cards `--status` selects (default `open`),
reports Layer-1 title antipatterns and missing summaries over them, and
with `--llm` sent the same list to `claude --model sonnet -p`:

```python
cards = load_all_cards()
if status_flag != "all":
    cards = [c for c in cards if c.status == status_flag]
# ... Layer 1 ...
sample = cards if limit is None else cards[:limit]
```

With `--status all`, closed cards (`done`, `disproved`, `superseded`)
went into that sample; with `--status done`, `disproved` or
`superseded`, the sample was nothing but closed cards. Every accepted
verdict — all of them under `--yes` — then went through
`_apply_summary_rewrite` and `_apply_dod_rewrite`, which parse the
README, replace the field and write it back with no status check. A
maintainer running `goc quality-pass --status all --llm --yes` to tidy
the whole deck silently rewrote what its closed cards had been held to.

## Why it matters

A closed card is the deck's durable record: its summary and DoD state
what the work was contracted to deliver and what it met. Post-close
evidence goes into a new card, pointed to from the closed card's
`log.md` (`Skill(finish-card)` "After closure"), so a reader can follow
the thread without the contract itself being retconned. The Layer-2
rewrite path was that retcon. Layer 1 only reads, so it is safe over
any status.

## Empirical evidence

`reproduce.py` builds a two-card deck — one open, one done — and runs
`_cmd_quality_pass` with `--status all --llm --yes` against a stubbed
Sonnet reply that proposes a summary and a DoD rewrite for both. On
`main` before the fix (2026-10-25) both cards were rewritten:

```
done card summary mutated:    True
done card DoD mutated:        True
open card summary mutated:    True  (sanity: expected True)

FAIL: defect present — terminal-status card was mutated.
```

After the fix the done card's README is untouched and the open card is
still rewritten. Exit codes: 0 = defect no longer fires, 1 = defect
fires, 2 = harness broken (the open card was not rewritten either, so
the run never reached the apply path).

## Decision

*Resolved 2026-10-22T05:17:58Z:* Decided via parent terminal-status-guard-missing-across-mutation-verbs: (a) + (c) combined — filter terminal cards out of the Layer-2 LLM sample regardless of --status, and guard _apply_summary_rewrite / _apply_dod_rewrite

*Reasoning:* The maintainer approved the parent's recommended bundle in a human session on 2026-10-22, which resolves exactly this card's question; implement through the parent's shared _refuse_terminal_mutation helper, whose message is written fresh because _cmd_decide has stopped refusing terminal cards

## Fix

Applied 2026-10-25 per the decision:

- **(a) Sample filter.** `_cmd_quality_pass` drops closed cards from the
  Layer-2 sample whatever `--status` selected, before `--limit` caps
  it, and prints `Layer-2 (Sonnet pass): skipping N closed cards — …`.
  When every selected card is closed it stops there, without calling
  the LLM. Layer 1 still reports over every selected card. `--dry-run`
  skips closed cards too: a proposal that can never be applied costs
  tokens and shows nothing actionable. `goc quality-pass --help` says
  `--llm` skips closed cards.
- **(c) Helper guards.** `_apply_summary_rewrite` and
  `_apply_dod_rewrite` call `_refuse_terminal_mutation(load_card_or_exit(card.path, card.title), "quality-pass")`
  before writing, so any caller inherits the refusal: exit 2, README
  byte-identical. They re-read the card rather than trust the one they
  are handed. Quality-pass loads its sample before the LLM call and the
  accept/reject prompts, so a card closed in that window — by a
  parallel session, say — still reads as live in the caller's copy.
  With (a) in place, that window is the only way a closed card reaches
  the helpers today.
- **Tests.** `tests/test_terminal_status_guard.py` gains
  `QualityPassRewriteHelperTest` (both helpers refuse every terminal
  status; a card closed after the caller loaded it is refused; a live
  card is still rewritten) and two CLI tests that put a fake `claude`
  on PATH: `--status all --llm --yes` leaves the three closed cards
  byte-identical, keeps them out of the prompt and still rewrites the
  live card, and `--status done --llm --yes` never invokes `claude`.
  Against the pre-fix engine all 13 new subtests fail; the live-card
  control passes on both.

## Sibling sweep

- `goc move` (`_cmd_move`, engine.py:7077) still has no terminal-status
  guard: on 2026-10-25 `goc move done-card renamed-done-card` renamed a
  `done` card with exit 0. Quality-pass's title rewrite reaches `move`
  through a subprocess, but no longer for a closed card, since none
  enters the sample. The standalone verb is
  [goc-move-renames-terminal-status-cards-without-any-guard](../goc-move-renames-terminal-status-cards-without-any-guard/),
  already filed, so no new card. Per the parent's decision it gets a
  `--force` escape hatch.
- The other guarded members of the family adopted the same helper:
  [goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard](../goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard/)
  (closed 2026-10-24) and
  [goc-attest-mutates-log-md-on-already-closed-cards](../goc-attest-mutates-log-md-on-already-closed-cards/)
  (closed 2026-10-25). The family is coordinated by
  [terminal-status-guard-missing-across-mutation-verbs](../terminal-status-guard-missing-across-mutation-verbs/).
