---
title: goc-triage-reports-no-parked-cards-in-a-repo-that-has-no-deck
summary: "In a repo with no deck, goc triage prints No parked cards and goc triage --json prints [], exit 0 with nothing on stderr. The missing-deck notice that every other read view prints, carrying the phrase the skill Preflights route to Skill(kickoff) on, was added to the default view only. scan-deck, which has no Preflight, runs goc triage first, so a deckless repo reads as one where nothing waits on the human."
status: active
stage: null
contribution: medium
created: "2026-11-16T01:20:11Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, unverified]
definition_of_done: |
  - [ ] EMPIRICAL: a `reproduce.py` runs `goc triage` and `goc triage --json` in a deckless scratch repo and checks stderr for `MISSING_DECK_PHRASE`, with the default view as the control. Run it on today's engine, record the verdict in log.md, and drop the `unverified` tag once it works.
  - [ ] TDD: if the hypothesis holds, `reproduce.py` exits 0 after the fix. Both triage forms print the same stderr notice as the default view, and exit 0 and the `[]` stdout of `--json` stay unchanged.
  - [ ] TDD: `tests/test_missing_deck_notice.py`, whose docstring already states the contract for every read view, covers `goc triage` and `goc triage --json`, and fails on today's engine.
worker: {who: "claude[bot]", where: main}
---

# `goc triage` reports no parked cards in a repo that has no deck

Parked as `unverified`. A hunter agent reproduced it during an audit-deck run,
and the auditing agent reproduced it again by hand (output below), but there
is no `reproduce.py` yet.

## Hypothesis

`974a1400` added the missing-deck notice so that a deckless repo stops
reading like an empty queue. Its commit message and the active card it served,
[denied-preamble-block-aborts-skill-load-before-the-preflight-routes-to-kickoff](../denied-preamble-block-aborts-skill-load-before-the-preflight-routes-to-kickoff/),
say that goc's read views name a missing deck on stderr. The notice was
wired into `_cmd_default` only (`goc/engine.py:4854-4855`):

```python
    if not DECK_DIR.exists():
        print(f"goc: {_missing_deck_message()}", file=sys.stderr)
```

`_cmd_triage` (`:7856`) reads `load_all_cards()`, which returns `[]` when
there is no deck (`:1222-1224`). It filters that empty list (`:7861`) and
prints `render_empty_triage_line(worker, hidden_drafts)` (`:7900`). That is
the line an empty park queue prints. `render_empty_triage_line`'s own
docstring (`:4400-4412`) calls the bug it was written to fix "Three unrelated
deck states then rendered byte-identically". The deckless repo is a fourth
state that still renders byte-identically.

The test module's docstring states the contract for every read view (`tests/test_missing_deck_notice.py:1`):

> A read view in a repo without a deck names the missing deck.

Its tests run only the default view and `--ready --json`.

## Falsification recipe

Run on 2026-11-16 against `main` at `ada1d2e7`, in a fresh `git init`
directory with no `.game-of-cards/`:

```
--- deckless: goc triage
No parked cards (status: open; gate ≠ none).
exit=0
--- deckless: goc triage --json
[]
--- deckless: goc (default view)
goc: no Game of Cards deck found from /tmp/c3 upward (no such file or directory: .game-of-cards/deck/). Run `goc install` at the intended project root first (agents: invoke Skill(kickoff)).
No cards match (status: open).
```

The hypothesis is falsified if `goc triage` (either form) prints the notice
on stderr.

## Why it matters

`Skill(scan-deck)` has no Preflight. Its default mode (`SKILL.md:32`) runs
`goc triage` first, to show what is waiting on the human, and its JSON mode
(`:67`) runs `goc triage --json`. In a repo without a deck, the first answer
the user gets is "nothing is parked", not "there is no deck here — run
kickoff". Mode A's follow-up `goc -v` does print the notice on stderr. So
the damage is a misleading first answer, not a silent dead end. That is why
this card is `medium`.

## Why deferred

The audit round filed its own card and parked the hunter's other candidates;
there was no budget for a `reproduce.py`. The fix is mechanical: print the
same notice from `_cmd_triage`, or move it into a helper every read view
calls. The second option keeps the next read view from missing it. The
active card above is held by another worker and its remaining DoD is about
the release, so this gap is filed separately rather than appended to that
card.

Surfaced by: the audit-deck hunter subagent (general-purpose, briefed on the
scheduler core: publish, claim, queue views).
