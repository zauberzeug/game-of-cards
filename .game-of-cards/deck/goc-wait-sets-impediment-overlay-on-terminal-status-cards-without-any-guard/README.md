---
title: goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard
summary: "`goc wait` lets a caller attach `waiting_on` / `waiting_until` to a card whose `status` is already terminal (`done`, `disproved`, `superseded`). Sibling mutation verbs (`decide`, `status`, `done`) all reject terminal targets; `wait` is the missing member of the family. `goc validate` does not flag the resulting contradictory overlay — `validate_waiting_overlay` skips terminal cards, so the bad state lives indefinitely."
status: open
stage: null
contribution: medium
created: "2026-05-29T15:56:05Z"
closed_at: null
human_gate: none
advances:
  - terminal-status-guard-missing-across-mutation-verbs
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] PROCESS: decision recorded in `## Decision required` — guard `goc wait` against terminal targets (the sibling-consistent option), allow with a "historical record" semantic, or split (allow `--clear` but reject `--reason`/`--until`).
  - [ ] TDD: `reproduce.py` exits non-zero — running `goc wait` against a terminal card no longer mutates the overlay (or behaves per the recorded decision).
  - [ ] MECHANICAL: `_cmd_wait` in `goc/engine.py` carries a `TERMINAL_STATUSES` guard mirroring `_cmd_decide` (engine.py:4958), with an error message naming the replacement path (file a new card; supersede if the closed card needs revisiting).
  - [ ] PROCESS: `validate_waiting_overlay` (engine.py:2271) decision recorded — either keep the terminal skip (now defensible because the setter refuses) or extend it to emit a `TERMINAL_OVERLAY` warning for legacy stragglers.
---

# `goc wait` sets an impediment overlay on a terminal-status card without any guard

## Location

`goc/engine.py:4310-4358` — `_cmd_wait`.

## What's broken

`_cmd_wait` mutates the frontmatter (`fm["waiting_on"]`, `fm["waiting_until"]`)
without ever checking the card's status. A `done`, `disproved`, or
`superseded` card silently gains a fresh impediment overlay that
contradicts its terminal state.

The full body of `_cmd_wait` (engine.py:4310-4358) has no
`TERMINAL_STATUSES` reference; the schema-validation branch checks the
reason enum and the date format, then writes:

```python
if new_reason is not None:
    fm["waiting_on"] = new_reason
if new_until is not None:
    fm["waiting_until"] = new_until
(card_dir / "README.md").write_text(emit_frontmatter(fm, body=body))
```

Compare the explicit guard in `_cmd_decide` at `engine.py:4557-4565`:

```python
if t.status in TERMINAL_STATUSES:
    print(
        f"ERROR: {title}: status is {t.status!r} (terminal); "
        f"`goc decide` records a *pending* decision — terminal cards "
        f"cannot be re-decided. To replace a recorded decision, file "
        f"a new card and link it via `goc status <old> superseded --by <new>`.",
        file=sys.stderr,
    )
    sys.exit(2)
```

`_cmd_status` (engine.py:5957+) and `_cmd_done` (engine.py:4853+) carry
analogous terminal-status guards. `_cmd_wait` is the sibling that was
overlooked when this family of guards was added.

The validator silently swallows the resulting contradiction.
`validate_waiting_overlay` (engine.py:1471) opens its loop with:

```python
for c in cards:
    if c.status in TERMINAL_STATUSES:
        continue
```

The terminal-skip is defensible *only* if the setter refuses to write
the overlay in the first place. Today, the setter writes it and the
validator looks away — the worst combination.

## Empirical evidence

```bash
cd $(mktemp -d) && git init -q
PYTHONPATH=<goc-repo> python3 -m goc.cli install
PYTHONPATH=<goc-repo> python3 -m goc.cli new test-card
PYTHONPATH=<goc-repo> python3 -m goc.cli status test-card disproved
PYTHONPATH=<goc-repo> python3 -m goc.cli wait test-card --reason external --until 2027-01-01
PYTHONPATH=<goc-repo> python3 -m goc.cli validate
```

Observed (run 2026-05-29 on `main`):

- `goc wait` exits zero. Output: `test-card: waiting_on='external' waiting_until='2027-01-01'`.
- Frontmatter now contains `status: disproved` AND `waiting_on: external`
  AND `waiting_until: 2027-01-01` — a closed card carrying a future-dated
  external wait.
- `goc validate` reports `OK  test-card`. The contradictory overlay is
  invisible to the auditor whose job is to catch this class of state.

A canonical `reproduce.py` will land at
`deck/<title>/reproduce.py` when the DoD's TDD line is implemented; the
recipe above is the script outline.

## Why it matters — reachability path

The overlay is the "can't *pull* yet" signal that
`pull-card`/`next-card`/`standup`/board-rendering all read. Terminal
cards are never pullable, so the overlay on a closed card is by
construction noise — but it persists in source control, ships to
consumers via `git pull`, and any downstream tool that reads the
overlay without re-checking status (the same shape that motivated
`board-paints-impediment-marker-on-terminal-cards-with-stale-overlay`)
will misbehave. That sibling fix preserved overlays that were *set
while the card was live* as a historical record; the present defect is
the inverse — overlays set *after* the card closed, which are not
history but contradiction.

Reachability: a session that closes a card and then runs `goc wait` on
it (typo, slug-collision, batch script, autonomous-loop misfire) is the
producing path. Per [board-paints-impediment-marker-on-terminal-cards-with-stale-overlay](../board-paints-impediment-marker-on-terminal-cards-with-stale-overlay/),
the closure verbs deliberately do NOT clear the overlay — so any later
`goc wait` call on the closed card is a write of fresh state that the
closure-as-historical-record contract does not endorse.

## Decision

*Resolved 2026-10-22T05:17:57Z:* Decided via parent terminal-status-guard-missing-across-mutation-verbs: option 1, strict terminal-status guard — goc wait refuses terminal targets for the setters and --clear alike; validate_waiting_overlay keeps its terminal skip

*Reasoning:* The maintainer approved the parent's recommended bundle in a human session on 2026-10-22, which resolves exactly this card's question; implement through the parent's shared _refuse_terminal_mutation helper, whose message is written fresh because _cmd_decide no longer refuses terminal cards

## Fix sketch (option 1)

After `t = load_card_or_exit(card_dir, title)` at `engine.py:4319`,
before any frontmatter read:

```python
if t.status in TERMINAL_STATUSES:
    print(
        f"ERROR: {title}: status is {t.status!r} (terminal); "
        f"`goc wait` records a *live-card* impediment — terminal "
        f"cards have no further work to wait on. To revisit a closed "
        f"card, file a new card and supersede via "
        f"`goc status <old> superseded --by <new>`.",
        file=sys.stderr,
    )
    sys.exit(2)
```

`reproduce.py` then exits non-zero on the same recipe above.
