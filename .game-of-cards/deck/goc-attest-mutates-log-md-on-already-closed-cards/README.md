---
title: goc-attest-mutates-log-md-on-already-closed-cards
summary: "`goc attest` is the only state-touching verb in the family (`done`, `decide`, `status`, `wait`) that does not refuse a terminal target. Running it on a `done` / `disproved` / `superseded` card writes a fresh `## Closure verification (<today>)` block into the closed card's `log.md`, vandalising the historical record and — when a layer-3 derived check fails on a year-old card whose closure heading no longer matches today's date — recording a `FAIL` line that contradicts the card's actual closure outcome."
status: open
stage: null
contribution: medium
created: "2026-05-29T18:08:20Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] PROCESS: decision recorded in `## Decision required` — guard `goc attest` against terminal targets (the sibling-consistent option), allow with a "re-attest is a no-op echo of the original" semantic, or split (re-attest passes by reading the already-recorded block instead of mutating).
  - [ ] TDD: `reproduce.py` exits zero — running `goc attest` against a closed card no longer mutates `log.md` (or behaves per the recorded decision).
  - [ ] MECHANICAL: `_cmd_attest` in `goc/engine.py` carries a `TERMINAL_STATUSES` guard mirroring `_cmd_decide` (engine.py:4556) and `_cmd_done` (engine.py:3243), with an error message naming the replacement path (re-open is forbidden; file a new card).
  - [ ] MECHANICAL: the misleading `Next: goc done <title> to close once all DoD items are ticked.` print at `engine.py:3899` is dropped on terminal-card paths (or removed entirely if the guard short-circuits before it runs).
  - [ ] PROCESS: `uv run goc validate` clean; full regression suite green.
---

# `goc attest` mutates `log.md` on already-closed cards

## Location

`goc/engine.py:3828-3899` — `_cmd_attest`.

The verb loads the card, iterates the configured layer-2 / layer-3
checks, then unconditionally writes the `## Closure verification`
block to `log.md`. It never reads `card.status` — `done`, `disproved`,
and `superseded` cards take the mutation just like an active one would.

```python
def _cmd_attest(args):
    """Run layer-2 + layer-3 closure checks; append "Closure verification" block to log.md."""
    title = args.title
    skips = args.skips
    non_interactive = args.non_interactive
    card_dir = DECK_DIR / title
    card = load_card_or_exit(card_dir, title)
    config = load_deck_config()
    all_cards = load_all_cards()
    today = _utc_now_iso()
    skips_set = set(skips)
    results: list[dict] = []
    any_failed = False
    # ... runs all configured checks ...

    log_path = card_dir / "log.md"
    block = _format_attestation_block(today, results)
    existing = log_path.read_text() if log_path.exists() else ""
    log_path.write_text((existing.rstrip() + "\n\n" + block) if existing.strip() else block)
    print(f"\nWrote attestation to {log_path}")

    if any_failed:
        print("\nERROR: attestation has failures; finish-card will block closure.", file=sys.stderr)
        sys.exit(2)
    print("\nAttestation OK.")
    print(f"Next: goc done {title} to close once all DoD items are ticked.")
```

The sibling state-touching verbs all refuse terminal targets:

- `_cmd_done` — `engine.py:3243` — `if prior in TERMINAL_STATUSES: ...`
- `_cmd_status` — `engine.py:3982` — `if prior in TERMINAL_STATUSES: ...`
- `_cmd_decide` — `engine.py:4556` — `if t.status in TERMINAL_STATUSES: ...`
- `_cmd_attest` — **no guard**.

(`_cmd_wait` is the other missing member of the family; see
[goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard](../goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard/).
This card is the `attest` sibling of that one.)

## Empirical evidence

`reproduce.py` builds a one-card deck containing a card with
`status: done` and `closed_at: 2026-01-02`, runs
`uv run goc attest dummy-closed-card --non-interactive`, then diffs
the card's `log.md`:

```
goc attest dummy-closed-card  (card status: done)
exit code: 2

--- log.md before ---
## 2026-01-02T00:00:00Z: closure

Closed.

--- log.md after ---
## 2026-01-02T00:00:00Z: closure

Closed.

## Closure verification (2026-05-29T18:09:09Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 1/1 ticked
- [ ] log-md-closure-entry FAIL — no '## 2026-05-29 — Closure' section

DEFECT CHECK
  card status:                       done (closed 2026-01-02)
  log.md mutated by attest verb:     True
  verb refused with terminal-guard:  False
```

The card was closed cleanly on 2026-01-02. After a stray `goc attest`
on 2026-05-29 it carries a spurious 2026-05-29 verification block
that records `log-md-closure-entry FAIL` — the derived check looks for
a `## <today> — Closure` heading, which obviously isn't there on a
year-old card. The historical record now reads as if attestation
re-failed long after closure.

## Why it matters

Three concrete harms:

1. **Log vandalism on a closed card.** A reader scanning a closed
   card's `log.md` expects the entries to date-sort chronologically
   from open → closure. A stray late-dated `## Closure verification`
   block tells the reader that closure was re-litigated, which it
   wasn't. The card-as-record axis (`Skill(card-schema)` "Deck as
   scheduler vs deck as record") relies on closed-card history being
   stable.

2. **False `FAIL` markers on a year-old closure.** The `log-md-closure-entry`
   derived check requires a `## <today> — Closure` heading in `log.md`.
   That heading only matches on the day the card actually closes — so
   re-attesting any closed card on a later date will always record a
   spurious `FAIL` for that check, contradicting the card's terminal
   status.

3. **Reachability path.** This is not a theoretical defect. The
   methodology hands agents a sequence: `attest` runs before `done`.
   An agent driven by `pull-card` or `/loop` can easily land on a
   card that was already closed by a parallel session (the soft
   `status: active` lock isn't a hard one) and run `attest` on it
   reflexively. `goc done` would have refused at line 3243; `goc
   attest` accepts.

Two recently-closed sibling cards establish the family contract:
[`goc-decide-accepts-decisions-on-already-closed-cards`](../goc-decide-accepts-decisions-on-already-closed-cards/)
added the guard to `_cmd_decide`; the deck rule "closed cards are
read-only for state-touching verbs" needs to extend to `_cmd_attest`
for sibling consistency.

## Decision required

Three coherent options:

1. **Refuse outright** (sibling-consistent, matches
   `_cmd_done` / `_cmd_status` / `_cmd_decide`). Run the
   `TERMINAL_STATUSES` guard at the top of `_cmd_attest` and exit 2
   with a message naming the replacement path (re-open is forbidden;
   if the closure outcome itself is wrong, file a new card and link
   via `goc status <old> superseded --by <new>`). Pros: matches the
   family. Cons: a caller who genuinely wants to *replay* the
   original attestation (e.g., a CI smoke check) loses that path.

2. **Allow with a "re-attest is read-only" semantic.** On a terminal
   card, print the previously-recorded `## Closure verification`
   block (if any) and exit 0 without writing anything new. Pros:
   keeps the verb usable as a query. Cons: bifurcates the verb's
   behavior by status, which is the same kind of split that
   `goc decide` rejected.

3. **Split into `goc attest` (mutating) and `goc attest --replay`
   (read-only).** Replay reads the existing block; the bare verb
   refuses terminal targets. Pros: clean separation. Cons: new
   surface area for a low-frequency need.

Option 1 is the default unless a caller surfaces a real use case
for replay. The `goc-wait` sibling card uses the same Option-1
default.

## Fix

For Option 1, insert a guard at the top of `_cmd_attest` mirroring
`_cmd_decide`:

```python
def _cmd_attest(args):
    title = args.title
    card_dir = DECK_DIR / title
    card = load_card_or_exit(card_dir, title)
    if card.status in TERMINAL_STATUSES:
        print(
            f"ERROR: {title}: status is {card.status!r} (terminal); "
            f"`goc attest` mutates `log.md` and is meaningful only for "
            f"pre-closure cards. To revisit a closed card's outcome, "
            f"file a new card and link via `goc status <old> superseded --by <new>`.",
            file=sys.stderr,
        )
        sys.exit(2)
    # ... rest of the function unchanged ...
```

Drop the misleading `Next: goc done <title> ...` print at line 3899
on the terminal-card path (the guard already short-circuits before
it, so no extra change needed — but make sure the message stays
inside the post-guard block).
