---
title: quality-pass-llm-calls-claude-to-audit-zero-cards
summary: "goc quality-pass --llm starts claude -p even when its selection holds no live card: an empty deck, a status filter that matches nothing, or --limit 0. The guard that skips Layer 2 when nothing is live sits inside the branch that reports skipped closed cards, so it fires only when closed cards were matched. Without claude the pass then exits 1 over nothing to audit, and with it the pass spends a Sonnet call on a prompt that lists no card."
status: done
stage: null
contribution: low
created: "2026-11-19T04:53:18Z"
closed_at: "2026-11-19T04:57:06Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits 0. With no deck, an empty deck, `--limit 0` and a `--status` filter that matches nothing, `goc quality-pass --llm --dry-run` never starts `claude` and exits 0. The control, one open card, still starts it once.
  - [x] TDD: `tests/test_quality_pass_llm_prompt_delivery.py` pins the same: no `claude` call for an empty selection, and exit 0 with no `claude` on PATH. The new cases fail on the engine before the fix.
  - [x] MECHANICAL: one guard on the selected sample covers every empty selection, and the all-closed path keeps its existing output. Plugin mirrors are re-synced.
worker: {who: "claude[bot]", where: main}
---

# `goc quality-pass --llm` calls `claude` to audit zero cards

Surfaced while fixing
[goc-quality-pass-reports-a-clean-deck-in-a-repo-that-has-no-deck](../goc-quality-pass-reports-a-clean-deck-in-a-repo-that-has-no-deck/):
`goc quality-pass --llm` in a repo with no deck went on to start `claude`.

## Location

At `12f1c755`, `goc/engine.py:5551-5562` in `_cmd_quality_pass`:

```python
    live = [c for c in cards if c.status not in TERMINAL_STATUSES]
    if len(live) < len(cards):
        closed = len(cards) - len(live)
        print(
            f"Layer-2 (Sonnet pass): skipping {closed} closed {_plural(closed, 'card')} — "
            f"a closed card is the deck's record, so Layer 2 never rewrites one."
        )
        if not live:
            return
    sample = live if limit is None else live[:limit]
    print(f"Layer-2 (Sonnet pass): auditing {len(sample)} {_plural(len(sample), 'card')} via `claude --model sonnet -p`…")
    prompt = _build_quality_prompt(sample)
```

`if not live: return` is the only check that stops Layer 2 when there is
nothing to audit, and it sits inside the branch that runs only when closed
cards were matched. When the selection matched nothing (`cards == []`), or
`--limit 0` cut the sample to nothing, the pass falls through to
`_run_sonnet_quality_pass` with a prompt that lists no card.

## Empirical evidence

`reproduce.py` on `12f1c755` uses a fake `claude` that is the only entry on
PATH, so no real `claude` is reached. The fake records each call:

```
--- control: one open card  exit=0  claude calls=1
--- no deck  exit=0  claude calls=1
    Layer-2 (Sonnet pass): auditing 0 cards via `claude --model sonnet -p`…
--- empty deck  exit=0  claude calls=1
    Layer-2 (Sonnet pass): auditing 0 cards via `claude --model sonnet -p`…
--- --limit 0  exit=0  claude calls=1
    Layer-2 (Sonnet pass): auditing 0 cards via `claude --model sonnet -p`…
--- --status active  exit=0  claude calls=1
    Layer-2 (Sonnet pass): auditing 0 cards via `claude --model sonnet -p`…

[FAIL] defect fires:
 - no deck: started `claude` 1x with no live card selected
 - empty deck: started `claude` 1x with no live card selected
 - --limit 0: started `claude` 1x with no live card selected
 - --status active: started `claude` 1x with no live card selected
```

With no `claude` on PATH, an empty deck ends in
`ERROR: cannot run claude: the `claude` CLI is not on PATH; …` and exit 1.

## Why it matters

The all-closed selection already skips the call
(`test_quality_pass_llm_over_only_closed_cards_never_calls_the_llm` in
`tests/test_terminal_status_guard.py`). Any other empty selection does not.
On a host with Claude Code it spends a Sonnet call, with its latency and cost,
on a prompt that holds only the instructions. Without Claude Code, or logged
out, a pass with nothing to audit fails with exit 1. A script that narrows the
pass with `--status` or samples with `--limit` then sees a failure caused only
by an empty selection.

## Fix

The guard now checks the sample, not the live list. Right after
`sample = live if limit is None else live[:limit]`, `_cmd_quality_pass`
returns when the sample is empty and prints
`Layer-2 (Sonnet pass): no live card selected, so there is nothing to audit.`
That covers no deck, an empty deck, a filter that matches nothing and
`--limit 0`. `claude` is neither started nor required, and the exit code is 0.
The all-closed case keeps its own skip line and nested return, so its output
is unchanged. After the fix, `reproduce.py` exits 0.

`tests/test_quality_pass_llm_prompt_delivery.py` gains
`test_an_empty_selection_never_starts_claude`, which walks the four empty
selections and then a one-card control that must start the fake once. It also
gains `test_an_empty_selection_needs_no_claude_on_path`. Both fail before the
fix.
