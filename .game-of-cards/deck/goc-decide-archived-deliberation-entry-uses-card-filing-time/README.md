---
title: goc-decide-archived-deliberation-entry-uses-card-filing-time
summary: "`goc decide` stamps the archived `## Decision required` block it relocates to log.md with the card's `created` timestamp instead of the now-of-writing. Every other log writer in the engine uses `_utc_now_iso()`. When log.md already carries an intermediate entry (typical for `goc attest` between filing and decide), the archived header lands out of chronological order, falsifying the journal axis the deck depends on for reconstructing history."
status: open
stage: null
contribution: medium
created: "2026-05-30T08:15:40Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero (log.md headers are in chronological order after `goc decide` on a card whose log.md already has a later entry).
  - [ ] TDD: a regression test asserts that all `## YYYY-…Z:` headers appended by `_cmd_decide` use `_utc_now_iso()` at decide-time, not the card's `created` field.
  - [ ] MECHANICAL: `goc/engine.py:4593` (`filed = t.created or now`) is replaced per the recorded decision; if the original filing date is still desired in the body, it appears as inline prose, not as the header timestamp.
  - [ ] PROCESS: decision recorded in this card's `## Decision` section via `Skill(decide-card)`; rationale captured in log.md.
---

# goc-decide-archived-deliberation-entry-uses-card-filing-time

## Location

`goc/engine.py:4584-4608` — the `_cmd_decide` function, specifically
line 4593 (`filed = t.created or now`) and line 4595
(`f"## {filed}: decision deliberation archived\n\n..."`).

## What's broken

`_cmd_decide` writes two log.md entries on a single invocation: the
archived `## Decision required` block (when present) and the
`decision recorded` line. The two adjacent entries use different
time conventions:

```python
# goc/engine.py:4581-4608 (excerpt)
now = _utc_now_iso()
...
archived = extract_decision_required_section(body)
...
log_path = card_dir / "log.md"
existing = log_path.read_text() if log_path.exists() else ""
entries = []
if archived:
    filed = t.created or now                          # ← uses card's created field
    entries.append(
        f"## {filed}: decision deliberation archived\n\n"
        ...
    )
entries.append(
    f"## {now}: decision recorded\n\n"                # ← uses now-of-writing
    f"{decision} — {reasoning}. Gate {prior_gate} → none.\n"
)
sep = "\n\n" if existing.strip() else ""
log_path.write_text(existing.rstrip("\n") + sep + "\n\n".join(entries))
```

Every other log writer in the engine uses the now-of-writing
convention:

- `_cmd_attest` (`engine.py:3846, 3898-3901`) — `today = _utc_now_iso()`
- `_cmd_done` / `_cmd_done_bundle` (`engine.py:3260, 3283, 3344`) — `now = _utc_now_iso()`
- `_cmd_move` (`engine.py:4547-4551`) — `now = _utc_now_iso()`
- The sibling `decision recorded` entry one line below (line 4604)

The contradicted invariant is documented as
`Skill(card-schema)`'s "Deck as scheduler vs deck as record" — log.md
is the append-only journal whose chronological ordering lets a cold
reader reconstruct the history of a decision. The skill
`Skill(finish-card)` calls log.md "the journal — history." Stamping
the archival event with the card's filing date breaks that
reconstruction whenever any other entry has been written between
the filing and the decide.

## Empirical evidence

```
============================================================
log.md headers in file order:
  ## 2026-05-15T10:00:00Z: attestation run
  ## 2026-04-01T00:00:00Z: decision deliberation archived
  ## 2026-05-30T08:16:08Z: decision recorded
============================================================
FAIL: log.md headers are NOT in chronological order.

  earlier header (later in file):
    ## 2026-05-15T10:00:00Z: attestation run
  later header (earlier in file):
    ## 2026-04-01T00:00:00Z: decision deliberation archived

The 'decision deliberation archived' entry uses the card's
`created` timestamp instead of _utc_now_iso() at decide-time.
Cited code: goc/engine.py:4593 — `filed = t.created or now`
```

See [`reproduce.py`](reproduce.py).

## Why it matters / reachability path

Every card filed with `human_gate != none` (the schema default) is
reachable: parked at file-time, optionally attested while parked,
then decided via `Skill(decide-card)` / `goc decide`. The bug fires
whenever the card was filed before the decide call **and** any
intermediate entry has been written to log.md. The canonical path is:

1. `goc new <title> --gate decision` (writes `created: <T0>`)
2. (optional, common) `goc attest <title>` while parked — appends a
   header timestamped at `T1 > T0`.
3. `goc decide <title> --decision X --because Y` at `T2 > T1` —
   appends the archived block timestamped at `T0`, then the
   decision-recorded entry at `T2`. The middle header is older than
   either neighbour and is also older than its file-position
   predecessor.

When log.md has no intermediate entry (the common path for
non-attested cards decided shortly after filing), the resulting
ordering is still semantically wrong — the archival event happened
at `T2`, not `T0` — but the violation is invisible without an
intermediate writer. The bug nevertheless rewrites history: a reader
landing on log.md sees an event that did not occur on that date.

The defect was introduced by the fix card
`goc-decide-loses-deliberation-history-by-not-archiving-replaced-section`
(done), which added the archive-to-log behavior. The new entry was
stamped with the card's filing date — likely an attempt to preserve
"when was the deliberation originally framed" semantics in the
journal — but that information belongs in the entry body, not in
the header timestamp.

## Decision required

The header timestamp must record the write-of-archival event (now),
to align with every other log writer and preserve the journal's
chronological-ordering invariant. The open question is whether the
card's original `created` date is worth preserving inside the entry
body.

- **Option A — drop the filing date.** Replace
  `filed = t.created or now` with `now`. The entry header becomes
  `## {now}: decision deliberation archived`. The card's `created`
  field still exists in frontmatter for anyone who cares about
  filing-time.
  - Pros: minimal change; matches every sibling log writer; the
    archived section's content is unchanged.
  - Cons: a reader of log.md alone cannot tell when the deliberation
    was originally framed (they'd have to cross-reference the README
    frontmatter or `git log`).

- **Option B — keep the filing date in body prose.** Replace
  `filed = t.created or now` with `now` for the header, AND extend
  the archive-block body to mention the original filing date inline
  (e.g. "Archived from the README's `## Decision required` section
  (originally framed `{t.created}`) by `goc decide` ...").
  - Pros: same chronological correctness as A; preserves the
    "when was this first framed" signal inside the log entry itself.
  - Cons: slightly more text; introduces a redundant copy of
    `created` (frontmatter already has it). Adds a second template
    string the regression test must check.

Recommendation: **Option A** unless a concrete consumer of the
in-body filing date is identified. The `created` field in
frontmatter is the canonical source for filing time; duplicating it
inline risks the two values drifting if the card is `goc move`d or
its frontmatter is rewritten by a future tool.

## Fix

Change `goc/engine.py:4593` from:

```python
    if archived:
        filed = t.created or now
        entries.append(
            f"## {filed}: decision deliberation archived\n\n"
```

to (Option A):

```python
    if archived:
        entries.append(
            f"## {now}: decision deliberation archived\n\n"
```

or (Option B):

```python
    if archived:
        framed_note = f" (originally framed {t.created})" if t.created else ""
        entries.append(
            f"## {now}: decision deliberation archived\n\n"
            f"Archived from the README's `## Decision required` section{framed_note} by "
            ...
```

Add a regression test in `tests/` that calls `_cmd_decide` on a card
with `created: T0` and a pre-existing log.md entry at `T1 > T0`,
then asserts that every header timestamp in the resulting log.md is
≥ the previous header's timestamp.
